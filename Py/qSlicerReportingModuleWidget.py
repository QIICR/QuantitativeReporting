from __main__ import vtk, qt, ctk, slicer

from Helper import *

class qSlicerReportingModuleWidget:
  def __init__( self, parent=None ):

    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout( qt.QVBoxLayout() )
    else:
      self.parent = parent

    self.layout = self.parent.layout()

    # this flag is 1 if there is an update in progress
    self.__updating = 1

    # Reference to the logic
    self.__logic = slicer.modulelogic.vtkSlicerReportingModuleLogic()
    # print 'Logic is ',self.__logic

    if not self.__logic.GetMRMLScene():
      # set the logic's mrml scene
      self.__logic.SetMRMLScene(slicer.mrmlScene)

    if not parent:
      self.setup()
      self.parent.setMRMLScene( slicer.mrmlScene )
      # after setup, be ready for events
      self.__updating = 0

      self.parent.show()

  def setup( self ):
    # Use the logic associated with the module
    #if not self.__logic:
    #  self.__logic = self.parent.module().logic()

    self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    
    '''
    # if we don't like the parent widget layout
    w = qt.QWidget()
    layout = qt.QFormLayout()
    w.setLayout(layout)
    self.layout.addWidget(w)
    w.show()
    self.layout = layout
    '''
    
    self.__inputFrame = ctk.ctkCollapsibleButton()
    self.__inputFrame.text = "Input"
    self.__inputFrame.collapsed = 0
    inputFrameLayout = qt.QFormLayout(self.__inputFrame)
    
    self.layout.addWidget(self.__inputFrame)

    '''
    Report MRML node, will contain:
     -- pointer to the markup elements hierarchy head
    On updates:
     -- reset the content of the widgets
     -- existing content repopulated from the node
    '''
    label = qt.QLabel('Report: ')
    self.__reportSelector = slicer.qMRMLNodeComboBox()
    self.__reportSelector.nodeTypes =  ['vtkMRMLReportingReportNode']
    self.__reportSelector.setMRMLScene(slicer.mrmlScene)
    self.__reportSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    self.__reportSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onReportNodeChanged)
    self.__reportSelector.addEnabled = 1
    
    inputFrameLayout.addRow(label, self.__reportSelector)
 
    '''
    Choose the volume being annotated.
    Will need to handle selection change:
      -- on new, update viewers, create storage node 
      -- on swich ask if the previous report should be saved
    TODO: disable this unless Report selector is initialized!
    '''
    label = qt.QLabel('Annotated volume: ')
    self.__volumeSelector = slicer.qMRMLNodeComboBox()
    self.__volumeSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    self.__volumeSelector.setMRMLScene(slicer.mrmlScene)
    self.__volumeSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    # todo: move the connection to the report drop down
    self.__volumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onAnnotatedVolumeNodeChanged)
    self.__volumeSelector.addEnabled = 0
    
    inputFrameLayout.addRow(label, self.__volumeSelector)



    self.__annotationsFrame = ctk.ctkCollapsibleButton()
    self.__annotationsFrame.text = "Annotations"
    self.__annotationsFrame.collapsed = 0
    annotationsFrameLayout = qt.QFormLayout(self.__annotationsFrame)
    
    self.layout.addWidget(self.__annotationsFrame)


    self.__markupFrame = ctk.ctkCollapsibleButton()
    self.__markupFrame.text = "Markup"
    self.__markupFrame.collapsed = 0
    markupFrameLayout = qt.QFormLayout(self.__markupFrame)
    
    self.layout.addWidget(self.__markupFrame)
 
    # Add the tree widget
    self.__markupTreeView = slicer.qMRMLTreeView()
    self.__markupTreeView.setMRMLScene(self.__logic.GetMRMLScene())
    nodeTypes = ['vtkMRMLDisplayableHierarchyNode', 'vtkMRMLAnnotationHierarchyNode', 'vtkMRMLAnnotationNode', 'vtkMRMLVolumeNode', 'vtkMRMLReportingReportNode']
    self.__markupTreeView.nodeTypes = nodeTypes
    self.__markupTreeView.listenNodeModifiedEvent = 1
    self.__markupTreeView.sceneModelType = "Displayable"
    # show these nodes even if they're hidden by being children of hidden hierarchy nodes
    showHiddenNodeTypes = ['vtkMRMLAnnotationNode', 'vtkMRMLVolumeNode', 'vtkMRMLDisplayableHierarchyNode'] 
    self.__markupTreeView.model().showHiddenForTypes = showHiddenNodeTypes    

    markupFrameLayout.addRow(self.__markupTreeView)

    # save/load report using AIM XML serialization
    button = qt.QPushButton('Save Report')
    button.connect('clicked()', self.onReportImport)
    self.layout.addWidget(button)

    button = qt.QPushButton('Load Report')
    button.connect('clicked()', self.onReportExport)
    self.layout.addWidget(button)

  def enter(self):
    # print "Reporting Enter"
    # update the logic active markup
    vnode = self.__volumeSelector.currentNode()
    if vnode != None:
      # print "Enter: setting active hierarchy from node ",vnode.GetID()
      self.__logic.SetActiveMarkupHierarchyIDFromNode(vnode)
      self.updateTreeView()

  def exit(self):
    # print "Reporting Exit. setting active hierarchy to 0"
    # turn off the active mark up so new annotations can go elsewhere
    self.__logic.SetActiveMarkupHierarchyIDToNull()
     
  # AF: I am not exactly sure what are the situations when MRML scene would
  # change, but I recall handling of this is necessary, otherwise adding
  # nodes from selector would not work correctly
  def onMRMLSceneChanged(self, mrmlScene):
    #self.__volumeSelector.setMRMLScene(slicer.mrmlScene)
    self.__reportSelector.setMRMLScene(slicer.mrmlScene)
    # print 'Current report node: ',self.__reportSelector.currentNode()
    
    # self.onAnnotatedVolumeNodeChanged()
    
    if mrmlScene != self.__logic.GetMRMLScene():
      self.__logic.SetMRMLScene(mrmlScene)
      self.__logic.RegisterNodes()
    # AF: need to look what this means ...
    # self.__logic.GetMRMLManager().SetMRMLScene(mrmlScene)
    
  def updateTreeView(self):
    # make the tree view update
    # self.__markupTreeView.sceneModelType = "Displayable"
    # set the root to be the reporting hierarchy root so don't see the annotation module hierarchies
    rootNode = slicer.mrmlScene.GetFirstNodeByName("Reporting Hierarchy")
    if rootNode:
      self.__markupTreeView.setRootNode(rootNode)

  def onAnnotatedVolumeNodeChanged(self):
    # get the current volume node
    self.__vNode = self.__volumeSelector.currentNode()
    if self.__vNode != None:
      Helper.SetBgFgVolumes(self.__vNode.GetID(), '')
      # TODO: rotate all slices into acq plane
      # print "Calling logic to set up hierarchy"
      self.__logic.InitializeHierarchyForVolume(self.__vNode)
      self.updateTreeView()

  def onReportNodeChanged(self):
    # TODO
    #  -- initialize annotations and markup frames based on the report node
    #  content
    self.__rNode = self.__reportSelector.currentNode()
    # print 'Selected report has changed to ',self.__rNode
    if self.__rNode != None:
      self.__logic.InitializeHierarchyForReport(self.__rNode)
      self.updateTreeView()

  '''
  Load report and initialize GUI based on .xml report file content
  '''
  def onReportImport(self):
    # TODO
    #  -- popup file open dialog to choose the .xml AIM file
    #  -- warn the user if the selected report node is not empty
    #  -- populate the selected report node, initializing annotation template,
    #  content, markup hierarchy and content
    print 'onReportImport'

  '''
  Save report to an xml file
  '''
  def onReportExport(self):
    # TODO
    #  -- popup file dialog prompting output file
    #  -- translate populated annotation frame into AIM
    #  -- traverse markup hierarchy and translate
    print 'onReprtingReportExport'
