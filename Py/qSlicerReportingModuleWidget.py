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

    # for export
    self.exportFileName = None
    self.exportFileDialog = None

    if not parent:
      self.setup()
      self.parent.setMRMLScene( slicer.mrmlScene )
      # after setup, be ready for events
      self.__updating = 0

      self.parent.show()


    # initialize parameter node
    self.__parameterNode = None
    nNodes = slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLScriptedModuleNode')
    for n in xrange(nNodes):
      compNode = slicer.mrmlScene.GetNthNodeByClass(n, 'vtkMRMLScriptedModuleNode')
      nodeid = None
      if compNode.GetModuleName() == 'Reporting':
        self.__parameterNode = compNode
        print 'Found existing Reporting parameter node'
        break
    if self.__parameterNode == None:
      self.__parameterNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLScriptedModuleNode')
      self.__parameterNode.SetModuleName('Reporting')
      slicer.mrmlScene.AddNode(self.__parameterNode)
 

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
    self.__reportSelector.addEnabled = 1
    
    inputFrameLayout.addRow(label, self.__reportSelector)

    self.__reportSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    self.__reportSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onReportNodeChanged)
 
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
    # todo: move the connection to the report drop down
    self.__volumeSelector.addEnabled = 0
    
    inputFrameLayout.addRow(label, self.__volumeSelector)

    self.__volumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onAnnotatedVolumeNodeChanged)
    self.__volumeSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)

    self.__annotationsFrame = ctk.ctkCollapsibleButton()
    self.__annotationsFrame.text = "Annotations"
    self.__annotationsFrame.collapsed = 0
    annotationsFrameLayout = qt.QFormLayout(self.__annotationsFrame)
    
    self.layout.addWidget(self.__annotationsFrame)

    self.__annotationWidget = slicer.qMRMLReportingAnnotationRANOWidget()
    self.__annotationWidget.setMRMLScene(slicer.mrmlScene)
    
    annotationsFrameLayout.addRow(self.__annotationWidget)

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
    button = qt.QPushButton('Save Report ...')
    button.connect('clicked()', self.onReportExport)
    self.layout.addWidget(button)

    button = qt.QPushButton('Load Report ...')
    button.connect('clicked()', self.onReportImport)
    self.layout.addWidget(button)

    self.__reportSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.enableWidgets)
    self.__volumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.enableWidgets)
    self.enableWidgets()

  def enter(self):
    # print "Reporting Enter"
    # update the logic active markup
    vnode = self.__volumeSelector.currentNode()
    if vnode != None:
      # print "Enter: setting active hierarchy from node ",vnode.GetID()
      self.__logic.SetActiveMarkupHierarchyIDFromNode(vnode)
      self.updateTreeView()

    self.updateWidgetFromParameters()

  def exit(self):
    self.updateParametersFromWidget()

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
    self.__markupTreeView.sceneModelType = "Displayable"
    # set the root to be the current report hierarchy root 
    rootNodeID = self.__parameterNode.GetParameter('reportID')
    rootNode = slicer.mrmlScene.GetNodeByID(rootNodeID)
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
    # set the volume to be none
    self.__vNode = None
    self.__volumeSelector.setCurrentNode(None)
    if self.__rNode != None:
      self.__logic.InitializeHierarchyForReport(self.__rNode)
      self.updateTreeView()
      vID = self.__logic.GetVolumeIDForReportNode(self.__rNode)
      if vID:
        self.__vNode = slicer.mrmlScene.GetNodeByID(vID)      
        self.__volumeSelector.setCurrentNode(Helper.getNodeByID(vID))
      # get the annotation node for this report
      aID = self.__logic.GetAnnotationIDForReportNode(self.__rNode)
      if aID:
        # set the node on the widget
        self.__annotationNode = slicer.mrmlScene.GetNodeByID(aID)   
        self.__annotationWidget.setMRMLAnnotationNode(self.__annotationNode)
      # hide the markups that go with other report nodes
      self.__logic.HideAnnotationsForOtherReports(self.__rNode)

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
    print 'onReprtingReportExport'
    
    #  -- popup file dialog prompting output file
    if not self.exportFileDialog:
      self.exportFileDialog = qt.QFileDialog(self.parent)
      self.exportFileDialog.acceptMode = 1 # save dialog
      self.exportFileDialog.defaultSuffix = "xml"
      self.exportFileDialog.setNameFilter("AIM XML files (*.xml)")
      self.exportFileDialog.connect("fileSelected(QString)", self.onExportFileSelected)
    self.exportFileDialog.show()

  def onExportFileSelected(self,fileName):
    # use the currently selected report
    self.__rNode = self.__reportSelector.currentNode()
    # TODO
    #  -- translate populated annotation frame into AIM
    md = self.__annotationWidget.measurableDiseaseIndex
    nmd = self.__annotationWidget.nonmeasurableDiseaseIndex
    f = self.__annotationWidget.flairIndex

    print "Indices of interest: ", md,' ',nmd,' ',f

    # get the annotation node and fill it in
    aID = self.__logic.GetAnnotationIDForReportNode(self.__rNode)
    if aID:
      # get the node
      self.__annotationNode = slicer.mrmlScene.GetNodeByID(aID) 
      # TODO: 
      # update the annotation node from te
      # self.__annotationNode = 

    #  -- traverse markup hierarchy and translate
    retval = self.__logic.SaveReportToAIM(self.__rNode, fileName)
    if retval == 0:
      print "Failed to save report to file '",fileName,"'"
    else:
      print "Saved report to file '",fileName,"'"

  def updateWidgetFromParameters(self):
    pn = self.__parameterNode
    if pn == None:
      return
    reportID = pn.GetParameter('reportID')
    volumeID = pn.GetParameter('volumeID')

    if reportID != None:
      self.__reportSelector.setCurrentNode(Helper.getNodeByID(reportID))
    if volumeID != None:
      self.__volumeSelector.setCurrentNode(Helper.getNodeByID(volumeID))

  def updateParametersFromWidget(self):
    pn = self.__parameterNode
    if pn == None:
      return

    report = self.__reportSelector.currentNode()
    volume = self.__volumeSelector.currentNode()
  
    if report != None:
      pn.SetParameter('reportID', report.GetID())
    if volume != None:
      pn.SetParameter('volumeID', volume.GetID())


  def enableWidgets(self):
    report = self.__reportSelector.currentNode()
    volume = self.__volumeSelector.currentNode()

    if report != None:
      self.__volumeSelector.enabled = 1
      
      if volume != None:
        self.__markupFrame.enabled = 1
        self.__annotationsFrame.enabled = 1
      else:
        self.__markupFrame.enabled = 0
        self.__annotationsFrame.enabled = 0

    else:
      self.__volumeSelector.enabled = 0
      self.__markupFrame.enabled = 0
      self.__annotationsFrame.enabled = 0
