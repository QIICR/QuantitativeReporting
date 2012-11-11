import os
import unittest
from __main__ import vtk, qt, ctk, slicer

#
# LabelToDICOMSEGConverter
#

class LabelToDICOMSEGConverter:
  def __init__(self, parent):
    parent.title = "LabelToDICOMSEGConverter" # TODO make this more human readable by adding spaces
    parent.categories = ["Work in Progress.Converters"]
    parent.dependencies = ["Reporting", "DICOM", "Volumes"]
    parent.contributors = ["Andrey Fedorov (Surgical Planning Lab)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = """
    Module to convert a Slicer label map into a DICOM SEG object.
    """
    parent.acknowledgementText = """
    This file was originally developed by Andrey Fedorov, supported by  ...
""" # replace with organization, grant and thanks.
    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['LabelToDICOMSEGConverter'] = self.runTest

  def runTest(self):
    tester = LabelToDICOMSEGConverterTest()
    tester.runTest()

#
# qLabelToDICOMSEGConverterWidget
#

class LabelToDICOMSEGConverterWidget:
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
    #self.reloadButton = qt.QPushButton("Reload")
    #self.reloadButton.toolTip = "Reload this module."
    #self.reloadButton.name = "LabelToDICOMSEGConverter Reload"
    #self.layout.addWidget(self.reloadButton)
    #self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    #self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    #self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    #self.layout.addWidget(self.reloadAndTestButton)
    #self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    # Collapsible button
    dummyCollapsibleButton = ctk.ctkCollapsibleButton()
    dummyCollapsibleButton.text = "IO"
    self.layout.addWidget(dummyCollapsibleButton)

    # Layout within the dummy collapsible button
    dummyFormLayout = qt.QFormLayout(dummyCollapsibleButton)

    # Input hint
    self.__helpLabel = qt.QLabel('Select a label associated with a DICOM volume')
    dummyFormLayout.addRow(self.__helpLabel)

    # Input label node
    label = qt.QLabel('Input label: ')
    self.segmentationSelector = slicer.qMRMLNodeComboBox()
    self.segmentationSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    self.segmentationSelector.setMRMLScene(slicer.mrmlScene)
    self.segmentationSelector.addEnabled = 0
    self.segmentationSelector.noneEnabled = 1
    self.segmentationSelector.removeEnabled = 0
    self.segmentationSelector.showHidden = 0
    self.segmentationSelector.showChildNodeTypes = 0
    self.segmentationSelector.selectNodeUponCreation = 1
    self.segmentationSelector.addAttribute('vtkMRMLScalarVolumeNode','LabelMap',1)
    self.segmentationSelector.addAttribute('vtkMRMLScalarVolumeNode','AssociatedNodeID')
    self.segmentationSelector.connect('currentNodeChanged(vtkMRMLNode*)',self.onInputChanged)
    dummyFormLayout.addRow(label, self.segmentationSelector)

    # Buttons to save/load report using AIM XML serialization
    label = qt.QLabel('Export folder')
    self.__exportFolderPicker = ctk.ctkDirectoryButton()
    self.__exportFolderPicker.connect('directoryChanged(const QString&)', self.onOutputDirChanged)
    self.exportButton = qt.QPushButton('Export')
    dummyFormLayout.addRow(label, self.__exportFolderPicker)
    dummyFormLayout.addRow(self.exportButton)
    self.exportButton.connect('clicked()', self.onLabelExport)
    self.exportButton.enabled = 0

    # Add vertical spacer
    self.layout.addStretch(1)

    self.outputDir = None  

  def onInputChanged(self,newNode):
    label = self.segmentationSelector.currentNode()
    if label == None:
      self.exportButton.enabled = 0
      self.__helpLabel.text = 'Select a label associated with a DICOM volume'
      return

    masterNodeID = label.GetAttribute('AssociatedNodeID')
    if masterNodeID == None or  masterNodeID == '':
      self.exportButton.enabled = 0
      self.__helpLabel.text = 'Selected label does not have an associated volume!'
      return

    masterNode = slicer.mrmlScene.GetNodeByID(masterNodeID)
    dicomUIDs = masterNode.GetAttribute('DICOM.instanceUIDs')
    if dicomUIDs == None or dicomUIDs == '':
      self.exportButton.enabled = 0
      self.__helpLabel.text = 'Selected label is not associated with a DICOM volume!'
      return
    
    self.__helpLabel.text = 'Ready to export the selected label!'
    self.exportButton.enabled = 1
  
  def onOutputDirChanged(self, newDir):
    self.outputDir = newDir

  def onLabelExport(self):
    '''
    TODO: add a check that the selected label is associated with a volume that
    has DICOM.instanceUIDs attribute set
    '''
    label = self.segmentationSelector.currentNode()
    reportingLogic = slicer.modules.reporting.logic()
    dirName = self.outputDir
    
    if label == None:
      print('Input label not defined')
      return
    
    labelCollection = vtk.vtkCollection()
    labelCollection.AddItem(label)
    reportingLogic.DicomSegWrite(labelCollection, dirName)

  def onReload(self,moduleName="LabelToDICOMSEGConverter"):
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

  def onReloadAndTest(self,moduleName="LabelToDICOMSEGConverter"):
    self.onReload()
    evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
    tester = eval(evalString)
    tester.runTest()

#
# LabelToDICOMSEGConverterLogic
#

class LabelToDICOMSEGConverterLogic:
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


class LabelToDICOMSEGConverterTest(unittest.TestCase):
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
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_LabelToDICOMSEGConverter1()

  def test_LabelToDICOMSEGConverter1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
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
        print('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        print('Loading %s...\n' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading\n')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = LabelToDICOMSEGConverterLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
