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
    <a href=\"http://wiki.slicer.org/slicerWiki/index.php/Documentation/4.2/Extensions/LabelToDICOMSEGConverter\">
    Usage instructions</a>;
    """
    parent.acknowledgementText = """
    This file was originally developed by Andrey Fedorov, supported by  a
    supplement to NCI U01CA151261 (PI Fiona Fennessy).
    """
    self.parent = parent

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

    # Collapsible button
    dummyCollapsibleButton = ctk.ctkCollapsibleButton()
    dummyCollapsibleButton.text = "IO"
    self.layout.addWidget(dummyCollapsibleButton)

    # Layout within the dummy collapsible button
    dummyFormLayout = qt.QFormLayout(dummyCollapsibleButton)

    # Input label node
    label = qt.QLabel('Input label: ')
    self.segmentationSelector = slicer.qMRMLNodeComboBox()
    self.segmentationSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
    self.segmentationSelector.setMRMLScene(slicer.mrmlScene)
    self.segmentationSelector.addEnabled = 0
    self.segmentationSelector.noneEnabled = 1
    self.segmentationSelector.removeEnabled = 0
    self.segmentationSelector.showHidden = 0
    self.segmentationSelector.showChildNodeTypes = 0
    self.segmentationSelector.selectNodeUponCreation = 1
    self.segmentationSelector.connect('currentNodeChanged(vtkMRMLNode*)',self.onInputChanged)
    dummyFormLayout.addRow(label, self.segmentationSelector)

    # Input volume node
    label = qt.QLabel('Input volume: ')
    self.volumeSelector = slicer.qMRMLNodeComboBox()
    self.volumeSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    self.volumeSelector.setMRMLScene(slicer.mrmlScene)
    self.volumeSelector.addEnabled = 0
    self.volumeSelector.noneEnabled = 1
    self.volumeSelector.removeEnabled = 0
    self.volumeSelector.showHidden = 0
    self.volumeSelector.showChildNodeTypes = 0
    self.volumeSelector.selectNodeUponCreation = 0
    self.volumeSelector.addAttribute('vtkMRMLScalarVolumeNode','DICOM.instanceUIDs')
    self.volumeSelector.connect('currentNodeChanged(vtkMRMLNode*)',self.onInputChanged)
    dummyFormLayout.addRow(label, self.volumeSelector)

    # Buttons to save/load report using AIM XML serialization
    label = qt.QLabel('Export folder')
    self.__exportFolderPicker = ctk.ctkDirectoryButton()
    self.__exportFolderPicker.connect('directoryChanged(const QString&)', self.onOutputDirChanged)
    self.exportButton = qt.QPushButton('Export')
    dummyFormLayout.addRow(label, self.__exportFolderPicker)
    dummyFormLayout.addRow(self.exportButton)
    self.exportButton.connect('clicked()', self.onLabelExport)
    self.exportButton.enabled = 1

    # Input hint
    self.__helpLabel = qt.QLabel('Select a label associated with a DICOM volume')
    dummyFormLayout.addRow(self.__helpLabel)

    # Add vertical spacer
    self.layout.addStretch(1)

    self.outputDir = self.__exportFolderPicker.directory

  def onInputChanged(self,newNode):
    pass

  def onOutputDirChanged(self, newDir):
    self.outputDir = newDir

  def onLabelExport(self):
    '''
    TODO: add a check that the selected label is associated with a volume that
    has DICOM.instanceUIDs attribute set
    '''
    
    label = self.segmentationSelector.currentNode()
    scalar = self.volumeSelector.currentNode()

    # assuming here the user does the 
    if label == None or scalar == None:
      self.exportButton.enabled = 0
      return
    
    labelImage = label.GetImageData()
    scalarImage = label.GetImageData()
    lDim = labelImage.GetDimensions()
    sDim = scalarImage.GetDimensions()
    if lDim[0]!=sDim[0] or lDim[1]!=sDim[1] or lDim[2]!=sDim[2]:
      self.__helpLabel.text = 'Geometries do not match'
      return

    label = self.segmentationSelector.currentNode()
    scalar = self.volumeSelector.currentNode()
 
    # need to set up the associated node ID
    label.SetAttribute('AssociatedNodeID', scalar.GetID())

    labelCollection = vtk.vtkCollection()
    labelCollection.AddItem(label)
    reportingLogic = slicer.modules.reporting.logic()
    dirName = self.outputDir
    fileName = reportingLogic.DicomSegWrite(labelCollection, dirName)

    if fileName == '':
      self.__helpLabel.text = 'Error!'
    else:
      self.__helpLabel.text = 'Exported to '+fileName.split('/')[-1]

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
