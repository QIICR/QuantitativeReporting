import os
import qt
import ctk
import vtk
import slicer
import logging
import inspect

from slicer.ScriptedLoadableModule import ScriptedLoadableModuleTest, ScriptedLoadableModuleWidget, \
  ScriptedLoadableModuleLogic

__all__ = ['QuantitativeReportingTest']


class QuantitativeReportingTests:

  def __init__(self, parent):
    parent.title = "Quantitative Reporting Tests"
    parent.categories = ["Testing.TestCases"]
    parent.dependencies = ["QuantitativeReporting"]
    parent.contributors = ["Christian Herz (SPL, BWH), Andrey Fedorov (SPL, BWH)"]
    parent.helpText = """
    This self test includes creation/read of a structured report (DICOM TID1500) including its segmentation.
    For more information: <a>https://github.com/QIICR/QuantitativeReporting</a>
    """
    parent.acknowledgementText = """
    This work was supported in part by the National Cancer Institute funding to the
    Quantitative Image Informatics for Cancer Research (QIICR) (U24 CA180918).
    """
    self.parent = parent

    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['QuantitativeReporting'] = self.runTest

  def runTest(self):
    tester = QuantitativeReportingTest()
    tester.runTest()


class QuantitativeReportingTestsWidget(ScriptedLoadableModuleWidget):

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.testsCollapsibleButton = ctk.ctkCollapsibleButton()
    self.testsCollapsibleButton.setLayout(qt.QFormLayout())
    self.testsCollapsibleButton.text = "Quantitative Reporting Tests"
    self.layout.addWidget(self.testsCollapsibleButton)
    self.generateButtons()

  def generateButtons(self):

    def onButtonPressed(button):
      print "pressed button %s" % button.name
      tester = QuantitativeReportingTest()
      tester.setUp()
      getattr(tester, button.name)()

    buttons = []
    for testName in [f for f in QuantitativeReportingTest.__dict__.keys() if f.startswith('test_')]:
      b = qt.QPushButton(testName)
      b.name = testName
      self.testsCollapsibleButton.layout().addWidget(b)
      buttons.append(b)

    map(lambda b: b.clicked.connect(lambda clicked: onButtonPressed(b)), buttons)


class QuantitativeReportingTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  @property
  def layoutManager(self):
    return slicer.app.layoutManager()

  def setUp(self):
    self.delayDisplay("Closing the scene")
    slicer.mrmlScene.Clear(0)

  def loadTestData(self):
    self.delayDisplay("Loading testdata")

    liverCTSeriesUID = "1.2.392.200103.20080913.113635.1.2009.6.22.21.43.10.23430.1"
    collection = "CTLiver"

    qrWidget = slicer.modules.QuantitativeReportingWidget
    qrWidget.loadTestData(collection, liverCTSeriesUID)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_create_report()
    self.test_import_labelmap()
    self.test_import_segmentation()

    self.test_read_report()

  def test_create_report(self):

    self.delayDisplay('Starting %s' % inspect.stack()[0][3])

    self.layoutManager.selectModule("QuantitativeReporting")
    qrWidget = slicer.modules.QuantitativeReportingWidget

    self.loadTestData()
    success, err = qrWidget.saveReport()
    self.assertFalse(success)

    self.delayDisplay('Add segments')

    import vtkSegmentationCorePython as vtkSegmentationCore

    qrWidget = slicer.modules.QuantitativeReportingWidget
    segmentation = qrWidget.segmentEditorWidget.segmentationNode.GetSegmentation()

    segmentGeometries = {
      'Tumor': [[2, 30, 30, -127.7], [2, 40, 40, -127.7], [2, 50, 50, -127.7], [2, 40, 80, -127.7]],
      'Air': [[2, 60, 100, -127.7], [2, 80, 30, -127.7]]
    }

    for segmentName, segmentGeometry in segmentGeometries.iteritems():
      appender = vtk.vtkAppendPolyData()

      for sphere in segmentGeometry:
        sphereSource = vtk.vtkSphereSource()
        sphereSource.SetRadius(sphere[0])
        sphereSource.SetCenter(sphere[1], sphere[2], sphere[3])
        appender.AddInputConnection(sphereSource.GetOutputPort())

      segment = vtkSegmentationCore.vtkSegment()
      segment.SetName(segmentation.GenerateUniqueSegmentID(segmentName))

      appender.Update()
      representationName = vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()
      segment.AddRepresentation(representationName, appender.GetOutput())
      segmentation.AddSegment(segment)

    self.delayDisplay('Save report')

    success, err = qrWidget.saveReport()
    self.assertTrue(success)

    self.delayDisplay('Test passed!')

  def test_import_labelmap(self):

    self.delayDisplay('Starting %s' % inspect.stack()[0][3])

    self.layoutManager.selectModule("QuantitativeReporting")

    qrWidget = slicer.modules.QuantitativeReportingWidget
    self.loadTestData()

    sampleData = TestDataLogic.downloadAndUnzipSampleData("CTLiver")
    segmentationsDir = sampleData['seg_nrrd']

    labels = []
    for f in [os.path.join(segmentationsDir, f) for f in os.listdir(segmentationsDir) if f.endswith(".nrrd")]:
      _, label = slicer.util.loadVolume(f, {'labelmap': True}, returnNode=True)
      if label:
        labels.append(label)

    labelImportWidget = qrWidget.labelMapImportWidget

    timer = qt.QTimer()
    timer.setInterval(2000)
    timer.timeout.connect(self._checkFocusAndClickButton)
    timer.start()

    for label in labels:
      labelImportWidget.labelMapSelector.setCurrentNode(label)
      labelImportWidget.importButton.click()

    timer.stop()

    segmentation = qrWidget.segmentEditorWidget.segmentationNode.GetSegmentation()
    self.assertEquals(segmentation.GetNumberOfSegments(), len(labels))

    self.delayDisplay('Test passed!')

  def _checkFocusAndClickButton(self):
    focus = slicer.app.focusWidget()
    if type(focus) is qt.QPushButton:
      focus.click()

  def test_import_segmentation(self):
    self.delayDisplay('Starting %s' % inspect.stack()[0][3])

    self.delayDisplay('Test passed!')

  def test_read_report(self):
    self.delayDisplay('Starting %s' % inspect.stack()[0][3])

    self.delayDisplay('Test passed!')


