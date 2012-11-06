
import os
import unittest
import vtk
import qt
import slicer, ctk
import EditorLib

class ReportingSelfTest(unittest.TestCase):
  """ Test for slicer data bundle

Run manually from within slicer by pasting an version of this with the correct path into the python console:
execfile('/Users/pieper/slicer4/latest/Slicer/Applications/SlicerApp/Testing/Python/ReportingSelfTestTest.py'); t = ReportingSelfTest(); t.setUp(); t.runTest()

  """

  def __init__(self,methodName='runTest', useCase='small', uniqueDirectory=True,strict=False):
    """
    Load MRB and check that switching across scene views does not lead to a
    crash

    uniqueDirectory: boolean about save directory
                     False to reuse standard dir name
                     True timestamps dir name
    strict: boolean about how carefully to check result
                     True then check every detail
                     False then confirm basic operation, but allow non-critical issues to pass
    """
    unittest.TestCase.__init__(self,methodName)
    self.uniqueDirectory = uniqueDirectory
    self.strict = strict
    self.useCase = useCase

  def delayDisplay(self,message,msec=1000):
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    self.setUp()
    self.test_ReportingSelfTest()
    self.test_PercentEncode()


  def test_ReportingSelfTest(self):
    """
    Replicate one of the crashes in issue 2512
    """

    print("Running ReportingSelfTest Test case with:")
    print("uniqueDirectory : %s" % self.uniqueDirectory)
    print("strict : %s" % self.strict)

    import urllib

    if self.useCase == 'small':
      downloads = (
          ('http://slicer.kitware.com/midas3/download?items=10706', '1.dcm'),
          ('http://slicer.kitware.com/midas3/download?items=10707', '2.dcm'),
          ('http://slicer.kitware.com/midas3/download?items=10708', '3.dcm'),
       )

    # perform the downloads if needed, then load
    inputDataDir = self.tempDirectory('ReportingInputDICOM')
    for url,name in downloads:
      filePath = inputDataDir + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        self.delayDisplay('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
 
    # perform the downloads if needed, then load
    slicer.mrmlScene.Clear(0)
    appLogic = slicer.app.applicationLogic()
    self.delayDisplay('Done loading data! Will now open the bundle')

    # create a new DICOM DB
    self.delayDisplay('Initializing a temporary DICOM DB')
    dicomDBDir = self.tempDirectory('ReportingDICOMDB')
    if not os.access(dicomDBDir, os.F_OK):
      os.mkdir(dicomDBDir)
    
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
    dicomWidget.onDatabaseDirectoryChanged(dicomDBDir)
    self.assertTrue(slicer.dicomDatabase.isOpen)

    initialized = slicer.dicomDatabase.initializeDatabase()
    self.assertTrue(initialized)

    # add test data to the db
    indexer = ctk.ctkDICOMIndexer()
    self.assertTrue(indexer)

    indexer.addDirectory(slicer.dicomDatabase, inputDataDir)
    indexer.waitForImportFinished()

    self.assertTrue(len(slicer.dicomDatabase.patients()) == 1)
    self.assertTrue(slicer.dicomDatabase.patients()[0])

    # load input data
    detailsPopup = slicer.modules.dicom.widgetRepresentation().self().detailsPopup
    detailsPopup.offerLoadables( slicer.dicomDatabase.patients()[0], "Patient" )

    loadables = detailsPopup.loadableTable.loadables
    self.assertTrue( len(loadables) == 4 )
    
    detailsPopup.loadCheckedLoadables()

    volumes = slicer.util.getNodes('vtkMRMLScalarVolumeNode*')
    self.assertTrue(len(volumes) == 1)

    (name,volume) = volumes.items()[0]
    self.delayDisplay('Loaded volume name %s' % volume.GetName())

    self.delayDisplay('Configure Module')
    mainWindow = slicer.util.mainWindow()
    mainWindow.moduleSelector().selectModule('Reporting')

    reporting = slicer.modules.reporting.widgetRepresentation().self()

    report = slicer.mrmlScene.CreateNodeByClass('vtkMRMLReportingReportNode')
    report.SetReferenceCount(report.GetReferenceCount()-1)

    reporting.reportSelector.setCurrentNode(report)
    slicer.app.processEvents()
    reporting.volumeSelector.setCurrentNode(volume)
    slicer.app.processEvents()

    # add fiducial
    fidNode = slicer.vtkMRMLAnnotationFiducialNode()
    fidName = "AIM Round Trip Test Fiducial"
    fidNode.SetName(fidName)
    fidNode.SetSelected(1)
    fidNode.SetDisplayVisibility(1)
    fidNode.SetLocked(0)
    print("Calling set fid coords")
    startCoords = [15.8, 70.8, -126.7]    
    fidNode.SetFiducialCoordinates(startCoords[0],startCoords[1],startCoords[2])
    print("Starting fiducial coordinates: "+str(startCoords))
    slicer.mrmlScene.AddNode(fidNode)

    # add ruler
    rulerNode = slicer.vtkMRMLAnnotationRulerNode()
    rulerNode.SetName('Test Ruler')
    rulerNode.SetPosition1(-21.59, -104.097, -126.69)
    rulerNode.SetPosition2(-84.36, 87.709, -126.69)
    slicer.mrmlScene.AddNode(rulerNode)
    slicer.app.processEvents()

    self.delayDisplay('Check Reporting table!', 5000)
    
    # add label node
    volumesLogic = slicer.modules.volumes.logic()
    labelNode = volumesLogic.CreateAndAddLabelVolume(slicer.mrmlScene, volume, "Segmentation")
    labelDisplayNode = labelNode.GetDisplayNode()
    labelDisplayNode.SetAndObserveColorNodeID('vtkMRMLColorTableNodeFileGenericAnatomyColors.txt')
    reporting.segmentationSelector.setCurrentNode(labelNode)

    slicer.mrmlScene.Clear(0)
    self.delayDisplay('Test passed')

  def tempDirectory(self,key='__SlicerReportingTestTemp__',tempDir=None):
    """Come up with a unique directory name in the temp dir and make it and return it
    # TODO: switch to QTemporaryDir in Qt5.
    # For now, create a named directory if uniqueDirectory attribute is true
    Note: this directory is not automatically cleaned up
    """
    if not tempDir:
      tempDir = qt.QDir(slicer.app.temporaryPath)
    tempDirName = key
    if self.uniqueDirectory:
      key += qt.QDateTime().currentDateTime().toString("yyyy-MM-dd_hh+mm+ss.zzz")
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), tempDirName)
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath


#
# ReportingSelfTestTest
#

class ReportingSelfTestTest:
  """
  This class is the 'hook' for slicer to detect and recognize the test
  as a loadable scripted module (with a hidden interface)
  """
  def __init__(self, parent):
    parent.title = "ReportingSelfTestTest"
    parent.categories = ["Testing"]
    parent.contributors = ["Andrey Fedorov (SPL)"]
    parent.helpText = """
    Self-test for RSNA2012 Reporting Demo
    No module interface here, only used in SelfTests module
    """
    parent.acknowledgementText = """
    """

    # don't show this module
    parent.hidden = True

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['ReportingSelfTestTest'] = self.runTest

  def runTest(self):
    tester = ReportingSelfTest()
    tester.setUp()
    tester.runTest()


#
# ReportingSelfTestTestWidget
#

class ReportingSelfTestTestWidget:
  def __init__(self, parent = None):
    self.parent = parent

  def setup(self):
    # don't display anything for this widget - it will be hidden anyway
    pass

  def enter(self):
    pass

  def exit(self):
    pass


