import getpass
import json
import logging
import os
import ctk
import qt
import slicer
from slicer.ScriptedLoadableModule import *

import vtkSegmentationCorePython as vtkSegmentationCore
from DICOMSegmentationPlugin import DICOMSegmentationExporter
from SegmentStatistics import SegmentStatisticsParameterEditorDialog

from SlicerDevelopmentToolboxUtils.buttons import CrosshairButton
from SlicerDevelopmentToolboxUtils.buttons import RedSliceLayoutButton, FourUpLayoutButton, FourUpTableViewLayoutButton
from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS
from SlicerDevelopmentToolboxUtils.decorators import postCall
from SlicerDevelopmentToolboxUtils.helpers import WatchBoxAttribute
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.widgets import CopySegmentBetweenSegmentationsWidget
from SlicerDevelopmentToolboxUtils.widgets import DICOMBasedInformationWatchBox, ImportLabelMapIntoSegmentationWidget

from QRUtils.htmlReport import HTMLReportCreator
from QRUtils.testdata import TestDataLogic

from QRCustomizations.CustomSegmentEditor import CustomSegmentEditorWidget
from QRCustomizations.CustomDICOMDetailsWidget import CustomDICOMDetailsWidget


class QuantitativeReporting(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Quantitative Reporting"
    self.parent.categories = ["Informatics", "Quantification", "Segmentation"]
    self.parent.dependencies = ["SlicerDevelopmentToolbox"]
    self.parent.contributors = ["Christian Herz (SPL, BWH), Andrey Fedorov (SPL, BWH), "
                                "Csaba Pinter (Queen's), Andras Lasso (Queen's), Steve Pieper (Isomics)"]
    self.parent.helpText = """
    Segmentation-based measurements with DICOM-based import and export of the results.
    <a href="https://qiicr.gitbooks.io/quantitativereporting-guide">Documentation.</a>
    """
    self.parent.acknowledgementText = """
    This work was supported in part by the National Cancer Institute funding to the
    Quantitative Image Informatics for Cancer Research (QIICR) (U24 CA180918).
    """


class QuantitativeReportingWidget(ModuleWidgetMixin, ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.slicerTempDir = slicer.util.tempDirectory()
    slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, self.onSceneClosed)

  def initializeMembers(self):
    self.tableNode = None
    self.segmentationObservers = []
    self.dicomSegmentationExporter = None

  def enter(self):
    self.measurementReportSelector.setCurrentNode(None)
    self.segmentEditorWidget.editor.setSegmentationNode(None)
    self.segmentEditorWidget.editor.setMasterVolumeNode(None)
    self.segmentEditorWidget.editor.masterVolumeNodeChanged.connect(self.onImageVolumeSelected)
    self.segmentEditorWidget.editor.segmentationNodeChanged.connect(self.onSegmentationSelected)
    # self.setupDICOMBrowser()
    qt.QTimer.singleShot(0, lambda: self.updateSizes(self.tabWidget.currentIndex))

  def exit(self):
    self.segmentEditorWidget.editor.masterVolumeNodeChanged.disconnect(self.onImageVolumeSelected)
    self.segmentEditorWidget.editor.segmentationNodeChanged.disconnect(self.onSegmentationSelected)
    # self.removeDICOMBrowser()
    qt.QTimer.singleShot(0, lambda: self.tabWidget.setCurrentIndex(0))

  def onReload(self):
    self.cleanupUIElements()
    self.removeAllUIElements()
    super(QuantitativeReportingWidget, self).onReload()

  def onSceneClosed(self, caller, event):
    if hasattr(self, "watchBox"):
      self.watchBox.reset()
    if hasattr(self, "testArea"):
      self.retrieveTestDataButton.enabled = True

  def cleanupUIElements(self):
    self.removeSegmentationObserver()
    self.removeConnections()
    self.initializeMembers()

  def removeAllUIElements(self):
    for child in [c for c in self.parent.children() if not isinstance(c, qt.QVBoxLayout)]:
      try:
        child.delete()
      except AttributeError:
        pass

  def refreshUIElementsAvailability(self):

    def refresh():
      self.segmentEditorWidget.editor.masterVolumeNodeSelectorVisible = \
        self.measurementReportSelector.currentNode() and \
        not ModuleLogicMixin.getReferencedVolumeFromSegmentationNode(self.segmentEditorWidget.segmentationNode)
      masterVolume = self.segmentEditorWidget.masterVolumeNode
      self.importSegmentationCollapsibleButton.enabled = masterVolume is not None
      if not self.importSegmentationCollapsibleButton.collapsed:
        self.importSegmentationCollapsibleButton.collapsed = masterVolume is None

      self.importLabelMapCollapsibleButton.enabled = masterVolume is not None
      if not self.importLabelMapCollapsibleButton.collapsed:
        self.importLabelMapCollapsibleButton.collapsed = masterVolume is None
      if not self.tableNode:
        self.enableReportButtons(False)
        self.updateMeasurementsTable(triggered=True)

    qt.QTimer.singleShot(0, refresh)

  @postCall(refreshUIElementsAvailability)
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.initializeMembers()
    self.setupTabBarNavigation()
    self.setupWatchBox()
    self.setupViewSettingsArea()
    self.setupTestArea()
    self.setupSegmentationsArea()
    self.setupSelectionArea()
    self.setupImportArea()
    self.mainModuleWidgetLayout.addWidget(self.segmentationGroupBox)
    self.setupMeasurementsArea()
    self.setupActionButtons()

    self.setupConnections()
    self.layout.addStretch(1)
    self.fourUpSliceLayoutButton.checked = True

  def setupTabBarNavigation(self):
    self.tabWidget = qt.QTabWidget()
    self.layout.addWidget(self.tabWidget)

    self.mainModuleWidget = qt.QWidget()

    self.mainModuleWidgetLayout = qt.QGridLayout()

    self.mainModuleWidget.setLayout(self.mainModuleWidgetLayout)

    self.tabWidget.setIconSize(qt.QSize(85, 30))
    self.tabWidget.addTab(self.mainModuleWidget, 'QR')

  def setupDICOMBrowser(self):
    self.dicomBrowser = CustomDICOMDetailsWidget()
    self.dicomBrowser.addEventObserver(CustomDICOMDetailsWidget.FinishedLoadingEvent, self.onLoadingFinishedEvent)
    self.tabWidget.addTab(self.dicomBrowser, 'DICOM')

  def removeDICOMBrowser(self):
    if not self.dicomBrowser:
      return
    self.dicomBrowser.removeEventObserver(CustomDICOMDetailsWidget.FinishedLoadingEvent, self.onLoadingFinishedEvent)
    self.tabWidget.removeTab(self.tabWidget.indexOf(self.dicomBrowser))
    self.dicomBrowser = None

  def enableReportButtons(self, enabled):
    self.saveReportButton.enabled = enabled
    self.completeReportButton.enabled = enabled
    self.exportToHTMLButton.enabled = enabled

  def setupWatchBox(self):
    self.watchBoxInformation = [
      WatchBoxAttribute('StudyID', 'Study ID: ', DICOMTAGS.STUDY_ID),
      WatchBoxAttribute('PatientName', 'Patient Name: ', DICOMTAGS.PATIENT_NAME),
      WatchBoxAttribute('DOB', 'Date of Birth: ', DICOMTAGS.PATIENT_BIRTH_DATE),
      WatchBoxAttribute('Reader', 'Reader Name: ', callback=getpass.getuser)]
    self.watchBox = DICOMBasedInformationWatchBox(self.watchBoxInformation)
    self.mainModuleWidgetLayout.addWidget(self.watchBox)

  def setupTestArea(self):
    self.testArea = qt.QGroupBox("Test Area")
    self.testAreaLayout = qt.QFormLayout(self.testArea)
    self.retrieveTestDataButton = self.createButton("Retrieve and load test data")
    self.testAreaLayout.addWidget(self.retrieveTestDataButton)

    if self.developerMode:
      self.mainModuleWidgetLayout.addWidget(self.testArea)

  def loadTestData(self, collection="MRHead",
                   uid="2.16.840.1.113662.4.4168496325.1025306170.548651188813145058"):
    if not len(slicer.dicomDatabase.filesForSeries(uid)):
      sampleData = TestDataLogic.downloadAndUnzipSampleData(collection)
      TestDataLogic.importIntoDICOMDatabase(sampleData['volume'])
    self.loadSeries(uid)
    masterNode = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')[-1]
    tableNode = slicer.vtkMRMLTableNode()
    tableNode.SetAttribute("QuantitativeReporting", "Yes")
    slicer.mrmlScene.AddNode(tableNode)
    self.measurementReportSelector.setCurrentNode(tableNode)
    self.segmentEditorWidget.editor.setMasterVolumeNode(masterNode)
    self.retrieveTestDataButton.enabled = False

  def loadSeriesByFileName(self, filename):
    seriesUID = slicer.dicomDatabase.seriesForFile(filename)
    self.loadSeries(seriesUID)

  def loadSeries(self, seriesUID):
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
    dicomWidget.detailsPopup.offerLoadables(seriesUID, 'Series')
    dicomWidget.detailsPopup.examineForLoading()
    dicomWidget.detailsPopup.loadCheckedLoadables()

  def setupSelectionArea(self):
    self.segmentEditorWidget.editor.masterVolumeNodeSelectorAddAttribute("vtkMRMLScalarVolumeNode",
                                                                         "DICOM.instanceUIDs", None)
    self.measurementReportSelector = self.createComboBox(nodeTypes=["vtkMRMLTableNode", ""], showChildNodeTypes=False,
                                                         addEnabled=True, removeEnabled=True, noneEnabled=True,
                                                         selectNodeUponCreation=True,
                                                         toolTip="Select measurement report")
    self.measurementReportSelector.addAttribute("vtkMRMLTableNode", "QuantitativeReporting", "Yes")

    self.selectionAreaWidget = qt.QWidget()
    self.selectionAreaWidgetLayout = qt.QGridLayout()
    self.selectionAreaWidget.setLayout(self.selectionAreaWidgetLayout)

    self.selectionAreaWidgetLayout.addWidget(qt.QLabel("Measurement report"), 0, 0)
    self.selectionAreaWidgetLayout.addWidget(self.measurementReportSelector, 0, 1)
    self.mainModuleWidgetLayout.addWidget(self.selectionAreaWidget)

  def setupImportArea(self):
    self.setupImportSegmentation()
    self.setupImportLabelmap()

  def setupImportSegmentation(self):
    self.importSegmentationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.importSegmentationCollapsibleButton.collapsed = True
    self.importSegmentationCollapsibleButton.enabled = False
    self.importSegmentationCollapsibleButton.text = "Import from segmentation"
    self.importSegmentsCollapsibleLayout = qt.QGridLayout(self.importSegmentationCollapsibleButton)

    self.segmentImportWidget = CopySegmentBetweenSegmentationsWidget()
    self.segmentImportWidget.addEventObserver(self.segmentImportWidget.FailedEvent, self.onImportFailed)
    self.segmentImportWidget.currentSegmentationNodeSelectorEnabled = False
    self.importSegmentsCollapsibleLayout.addWidget(self.segmentImportWidget)
    self.mainModuleWidgetLayout.addWidget(self.importSegmentationCollapsibleButton)

  def setupImportLabelmap(self):
    self.importLabelMapCollapsibleButton = ctk.ctkCollapsibleButton()
    self.importLabelMapCollapsibleButton.collapsed = True
    self.importLabelMapCollapsibleButton.enabled = False
    self.importLabelMapCollapsibleButton.text = "Import from labelmap"
    self.importLabelMapCollapsibleLayout = qt.QGridLayout(self.importLabelMapCollapsibleButton)

    self.labelMapImportWidget = ImportLabelMapIntoSegmentationWidget()
    self.labelMapImportWidget.addEventObserver(self.labelMapImportWidget.FailedEvent, self.onImportFailed)
    self.labelMapImportWidget.addEventObserver(self.labelMapImportWidget.SuccessEvent, self.onLabelMapImportSuccessful)
    self.labelMapImportWidget.segmentationNodeSelectorVisible = False
    self.importLabelMapCollapsibleLayout.addWidget(self.labelMapImportWidget)
    self.mainModuleWidgetLayout.addWidget(self.importLabelMapCollapsibleButton)

  def onImportFailed(self, caller, event):
    slicer.util.errorDisplay("Import failed. Check console for details.")

  def onLabelMapImportSuccessful(self, caller, event):
    def hideAllLabels():
      # TODO: move up in SlicerDevelopmentToolbox
      for widget in self.getAllVisibleWidgets():
        compositeNode = widget.mrmlSliceCompositeNode()
        compositeNode.SetLabelVolumeID(None)

    hideAllLabels()

  def setupViewSettingsArea(self):
    self.redSliceLayoutButton = RedSliceLayoutButton()
    self.fourUpSliceLayoutButton = FourUpLayoutButton()
    self.fourUpSliceTableViewLayoutButton = FourUpTableViewLayoutButton()
    self.crosshairButton = CrosshairButton()
    self.crosshairButton.setSliceIntersectionEnabled(True)

    hbox = self.createHLayout([self.redSliceLayoutButton, self.fourUpSliceLayoutButton,
                               self.fourUpSliceTableViewLayoutButton, self.crosshairButton])
    self.mainModuleWidgetLayout.addWidget(hbox)

  def setupSegmentationsArea(self):
    self.segmentationGroupBox = qt.QGroupBox("Segmentations")
    self.segmentationGroupBoxLayout = qt.QFormLayout()
    self.segmentationGroupBox.setLayout(self.segmentationGroupBoxLayout)
    self.segmentEditorWidget = CustomSegmentEditorWidget(parent=self.segmentationGroupBox)
    self.segmentEditorWidget.setup()

  def setupMeasurementsArea(self):
    self.measurementsGroupBox = qt.QGroupBox("Measurements")
    self.measurementsGroupBox.setLayout(qt.QGridLayout())
    self.tableView = slicer.qMRMLTableView()
    self.tableView.setMinimumHeight(150)
    self.tableView.setMaximumHeight(150)
    self.tableView.setSelectionBehavior(qt.QTableView.SelectRows)
    self.tableView.horizontalHeader().setResizeMode(qt.QHeaderView.Stretch)
    self.fourUpTableView = None
    self.segmentStatisticsConfigButton = self.createButton("Segment Statistics Parameters")

    self.calculateMeasurementsButton = self.createButton("Calculate Measurements", enabled=False)
    self.calculateAutomaticallyCheckbox = qt.QCheckBox("Auto Update")
    self.calculateAutomaticallyCheckbox.checked = True

    self.measurementsGroupBox.layout().addWidget(self.tableView, 0, 0, 1, 2)
    self.measurementsGroupBox.layout().addWidget(self.segmentStatisticsConfigButton, 1, 0, 1, 2)
    self.measurementsGroupBox.layout().addWidget(self.calculateMeasurementsButton, 2, 0)
    self.measurementsGroupBox.layout().addWidget(self.calculateAutomaticallyCheckbox, 2, 1)

    self.mainModuleWidgetLayout.addWidget(self.measurementsGroupBox)

  def setupActionButtons(self):
    self.saveReportButton = self.createButton("Save Report")
    self.completeReportButton = self.createButton("Complete Report")
    self.exportToHTMLButton = self.createButton("Export to HTML")
    self.enableReportButtons(False)
    self.mainModuleWidgetLayout.addWidget(self.createHLayout([self.saveReportButton, self.completeReportButton,
                                                              self.exportToHTMLButton]))

  def setupConnections(self, funcName="connect"):

    def setupSelectorConnections():
      getattr(self.measurementReportSelector, funcName)('currentNodeChanged(vtkMRMLNode*)',
                                                        self.onMeasurementReportSelected)

    def setupButtonConnections():
      getattr(self.saveReportButton.clicked, funcName)(self.onSaveReportButtonClicked)
      getattr(self.completeReportButton.clicked, funcName)(self.onCompleteReportButtonClicked)
      getattr(self.calculateMeasurementsButton.clicked, funcName)(lambda: self.updateMeasurementsTable(triggered=True))
      getattr(self.segmentStatisticsConfigButton.clicked, funcName)(self.onEditParameters)
      getattr(self.exportToHTMLButton.clicked, funcName)(self.onExportToHTMLButtonClicked)
      getattr(self.retrieveTestDataButton.clicked, funcName)(lambda clicked: self.loadTestData())

    def setupOtherConnections():
      getattr(self.layoutManager.layoutChanged, funcName)(self.onLayoutChanged)
      getattr(self.layoutManager.layoutChanged, funcName)(self.setupFourUpTableViewConnection)
      getattr(self.calculateAutomaticallyCheckbox.toggled, funcName)(self.onCalcAutomaticallyToggled)
      getattr(self.segmentEditorWidget.editor.currentSegmentIDChanged, funcName)(self.onCurrentSegmentIDChanged)
      getattr(self.tableView.selectionModel().selectionChanged, funcName)(self.onSegmentSelectionChanged)
      getattr(self.tabWidget.currentChanged, funcName)(self.onTabWidgetClicked)

    setupSelectorConnections()
    setupButtonConnections()
    setupOtherConnections()

  def onEditParameters(self, calculatorName=None):
    """Open dialog box to edit calculator's parameters"""
    pNode = self.segmentEditorWidget.logic.segmentStatisticsLogic.getParameterNode()
    if pNode:
      SegmentStatisticsParameterEditorDialog.editParameters(pNode,calculatorName)
      self.updateMeasurementsTable(triggered=True)

  def onExportToHTMLButtonClicked(self):
    creator = HTMLReportCreator(self.segmentEditorWidget.segmentationNode, self.tableNode)
    creator.generateReport()

  def onTabWidgetClicked(self, currentIndex):
    if currentIndex == 0:
      slicer.app.layoutManager().parent().parent().show()
      self.dicomBrowser.close()
    elif currentIndex == 1:
      slicer.app.layoutManager().parent().parent().hide()
      self.dicomBrowser.open()

    qt.QTimer.singleShot(0, lambda: self.updateSizes(currentIndex))

  def updateSizes(self, index):
    mainWindow = slicer.util.mainWindow()
    dockWidget = slicer.util.findChildren(mainWindow, name='dockWidgetContents')[0]
    tempPolicy = dockWidget.sizePolicy
    if index==0:
      dockWidget.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Preferred)
    qt.QTimer.singleShot(0, lambda: dockWidget.setSizePolicy(tempPolicy))

  def onCurrentSegmentIDChanged(self, segmentID):
    if segmentID == '':
      return
    selectedRow = self.segmentEditorWidget.getSegmentIndexByID(segmentID)
    self.onSegmentSelected(selectedRow)

  def onSegmentSelectionChanged(self, itemSelection):
    selectedRow = itemSelection.indexes()[0].row() if len(itemSelection.indexes()) else None
    if selectedRow is not None:
      self.onSegmentSelected(selectedRow)

  def onSegmentSelected(self, index):
    segmentID = self.segmentEditorWidget.getSegmentIDByIndex(index)
    self.segmentEditorWidget.editor.setCurrentSegmentID(segmentID)
    self.selectRowIfNotSelected(self.tableView, index)
    self.selectRowIfNotSelected(self.fourUpTableView, index)
    self.segmentEditorWidget.onSegmentSelected(index)

  def selectRowIfNotSelected(self, tableView, selectedRow):
    if tableView:
      if len(tableView.selectedIndexes()):
        if tableView.selectedIndexes()[0].row() != selectedRow:
          tableView.selectRow(selectedRow)
      elif tableView.model().rowCount() > selectedRow:
        tableView.selectRow(selectedRow)

  def removeConnections(self):
    self.setupConnections(funcName="disconnect")
    if self.fourUpTableView:
      self.fourUpTableView.selectionModel().selectionChanged.disconnect(self.onSegmentSelectionChanged)

  def onCalcAutomaticallyToggled(self, checked):
    if checked and self.segmentEditorWidget.segmentation is not None:
      self.updateMeasurementsTable(triggered=True)
    self.calculateMeasurementsButton.enabled = not checked and self.tableNode

  def removeSegmentationObserver(self):
    if self.segmentEditorWidget.segmentation and len(self.segmentationObservers):
      while len(self.segmentationObservers):
        observer = self.segmentationObservers.pop()
        self.segmentEditorWidget.segmentation.RemoveObserver(observer)

  def setupFourUpTableViewConnection(self):
    if not self.fourUpTableView and self.layoutManager.layout == self.fourUpSliceTableViewLayoutButton.LAYOUT:
      if slicer.app.layoutManager().tableWidget(0):
        self.fourUpTableView = slicer.app.layoutManager().tableWidget(0).tableView()
        self.fourUpTableView.selectionModel().selectionChanged.connect(self.onSegmentSelectionChanged)
        self.fourUpTableView.setSelectionBehavior(qt.QTableView.SelectRows)

  def onLoadingFinishedEvent(self, caller, event):
    self.tabWidget.setCurrentIndex(0)

  def onLayoutChanged(self):
    self.onDisplayMeasurementsTable()
    self.onCurrentSegmentIDChanged(self.segmentEditorWidget.editor.currentSegmentID())

  @postCall(refreshUIElementsAvailability)
  def onSegmentationSelected(self, node):
    if not node:
      return
    masterVolume = ModuleLogicMixin.getReferencedVolumeFromSegmentationNode(node)
    if masterVolume:
      self.initializeWatchBox(masterVolume)

  @postCall(refreshUIElementsAvailability)
  def onImageVolumeSelected(self, node):
    self.seriesNumber = None
    self.initializeWatchBox(node)

  @postCall(refreshUIElementsAvailability)
  def onMeasurementReportSelected(self, node):
    # TODO check here if it's longitudinal data
    self.removeSegmentationObserver()
    self.segmentEditorWidget.editor.setMasterVolumeNode(None)
    self.calculateAutomaticallyCheckbox.checked = True
    self.tableNode = node
    self.hideAllSegmentations()
    if node is None:
      self.segmentEditorWidget.editor.setSegmentationNode(None)
      self.updateImportArea(None)
      self.watchBox.reset()
      return

    segmentationNode = self._getOrCreateSegmentationNodeAndConfigure()
    self.updateImportArea(segmentationNode)
    self._setupSegmentationObservers()
    self._configureReadWriteAccess()

  def _configureReadWriteAccess(self):
    if not self.tableNode:
      return
    if self.tableNode.GetAttribute("readonly"):
      logging.debug("Selected measurements report is readonly")
      self.setMeasurementsTable(self.tableNode)
      self.segmentEditorWidget.enabled = False
      self.enableReportButtons(False)
      self.calculateAutomaticallyCheckbox.enabled = False
      self.segmentStatisticsConfigButton.enabled = False
    else:
      self.segmentEditorWidget.enabled = True
      self.calculateAutomaticallyCheckbox.enabled = True
      self.segmentStatisticsConfigButton.enabled = True
      self.onSegmentationNodeChanged()
    self.exportToHTMLButton.enabled = True

  def _getOrCreateSegmentationNodeAndConfigure(self):
    segmentationNodeID = self.tableNode.GetAttribute('ReferencedSegmentationNodeID')
    logging.debug("ReferencedSegmentationNodeID {}".format(segmentationNodeID))
    if segmentationNodeID:
      segmentationNode = slicer.mrmlScene.GetNodeByID(segmentationNodeID)
    else:
      segmentationNode = self._createAndReferenceNewSegmentationNode()
    self._configureSegmentationNode(segmentationNode)
    return segmentationNode

  def _configureSegmentationNode(self, node):
    self.hideAllSegmentations()
    self.segmentEditorWidget.editor.setSegmentationNode(node)
    node.SetDisplayVisibility(True)

  def _createAndReferenceNewSegmentationNode(self):
    segmentationNode = self.createNewSegmentationNode()
    self.tableNode.SetAttribute('ReferencedSegmentationNodeID', segmentationNode.GetID())
    return segmentationNode

  def updateImportArea(self, node):
    self.segmentImportWidget.otherSegmentationNodeSelector.setCurrentNode(None)
    self.segmentImportWidget.setCurrentSegmentationNode(node)
    self.labelMapImportWidget.setSegmentationNode(node)

  def _setupSegmentationObservers(self):
    segNode = self.segmentEditorWidget.segmentation
    if not segNode:
      return
    segmentationEvents = [vtkSegmentationCore.vtkSegmentation.SegmentAdded,
                          vtkSegmentationCore.vtkSegmentation.SegmentRemoved,
                          vtkSegmentationCore.vtkSegmentation.SegmentModified,
                          vtkSegmentationCore.vtkSegmentation.RepresentationModified]
    for event in segmentationEvents:
      self.segmentationObservers.append(segNode.AddObserver(event, self.onSegmentationNodeChanged))

  def initializeWatchBox(self, node):
    if not node:
      self.watchBox.sourceFile = None
      return
    try:
      dicomFileName = slicer.dicomDatabase.fileForInstance(node.GetAttribute("DICOM.instanceUIDs").split(" ")[0])
      self.watchBox.sourceFile = dicomFileName
    except AttributeError:
      self.watchBox.sourceFile = None
      if slicer.util.confirmYesNoDisplay("The referenced master volume from the current segmentation is not of type "
                                         "DICOM. QuantitativeReporting will create a new segmentation node for the "
                                         "current measurement report. You will need to select a proper DICOM master "
                                         "volume in order to create a segmentation. Do you want to proceed?",
                                         detailedText="In some cases a non DICOM master volume was selected from the "
                                                      "SegmentEditor module itself. QuantitativeReporting currently "
                                                      "does not support non DICOM master volumes."):
        self._configureSegmentationNode(self._createAndReferenceNewSegmentationNode())
        self.segmentEditorWidget.editor.setMasterVolumeNode(None)
      else:
        self.measurementReportSelector.setCurrentNode(None)

  def createNewSegmentationNode(self):
    return slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")

  @postCall(refreshUIElementsAvailability)
  def onSegmentationNodeChanged(self, observer=None, caller=None):
    self.enableReportButtons(True)
    self.updateMeasurementsTable()

  def updateMeasurementsTable(self, triggered=False, visibleOnly=False):
    if not self.calculateAutomaticallyCheckbox.checked and not triggered:
      self.tableView.setStyleSheet("QTableView{border:2px solid red;};")
      return
    table = self.segmentEditorWidget.calculateSegmentStatistics(self.tableNode, visibleOnly)
    self.setMeasurementsTable(table)

  def setMeasurementsTable(self, table):
    if table:
      self.tableNode = table
      self.tableNode.SetLocked(True)
      self.tableView.setMRMLTableNode(self.tableNode)
      self.tableView.setStyleSheet("QTableView{border:none};")
    else:
      if self.tableNode:
        self.tableNode.RemoveAllColumns()
      self.tableView.setMRMLTableNode(self.tableNode if self.tableNode else None)
    self.onDisplayMeasurementsTable()

  def onDisplayMeasurementsTable(self):
    self.tableView.visible = not self.layoutManager.layout == self.fourUpSliceTableViewLayoutButton.LAYOUT
    if self.layoutManager.layout == self.fourUpSliceTableViewLayoutButton.LAYOUT and self.tableNode:
      slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveTableID(self.tableNode.GetID())
      slicer.app.applicationLogic().PropagateTableSelection()

  def onSaveReportButtonClicked(self):
    success, err = self.saveReport()
    self.saveReportButton.enabled = not success
    if success:
      slicer.util.infoDisplay("Report successfully saved into SlicerDICOMDatabase")
    if err:
      slicer.util.warningDisplay(err)

  def onCompleteReportButtonClicked(self):
    success, err = self.saveReport(completed=True)
    self.saveReportButton.enabled = not success
    self.completeReportButton.enabled = not success
    if success:
      slicer.util.infoDisplay("Report successfully completed and saved into SlicerDICOMDatabase")
      self.tableNode.SetAttribute("readonly", "Yes")
    else:
      slicer.util.warningDisplay(err)

  def saveReport(self, completed=False):
    try:
      self.dicomSegmentationExporter = DICOMSegmentationExporter(self.segmentEditorWidget.segmentationNode)
      segFilename = "quantitative_reporting_export.SEG" + self.dicomSegmentationExporter.currentDateTime + ".dcm"
      dcmSegmentationPath = os.path.join(self.dicomSegmentationExporter.tempDir, segFilename)
      self.createSEG(dcmSegmentationPath)
      self.createDICOMSR(dcmSegmentationPath, completed)
      self.addProducedDataToDICOMDatabase()
    except (RuntimeError, ValueError, AttributeError) as exc:
      return False, exc.message
    finally:
      self.cleanupTemporaryData()
    return True, None

  def createSEG(self, dcmSegmentationPath):
    segmentIDs = None
    if self.segmentEditorWidget.hiddenSegmentsAvailable():
      if not slicer.util.confirmYesNoDisplay("Hidden segments have been found. Do you want to export them as well?"):
        self.updateMeasurementsTable(visibleOnly=True)
        visibleSegments = self.segmentEditorWidget.logic.getVisibleSegments(self.segmentEditorWidget.segmentationNode)
        segmentIDs = [segment.GetName() for segment in visibleSegments]
    try:
      try:
        self.dicomSegmentationExporter.export(os.path.dirname(dcmSegmentationPath),
                                              os.path.basename(dcmSegmentationPath), segmentIDs=segmentIDs)
      except DICOMSegmentationExporter.EmptySegmentsFoundError:
        raise ValueError("Empty segments found. Please make sure that there are no empty segments.")
      logging.debug("Saved DICOM Segmentation to {}".format(dcmSegmentationPath))
      slicer.dicomDatabase.insert(dcmSegmentationPath)
      logging.info("Added segmentation to DICOM database (%s)", dcmSegmentationPath)
    except (DICOMSegmentationExporter.NoNonEmptySegmentsFoundError, ValueError) as exc:
      raise ValueError(exc.message)

  def createDICOMSR(self, referencedSegmentation, completed):
    data = self.dicomSegmentationExporter.getSeriesAttributes()
    data["SeriesDescription"] = "Measurement Report"

    compositeContextDataDir, data["compositeContext"] = \
      os.path.dirname(referencedSegmentation), [os.path.basename(referencedSegmentation)]
    imageLibraryDataDir, data["imageLibrary"] = \
      self.dicomSegmentationExporter.getDICOMFileList(self.segmentEditorWidget.masterVolumeNode)
    data.update(self._getAdditionalSRInformation(completed))

    data["Measurements"] = \
      self.segmentEditorWidget.logic.segmentStatisticsLogic.generateJSON4DcmSR(referencedSegmentation,
                                                                               self.segmentEditorWidget.masterVolumeNode)
    logging.debug("DICOM SR Metadata output:")
    logging.debug(json.dumps(data, indent=2, separators=(',', ': ')))

    metaFilePath = self.saveJSON(data, os.path.join(self.dicomSegmentationExporter.tempDir, "sr_meta.json"))
    outputSRPath = os.path.join(self.dicomSegmentationExporter.tempDir, "sr.dcm")

    params = {"metaDataFileName": metaFilePath,
              "compositeContextDataDir": compositeContextDataDir,
              "imageLibraryDataDir": imageLibraryDataDir,
              "outputFileName": outputSRPath}

    logging.debug(params)
    cliNode = None
    cliNode = slicer.cli.run(slicer.modules.tid1500writer, cliNode, params, wait_for_completion=True)
    waitCount = 0
    while cliNode.IsBusy() and waitCount < 20:
      slicer.util.delayDisplay("Running SR Encoding... %d" % waitCount, 1000)
      waitCount += 1

    if cliNode.GetStatusString() != 'Completed':
      raise Exception("tid1500writer CLI did not complete cleanly")

  def addProducedDataToDICOMDatabase(self):
    indexer = ctk.ctkDICOMIndexer()
    indexer.addDirectory(slicer.dicomDatabase, self.dicomSegmentationExporter.tempDir, "copy")  # TODO: doesn't really expect a destination dir

  def cleanupTemporaryData(self):
    if self.dicomSegmentationExporter:
      self.dicomSegmentationExporter.cleanup()
    self.dicomSegmentationExporter = None

  def _getAdditionalSRInformation(self, completed=False):
    data = dict()
    data["observerContext"] = {"ObserverType": "PERSON",
                               "PersonObserverName": self.watchBox.getAttribute("Reader").value}
    data["VerificationFlag"] = "VERIFIED" if completed else "UNVERIFIED"
    data["CompletionFlag"] = "COMPLETE" if completed else "PARTIAL"
    data["activitySession"] = "1"
    data["timePoint"] = "1"
    return data

  def saveJSON(self, data, destination):
    with open(os.path.join(destination), 'w') as outfile:
      json.dump(data, outfile, indent=2)
    return destination


