import os
import unittest
from __main__ import vtk, qt, ctk, slicer

#
# ReportingSelfTest
#

class ReportingSelfTest:
  def __init__(self, parent):
    parent.title = "ReportingSelfTest" # TODO make this more human readable by adding spaces
    parent.categories = ["Work in Progress.Informatics.TestCases"]
    parent.dependencies = []
    parent.contributors = ["Steve Pieper (Isomics)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = """
    This module was developed as a self test to perform the operations needed for the RSNA 2012 Visualization Tutorial
    """
    parent.acknowledgementText = """
    This file was originally developed by Steve Pieper, Isomics, Inc.  and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.
    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['ReportingSelfTest'] = self.runTest
    print slicer.selfTests

  def runTest(self):
    tester = ReportingSelfTestTest()
    tester.runTest()

#
# qReportingSelfTestWidget
#

class ReportingSelfTestWidget:
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
    self.reloadButton.name = "ReportingSelfTest Reload"
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
    tests = ( ("Reporting test 1",self.onReportingTest1),)
    for text,slot in tests:
      testButton = qt.QPushButton(text)
      testButton.toolTip = "Run the test."
      formLayout.addWidget(testButton)
      testButton.connect('clicked(bool)', slot)

    # Add vertical spacer
    self.layout.addStretch(1)

  def onReportingTest1(self):
    tester = ReportingSelfTestTest()
    tester.runTest()

  def onReload(self,moduleName="ReportingSelfTest"):
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

  def onReloadAndTest(self,moduleName="ReportingSelfTest"):
    self.onReload()
    evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
    tester = eval(evalString)
    tester.runTest()

#
# ReportingSelfTestLogic
#

class ReportingSelfTestLogic:
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


class ReportingSelfTestTest(unittest.TestCase):
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
    self.test_ReportingAIMRoundTrip()
    '''
    self.test_Part2Setup()
    self.test_Part3PlaceMarkups()
    self.restorDICOMDirectory()
    '''

  def test_ReportingAIMRoundTrip(self):
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

    reportingTempDir = slicer.app.temporaryPath+'/Reporting'
    qt.QDir().mkpath(reportingTempDir)
    dicomFilesDirectory = reportingTempDir + '/dicomFiles'
    qt.QDir().mkpath(dicomFilesDirectory)
    slicer.app.applicationLogic().Unzip(filePath, dicomFilesDirectory)

    try:
      self.delayDisplay("Switching to temp database directory")
      tempDatabaseDirectory = reportingTempDir + '/tempDICOMDatbase'
      qt.QDir().mkpath(tempDatabaseDirectory)
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
      dicomWidget.dicomApp.suspendModel()
      indexer = ctk.ctkDICOMIndexer()
      indexer.addDirectory(slicer.dicomDatabase, dicomFilesDirectory, None)
      indexer.waitForImportFinished()
      dicomWidget.dicomApp.resumeModel()
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
      mainWindow.moduleSelector().selectModule('Reporting')
  
      reporting = slicer.modules.reporting.widgetRepresentation().self()

      report = slicer.mrmlScene.CreateNodeByClass('vtkMRMLReportingReportNode')
      report.SetReferenceCount(report.GetReferenceCount()-1)
      slicer.mrmlScene.AddNode(report)
      report.SetFindingLabel(7)
  
      reporting.reportSelector.setCurrentNode(report)
      self.delayDisplay('Setting volume to %s' % volume.GetName())
      reporting.volumeSelector.setCurrentNode(volume)
      slicer.app.processEvents()

      # place some markups and add a segmentation label

      # add fiducial
      fidNode = slicer.vtkMRMLAnnotationFiducialNode()
      fidName = "AIM Round Trip Test Fiducial"
      fidNode.SetName(fidName)
      fidNode.SetSelected(1)
      fidNode.SetDisplayVisibility(1)
      fidNode.SetLocked(0)
      # TODO: ask Nicole where this is assigned in the regular workflow
      fidNode.SetAttribute('AssociatedNodeID',volume.GetID())
      print("Calling set fid coords")
      startCoords = [15.8, 70.8, -126.7]    
      fidNode.SetFiducialCoordinates(startCoords[0],startCoords[1],startCoords[2])
      print("Starting fiducial coordinates: "+str(startCoords))
      slicer.mrmlScene.AddNode(fidNode)
  
      # add ruler
      rulerNode = slicer.vtkMRMLAnnotationRulerNode()
      rulerNode.SetName('Test Ruler')
      m = vtk.vtkMatrix4x4()
      volume.GetIJKToRASMatrix(m)
      ijk0 = [0,0,1,1]
      ijk1 = [50,50,1,1]
      ras0 = m.MultiplyPoint(ijk0)
      ras1 = m.MultiplyPoint(ijk1)
      rulerNode.SetPosition1(19.386751174926758, 68.528785705566406, -127.69000244140625)
      rulerNode.SetPosition2(132.72709655761719, -34.349384307861328, -127.69000244140625)
      rulerNode.SetAttribute('AssociatedNodeID',volume.GetID())
      slicer.mrmlScene.AddNode(rulerNode)
      slicer.app.processEvents()

      # add label node
      volumesLogic = slicer.modules.volumes.logic()
      labelNode = volumesLogic.CreateAndAddLabelVolume(slicer.mrmlScene, volume, "Segmentation")
      labelDisplayNode = labelNode.GetDisplayNode()
      labelDisplayNode.SetAndObserveColorNodeID('vtkMRMLColorTableNodeFileGenericAnatomyColors.txt')
      image = volume.GetImageData()
      thresh = vtk.vtkImageThreshold()
      thresh.SetInput(image)
      thresh.ThresholdBetween(10,400)
      thresh.SetInValue(report.GetFindingLabel())
      thresh.SetOutValue(0)
      thresh.Update()
      labelNode.SetAndObserveImageData(thresh.GetOutput())
      reporting.segmentationSelector.setCurrentNode(labelNode)

      # Save the report

      exportDir = reportingTempDir+'/Output'
      qt.QDir().mkpath(exportDir)
      report.SetStorageDirectoryName(exportDir)
      reportingLogic = slicer.modules.reporting.logic()
      reportingLogic.SaveReportToAIM(report)

      self.delayDisplay('Report saved')
      
      slicer.mrmlScene.Clear(0)

      # parse on patient level, find segmentation object, load and make sure
      # it matches the input
      # close the scene and load the report, check consistency

      # try to load back the saved AIM
      import glob
      print glob.glob(exportDir+'/*')      
      xmlFiles = glob.glob(exportDir+'/*xml')
      print xmlFiles

      self.assertTrue(len(xmlFiles) == 1)
      reporting.importAIMFile = xmlFiles[0]
      reporting.onReportImport()

      self.delayDisplay('Report loaded from AIM! Test passed.')
      
      self.delayDisplay("Restoring original database directory")
      if self.originalDatabaseDirectory:
        dicomWidget.onDatabaseDirectoryChanged(self.originalDatabaseDirectory)

    except Exception, e:
      import traceback
      traceback.print_exc()
      self.delayDisplay('Test caused exception!\n' + str(e))
