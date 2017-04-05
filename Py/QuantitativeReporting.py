import getpass
import json
import logging, os
from datetime import datetime

from slicer.ScriptedLoadableModule import *
import vtkSegmentationCorePython as vtkSegmentationCore

from SlicerProstateUtils.mixins import *
from SlicerProstateUtils.decorators import *
from SlicerProstateUtils.helpers import WatchBoxAttribute, DICOMBasedInformationWatchBox
from SlicerProstateUtils.constants import DICOMTAGS
from SlicerProstateUtils.buttons import *

from SegmentEditor import SegmentEditorWidget
from SegmentStatistics import SegmentStatisticsLogic

from DICOMLib.DICOMWidgets import DICOMDetailsWidget


class QuantitativeReporting(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Quantitative Reporting"
    self.parent.categories = ["Informatics"]
    self.parent.dependencies = ["SlicerProstate"]
    self.parent.contributors = ["Christian Herz (SPL), Andrey Fedorov (SPL, BWH), "
                                "Csaba Pinter (Queen's), Andras Lasso (Queen's), Steve Pieper (Isomics)"]
    self.parent.helpText = """
    Segmentation-based measurements with DICOM-based import and export of the results.
    <a href="https://qiicr.gitbooks.io/quantitativereporting-guide">Documentation.</a>
    """  # TODO:
    self.parent.acknowledgementText = """
    This work was supported in part by the National Cancer Institute funding to the
    Quantitative Image Informatics for Cancer Research (QIICR) (U24 CA180918).
    """  # TODO: replace with organization, grant and thanks.


class QuantitativeReportingWidget(ModuleWidgetMixin, ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.segmentationsLogic = slicer.modules.segmentations.logic()
    self.slicerTempDir = slicer.util.tempDirectory()

  def initializeMembers(self):
    self.tableNode = None
    self.segmentationObservers = []

  def onReload(self):
    self.cleanupUIElements()
    self.removeAllUIElements()
    super(QuantitativeReportingWidget, self).onReload()

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
    self.imageVolumeSelector.enabled = self.measurementReportSelector.currentNode() is not None \
                                       and not self.getReferencedVolumeFromSegmentationNode(self.segmentEditorWidget.segmentationNode)
    self.segmentationGroupBox.enabled = self.imageVolumeSelector.currentNode() is not None
    self.measurementsGroupBox.enabled = len(self.segmentEditorWidget.segments)
    if not self.tableNode:
      self.enableReportButtons(False)
      self.updateMeasurementsTable(triggered=True)

  @postCall(refreshUIElementsAvailability)
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.initializeMembers()
    self.setupTabBarNavigation()
    self.setupWatchbox()
    self.setupViewSettingsArea()
    self.setupTestArea()
    self.setupSegmentationsArea()
    self.setupSelectionArea()
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
    self.dicomBrowser = CustomDICOMDetailsWidget()
    self.dicomBrowser.addEventObserver(CustomDICOMDetailsWidget.FinishedLoadingEvent, self.onLoadingFinishedEvent)
    self.tabWidget.addTab(self.dicomBrowser, 'DICOM')

  def enableReportButtons(self, enabled):
    self.saveReportButton.enabled = enabled
    self.completeReportButton.enabled = enabled

  def setupWatchbox(self):
    self.watchBoxInformation = [
      WatchBoxAttribute('StudyID', 'Study ID: ', DICOMTAGS.STUDY_ID),
      WatchBoxAttribute('PatientName', 'Patient Name: ', DICOMTAGS.PATIENT_NAME),
      WatchBoxAttribute('DOB', 'Date of Birth: ', DICOMTAGS.PATIENT_BIRTH_DATE),
      WatchBoxAttribute('Reader', 'Reader Name: ', callback=getpass.getuser)]
    self.watchBox = DICOMBasedInformationWatchBox(self.watchBoxInformation)
    self.mainModuleWidgetLayout.addWidget(self.watchBox)

  def setupTestArea(self):

    def loadTestData():
      mrHeadSeriesUID = "2.16.840.1.113662.4.4168496325.1025306170.548651188813145058"
      if not len(slicer.dicomDatabase.filesForSeries(mrHeadSeriesUID)):
        from SEGExporterSelfTest import SEGExporterSelfTestLogic
        sampleData = SEGExporterSelfTestLogic.downloadSampleData()
        unzipped = SEGExporterSelfTestLogic.unzipSampleData(sampleData)
        SEGExporterSelfTestLogic.importIntoDICOMDatabase(unzipped)
      self.loadSeries(mrHeadSeriesUID)
      masterNode = slicer.util.getNode('2: SAG*')
      tableNode = slicer.vtkMRMLTableNode()
      tableNode.SetAttribute("QuantitativeReporting", "Yes")
      slicer.mrmlScene.AddNode(tableNode)
      self.measurementReportSelector.setCurrentNode(tableNode)
      self.imageVolumeSelector.setCurrentNode(masterNode)
      self.retrieveTestDataButton.enabled = False

    self.testArea = qt.QGroupBox("Test Area")
    self.testAreaLayout = qt.QFormLayout(self.testArea)
    self.retrieveTestDataButton = self.createButton("Retrieve and load test data")
    self.testAreaLayout.addWidget(self.retrieveTestDataButton)
    self.retrieveTestDataButton.clicked.connect(loadTestData)
    self.mainModuleWidgetLayout.addWidget(self.testArea)

  def loadSeriesByFileName(self, filename):
    seriesUID = slicer.dicomDatabase.seriesForFile(filename)
    self.loadSeries(seriesUID)

  def loadSeries(self, seriesUID):
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
    dicomWidget.detailsPopup.offerLoadables(seriesUID, 'Series')
    dicomWidget.detailsPopup.examineForLoading()
    dicomWidget.detailsPopup.loadCheckedLoadables()

  def setupSelectionArea(self):

    self.imageVolumeSelector = self.segmentEditorWidget.masterVolumeNodeSelector
    self.imageVolumeSelector.addAttribute("vtkMRMLScalarVolumeNode", "DICOM.instanceUIDs", None)
    self.segmentationNodeSelector = self.segmentEditorWidget.segmentationNodeSelector
    self.measurementReportSelector = self.createComboBox(nodeTypes=["vtkMRMLTableNode", ""], showChildNodeTypes=False,
                                                         addEnabled=True, removeEnabled=True, noneEnabled=True,
                                                         selectNodeUponCreation=True, toolTip="Select measurement report")
    self.measurementReportSelector.addAttribute("vtkMRMLTableNode", "QuantitativeReporting", "Yes")

    self.selectionAreaWidget = qt.QWidget()
    self.selectionAreaWidgetLayout = qt.QGridLayout()
    self.selectionAreaWidget.setLayout(self.selectionAreaWidgetLayout)

    self.selectionAreaWidgetLayout.addWidget(qt.QLabel("Measurement report"), 0, 0)
    self.selectionAreaWidgetLayout.addWidget(self.measurementReportSelector, 0, 1)
    self.selectionAreaWidgetLayout.addWidget(qt.QLabel("Image volume to annotate"), 1, 0)
    self.selectionAreaWidgetLayout.addWidget(self.imageVolumeSelector, 1, 1)
    self.mainModuleWidgetLayout.addWidget(self.selectionAreaWidget)
    self.mainModuleWidgetLayout.addWidget(self.segmentationGroupBox)

  def setupViewSettingsArea(self):
    self.redSliceLayoutButton = RedSliceLayoutButton()
    self.fourUpSliceLayoutButton = FourUpLayoutButton()
    self.fourUpSliceTableViewLayoutButton = FourUpTableViewLayoutButton()
    self.crosshairButton = CrosshairButton()
    self.crosshairButton.setSliceIntersectionEnabled(True)

    hbox = self.createHLayout([self.redSliceLayoutButton, self.fourUpSliceLayoutButton,
                               self.fourUpSliceTableViewLayoutButton, self.crosshairButton])
    hbox.layout().addStretch(1)
    self.mainModuleWidgetLayout.addWidget(hbox)

  def setupSegmentationsArea(self):
    self.segmentationGroupBox = qt.QGroupBox("Segmentations")
    self.segmentationGroupBoxLayout = qt.QFormLayout()
    self.segmentationGroupBox.setLayout(self.segmentationGroupBoxLayout)
    self.segmentEditorWidget = QuantitativeReportingSegmentEditorWidget(parent=self.segmentationGroupBox)
    self.segmentEditorWidget.setup()

  def setupMeasurementsArea(self):
    self.measurementsGroupBox = qt.QGroupBox("Measurements")
    self.measurementsGroupBoxLayout = qt.QVBoxLayout()
    self.measurementsGroupBox.setLayout(self.measurementsGroupBoxLayout)
    self.tableView = slicer.qMRMLTableView()
    self.tableView.setMinimumHeight(150)
    self.tableView.setMaximumHeight(150)
    self.tableView.setSelectionBehavior(qt.QTableView.SelectRows)
    self.tableView.horizontalHeader().setResizeMode(qt.QHeaderView.Stretch)
    self.fourUpTableView = None
    self.measurementsGroupBoxLayout.addWidget(self.tableView)
    self.mainModuleWidgetLayout.addWidget(self.measurementsGroupBox)

  def setupActionButtons(self):
    self.calculateMeasurementsButton = self.createButton("Calculate Measurements", enabled=False)
    self.calculateAutomaticallyCheckbox = qt.QCheckBox("Auto Update")
    self.calculateAutomaticallyCheckbox.checked = True
    self.saveReportButton = self.createButton("Save Report")
    self.completeReportButton = self.createButton("Complete Report")
    self.enableReportButtons(False)
    self.mainModuleWidgetLayout.addWidget(self.createHLayout([self.calculateMeasurementsButton, self.calculateAutomaticallyCheckbox]))
    self.mainModuleWidgetLayout.addWidget(self.createHLayout([self.saveReportButton, self.completeReportButton]))

  def setupConnections(self, funcName="connect"):

    def setupSelectorConnections():
      getattr(self.imageVolumeSelector, funcName)('currentNodeChanged(vtkMRMLNode*)', self.onImageVolumeSelected)
      getattr(self.measurementReportSelector, funcName)('currentNodeChanged(vtkMRMLNode*)', self.onMeasurementReportSelected)

    def setupButtonConnections():
      getattr(self.saveReportButton.clicked, funcName)(self.onSaveReportButtonClicked)
      getattr(self.completeReportButton.clicked, funcName)(self.onCompleteReportButtonClicked)
      getattr(self.calculateMeasurementsButton.clicked, funcName)(lambda: self.updateMeasurementsTable(triggered=True))

    def setupOtherConnections():
      getattr(self.layoutManager.layoutChanged, funcName)(self.onLayoutChanged)
      getattr(self.layoutManager.layoutChanged, funcName)(self.setupFourUpTableViewConnection)
      getattr(self.calculateAutomaticallyCheckbox.toggled, funcName)(self.onCalcAutomaticallyToggled)
      getattr(self.segmentEditorWidget.tableWidget.selectionModel().selectionChanged, funcName)(self.onSegmentSelected)
      getattr(self.tableView.selectionModel().selectionChanged, funcName)(self.onSegmentSelected)
      getattr(self.tabWidget.currentChanged, funcName)(self.onTabWidgetClicked)

    setupSelectorConnections()
    setupButtonConnections()
    setupOtherConnections()

  def onTabWidgetClicked(self, currentIndex):
    if currentIndex == 0:
      slicer.app.layoutManager().parent().parent().show()
      self.dicomBrowser.close()
    elif currentIndex == 1:
      slicer.app.layoutManager().parent().parent().hide()
      self.dicomBrowser.open()
    self.updateSizes(currentIndex)

  def updateSizes(self, index):
    for tab in [self.tabWidget.widget(i) for i in range(self.tabWidget.count) if i!=index]:
      tab.setSizePolicy(qt.QSizePolicy.Ignored, qt.QSizePolicy.Ignored)

    self.tabWidget.widget(index).setSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Preferred)
    self.tabWidget.widget(index).resize(self.tabWidget.widget(index).minimumSizeHint)
    self.tabWidget.widget(index).adjustSize()
    # self.parent.resize(self.parent.minimumSizeHint)

  def onSegmentSelected(self, itemSelection):
    selectedRow = itemSelection.indexes()[0].row() if len(itemSelection.indexes()) else None
    if selectedRow is not None:
      self.segmentEditorWidget.tableWidget.selectRow(selectedRow)
      self.selectRowIfNotSelected(self.segmentEditorWidget.tableWidget, selectedRow)
      self.selectRowIfNotSelected(self.tableView, selectedRow)
      self.selectRowIfNotSelected(self.fourUpTableView, selectedRow)
      self.segmentEditorWidget.onSegmentSelected(selectedRow)

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
      self.fourUpTableView.selectionModel().selectionChanged.disconnect(self.onSegmentSelected)

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
        self.fourUpTableView.selectionModel().selectionChanged.connect(self.onSegmentSelected)
        self.fourUpTableView.setSelectionBehavior(qt.QTableView.SelectRows)

  def onLoadingFinishedEvent(self, caller, event):
    self.tabWidget.setCurrentIndex(0)

  def onLayoutChanged(self):
    self.onDisplayMeasurementsTable()
    selectedIndexes = self.segmentEditorWidget.tableWidget.selectedIndexes()
    if selectedIndexes:
      self.segmentEditorWidget.tableWidget.selectRow(selectedIndexes[0].row())

  @postCall(refreshUIElementsAvailability)
  def onImageVolumeSelected(self, node):
    self.seriesNumber = None
    self.initializeWatchBox(node)

  @postCall(refreshUIElementsAvailability)
  def onMeasurementReportSelected(self, node):
    self.removeSegmentationObserver()
    self.imageVolumeSelector.setCurrentNode(None)
    self.calculateAutomaticallyCheckbox.checked = True
    self.tableNode = node
    self.hideAllSegmentations()
    if node is None:
      self.segmentationNodeSelector.setCurrentNode(None)
      return

    segmentationNodeID = self.tableNode.GetAttribute('ReferencedSegmentationNodeID')
    logging.debug("ReferencedSegmentationNodeID {}".format(segmentationNodeID))
    if segmentationNodeID:
      segmentationNode = slicer.mrmlScene.GetNodeByID(segmentationNodeID)
    else:
      segmentationNode = self.createNewSegmentationNode()
      self.tableNode.SetAttribute('ReferencedSegmentationNodeID', segmentationNode.GetID())
    self.segmentationNodeSelector.setCurrentNode(segmentationNode)
    segmentationNode.SetDisplayVisibility(True)
    self.setupSegmentationObservers()
    if self.tableNode.GetAttribute("readonly"):
      logging.debug("Selected measurements report is readonly")
      self.setMeasurementsTable(self.tableNode)
      self.segmentEditorWidget.table.setReadOnly(True)
      self.segmentEditorWidget.enabled = False
      self.enableReportButtons(False)
      self.calculateAutomaticallyCheckbox.enabled = False
    else:
      self.segmentEditorWidget.enabled = True
      self.calculateAutomaticallyCheckbox.enabled = True
      self.onSegmentationNodeChanged()

  def hideAllSegmentations(self):
    segmentations = slicer.mrmlScene.GetNodesByClass("vtkMRMLSegmentationNode")
    for segmentation in [segmentations.GetItemAsObject(idx) for idx in range(0, segmentations.GetNumberOfItems())]:
      segmentation.SetDisplayVisibility(False)

  def getReferencedVolumeFromSegmentationNode(self, segmentationNode):
    if not segmentationNode:
      return None
    return segmentationNode.GetNodeReference(segmentationNode.GetReferenceImageGeometryReferenceRole())

  def setupSegmentationObservers(self):
    segNode = self.segmentEditorWidget.segmentation
    if not segNode:
      return
    segmentationEvents = [vtkSegmentationCore.vtkSegmentation.SegmentAdded, vtkSegmentationCore.vtkSegmentation.SegmentRemoved,
                          vtkSegmentationCore.vtkSegmentation.SegmentModified,
                          vtkSegmentationCore.vtkSegmentation.RepresentationModified]
    for event in segmentationEvents:
      self.segmentationObservers.append(segNode.AddObserver(event, self.onSegmentationNodeChanged))

    self.segmentationObservers.append(
      segNode.AddObserver(vtkSegmentationCore.vtkSegmentation.SegmentAdded, self.onSegmentAdded))

  def initializeWatchBox(self, node):
    try:
      dicomFileName = node.GetStorageNode().GetFileName()
      self.watchBox.sourceFile = dicomFileName if os.path.exists(dicomFileName) else None
    except AttributeError:
      self.watchBox.sourceFile = None

  def createNewSegmentationNode(self):
    segNode = slicer.vtkMRMLSegmentationNode()
    slicer.mrmlScene.AddNode(segNode)
    return segNode

  def onSegmentAdded(self, observer=None, caller=None):
    segment = self.segmentEditorWidget.logic.getAllSegments(self.segmentEditorWidget.segmentationNode)[-1]
    self.segmentEditorWidget.setDefaultTerminologyAndColor(segment)

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
    self.measurementsGroupBox.visible = not self.layoutManager.layout == self.fourUpSliceTableViewLayoutButton.LAYOUT
    if self.layoutManager.layout == self.fourUpSliceTableViewLayoutButton.LAYOUT and self.tableNode:
      slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveTableID(self.tableNode.GetID())
      slicer.app.applicationLogic().PropagateTableSelection()

  def onSaveReportButtonClicked(self):
    success = self.saveReport()
    self.saveReportButton.enabled = not success
    if success:
      slicer.util.infoDisplay("Report successfully saved into SlicerDICOMDatabase")

  def onCompleteReportButtonClicked(self):
    success = self.saveReport(completed=True)
    self.saveReportButton.enabled = not success
    self.completeReportButton.enabled = not success
    if success:
      slicer.util.infoDisplay("Report successfully completed and saved into SlicerDICOMDatabase")
      self.tableNode.SetAttribute("readonly", "Yes")

  def saveReport(self, completed=False):
    if self.segmentEditorWidget.hiddenSegmentsAvailable():
      if not slicer.util.confirmYesNoDisplay("Hidden segments have been found. Do you want to export them as well?"):
        self.updateMeasurementsTable(visibleOnly=True)
    try:
      dcmSegmentationPath = self.createSEG()
      self.createDICOMSR(dcmSegmentationPath, completed)
      self.addProducedDataToDICOMDatabase()
    except (RuntimeError, ValueError, AttributeError) as exc:
      slicer.util.warningDisplay(exc.message)
      return False
    finally:
      self.cleanupTemporaryData()
    return True

  def createSEG(self):
    segmentStatisticsLogic = self.segmentEditorWidget.logic.segmentStatisticsLogic
    data = dict()
    data.update(self._getSeriesAttributes())
    data["SeriesDescription"] =  "Segmentation"
    data.update(self._getAdditionalSeriesAttributes())
    data["segmentAttributes"] = segmentStatisticsLogic.generateJSON4DcmSEGExport()

    logging.debug("DICOM SEG Metadata output:")
    logging.debug(data)

    self.currentDateTime = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    self.tempDir = os.path.join(self.slicerTempDir, self.currentDateTime)
    os.mkdir(self.tempDir)

    segmentFiles = []
    for segmentID in segmentStatisticsLogic.statistics["SegmentIDs"]:
      if not segmentStatisticsLogic.statistics[segmentID, "GS voxel count"] > 0:
        continue
      segmentLabelmap = self.segmentEditorWidget.createLabelNodeFromSegment(segmentID)
      filename = os.path.join(self.tempDir, "{}.nrrd".format(segmentLabelmap.GetName()))
      slicer.util.saveNode(segmentLabelmap, filename)
      segmentFiles.append(filename)

    metaFilePath = self.saveJSON(data, os.path.join(self.tempDir, "seg_meta.json"))
    outputSegmentationPath = os.path.join(self.tempDir, "seg.dcm")

    params = {"dicomImageFiles": ', '.join(self.getDICOMFileList(self.segmentEditorWidget.masterVolumeNode,
                                                                 absolutePaths=True)).replace(', ', ","),
              "segImageFiles": ', '.join(segmentFiles).replace(', ', ","),
              "metaDataFileName": metaFilePath,
              "outputSEGFileName": outputSegmentationPath}

    logging.debug(params)

    cliNode = None
    cliNode = slicer.cli.run(slicer.modules.itkimage2segimage, cliNode, params, wait_for_completion=True)
    waitCount = 0
    while cliNode.IsBusy() and waitCount < 20:
      slicer.util.delayDisplay("Running SEG Encoding... %d" % waitCount, 1000)
      waitCount += 1

    if cliNode.GetStatusString() != 'Completed':
      raise RuntimeError("itkimage2segimage CLI did not complete cleanly")

    if not os.path.exists(outputSegmentationPath):
      raise RuntimeError("DICOM Segmentation was not created. Check Error Log for further information.")

    logging.debug("Saved DICOM Segmentation to {}".format(outputSegmentationPath))
    return outputSegmentationPath

  def createDICOMSR(self, referencedSegmentation, completed):
    data = self._getSeriesAttributes()
    data["SeriesDescription"] = "Measurement Report"

    compositeContextDataDir, data["compositeContext"] = os.path.dirname(referencedSegmentation), [os.path.basename(referencedSegmentation)]
    imageLibraryDataDir, data["imageLibrary"] = self.getDICOMFileList(self.segmentEditorWidget.masterVolumeNode)
    data.update(self._getAdditionalSRInformation(completed))

    data["Measurements"] = self.segmentEditorWidget.logic.segmentStatisticsLogic.generateJSON4DcmSR(referencedSegmentation,
                                                                                                    self.segmentEditorWidget.masterVolumeNode)
    logging.debug("DICOM SR Metadata output:")
    logging.debug(json.dumps(data, indent=2, separators=(',', ': ')))

    metaFilePath = self.saveJSON(data, os.path.join(self.tempDir, "sr_meta.json"))
    outputSRPath = os.path.join(self.tempDir, "sr.dcm")

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
    indexer.addDirectory(slicer.dicomDatabase, self.tempDir, "copy")  # TODO: doesn't really expect a destination dir

  def cleanupTemporaryData(self):
    try:
      import shutil
      logging.debug("Cleaning up temporarily created directory {}".format(self.tempDir))
      shutil.rmtree(self.tempDir)
    except AttributeError:
      pass

  def _getSeriesAttributes(self):
    attributes = dict()
    if not self.seriesNumber:
      self.seriesNumber = ModuleLogicMixin.getDICOMValue(self.watchBox.sourceFile, DICOMTAGS.SERIES_NUMBER)
    self.seriesNumber = "100" if self.seriesNumber in [None,''] else str(int(self.seriesNumber)+100)
    attributes["SeriesNumber"] = self.seriesNumber
    attributes["InstanceNumber"] = "1"
    return attributes

  def _getAdditionalSeriesAttributes(self):
    return {"ContentCreatorName": self.watchBox.getAttribute("Reader").value,
            "ClinicalTrialSeriesID": "1",
            "ClinicalTrialTimePointID": "1",
            "ClinicalTrialCoordinatingCenterName": "QIICR"}

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

  def getDICOMFileList(self, volumeNode, absolutePaths=False):
    # TODO: move to general class
    attributeName = "DICOM.instanceUIDs"
    instanceUIDs = volumeNode.GetAttribute(attributeName)
    if not instanceUIDs:
      raise ValueError("VolumeNode {0} has no attribute {1}".format(volumeNode.GetName(), attributeName))
    fileList = []
    rootDir = None
    for uid in instanceUIDs.split():
      rootDir, filename = self.getInstanceUIDDirectoryAndFileName(uid)
      fileList.append(str(filename if not absolutePaths else os.path.join(rootDir, filename)))
    if not absolutePaths:
      return rootDir, fileList
    return fileList

  def getInstanceUIDDirectoryAndFileName(self, uid):
    # TODO: move this method to a general class
    path = slicer.dicomDatabase.fileForInstance(uid)
    return os.path.dirname(path), os.path.basename(path)


class QuantitativeReportingTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_Reporting1()

  def test_Reporting1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')
    self.delayDisplay('Test passed!')


class QuantitativeReportingSegmentEditorWidget(SegmentEditorWidget, ModuleWidgetMixin):

  @property
  def segmentationNode(self):
    return self.editor.segmentationNode()

  @property
  def segmentationNodeSelector(self):
    return self.find("SegmentationNodeComboBox")

  @property
  def masterVolumeNode(self):
    return self.editor.masterVolumeNode()

  @property
  def masterVolumeNodeSelector(self):
    return self.find("MasterVolumeNodeComboBox")

  @property
  @onExceptionReturnNone
  def segmentation(self):
    return self.segmentationNode.GetSegmentation()

  @property
  def segments(self):
    if not self.segmentationNode:
      return []
    return self.logic.getAllSegments(self.segmentationNode)

  @property
  def table(self):
    return self.find("SegmentsTableView")

  @property
  @onExceptionReturnNone
  def tableWidget(self):
    return self.table.tableWidget()

  @onExceptionReturnNone
  def find(self, objectName):
    return slicer.util.findChildren(self.layout.parent(), objectName)[0]

  @property
  def enabled(self):
    return self.editor.enabled

  @enabled.setter
  def enabled(self, enabled):
    self._enabled = enabled
    # TODO: once readonly mode in Segment Editor is available replace the following code
    for widgetName in ["UndoRedoButtonBox", "EffectsGroupBox", "OptionsGroupBox", "MaskingGroupBox",
                       "AddSegmentButton", "RemoveSegmentButton", "CreateSurfaceButton"]:
      widget = self.find(widgetName)
      if widget:
        widget.visible = enabled
    self.table.setReadOnly(not enabled)

  def __init__(self, parent):
    SegmentEditorWidget.__init__(self, parent)
    self.logic = QuantitativeReportingSegmentEditorLogic()

  def setup(self):
    super(QuantitativeReportingSegmentEditorWidget, self).setup()
    if self.developerMode:
      self.reloadCollapsibleButton.hide()
    self.editor.segmentationNodeSelectorVisible = False
    self.editor.setEffectButtonStyle(qt.Qt.ToolButtonIconOnly)
    self.clearSegmentationEditorSelectors()

  def onSegmentSelected(self, selectedRow):
    try:
      segment = self.segments[selectedRow]
      self.jumpToSegmentCenter(segment)
    except IndexError:
      pass

  def jumpToSegmentCenter(self, segment):
    centroid = self.logic.getSegmentCentroid(self.segmentationNode, segment)
    if centroid:
      markupsLogic = slicer.modules.markups.logic()
      markupsLogic.JumpSlicesToLocation(centroid[0], centroid[1], centroid[2], False)

  def clearSegmentationEditorSelectors(self):
    self.editor.setSegmentationNode(None)
    self.editor.setMasterVolumeNode(None)

  def enter(self):
    # overridden because SegmentEditorWidget automatically creates a new Segmentation upon instantiation
    self.turnOffLightboxes()
    self.installShortcutKeys()

    # Set parameter set node if absent
    self.selectParameterNode()
    self.editor.updateWidgetFromMRML()

  def calculateSegmentStatistics(self, tableNode, visibleOnly):
    if not self.segmentationNode or not self.masterVolumeNode:
      return None
    return self.logic.calculateSegmentStatistics(self.segmentationNode, self.masterVolumeNode, visibleOnly, tableNode)

  def createLabelNodeFromSegment(self, segmentID):
    return self.logic.createLabelNodeFromSegment(self.segmentationNode, segmentID)

  def setDefaultTerminologyAndColor(self, segment):
    meaning, terminologyEntryString = self.getDefaultTerminologyString()
    segment.SetTag(vtkSegmentationCore.vtkSegment.GetTerminologyEntryTagName(),
                   terminologyEntryString)
    color = self.getColorFromTerminologyEntry(terminologyEntryString)
    segment.SetColor(map(lambda c: float(c) / 255., [color.red(), color.green(), color.blue()]))
    segment.SetName("{}_{}".format(meaning, str(self.getNumberOfSegmentsStartingWith(meaning) + 1)))

  def getDefaultTerminologyString(self):
    terminologies = slicer.modules.terminologies.logic()
    loadedTerminologyContextNames = vtk.vtkStringArray()
    terminologies.GetLoadedTerminologyNames(loadedTerminologyContextNames)
    loadedAnatomyContextNames = vtk.vtkStringArray()
    terminologies.GetLoadedAnatomicContextNames(loadedAnatomyContextNames)
    terminologyWidget = slicer.qSlicerTerminologyNavigatorWidget()
    code, scheme, meaning = ['T-D0050', 'SRT', 'Tissue']
    terminologyEntryString = terminologyWidget.serializeTerminologyEntry(
      loadedTerminologyContextNames.GetValue(int(loadedTerminologyContextNames.GetNumberOfValues() - 2)),
      code, scheme, meaning,
      code, scheme, meaning,
      "", "", "",
      loadedAnatomyContextNames.GetValue(int(loadedAnatomyContextNames.GetNumberOfValues() - 1)),
      "", "", "", "", "", "")
    return meaning, terminologyEntryString

  def getColorFromTerminologyEntry(self, segmentTerminologyTag):
    terminologyWidget = slicer.qSlicerTerminologyNavigatorWidget()
    terminologyEntry = slicer.vtkSlicerTerminologyEntry()
    terminologyWidget.deserializeTerminologyEntry(segmentTerminologyTag, terminologyEntry)
    color = terminologyWidget.recommendedColorFromTerminology(terminologyEntry)
    return color

  def getNumberOfSegmentsStartingWith(self, name):
    segments = self.logic.getAllSegments(self.segmentationNode)
    return sum(1 for segment in segments if str.startswith(segment.GetName(), name))

  def hiddenSegmentsAvailable(self):
    return len(self.logic.getAllSegments(self.segmentationNode)) \
           != len(self.logic.getVisibleSegments(self.segmentationNode))

class QuantitativeReportingSegmentEditorLogic(ScriptedLoadableModuleLogic):

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    self.parent = parent
    self.volumesLogic = slicer.modules.volumes.logic()
    self.segmentationsLogic = slicer.modules.segmentations.logic()
    self.segmentStatisticsLogic = CustomSegmentStatisticsLogic()

  def getSegmentIDs(self, segmentationNode, visibleOnly):
    if not segmentationNode:
      return []
    segmentIDs = vtk.vtkStringArray()
    segmentation = segmentationNode.GetSegmentation()
    command = segmentationNode.GetDisplayNode().GetVisibleSegmentIDs if visibleOnly else segmentation.GetSegmentIDs
    command(segmentIDs)
    return [segmentIDs.GetValue(idx) for idx in range(segmentIDs.GetNumberOfValues())]

  def getAllSegments(self, segmentationNode):
    segmentation = segmentationNode.GetSegmentation()
    return [segmentation.GetSegment(segmentID) for segmentID in self.getSegmentIDs(segmentationNode, False)]

  def getVisibleSegments(self, segmentationNode):
    segmentation = segmentationNode.GetSegmentation()
    return [segmentation.GetSegment(segmentID) for segmentID in self.getSegmentIDs(segmentationNode, True)]

  def getSegmentCentroid(self, segmentationNode, segment):
    imageData = vtkSegmentationCore.vtkOrientedImageData()
    segmentID = segmentationNode.GetSegmentation().GetSegmentIdBySegment(segment)
    self.segmentationsLogic.GetSegmentBinaryLabelmapRepresentation(segmentationNode, segmentID, imageData)
    extent = imageData.GetExtent()
    if extent[1] != -1 and extent[3] != -1 and extent[5] != -1:
      tempLabel = slicer.vtkMRMLLabelMapVolumeNode()
      slicer.mrmlScene.AddNode(tempLabel)
      tempLabel.SetName(segment.GetName() + "CentroidHelper")
      self.segmentationsLogic.CreateLabelmapVolumeFromOrientedImageData(imageData, tempLabel)
      self.applyThreshold(tempLabel, 1)
      centroid = ModuleLogicMixin.getCentroidForLabel(tempLabel, 1)
      slicer.mrmlScene.RemoveNode(tempLabel)
      return centroid
    return None

  def applyThreshold(self, labelNode, outValue):
    imageData = labelNode.GetImageData()
    backgroundValue = 0
    thresh = vtk.vtkImageThreshold()
    thresh.SetInputData(imageData)
    thresh.ThresholdByLower(0)
    thresh.SetInValue(backgroundValue)
    thresh.SetOutValue(outValue)
    thresh.SetOutputScalarType(vtk.VTK_UNSIGNED_CHAR)
    thresh.Update()
    labelNode.SetAndObserveImageData(thresh.GetOutput())

  def calculateSegmentStatistics(self, segNode, grayscaleNode, visibleSegmentsOnly, tableNode=None):
    self.segmentStatisticsLogic.computeStatistics(segNode, grayscaleNode, visibleSegmentsOnly=visibleSegmentsOnly)

    tableNode = self.segmentStatisticsLogic.exportToTable(tableNode)
    slicer.mrmlScene.AddNode(tableNode)
    return tableNode

  def createLabelNodeFromSegment(self, segmentationNode, segmentID):
    labelNode = slicer.vtkMRMLLabelMapVolumeNode()
    slicer.mrmlScene.AddNode(labelNode)
    segmentationsLogic = slicer.modules.segmentations.logic()

    def vtkStringArrayFromList(listToConvert):
      stringArray = vtk.vtkStringArray()
      for listElement in listToConvert:
        stringArray.InsertNextValue(listElement)
      return stringArray

    mergedImageData = vtkSegmentationCore.vtkOrientedImageData()
    segmentationNode.GenerateMergedLabelmapForAllSegments(mergedImageData, 0, None, vtkStringArrayFromList([segmentID]))
    if not segmentationsLogic.CreateLabelmapVolumeFromOrientedImageData(mergedImageData, labelNode):
      slicer.mrmlScene.RemoveNode(labelNode)
      return None
    labelNode.SetName("{}_label".format(segmentID))
    return labelNode


class CustomSegmentStatisticsLogic(SegmentStatisticsLogic):

  def __init__(self):
    SegmentStatisticsLogic.__init__(self)
    self.terminologyLogic = slicer.modules.terminologies.logic()
    self.segmentationsLogic = slicer.modules.segmentations.logic()

  def reset(self):
    if hasattr(self, "statistics"):
      for segmentID in self.statistics["SegmentIDs"]:
        try:
          labelmap = self.statistics[segmentID, "LM label map"]
          slicer.mrmlScene.RemoveNode(labelmap)
        except Exception:
          continue
    SegmentStatisticsLogic.reset(self)

  def exportToTable(self, table=None, nonEmptyKeysOnly = True):
    if not table:
      table = slicer.vtkMRMLTableNode()
      table.SetName(slicer.mrmlScene.GenerateUniqueName(self.grayscaleNode.GetName() + ' statistics'))
    table.SetUseColumnNameAsColumnHeader(True)
    self.keys = ["Segment", "GS volume mm3", "GS volume cc",
                 "GS min", "GS max", "GS mean", "GS stdev"]
    SegmentStatisticsLogic.exportToTable(self, table, nonEmptyKeysOnly)
    self.keys.append("GS voxel count")
    return table

  def filterEmptySegments(self):
    return [self.segmentationNode.GetSegmentation().GetSegment(s) for s in self.statistics["SegmentIDs"]
            if self.statistics[s, "GS voxel count"] > 0]

  def generateJSON4DcmSEGExport(self):
    self.checkTerminologyOfSegments()
    segmentsData = []
    for segmentID in self.statistics["SegmentIDs"]:
      if self.statistics[segmentID, "GS voxel count"] == 0:
        continue
      segmentData = dict()
      segmentData["labelID"] = 1
      segment = self.segmentationNode.GetSegmentation().GetSegment(segmentID)

      terminologyEntry = self.getDeserializedTerminologyEntry(segment)

      category = terminologyEntry.GetCategoryObject()
      segmentData["SegmentDescription"] = category.GetCodeMeaning() if category != "" else self.statistics[segmentID, "Segment"]
      segmentData["SegmentAlgorithmType"] = "MANUAL"
      rgb = segment.GetColor()
      segmentData["recommendedDisplayRGBValue"] = [rgb[0]*255, rgb[1]*255, rgb[2]*255]
      segmentData.update(self.createJSONFromTerminologyContext(terminologyEntry))
      segmentData.update(self.createJSONFromAnatomicContext(terminologyEntry))
      segmentsData.append([segmentData])
    if not len(segmentsData):
      raise ValueError("No segments with pixel data found.")
    return segmentsData

  def createJSONFromTerminologyContext(self, terminologyEntry):

    segmentData = dict()

    # Both Category and Type are required, so return if not available
    # TODO: consider populating to "Tissue" if not available?
    categoryObject = terminologyEntry.GetCategoryObject()
    if categoryObject is None or not self.isTerminologyInformationValid(categoryObject):
      return {}
    segmentData["SegmentedPropertyCategoryCodeSequence"] = self.getJSONFromVtkSlicerTerminology(categoryObject)

    typeObject = terminologyEntry.GetTypeObject()
    if typeObject is None or not self.isTerminologyInformationValid(typeObject):
      return {}
    segmentData["SegmentedPropertyTypeCodeSequence"] = self.getJSONFromVtkSlicerTerminology(typeObject)

    modifierObject = terminologyEntry.GetTypeModifierObject()
    if modifierObject is not None and self.isTerminologyInformationValid(modifierObject):
      segmentData["SegmentedPropertyTypeModifierCodeSequence"] = self.getJSONFromVtkSlicerTerminology(modifierObject)

    return segmentData

  def createJSONFromAnatomicContext(self, terminologyEntry):

    segmentData = dict()

    regionObject = terminologyEntry.GetAnatomicRegionObject()
    if regionObject is None or not self.isTerminologyInformationValid(regionObject):
      return {}
    segmentData["AnatomicRegionSequence"] = self.getJSONFromVtkSlicerTerminology(regionObject)

    regionModifierObject = terminologyEntry.GetAnatomicRegionModifierObject()
    if regionModifierObject is not None and self.isTerminologyInformationValid(regionModifierObject):
      segmentData["AnatomicRegionModifierSequence"] = self.getJSONFromVtkSlicerTerminology(regionModifierObject)
    return segmentData

  def isTerminologyInformationValid(self, termTypeObject):
    return all(t is not None for t in [termTypeObject.GetCodeValue(), termTypeObject.GetCodingScheme(), termTypeObject.GetCodeMeaning()])

  def getJSONFromVtkSlicerTerminology(self, termTypeObject):
    return self.createCodeSequence(termTypeObject.GetCodeValue(), termTypeObject.GetCodingScheme(), termTypeObject.GetCodeMeaning())

  def generateJSON4DcmSR(self, dcmSegmentationFile, sourceVolumeNode):
    measurements = []
    modality = ModuleLogicMixin.getDICOMValue(sourceVolumeNode, "0008,0060")

    sourceImageSeriesUID = ModuleLogicMixin.getDICOMValue(sourceVolumeNode, "0020,000E")
    logging.debug("SourceImageSeriesUID: {}".format(sourceImageSeriesUID))
    segmentationSOPInstanceUID = ModuleLogicMixin.getDICOMValue(dcmSegmentationFile, "0008,0018")
    logging.debug("SegmentationSOPInstanceUID: {}".format(segmentationSOPInstanceUID))

    for segmentID in self.statistics["SegmentIDs"]:
      if self.statistics[segmentID, "GS voxel count"] == 0:
        continue

      data = dict()
      data["TrackingIdentifier"] = self.statistics[segmentID, "Segment"]
      data["ReferencedSegment"] = len(measurements)+1
      data["SourceSeriesForImageSegmentation"] = sourceImageSeriesUID
      data["segmentationSOPInstanceUID"] = segmentationSOPInstanceUID
      segment = self.segmentationNode.GetSegmentation().GetSegment(segmentID)

      terminologyEntry = self.getDeserializedTerminologyEntry(segment)

      data["Finding"] = self.createJSONFromTerminologyContext(terminologyEntry)["SegmentedPropertyTypeCodeSequence"]
      anatomicContext = self.createJSONFromAnatomicContext(terminologyEntry)
      if anatomicContext.has_key("AnatomicRegionSequence"):
        data["FindingSite"] = anatomicContext["AnatomicRegionSequence"]
      data["measurementItems"] = self.createMeasurementItemsForLabelValue(segmentID, modality)
      measurements.append(data)

    return measurements

  def createMeasurementItemsForLabelValue(self, segmentValue, modality):
    measurementItems = []
    for key in [k for k in self.keys if k not in ["Segment", "GS voxel count"]]:
      item = dict()
      item["value"] = str(self.statistics[segmentValue, key])
      item["quantity"] = self.getQuantityCSforKey(key)
      item["units"] = self.getUnitsCSForKey(key, modality)
      derivationModifier = self.getDerivationModifierCSForKey(key)
      if derivationModifier:
        item["derivationModifier"] = derivationModifier
      measurementItems.append(item)
    return measurementItems

  def getQuantityCSforKey(self, key, modality="CT"):
    if key in ["GS min", "GS max", "GS mean", "GS stdev"]:
      if modality == "CT":
        return self.createCodeSequence("122713", "DCM", "Attenuation Coefficient")
      elif modality == "MR":
        return self.createCodeSequence("110852", "DCM", "MR signal intensity")
    elif key in ["GS volume mm3", "GS volume cc"]:
      return self.createCodeSequence("G-D705", "SRT", "Volume")
    raise ValueError("No matching quantity code sequence found for key {}".format(key))

  def getUnitsCSForKey(self, key, modality="CT"):
    keys = ["GS min", "GS max", "GS mean", "GS stdev"]
    if key in keys:
      if modality == "CT":
        return self.createCodeSequence("[hnsf'U]", "UCUM", "Hounsfield unit")
      elif modality == "MR":
        return self.createCodeSequence("1", "UCUM", "no units")
      raise ValueError("No matching units code sequence found for key {}".format(key))
    elif key == "GS volume mm3":
      return self.createCodeSequence("mm3", "UCUM", "cubic millimeter")
    elif key == "GS volume cc":
      return self.createCodeSequence("cm3", "UCUM", "cubic centimeter")
    return None

  def getDerivationModifierCSForKey(self, key):
    keys = ["GS min", "GS max", "GS mean", "GS stdev"]
    if key in keys:
      if key == keys[0]:
        return self.createCodeSequence("R-404FB", "SRT", "Minimum")
      elif key == keys[1]:
        return self.createCodeSequence("G-A437", "SRT", "Maximum")
      elif key == keys[2]:
        return self.createCodeSequence("R-00317", "SRT", "Mean")
      else:
        return self.createCodeSequence("R-10047", "SRT", "Standard Deviation")
    return None

  def createCodeSequence(self, value, designator, meaning):
    return {"CodeValue": value,
            "CodingSchemeDesignator": designator,
            "CodeMeaning": meaning}

  def checkTerminologyOfSegments(self):
    for segmentID in self.statistics["SegmentIDs"]:
      segment = self.segmentationNode.GetSegmentation().GetSegment(segmentID)
      terminologyEntry = self.getDeserializedTerminologyEntry(segment)
      category = terminologyEntry.GetCategoryObject()
      propType = terminologyEntry.GetTypeObject()
      if any(v is None for v in [category, propType]):
        raise ValueError("Segment {} has missing attributes. Make sure to set terminology.".format(segment.GetName()))

  def isSegmentEmpty(self, segment):
    bounds = [0.0,0.0,0.0,0.0,0.0,0.0]
    segment.GetBounds(bounds)
    return bounds[1] < 0 and bounds[3] < 0 and bounds[5] < 0

  def getTagValue(self, segment, tagName):
    value = vtk.mutable("")
    segment.GetTag(tagName, value)
    return value.get()

  def getDeserializedTerminologyEntry(self, segment):
    terminologyWidget = slicer.qSlicerTerminologyNavigatorWidget()
    terminologyEntry = slicer.vtkSlicerTerminologyEntry()
    tag = vtk.mutable("")
    segment.GetTag(segment.GetTerminologyEntryTagName(), tag)
    terminologyWidget.deserializeTerminologyEntry(tag, terminologyEntry)
    return terminologyEntry


class CustomDICOMDetailsWidget(DICOMDetailsWidget, ParameterNodeObservationMixin):

  FinishedLoadingEvent = vtk.vtkCommand.UserEvent + 101

  def __init__(self, dicomBrowser=None, parent=None):
    DICOMDetailsWidget.__init__(self, dicomBrowser, parent)
    self.browserPersistentButton.visible = True
    self.browserPersistentButton.checked = False

  def onLoadingFinished(self):
    DICOMDetailsWidget.onLoadingFinished(self)
    if not self.browserPersistent:
      self.invokeEvent(self.FinishedLoadingEvent)


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
