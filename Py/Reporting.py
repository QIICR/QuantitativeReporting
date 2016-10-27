import getpass
import json
import logging, os
from datetime import datetime

from slicer.ScriptedLoadableModule import *
import vtkSegmentationCorePython as vtkCoreSeg

from SlicerProstateUtils.mixins import *
from SlicerProstateUtils.decorators import *
from SlicerProstateUtils.helpers import WatchBoxAttribute, DICOMBasedInformationWatchBox
from SlicerProstateUtils.constants import DICOMTAGS
from SlicerProstateUtils.buttons import *

from SegmentEditor import SegmentEditorWidget
from LabelStatistics import LabelStatisticsLogic


class Reporting(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Reporting"
    self.parent.categories = ["Examples"]
    self.parent.dependencies = ["SlicerProstate"]
    self.parent.contributors = ["Christian Herz (SPL), Andrey Fedorov (SPL, BWH), Nicole Aucoin (SPL, BWH), "
                                "Steve Pieper (Isomics)"]
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    It performs a simple thresholding on the input volume and optionally captures a screenshot.
    """  # TODO:
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
    """  # TODO: replace with organization, grant and thanks.


class ReportingWidget(ModuleWidgetMixin, ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.segmentationsLogic = slicer.modules.segmentations.logic()
    self.tempDir = slicer.util.tempDirectory()

  def initializeMembers(self):
    self.tableNode = None
    self.segmentationObservers = []

  def onReload(self):
    self.cleanupUIElements()
    self.removeAllUIElements()
    super(ReportingWidget, self).onReload()

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

  @postCall(refreshUIElementsAvailability)
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.initializeMembers()
    self.setupWatchbox()
    self.setupTestArea()
    self.setupViewSettingsArea()
    self.setupSegmentationsArea()
    self.setupSelectionArea()
    self.setupMeasurementsArea()
    self.setupActionButtons()
    self.setupConnections()
    self.layout.addStretch(1)
    self.fourUpSliceLayoutButton.checked = True

  def setupWatchbox(self):
    self.watchBoxInformation = [
      WatchBoxAttribute('StudyID', 'Study ID: ', DICOMTAGS.STUDY_ID),
      WatchBoxAttribute('PatientName', 'Patient Name: ', DICOMTAGS.PATIENT_NAME),
      WatchBoxAttribute('DOB', 'Date of Birth: ', DICOMTAGS.PATIENT_BIRTH_DATE),
      WatchBoxAttribute('Reader', 'Reader Name: ', callback=getpass.getuser)]
    self.watchBox = DICOMBasedInformationWatchBox(self.watchBoxInformation)
    self.layout.addWidget(self.watchBox)

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
      tableNode.SetAttribute("Reporting", "Yes")
      slicer.mrmlScene.AddNode(tableNode)
      self.measurementReportSelector.setCurrentNode(tableNode)
      self.imageVolumeSelector.setCurrentNode(masterNode)
      self.retrieveTestDataButton.enabled = False

    self.testArea = qt.QGroupBox("Test Area")
    self.testAreaLayout = qt.QFormLayout(self.testArea)
    self.retrieveTestDataButton = self.createButton("Retrieve and load test data")
    self.testAreaLayout.addWidget(self.retrieveTestDataButton)
    self.retrieveTestDataButton.clicked.connect(loadTestData)
    self.layout.addWidget(self.testArea)

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
    self.segmentionNodeSelector = self.segmentEditorWidget.segmentationNodeSelector
    self.measurementReportSelector = self.createComboBox(nodeTypes=["vtkMRMLTableNode", ""], showChildNodeTypes=False,
                                                         addEnabled=True, removeEnabled=True, noneEnabled=True,
                                                         selectNodeUponCreation=True, toolTip="Select measurement report")
    self.measurementReportSelector.addAttribute("vtkMRMLTableNode", "Reporting", "Yes")

    self.selectionAreaWidget = qt.QWidget()
    self.selectionAreaWidgetLayout = qt.QGridLayout()
    self.selectionAreaWidget.setLayout(self.selectionAreaWidgetLayout)

    self.selectionAreaWidgetLayout.addWidget(qt.QLabel("Measurement report"), 0, 0)
    self.selectionAreaWidgetLayout.addWidget(self.measurementReportSelector, 0, 1)
    self.selectionAreaWidgetLayout.addWidget(qt.QLabel("Image volume to annotate"), 1, 0)
    self.selectionAreaWidgetLayout.addWidget(self.imageVolumeSelector, 1, 1)
    self.layout.addWidget(self.selectionAreaWidget)
    self.layout.addWidget(self.segmentationGroupBox)

  def setupViewSettingsArea(self):
    self.redSliceLayoutButton = RedSliceLayoutButton()
    self.fourUpSliceLayoutButton = FourUpLayoutButton()
    self.fourUpSliceTableViewLayoutButton = FourUpTableViewLayoutButton()
    self.crosshairButton = CrosshairButton()

    hbox = self.createHLayout([self.redSliceLayoutButton, self.fourUpSliceLayoutButton,
                               self.fourUpSliceTableViewLayoutButton, self.crosshairButton])
    hbox.layout().addStretch(1)
    self.layout.addWidget(hbox)

  def setupSegmentationsArea(self):
    self.segmentationGroupBox = qt.QGroupBox("Segmentations")
    self.segmentationGroupBoxLayout = qt.QFormLayout()
    self.segmentationGroupBox.setLayout(self.segmentationGroupBoxLayout)
    self.segmentEditorWidget = ReportingSegmentEditorWidget(parent=self.segmentationGroupBox)
    self.segmentEditorWidget.setup()

  def setupMeasurementsArea(self):
    self.measurementsGroupBox = qt.QGroupBox("Measurements")
    self.measurementsGroupBoxLayout = qt.QVBoxLayout()
    self.measurementsGroupBox.setLayout(self.measurementsGroupBoxLayout)
    self.tableView = slicer.qMRMLTableView()
    self.tableView.minimumHeight = 150
    self.measurementsGroupBoxLayout.addWidget(self.tableView)
    self.layout.addWidget(self.measurementsGroupBox)

  def setupActionButtons(self):
    self.calculateMeasurementsButton = self.createButton("Calculate Measurements")
    self.calculateAutomaticallyCheckbox = qt.QCheckBox("Auto Update")
    self.calculateAutomaticallyCheckbox.checked = True
    self.saveReportButton = self.createButton("Save Report")
    self.completeReportButton = self.createButton("Complete Report")
    self.layout.addWidget(self.createHLayout([self.calculateMeasurementsButton, self.calculateAutomaticallyCheckbox]))
    self.layout.addWidget(self.createHLayout([self.saveReportButton, self.completeReportButton]))

  def setupConnections(self, funcName="connect"):

    def setupSelectorConnections():
      getattr(self.imageVolumeSelector, funcName)('currentNodeChanged(vtkMRMLNode*)', self.onImageVolumeSelected)
      getattr(self.measurementReportSelector, funcName)('currentNodeChanged(vtkMRMLNode*)', self.onMeasurementReportSelected)

    def setupButtonConnections():
      getattr(self.saveReportButton.clicked, funcName)(self.onSaveReportButtonClicked)
      getattr(self.completeReportButton.clicked, funcName)(self.onCompleteReportButtonClicked)
      getattr(self.calculateMeasurementsButton.clicked, funcName)(self.updateMeasurementsTable)

    getattr(self.layoutManager.layoutChanged, funcName)(self.onLayoutChanged)
    getattr(self.calculateAutomaticallyCheckbox.toggled, funcName)(self.onCalcAutomaticallyToggled)

    setupSelectorConnections()
    setupButtonConnections()

  def removeConnections(self):
    self.setupConnections(funcName="disconnect")

  def onCalcAutomaticallyToggled(self, checked):
    if checked:
      self.onSegmentationNodeChanged()

  def removeSegmentationObserver(self):
    if self.segmentEditorWidget.segmentation and len(self.segmentationObservers):
      while len(self.segmentationObservers):
        observer = self.segmentationObservers.pop()
        self.segmentEditorWidget.segmentation.RemoveObserver(observer)
    self.segNode = None

  def onLayoutChanged(self, layout):
    self.onDisplayMeasurementsTable()

  @postCall(refreshUIElementsAvailability)
  def onImageVolumeSelected(self, node):
    self.initializeWatchBox(node)

  @priorCall(refreshUIElementsAvailability)
  def onMeasurementReportSelected(self, node):
    self.removeSegmentationObserver()
    self.imageVolumeSelector.setCurrentNode(None)
    self.tableNode = node
    if node is None:
      self.segmentionNodeSelector.setCurrentNode(None)
      return

    segmentationNodeID = self.tableNode.GetAttribute('ReferencedSegmentationNodeID')
    if segmentationNodeID:
      segmentationNode = slicer.mrmlScene.GetNodeByID(segmentationNodeID)
    else:
      segmentationNode = self.createNewSegmentationNode()
      self.tableNode.SetAttribute('ReferencedSegmentationNodeID', segmentationNode.GetID())
    self.segmentionNodeSelector.setCurrentNode(segmentationNode)
    self.setupSegmentationObservers()
    self.onSegmentationNodeChanged()

  def getReferencedVolumeFromSegmentationNode(self, segmentationNode):
    if not segmentationNode:
      return None
    return segmentationNode.GetNodeReference(segmentationNode.GetReferenceImageGeometryReferenceRole())

  def setupSegmentationObservers(self):
    segNode = self.segmentEditorWidget.segmentation
    if not segNode:
      return
    segmentationEvents = [vtkCoreSeg.vtkSegmentation.SegmentAdded, vtkCoreSeg.vtkSegmentation.SegmentRemoved,
                          vtkCoreSeg.vtkSegmentation.SegmentModified,
                          vtkCoreSeg.vtkSegmentation.RepresentationModified]
    for event in segmentationEvents:
      self.segmentationObservers.append(segNode.AddObserver(event, self.onSegmentationNodeChanged))

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

  @postCall(refreshUIElementsAvailability)
  def onSegmentationNodeChanged(self, observer=None, caller=None):
    if not self.calculateAutomaticallyCheckbox.checked:
      self.tableView.setStyleSheet("QTableView{border:2px solid red;};")
      return
    self.updateMeasurementsTable()

  def updateMeasurementsTable(self):
    table = self.segmentEditorWidget.calculateLabelStatistics(self.tableNode)
    if table:
      self.tableNode = table
      self.tableNode.SetLocked(True)
      self.tableView.setMRMLTableNode(self.tableNode)
      self.tableView.setStyleSheet("QTableView{border:none};")
    self.onDisplayMeasurementsTable()

  def getActiveSlicerTableID(self):
    return slicer.app.applicationLogic().GetSelectionNode().GetActiveTableID()

  def onDisplayMeasurementsTable(self):
    self.measurementsGroupBox.visible = not self.layoutManager.layout == self.fourUpSliceTableViewLayoutButton.LAYOUT
    if self.layoutManager.layout == self.fourUpSliceTableViewLayoutButton.LAYOUT and self.tableNode:
      slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveTableID(self.tableNode.GetID())
      slicer.app.applicationLogic().PropagateTableSelection()

  def onSaveReportButtonClicked(self):
    try:
      dcmSegmentationPath = self.createSEG()
    except (RuntimeError, ValueError, AttributeError) as exc:
      slicer.util.warningDisplay(exc.message if isinstance(exc, ValueError) else "No segments found")
      return
    self.createDICOMSR(dcmSegmentationPath)

  def onCompleteReportButtonClicked(self):
    print "on complete report button clicked"

  def createSEG(self):
    data = dict()
    data.update(self._getSeriesAttributes())
    data.update(self._getAdditionalSeriesAttributes())
    data["segmentAttributes"] = self.segmentEditorWidget.logic.labelStatisticsLogic.generateJSON4DcmSEGExport()

    logging.debug("DICOM SEG Metadata output:")
    logging.debug(data)

    labelNode = self.segmentEditorWidget.logic.labelMapFromSegmentationNode(self.segmentEditorWidget.segmentationNode)
    slicer.mrmlScene.AddNode(labelNode)
    slicer.util.saveNode(labelNode, os.path.join(self.tempDir, "labelmap.nrrd"))

    self.currentDateTime = datetime.now().strftime('%Y-%m-%d_%H%M%S')

    metaFilePath = self.saveJSON(data, os.path.join(self.tempDir, "seg_meta_{}.json".format(self.currentDateTime)))
    outputSegmentationPath = os.path.join(self.tempDir, "seg_{}.dcm".format(self.currentDateTime))

    params = {"dicomImageFiles": ', '.join(self.getDICOMFileList(self.segmentEditorWidget.masterVolumeNode,
                                                                 absolutePaths=True)).replace(', ', ","),
              "segImageFiles": labelNode.GetStorageNode().GetFileName(),
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
    indexer = ctk.ctkDICOMIndexer()
    indexer.addFile(slicer.dicomDatabase, outputSegmentationPath)

    logging.debug("Saved DICOM Segmentation to {}".format(outputSegmentationPath))
    return outputSegmentationPath

  def createDICOMSR(self, referencedSegmentation):
    data = self._getSeriesAttributes()

    compositeContextDataDir, data["compositeContext"] = os.path.dirname(referencedSegmentation), [os.path.basename(referencedSegmentation)]
    imageLibraryDataDir, data["imageLibrary"] = self.getDICOMFileList(self.segmentEditorWidget.masterVolumeNode)
    data.update(self._getAdditionalSRInformation())

    data["Measurements"] = self.segmentEditorWidget.logic.labelStatisticsLogic.generateJSON4DcmSR(referencedSegmentation,
                                                                                                  self.segmentEditorWidget.masterVolumeNode)

    print json.dumps(data, indent=2, separators=(',', ': '))  # TODO: remove

    logging.debug("DICOM SR Metadata output:")
    logging.debug(data)

    metaFilePath = self.saveJSON(data, os.path.join(self.tempDir, "sr_meta_{}.json".format(self.currentDateTime)))
    outputSRPath = os.path.join(self.tempDir, "sr_{}.dcm".format(self.currentDateTime))

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
    # # TODO: Save Structured Report to DICOMDatabase

  def _getSeriesAttributes(self):
    return {"SeriesDescription": "Segmentation",
            "SeriesNumber": ModuleLogicMixin.getDICOMValue(self.watchBox.sourceFile, DICOMTAGS.SERIES_NUMBER),
            "InstanceNumber": ModuleLogicMixin.getDICOMValue(self.watchBox.sourceFile, DICOMTAGS.INSTANCE_NUMBER)}

  def _getAdditionalSeriesAttributes(self):
    # TODO: populate
    return {"ContentCreatorName": self.watchBox.getAttribute("Reader").value,
            "ClinicalTrialSeriesID": "1",
            "ClinicalTrialTimePointID": "1",
            "ClinicalTrialCoordinatingCenterName": "QIICR"}

  def _getAdditionalSRInformation(self):
    data = dict()
    data["observerContext"] = {"ObserverType": "PERSON",
                               "PersonObserverName": self.watchBox.getAttribute("Reader").value}
    data["VerificationFlag"] = "VERIFIED"
    data["CompletionFlag"] = "COMPLETE"
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


class ReportingTest(ScriptedLoadableModuleTest):
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

    volumeNode = slicer.util.getNode(pattern="FA")
    self.delayDisplay('Test passed!')


class ReportingSegmentEditorWidget(SegmentEditorWidget, ModuleWidgetMixin):

  @property
  def segmentationNode(self):
    return self.editor.segmentationNode()

  @property
  def segmentationNodeSelector(self):
    return self.find("MRMLNodeComboBox_Segmentation")

  @property
  def masterVolumeNode(self):
    return self.editor.masterVolumeNode()

  @property
  def masterVolumeNodeSelector(self):
    return self.find("MRMLNodeComboBox_MasterVolume")

  @property
  @onExceptionReturnNone
  def segmentation(self):
    return self.segmentationNode.GetSegmentation()

  @property
  def segments(self):
    return self.logic.getSegments(self.segmentation)

  @property
  def table(self):
    return self.find("SegmentsTableView")

  @property
  @onExceptionReturnNone
  def tableWidget(self):
    return self.table.tableWidget()

  @onExceptionReturnNone
  def find(self, objectName):
    return self.findAll(objectName)[0]

  def findAll(self, objectName):
    return slicer.util.findChildren(self.editor, objectName)

  def __init__(self, parent):
    SegmentEditorWidget.__init__(self, parent)
    self.logic = ReportingSegmentEditorLogic()

  def setup(self):
    super(ReportingSegmentEditorWidget, self).setup()
    self.reloadCollapsibleButton.hide()
    self.hideUnwantedEditorUIElements()
    self.reorganizeEffectButtons()
    self.changeUndoRedoSizePolicies()
    self.appendOptionsAndMaskingGroupBoxAtTheEnd()
    self.clearSegmentationEditorSelectors()
    self.setupConnections()

  def setupConnections(self):
    self.tableWidget.itemClicked.connect(self.onSegmentSelected)

  def onSegmentSelected(self, item):
    try:
      segment = self.segments[item.row()]
      self.jumpToSegmentCenter(segment)
    except IndexError:
      pass

  def jumpToSegmentCenter(self, segment):
    centroid = self.logic.getSegmentCentroid(segment)
    if centroid:
      markupsLogic = slicer.modules.markups.logic()
      markupsLogic.JumpSlicesToLocation(centroid[0], centroid[1], centroid[2], False)

  def clearSegmentationEditorSelectors(self):
    self.editor.setSegmentationNode(None)
    self.editor.setMasterVolumeNode(None)

  def hideUnwantedEditorUIElements(self):
    self.editor.segmentationNodeSelectorVisible = False
    # self.editor.masterVolumeNodeSelectorVisible = False

  def reorganizeEffectButtons(self):
    widget = self.find("EffectsGroupBox")
    if widget:
      buttons = [b for b in widget.children() if isinstance(b, qt.QPushButton)]
      self.layout.addWidget(self.createHLayout(buttons))
      widget.hide()

  def appendOptionsAndMaskingGroupBoxAtTheEnd(self):
    for widgetName in ["OptionsGroupBox", "MaskingGroupBox"]:
      widget = self.find(widgetName)
      self.layout.addWidget(widget)

  def changeUndoRedoSizePolicies(self):
    undo = self.find("UndoButton")
    redo = self.find("RedoButton")
    if undo and redo:
      undo.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)
      redo.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)
      self.layout.addWidget(self.createHLayout([undo, redo]))

  def enter(self):
    # overridden because SegmentEditorWidget automatically creates a new Segmentation upon instantiation
    self.turnOffLightboxes()
    self.installShortcutKeys()

    # Set parameter set node if absent
    self.selectParameterNode()
    self.editor.updateWidgetFromMRML()

  def calculateLabelStatistics(self, tableNode):
    return self.logic.calculateLabelStatistics(self.segmentationNode, self.masterVolumeNode, tableNode)


class ReportingSegmentEditorLogic(ScriptedLoadableModuleLogic):

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    self.parent = parent
    self.volumesLogic = slicer.modules.volumes.logic()
    self.segmentationsLogic = slicer.modules.segmentations.logic()
    self.labelStatisticsLogic = None

  def getSegments(self, segmentation):
    if not segmentation:
      return []
    segmentIDs = vtk.vtkStringArray()
    segmentation.GetSegmentIDs(segmentIDs)
    return [segmentation.GetSegment(segmentIDs.GetValue(idx)) for idx in range(segmentIDs.GetNumberOfValues())]

  def getSegmentCentroid(self, segment):
    binData = segment.GetRepresentation("Binary labelmap")
    extent = binData.GetExtent()
    if extent[1] != -1 and extent[3] != -1 and extent[5] != -1:
      tempLabel = slicer.vtkMRMLLabelMapVolumeNode()
      slicer.mrmlScene.AddNode(tempLabel)
      tempLabel.SetName(segment.GetName() + "CentroidHelper")
      self.segmentationsLogic.CreateLabelmapVolumeFromOrientedImageData(binData, tempLabel)
      centroid = ModuleLogicMixin.getCentroidForLabel(tempLabel, 1)
      slicer.mrmlScene.RemoveNode(tempLabel)
      return centroid
    return None

  def labelMapFromSegmentationNode(self, segNode):
    labelNode = slicer.vtkMRMLLabelMapVolumeNode()
    slicer.mrmlScene.AddNode(labelNode)

    mergedImageData = vtkCoreSeg.vtkOrientedImageData()
    segNode.GenerateMergedLabelmapForAllSegments(mergedImageData, 0)
    if not self.segmentationsLogic.CreateLabelmapVolumeFromOrientedImageData(mergedImageData, labelNode):
      slicer.mrmlScene.RemoveNode(labelNode)
      return None
    return labelNode

  def calculateLabelStatistics(self, segNode, grayscaleNode, tableNode=None):
    labelNode = self.labelMapFromSegmentationNode(segNode)
    if not labelNode:
      return None
    segments = self.getSegments(segNode.GetSegmentation())
    warnings = self.volumesLogic.CheckForLabelVolumeValidity(grayscaleNode, labelNode)
    if warnings != "":
      if 'mismatch' in warnings:
        resampledLabelNode = self.volumesLogic.ResampleVolumeToReferenceVolume(labelNode, grayscaleNode)
        self.labelStatisticsLogic = CustomLabelStatisticsLogic(segments, grayscaleNode, resampledLabelNode,
                                                               colorNode=labelNode.GetDisplayNode().GetColorNode(),
                                                               nodeBaseName=labelNode.GetName())
        slicer.mrmlScene.RemoveNode(resampledLabelNode)
      else:
        raise ValueError("Volumes do not have the same geometry.\n%s" % warnings)
    else:
      self.labelStatisticsLogic = CustomLabelStatisticsLogic(segments, grayscaleNode, labelNode)

    tableNode = self.labelStatisticsLogic.exportToTable(tableNode)
    slicer.mrmlScene.AddNode(tableNode)
    slicer.mrmlScene.RemoveNode(labelNode)
    return tableNode


class CustomLabelStatisticsLogic(LabelStatisticsLogic):

  def __init__(self, segments, grayscaleNode, labelNode, colorNode=None, nodeBaseName=None, fileName=None):
    LabelStatisticsLogic.__init__(self, grayscaleNode, labelNode, colorNode, nodeBaseName, fileName)
    self.terminologyLogic = slicer.modules.terminologies.logic()
    self.segments = segments

  def exportToTable(self, table=None):
    if not table:
      table = slicer.vtkMRMLTableNode()
      table.SetName(slicer.mrmlScene.GenerateUniqueName(self.nodeBaseName + ' statistics'))

    table.RemoveAllColumns()
    table.SetUseColumnNameAsColumnHeader(True)

    self.customizeLabelStats()

    tableWasModified = table.StartModify()
    for k in self.keys:
      col = table.AddColumn()
      col.SetName(k)
    for labelValue in self.labelStats["Labels"]:
      rowIndex = table.AddEmptyRow()
      for columnIndex, k in enumerate(self.keys):
        table.SetCellText(rowIndex, columnIndex, str(self.labelStats[labelValue, k]))

    table.EndModify(tableWasModified)
    return table

  def filterEmptySegments(self):
    return [s for s in self.segments if not self.isSegmentEmpty(s)]

  def customizeLabelStats(self):
    colorNode = self.getColorNode()
    if not colorNode:
      return self.keys, self.labelStats

    self.keys = ["Segment Name"] + list(self.keys)
    self.keys.remove("Index")

    try:
      del self.labelStats["Labels"][0]
    except KeyError:
      pass

    segments = self.filterEmptySegments()

    for segment, labelValue in zip(segments, self.labelStats["Labels"]):
      self.labelStats[labelValue, "Segment Name"] = segment.GetName()

  def generateJSON4DcmSEGExport(self):
    self.validateSegments()
    segmentsData = []
    segments = self.filterEmptySegments()
    if not len(segments):
      raise ValueError("No segments with pixel data found.")
    for segment, labelValue in zip(segments, self.labelStats["Labels"]):
      segmentData = dict()
      segmentData["LabelID"] = labelValue
      category = self.getTagValue(segment, segment.GetTerminologyCategoryTagName())
      segmentData["SegmentDescription"] = category if category != "" else segment.GetName()
      segmentData["SegmentAlgorithmType"] = "MANUAL"
      segmentData["recommendedDisplayRGBValue"] = segment.GetDefaultColor()
      segmentData.update(self.createJSONFromTerminologyContext(segment))
      segmentData.update(self.createJSONFromAnatomicContext(segment))
      segmentsData.append(segmentData)
    return [segmentsData]

  def createJSONFromTerminologyContext(self, segment):
    segmentData = dict()
    contextName = self.getTagValue(segment, segment.GetTerminologyContextTagName())
    categoryName = self.getTagValue(segment, segment.GetTerminologyCategoryTagName())

    category = slicer.vtkSlicerTerminologyCategory()
    if not self.terminologyLogic.GetCategoryInTerminology(contextName, categoryName, category):
      raise ValueError("Error: Cannot get category from terminology")
    segmentData["SegmentedPropertyCategoryCodeSequence"] = self.getJSONFromVtkSlicerCodeSequence(category)

    typeName = self.getTagValue(segment, segment.GetTerminologyTypeTagName())
    pType = slicer.vtkSlicerTerminologyType()
    if not self.terminologyLogic.GetTypeInTerminologyCategory(contextName, categoryName, typeName, pType):
      raise ValueError("Error: Cannot get type from terminology")
    segmentData["SegmentedPropertyTypeCodeSequence"] = self.getJSONFromVtkSlicerCodeSequence(pType)

    modifierName = self.getTagValue(segment, segment.GetTerminologyTypeModifierTagName())
    if modifierName != "":
      modifier = slicer.vtkSlicerTerminologyType()
      if self.terminologyLogic.GetTypeModifierInTerminologyType(contextName, categoryName, typeName, modifierName, modifier):
        segmentData["SegmentedPropertyTypeModifierCodeSequence"] = self.getJSONFromVtkSlicerCodeSequence(modifier)

    return segmentData

  def createJSONFromAnatomicContext(self, segment):
    segmentData = dict()
    anatomicContextName = self.getTagValue(segment, segment.GetAnatomicContextTagName())
    regionName = self.getTagValue(segment, segment.GetAnatomicRegionTagName())

    if regionName == "":
      return {}

    region = slicer.vtkSlicerTerminologyType()
    self.terminologyLogic.GetRegionInAnatomicContext(anatomicContextName, regionName, region)
    segmentData["AnatomicRegionSequence"] = self.getJSONFromVtkSlicerCodeSequence(region)

    modifierName = self.getTagValue(segment, segment.GetAnatomicRegionModifierTagName())
    if modifierName != "":
      modifier = slicer.vtkSlicerTerminologyType()
      self.terminologyLogic.GetRegionModifierInAnatomicRegion(anatomicContextName, regionName, modifierName, modifier)
      segmentData["AnatomicRegionModifierSequence"] = self.getJSONFromVtkSlicerCodeSequence(modifier)

    return segmentData

  def getJSONFromVtkSlicerCodeSequence(self, codeSequence):
    return self.createCodeSequence(codeSequence.GetCodeValue(), codeSequence.GetCodingScheme(), codeSequence.GetCodeMeaning())

  def generateJSON4DcmSR(self, dcmSegmentationFile, sourceVolumeNode):
    measurements = []
    segments = self.filterEmptySegments()

    modality = ModuleLogicMixin.getDICOMValue(sourceVolumeNode, "0008,0060")

    sourceImageSeriesUID = ModuleLogicMixin.getDICOMValue(sourceVolumeNode, "0020,000E")
    logging.debug("SourceImageSeriesUID: {}".format(sourceImageSeriesUID))
    segmentationSOPInstanceUID = ModuleLogicMixin.getDICOMValue(dcmSegmentationFile, "0008,00018")
    logging.debug("SegmentationSOPInstanceUID: {}".format(segmentationSOPInstanceUID))

    for segment, labelValue in zip(segments, self.labelStats["Labels"]):
      data = dict()
      data["TrackingIdentifier"] = segment.GetName()
      data["ReferencedSegment"] = labelValue
      data["SourceSeriesForImageSegmentation"] = sourceImageSeriesUID
      data["segmentationSOPInstanceUID"] = segmentationSOPInstanceUID
      data["Finding"] = self.createJSONFromTerminologyContext(segment)["SegmentedPropertyTypeCodeSequence"]
      anatomicContext = self.createJSONFromAnatomicContext(segment)
      if anatomicContext.has_key("AnatomicRegionSequence"):
        data["FindingSite"] = anatomicContext["AnatomicRegionSequence"]
      data["measurementItems"] = self.createMeasurementItemsForLabelValue(labelValue, modality)
      measurements.append(data)
    return measurements

  def createMeasurementItemsForLabelValue(self, labelValue, modality):
    measurementItems = []
    for key in [k for k in self.keys if k not in ["Index", "Segment Name", "Count"]]:
      item = dict()
      item["value"] = str(self.labelStats[labelValue, key])
      item["quantity"] = self.getQuantityCSforKey(key)
      item["units"] = self.getUnitsCSForKey(key, modality)
      derivationModifier = self.getDerivatinModifierCSForKey(key)
      if derivationModifier:
        item["derivationModifier"] = derivationModifier
      measurementItems.append(item)
    return measurementItems

  def getQuantityCSforKey(self, key, modality="CT"):
    if key in ["Min", "Max", "Mean", "StdDev"]:
      if modality == "CT":
        return self.createCodeSequence("122713", "DCM", "Attenuation Coefficient")
      elif modality == "MR":
        return self.createCodeSequence("110852", "DCM", "MR signal intensity")
    elif key in ["Volume mm^3", "Volume cc"]:
      return self.createCodeSequence("G-D705", "SRT", "Volume")
    raise ValueError("No matching quantity code sequence found for key {}".format(key))

  def getUnitsCSForKey(self, key, modality="CT"):
    keys = ["Min", "Max", "Mean", "StdDev"]
    if key in keys:
      if modality == "CT":
        return self.createCodeSequence("[hnsf'U]", "UCUM", "Hounsfield unit")
      elif modality == "MR":
        return self.createCodeSequence("1", "UCUM", "no units")
      raise ValueError("No matching units code sequence found for key {}".format(key))
    elif key == "Volume cc":
      return self.createCodeSequence("mm3", "UCUM", "cubic millimeter")
    elif key == "Volume mm^3":
      return self.createCodeSequence("cm3", "UCUM", "cubic centimeter")
    return None

  def getDerivatinModifierCSForKey(self, key):
    keys = ["Min", "Max", "Mean", "StdDev"]
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

  def validateSegments(self):
    segments = self.filterEmptySegments()
    for segment, labelValue in zip(segments, self.labelStats["Labels"]):
      category = self.getTagValue(segment, segment.GetTerminologyCategoryTagName())
      propType = self.getTagValue(segment, segment.GetTerminologyTypeTagName())
      if any(v == "" for v in [category, propType]):
        raise ValueError("Segment {} has missing attributes. Make sure to set terminology.".format(segment.GetName()))

  def isSegmentEmpty(self, segment):
    bounds = [0.0,0.0,0.0,0.0,0.0,0.0]
    segment.GetBounds(bounds)
    return bounds[1] < 0 and bounds[3] < 0 and bounds[5] < 0

  def getTagValue(self, segment, tagName):
    value = vtk.mutable("")
    segment.GetTag(tagName, value)
    return value.get()