class TestDataLogic(ScriptedLoadableModuleLogic):

  collections = {
    'MRHead': {
      'volume': ('http://slicer.kitware.com/midas3/download/item/220834/PieperMRHead.zip', 'PieperMRHead.zip')
    },
    'CTLiver': {
      'volume': ('https://github.com/QIICR/QuantitativeReporting/releases/download/test-data/CTLiver.zip', 'CTLiver.zip'),
      'sr': ('https://github.com/QIICR/QuantitativeReporting/releases/download/test-data/SR.zip', 'SR.zip'),
      'seg_dcm': ('https://github.com/QIICR/QuantitativeReporting/releases/download/test-data/Liver_Segmentation_DCM.zip',
                  'Liver_Segmentation_DCM.zip'),
      'seg_nrrd': ('https://github.com/QIICR/QuantitativeReporting/releases/download/test-data/Segmentations_NRRD.zip',
                   'Segmentations_NRRD.zip')
    }
  }

  DOWNLOAD_DIRECTORY = os.path.join(slicer.app.temporaryPath, 'dicomFiles')

  @staticmethod
  def importIntoDICOMDatabase(dicomFilesDirectory):
    indexer = ctk.ctkDICOMIndexer()
    indexer.addDirectory(slicer.dicomDatabase, dicomFilesDirectory, None)
    indexer.waitForImportFinished()

  @staticmethod
  def unzipSampleData(filePath, collection, kind):
    destinationDirectory = TestDataLogic.getUnzippedDirectoryPath(collection, kind)
    qt.QDir().mkpath(destinationDirectory)
    success = slicer.app.applicationLogic().Unzip(filePath, destinationDirectory)
    if not success:
      logging.error("Archive %s was NOT unzipped successfully." %  filePath)
    return destinationDirectory

  @staticmethod
  def getUnzippedDirectoryPath(collection, kind):
    return os.path.join(TestDataLogic.DOWNLOAD_DIRECTORY, collection, kind)

  @staticmethod
  def downloadAndUnzipSampleData(collection='MRHead'):
    import urllib
    slicer.util.delayDisplay("Downloading", 1000)

    downloaded = {}
    for kind, (url, filename) in TestDataLogic.collections[collection].iteritems():
      filePath = os.path.join(slicer.app.temporaryPath, 'downloads', collection, kind, filename)
      if not os.path.exists(os.path.dirname(filePath)):
        os.makedirs(os.path.dirname(filePath))
      logging.debug('Saving download %s to %s ' % (filename, filePath))
      expectedOutput = TestDataLogic.getUnzippedDirectoryPath(collection, kind)
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        slicer.util.delayDisplay('Requesting download %s from %s...\n' % (filename, url), 1000)
        urllib.urlretrieve(url, filePath)
      if not os.path.exists(expectedOutput) or not len(os.listdir(expectedOutput)):
        logging.debug('Unzipping data into %s' % expectedOutput)
        downloaded[kind] = TestDataLogic.unzipSampleData(filePath, collection, kind)
      else:
        downloaded[kind] = expectedOutput

    return downloaded