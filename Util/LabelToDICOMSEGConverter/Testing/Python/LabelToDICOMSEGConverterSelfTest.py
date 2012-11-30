import os
import unittest
from __main__ import vtk, qt, ctk, slicer

#
# LabelToDICOMSEGConverterSelfTest
#

class LabelToDICOMSEGConverterSelfTest:
  def __init__(self, parent):
    parent.title = "LabelToDICOMSEGConverterSelfTest" # TODO make this more human readable by adding spaces
    parent.categories = ["Work in Progress.Informatics.TestCases"]
    parent.dependencies = ['Reporting','DICOM','Volumes']
    parent.contributors = ["Andrey Fedorov (SPL)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = """
    Self-test for the Reporting module
    """
    parent.acknowledgementText = """
    This file was originally developed by Andrey Fedorov
""" # replace with organization, grant and thanks.
    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['LabelToDICOMSEGConverterSelfTest'] = self.runTest
    print slicer.selfTests

  def runTest(self):
    tester = LabelToDICOMSEGConverterSelfTestTest()
    tester.runTest()

#
# qLabelToDICOMSEGConverterSelfTestWidget
#

class LabelToDICOMSEGConverterSelfTestWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

  def setup(self):
    # Instantiate and connect widgets ...

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "LabelToDICOMSEGConverterSelfTest Reload"
    self.layout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    self.layout.addWidget(self.reloadAndTestButton)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    # Collapsible button
    testsCollapsibleButton = ctk.ctkCollapsibleButton()
    testsCollapsibleButton.text = "A collapsible button"
    self.layout.addWidget(testsCollapsibleButton)

    # Layout within the collapsible button
    formLayout = qt.QFormLayout(testsCollapsibleButton)

    # test buttons
    tests = ( ("LabelToDICOMSEGConverter test 1",self.onReportingTest1),)
    for text,slot in tests:
      testButton = qt.QPushButton(text)
      testButton.toolTip = "Run the test."
      formLayout.addWidget(testButton)
      testButton.connect('clicked(bool)', slot)

    # Add vertical spacer
    self.layout.addStretch(1)

  def onReportingTest1(self):
    tester = LabelToDICOMSEGConverterSelfTestTest()
    tester.runTest()

  def onReload(self,moduleName="LabelToDICOMSEGConverterSelfTest"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer

    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    print('Reloading file %s' % filePath)
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)
    # create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()

  def onReloadAndTest(self,moduleName="LabelToDICOMSEGConverterSelfTest"):
    self.onReload()
    evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
    tester = eval(evalString)
    tester.runTest()

#
# LabelToDICOMSEGConverterSelfTestLogic
#

class LabelToDICOMSEGConverterSelfTestLogic:
  """This class should implement all the actual 
  computation done by your module.  The interface 
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    pass

  def hasImageData(self,volumeNode):
    """This is a dummy logic method that 
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      print('no volume node')
      return False
    if volumeNode.GetImageData() == None:
      print('no image data')
      return False
    return True


class LabelToDICOMSEGConverterSelfTestTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
  """

  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    self.delayDisplay("Closing the scene")
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView)
    slicer.mrmlScene.Clear(0)

  def clickAndDrag(self,widget,button='Left',start=(10,10),end=(10,40),steps=20,modifiers=[]):
    """Send synthetic mouse events to the specified widget (qMRMLSliceWidget or qMRMLThreeDView)
    button : "Left", "Middle", "Right", or "None"
    start, end : window coordinates for action
    steps : number of steps to move in
    modifiers : list containing zero or more of "Shift" or "Control"
    """
    style = widget.interactorStyle()
    interator = style.GetInteractor()
    if button == 'Left':
      down = style.OnLeftButtonDown
      up = style.OnLeftButtonUp
    elif button == 'Right':
      down = style.OnRightButtonDown
      up = style.OnRightButtonUp
    elif button == 'Middle':
      down = style.OnMiddleButtonDown
      up = style.OnMiddleButtonUp
    elif button == 'None' or not button:
      down = lambda : None
      up = lambda : None
    else:
      raise Exception("Bad button - should be Left or Right, not %s" % button)
    if 'Shift' in modifiers:
      interator.SetShiftKey(1)
    if 'Control' in modifiers:
      interator.SetControlKey(1)
    interator.SetEventPosition(*start)
    down()
    for step in xrange(steps):
      frac = float(step)/steps
      x = int(start[0] + frac*(end[0]-start[0]))
      y = int(start[1] + frac*(end[1]-start[1]))
      interator.SetEventPosition(x,y)
      style.OnMouseMove()
    up()
    interator.SetShiftKey(0)
    interator.SetControlKey(0)


  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_LabelToDICOMSEGConverterRoundTrip()
    '''
    self.test_Part2Setup()
    self.test_Part3PlaceMarkups()
    self.restorDICOMDirectory()
    '''

  def test_LabelToDICOMSEGConverterRoundTrip(self):
    print("CTEST_FULL_OUTPUT")

    dir(slicer.modules)

    """ Load the data using DICOM module
    """

    import os
    self.delayDisplay("Starting the DICOM test")
    #
    # first, get the data - a zip file of dicom data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=10881', 'JANCT-CT.zip'),
        )

    self.delayDisplay("Downloading")
    for url,name in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        self.delayDisplay('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
    self.delayDisplay('Finished with download\n')

    reportingTempDir = slicer.app.temporaryPath+'/LabelToDICOMSEGConverter'
    qt.QDir().mkpath(reportingTempDir)
    dicomFilesDirectory = reportingTempDir + '/dicomFiles'
    self.cleanupDir(dicomFilesDirectory)
    qt.QDir().mkpath(dicomFilesDirectory)
    slicer.app.applicationLogic().Unzip(filePath, dicomFilesDirectory)

    try:
      self.delayDisplay("Switching to temp database directory")
      tempDatabaseDirectory = reportingTempDir + '/tempDICOMDatbase'
      qt.QDir().mkpath(tempDatabaseDirectory)
      self.cleanupDir(tempDatabaseDirectory)
      if slicer.dicomDatabase:
        self.originalDatabaseDirectory = os.path.split(slicer.dicomDatabase.databaseFilename)[0]
      else:
        self.originalDatabaseDirectory = None
        settings = qt.QSettings()
        settings.setValue('DatabaseDirectory', tempDatabaseDirectory)
      dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
      dicomWidget.onDatabaseDirectoryChanged(tempDatabaseDirectory)

      self.delayDisplay('Importing DICOM')
      mainWindow = slicer.util.mainWindow()
      mainWindow.moduleSelector().selectModule('DICOM')

      self.importDICOM(slicer.dicomDatabase, dicomFilesDirectory)
      '''
      dicomWidget.dicomApp.suspendModel()
      indexer = ctk.ctkDICOMIndexer()
      indexer.addDirectory(slicer.dicomDatabase, dicomFilesDirectory, None)
      indexer.waitForImportFinished()
      dicomWidget.dicomApp.resumeModel()
      '''

      dicomWidget.detailsPopup.open()
      # click on the first row of the tree
      index = dicomWidget.tree.indexAt(qt.QPoint(0,0))
      dicomWidget.onTreeClicked(index)

      self.delayDisplay('Loading Selection')
      dicomWidget.detailsPopup.loadCheckedLoadables()

      # initialize the module with the report and volume
      
      volumes = slicer.util.getNodes('vtkMRMLScalarVolumeNode*')
      self.assertTrue(len(volumes) == 1)

      (name,volume) = volumes.items()[0]
      self.delayDisplay('Loaded volume name %s' % volume.GetName())

      self.delayDisplay('Configure Module')
      mainWindow = slicer.util.mainWindow()
      mainWindow.moduleSelector().selectModule('LabelToDICOMSEGConverter')
  
      module = slicer.modules.labeltodicomsegconverter.widgetRepresentation().self()

      # add label node
      volumesLogic = slicer.modules.volumes.logic()
      labelNode = volumesLogic.CreateAndAddLabelVolume(slicer.mrmlScene, volume, "Segmentation")
      labelNode.SetAttribute('AssociatedNodeID', volume.GetID())
      labelDisplayNode = labelNode.GetDisplayNode()
      labelDisplayNode.SetAndObserveColorNodeID('vtkMRMLColorTableNodeFileGenericAnatomyColors.txt')
      image = volume.GetImageData()
      thresh = vtk.vtkImageThreshold()
      thresh.SetInput(image)
      thresh.ThresholdBetween(10,400)
      thresh.SetInValue(10)
      thresh.SetOutValue(0)
      thresh.Update()
      labelNode.SetAndObserveImageData(thresh.GetOutput())
      module.segmentationSelector.setCurrentNode(labelNode)
      module.volumeSelector.setCurrentNode(volume)

      self.delayDisplay('Input label initialized')

      module.outputDir = reportingTempDir+'/Output'

      # Save the report

      exportDir = reportingTempDir+'/Output'
      qt.QDir().mkpath(exportDir)
      self.cleanupDir(exportDir)
      module.onLabelExport()

      self.delayDisplay('Report saved')

      self.importDICOM(slicer.dicomDatabase, exportDir)
      
      slicer.mrmlScene.Clear(0)
  
      # try to load back the segmentation from DICOM module
      dicomWidget.detailsPopup.open()
      index = dicomWidget.tree.indexAt(qt.QPoint(0,0))
      dicomWidget.onTreeClicked(index)

      self.delayDisplay('Wait',10000)

      dicomWidget.detailsPopup.loadCheckedLoadables()
      volumes = slicer.util.getNodes('vtkMRMLScalarVolumeNode*')
      for n,v in volumes.items():
        print('Volume found: '+v.GetID())
      self.assertTrue(len(volumes) == 2)
      
      for name,volume in volumes.items():
        if volume.GetAttribute('Label') == '1':
          image = volume.GetImageData()
          previousImage = thresh.GetOutput()
          diff = vtk.vtkImageDifference()
          diff.SetInput(thresh.GetOutput())
          diff.SetImage(image)
          diff.Update()
          if diff.GetThresholdedError() > 1:
            self.delayDisplay('Reloaded image does not match')
            self.assertTrue(False)

      self.delayDisplay('Test passed')
      
      self.delayDisplay("Restoring original database directory")
      if self.originalDatabaseDirectory:
        dicomWidget.onDatabaseDirectoryChanged(self.originalDatabaseDirectory)

    except Exception, e:
      if self.originalDatabaseDirectory:
        dicomWidget.onDatabaseDirectoryChanged(self.originalDatabaseDirectory)
      import traceback
      traceback.print_exc()
      self.delayDisplay('Test caused exception!\n' + str(e))
      self.assertTrue(False)
      
  def cleanupDir(self, d):
    if not os.path.exists(d):
      return
    oldFiles = os.listdir(d)
    for f in oldFiles:
      path = d+'/'+f
      if not os.path.isdir(path):
        os.unlink(d+'/'+f)

  def importDICOM(self, dicomDatabase, dicomFilesDirectory):
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
    dicomWidget.dicomApp.suspendModel()
    indexer = ctk.ctkDICOMIndexer()
    indexer.addDirectory(dicomDatabase, dicomFilesDirectory, None)
    indexer.waitForImportFinished()
    dicomWidget.dicomApp.resumeModel()
