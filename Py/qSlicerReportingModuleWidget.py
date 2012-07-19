from __main__ import vtk, qt, ctk, slicer

from SlicerReportingModuleWidgetHelper import SlicerReportingModuleWidgetHelper as Helper
from EditColor import *

EXIT_SUCCESS=0

class qSlicerReportingModuleWidget:
  def __init__( self, parent=None ):

    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout( qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
      self.layout = self.parent.layout()
      self.setup()
      self.parent.show()
    else:
      self.parent = parent
      self.layout = parent.layout()

    # Reference to the logic that Slicer instantiated
    self.__logic  = slicer.modules.reporting.logic()
    if not self.__logic:
      # create a new instance
      self.__logic = slicer.modulelogic.vtkSlicerReportingModuleLogic()

    if self.__logic.InitializeDICOMDatabase():
      Helper.Info('DICOM database initialized correctly!')
    else:
      Helper.Error('Failed to initialize DICOM database!')

    if not self.__logic.GetMRMLScene():
      # set the logic's mrml scene
      self.__logic.SetMRMLScene(slicer.mrmlScene)

    # for export
    self.exportFileName = None
    self.exportFileDialog = None

    # initialize parameter node
    self.__parameterNode = None
    nNodes = slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLScriptedModuleNode')
    for n in xrange(nNodes):
      compNode = slicer.mrmlScene.GetNthNodeByClass(n, 'vtkMRMLScriptedModuleNode')
      nodeid = None
      if compNode.GetModuleName() == 'Reporting':
        self.__parameterNode = compNode
        'Found existing Reporting parameter node'
        break
    if self.__parameterNode == None:
      self.__parameterNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLScriptedModuleNode')
      self.__parameterNode.SetReferenceCount(self.__parameterNode.GetReferenceCount()-1)
      self.__parameterNode.SetModuleName('Reporting')
      slicer.mrmlScene.AddNode(self.__parameterNode)

      # keep active report and volume
      self.__rNode = None
      self.__vNode = None

    if self.__parameterNode != None:
      paramID = self.__parameterNode.GetID()
      self.__logic.SetActiveParameterNodeID(paramID)
    else:
      Helper.Error('Unable to set logic active parameter node')

  def setup( self ):
    #
    # Input frame
    #
    self.__inputFrame = ctk.ctkCollapsibleButton()
    self.__inputFrame.text = "Input"
    self.__inputFrame.collapsed = 0
    inputFrameLayout = qt.QFormLayout(self.__inputFrame)
    
    self.layout.addWidget(self.__inputFrame)

    # Active report node
    label = qt.QLabel('Report: ')
    self.__reportSelector = slicer.qMRMLNodeComboBox()
    self.__reportSelector.nodeTypes =  ['vtkMRMLReportingReportNode']
    self.__reportSelector.setMRMLScene(slicer.mrmlScene)
    self.__reportSelector.addEnabled = 1
    
    inputFrameLayout.addRow(label, self.__reportSelector)

    self.__reportSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    self.__reportSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onReportNodeChanged)
 
    # Volume being annotated (only one is allowed for the report)
    label = qt.QLabel('Annotated volume: ')
    self.__volumeSelector = slicer.qMRMLNodeComboBox()
    self.__volumeSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    self.__volumeSelector.setMRMLScene(slicer.mrmlScene)
    self.__volumeSelector.addEnabled = 0
    
    inputFrameLayout.addRow(label, self.__volumeSelector)

    self.__volumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onAnnotatedVolumeNodeChanged)
    self.__volumeSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)

    #
    # Annotation frame -- vocabulary-based description of what is
    # being annotated/marked up in this report
    #
    self.__annotationsFrame = ctk.ctkCollapsibleButton()
    self.__annotationsFrame.text = "Annotation"
    self.__annotationsFrame.collapsed = 0
    annotationsFrameLayout = qt.QFormLayout(self.__annotationsFrame)
    
    self.layout.addWidget(self.__annotationsFrame)

    self.__defaultColorNode = self.__logic.GetDefaultColorNode()

    self.__toolsColor = EditColor(self.__annotationsFrame,colorNode=self.__defaultColorNode)

    #
    # Markup frame -- summary of all the markup elements contained in the
    # report
    #
    self.__markupFrame = ctk.ctkCollapsibleButton()
    self.__markupFrame.text = "Markup"
    self.__markupFrame.collapsed = 0
    markupFrameLayout = qt.QFormLayout(self.__markupFrame)
    
    self.layout.addWidget(self.__markupFrame)

    # Add a flag to switch between different tree view models
    self.__useNewTreeView = 1

    # Add the tree widget
    if self.__useNewTreeView == 1:
      self.__markupTreeView = slicer.modulewidget.qMRMLReportingTreeView()
      self.__markupTreeView.sceneModelType = "DisplayableHierarchy"
    else:
      self.__markupTreeView = slicer.qMRMLTreeView()
      self.__markupTreeView.sceneModelType = "Displayable"
    self.__markupTreeView.setMRMLScene(self.__logic.GetMRMLScene())
        
    markupFrameLayout.addRow(self.__markupTreeView)

    # Buttons to save/load report using AIM XML serialization
    button = qt.QPushButton('Save Report into AIM format...')
    button.connect('clicked()', self.onReportExport)
    self.layout.addWidget(button)

    button = qt.QPushButton('Load Report from AIM format...')
    button.connect('clicked()', self.onReportImport)
    self.layout.addWidget(button)

    self.__reportSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.updateWidgets)
    self.__volumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.updateWidgets)
    self.updateWidgets()

  def enter(self):
    # switch to Two-over-Two layout
    lm = slicer.app.layoutManager()
    lm.setLayout(26) # two over two

    # update the logic to know that the module has been entered
    self.__logic.GUIHiddenOff()
    self.updateWidgetFromParameters()

    # respond to error events
    Helper.Info('Enter: Setting up connection to respond to logic error events')
    hasObserver = self.__logic.HasObserver(vtk.vtkCommand.ErrorEvent)
    if hasObserver == 0:
      tag = self.__logic.AddObserver(vtk.vtkCommand.ErrorEvent, self.respondToErrorMessage)
      # print '\tobserver tag = ',tag
    else:
      Helper.Debug('Logic already has an observer on the ErrorEvent')

    vnode = self.__volumeSelector.currentNode()
    if vnode != None:
      # print "Enter: setting active hierarchy from node ",vnode.GetID()
      # update the logic active markup
      self.__logic.SetActiveMarkupHierarchyIDFromNode(vnode)
      self.updateTreeView()


  def exit(self):
    self.updateParametersFromWidget()

    Helper.Debug("Reporting Exit. Letting logic know that module has been exited")
    # let the module logic know that the GUI is hidden, so that fiducials can go elsewehre
    self.__logic.GUIHiddenOn()
    # disconnect observation
    self.__logic.RemoveObservers(vtk.vtkCommand.ErrorEvent)

  # respond to error events from the logic
  def respondToErrorMessage(self, caller, event):
    errorMessage = self.__logic.GetErrorMessage()
    Helper.Debug('respondToErrorMessage, event = '+str(event)+', message =\n\t'+str(errorMessage))
    # popup only if the message is not empty
    if errorMessage != None:
      errorDialog = qt.QErrorMessage(self.parent)
      errorDialog.showMessage(errorMessage)
    
  def onMRMLSceneChanged(self, mrmlScene):
    if mrmlScene != self.__logic.GetMRMLScene():
      self.__logic.SetMRMLScene(mrmlScene)
      self.__logic.RegisterNodes()
    self.__reportSelector.setMRMLScene(slicer.mrmlScene)
    
  def updateTreeView(self):
    # make the tree view update
    if self.__useNewTreeView == 1:
      self.__markupTreeView.updateTreeView()
    else:
      self.__markupTreeView.sceneModelType = "Displayable"
      nodeTypes = ['vtkMRMLDisplayableHierarchyNode', 'vtkMRMLAnnotationHierarchyNode', 'vtkMRMLAnnotationNode', 'vtkMRMLVolumeNode', 'vtkMRMLReportingReportNode']
      self.__markupTreeView.nodeTypes = nodeTypes
      self.__markupTreeView.listenNodeModifiedEvent = 1      
      self.__markupTreeView.sceneModelType = "Displayable"
      # show these nodes even if they're hidden by being children of hidden hierarchy nodes
      showHiddenNodeTypes = ['vtkMRMLAnnotationNode', 'vtkMRMLVolumeNode', 'vtkMRMLDisplayableHierarchyNode'] 
      self.__markupTreeView.model().showHiddenForTypes = showHiddenNodeTypes
    # set the root to be the current report hierarchy root 
    if self.__rNode == None:
      Helper.Error("updateTreeView: report node is not initialized!")
      return
    else:
      # the tree root node has to be a hierarchy node, so get the associated hierarchy node for the active report node
      rootNode = slicer.vtkMRMLHierarchyNode().GetAssociatedHierarchyNode(self.__rNode.GetScene(), self.__rNode.GetID())
      if rootNode:
        self.__markupTreeView.setRootNode(rootNode)
        # print " setting tree view root to be ",rootNode.GetID()
        self.__markupTreeView.expandAll()

  def onAnnotatedVolumeNodeChanged(self):
    Helper.Debug("onAnnotatedVolumeNodeChanged()")

    # get the current volume node
    self.__vNode = self.__volumeSelector.currentNode()
    if self.__vNode != None:
      # update the report node
      if self.__rNode != None:
        self.__rNode.SetVolumeNodeID(self.__vNode.GetID())
        self.__rNode.SetName('Report for Volume '+self.__vNode.GetName())

      # is it a DICOM volume? check for UID attribute
      uids = self.__vNode.GetAttribute('DICOM.instanceUIDs')
      if uids == "None":
        Helper.ErrorPopup("DANGER: volume "+self.__vNode.GetName()+" was not loaded as a DICOM volume, will not be able to save your report in AIM XML format")

      Helper.SetBgFgVolumes(self.__vNode.GetID(), '')
      Helper.RotateToVolumePlanes()

      # go over all label nodes in the scene
      # if there is a label that has the selected volume as associated node, 
      #   initialize label selector to show that label
      volumeNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLScalarVolumeNode')
      volumeNodes.SetReferenceCount(volumeNodes.GetReferenceCount()-1)
      for i in range(volumeNodes.GetNumberOfItems()):
        vol = volumeNodes.GetItemAsObject(i)
        associatedNodeID = vol.GetAttribute('AssociatedNodeID')
        label = vol.GetAttribute('LabelMap')
        if associatedNodeID == self.__vNode.GetID() and label == '1':
          Helper.SetLabelVolume(vol.GetID())

      orientation = Helper.GetScanOrderSliceName(self.__vNode)
      message = "Please place mark ups in the "
      for sliceViewer in orientation:
          message = message + sliceViewer
          if orientation.index(sliceViewer) < (len(orientation) - 1 ):
            message = message + ", "
      message = message + " slice viewer"
      if len(orientation) > 1:
        message = message + "s."
      else:
        message = message + "."
      Helper.Debug(message)
      Helper.InfoPopup(self.parent, "Markup placement", message)
      # take the first one
      self.__parameterNode.SetParameter('acquisitionSliceViewer',orientation[0])

      # print "Calling logic to set up hierarchy"
      self.__logic.InitializeHierarchyForVolume(self.__vNode)
      self.updateTreeView()

  def onReportNodeChanged(self):
    Helper.Debug("onReportNodeChanged()")
    # TODO
    #  -- initialize annotations and markup frames based on the report node
    #  content
    self.__rNode = self.__reportSelector.currentNode()

    # print 'Selected report has changed to ',self.__rNode
    # set the volume to be none
    self.__vNode = None
    self.__volumeSelector.setCurrentNode(None)
    if self.__rNode != None:

      self.__parameterNode.SetParameter('reportID', self.__rNode.GetID())

      # setup the default color node, if not initialized
      if self.__rNode.GetColorNodeID() == "":
        self.__rNode.SetColorNodeID(self.__defaultColorNode.GetID())
        Helper.Debug('Set color node id to '+self.__defaultColorNode.GetID())
      else:
        Helper.Debug('Color node has already been set to '+self.__rNode.GetColorNodeID())

      self.__logic.InitializeHierarchyForReport(self.__rNode)
      self.updateTreeView()
      vID = self.__rNode.GetVolumeNodeID()
      if vID:
        self.__vNode = slicer.mrmlScene.GetNodeByID(vID)      
        self.__volumeSelector.setCurrentNode(self.__vNode)

      # hide the markups that go with other report nodes
      self.__logic.HideAnnotationsForOtherReports(self.__rNode)

      # update the GUI annotation name/label/color
      self.__toolsColor.setReportNode(self.__rNode)

      self.updateWidgets()


  '''
  Load report and initialize GUI based on .xml report file content
  '''
  def onReportImport(self):
    # TODO
    #  -- popup file open dialog to choose the .xml AIM file
    #  -- warn the user if the selected report node is not empty
    #  -- populate the selected report node, initializing annotation template,
    #  content, markup hierarchy and content
    Helper.Debug('onReportImport')

    # For now, always create a new report node
    newReport = slicer.mrmlScene.CreateNodeByClass('vtkMRMLReportingReportNode')
    newReport.SetReferenceCount(newReport.GetReferenceCount()-1)
    # always use the default color map
    newReport.SetColorNodeID(self.__defaultColorNode.GetID())

    slicer.mrmlScene.AddNode(newReport)
    self.__reportSelector.setCurrentNode(newReport)
    self.onReportNodeChanged()

    # initialize the report hierarchy
    #  -- assume that report node has been created and is in the selector

    fileName = qt.QFileDialog.getOpenFileName(self.parent, "Open AIM report","/","XML Files (*.xml)")
    if fileName == '':
      return

    Helper.LoadAIMFile(newReport,fileName)

    # update the GUI
    Helper.Debug('onReportImport --> calling onReportNodeChanged()')
    self.onReportNodeChanged()
    

  '''
  Save report to an xml file
  '''
  def onReportExport(self):
    if self.__rNode == None:
      return

    Helper.Debug('onReportingReportExport')
    
    #  -- popup file dialog prompting output file
    fileName = qt.QFileDialog.getSaveFileName(self.parent, "Save AIM report",self.__rNode.GetAIMFileName(),"XML Files (*.xml)")
    if fileName == '':
      return

    self.__rNode.SetAIMFileName(fileName)

    Helper.Debug('Will export to '+fileName)

    # use the currently selected report
    self.__rNode = self.__reportSelector.currentNode()
    if self.__rNode == None:
      return

    #  -- traverse markup hierarchy and translate
    retval = self.__logic.SaveReportToAIM(self.__rNode)
    if retval == EXIT_FAILURE:
      Helper.Error("Failed to save report to file '"+fileName+"'")
    else:
      Helper.Debug("Saved report to file '"+fileName+"'")

  def updateWidgetFromParameters(self):
    pn = self.__parameterNode
    if pn == None:
      return
    reportID = pn.GetParameter('reportID')

    if reportID != None:
      self.__rNode = Helper.getNodeByID(reportID)
      # AF: looks like this does not trigger event, why?
      self.__reportSelector.setCurrentNode(self.__rNode)

  def updateParametersFromWidget(self):
    pn = self.__parameterNode
    if pn == None:
      return

    report = self.__reportSelector.currentNode()
  
    if report != None:
      pn.SetParameter('reportID', report.GetID())


  def updateWidgets(self):

    Helper.Debug("updateWidgets()")

    report = self.__rNode
    volume = None

    if report != None:
      self.__reportSelector.setCurrentNode(self.__rNode)
      volume = slicer.mrmlScene.GetNodeByID(report.GetVolumeNodeID())

      if volume != None:
        self.__volumeSelector.setCurrentNode(volume)
        self.__markupFrame.enabled = 1
        self.__annotationsFrame.enabled = 1
        self.__volumeSelector.enabled = 0
      else:
        self.__volumeSelector.enabled = 1
        self.__markupFrame.enabled = 0
        self.__annotationsFrame.enabled = 0

    else:
      self.__volumeSelector.enabled = 0
      self.__markupFrame.enabled = 0
      self.__annotationsFrame.enabled = 0