class QuantitativeReportingSlicelet(qt.QWidget, ModuleWidgetMixin):

  def __init__(self):
    qt.QWidget.__init__(self)
    self.mainWidget = qt.QWidget()
    self.mainWidget.objectName = "qSlicerAppMainWindow"
    self.mainWidget.setLayout(qt.QHBoxLayout())

    self.setupLayoutWidget()

    self.moduleFrame = qt.QWidget()
    self.moduleFrame.setLayout(qt.QVBoxLayout())
    self.widget = QuantitativeReportingWidget(self.moduleFrame)
    self.widget.setup()

    # TODO: resize self.widget.parent to minimum possible width

    self.scrollArea = qt.QScrollArea()
    self.scrollArea.setWidget(self.widget.parent)
    self.scrollArea.setWidgetResizable(True)
    self.scrollArea.setMinimumWidth(self.widget.parent.minimumSizeHint.width())

    self.splitter = qt.QSplitter()
    self.splitter.setOrientation(qt.Qt.Horizontal)
    self.splitter.addWidget(self.scrollArea)
    self.splitter.addWidget(self.layoutWidget)
    self.splitter.splitterMoved.connect(self.onSplitterMoved)

    self.splitter.setStretchFactor(0,0)
    self.splitter.setStretchFactor(1,1)
    self.splitter.handle(1).installEventFilter(self)

    self.mainWidget.layout().addWidget(self.splitter)
    self.mainWidget.show()

  def setupLayoutWidget(self):
    self.layoutWidget = qt.QWidget()
    self.layoutWidget.setLayout(qt.QHBoxLayout())
    layoutWidget = slicer.qMRMLLayoutWidget()
    layoutManager = slicer.qSlicerLayoutManager()
    layoutManager.setMRMLScene(slicer.mrmlScene)
    layoutManager.setScriptedDisplayableManagerDirectory(slicer.app.slicerHome + "/bin/Python/mrmlDisplayableManager")
    layoutWidget.setLayoutManager(layoutManager)
    slicer.app.setLayoutManager(layoutManager)
    layoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    self.layoutWidget.layout().addWidget(layoutWidget)

  def eventFilter(self, obj, event):
    if event.type() == qt.QEvent.MouseButtonDblClick:
      self.onSplitterClick()

  def onSplitterMoved(self, pos, index):
    vScroll = self.scrollArea.verticalScrollBar()
    print self.moduleFrame.width, self.widget.parent.width, self.scrollArea.width, vScroll.width
    vScrollbarWidth = 4 if not vScroll.isVisible() else vScroll.width + 4 # TODO: find out, what is 4px wide
    if self.scrollArea.minimumWidth != self.widget.parent.minimumSizeHint.width() + vScrollbarWidth:
      self.scrollArea.setMinimumWidth(self.widget.parent.minimumSizeHint.width() + vScrollbarWidth)

  def onSplitterClick(self):
    if self.splitter.sizes()[0] > 0:
      self.splitter.setSizes([0, self.splitter.sizes()[1]])
    else:
      minimumWidth = self.widget.parent.minimumSizeHint.width()
      self.splitter.setSizes([minimumWidth, self.splitter.sizes()[1]-minimumWidth])


if __name__ == "QuantitativeReportingSlicelet":
  import sys
  print( sys.argv )

  slicelet = QuantitativeReportingSlicelet()
