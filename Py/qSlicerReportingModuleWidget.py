from __main__ import vtk, qt, ctk, slicer

from SlicerReportingModuleWidgetHelper import SlicerReportingModuleWidgetHelper as Helper
#from EditColor import *
from Editor import EditorWidget
from EditorLib import EditColor
import Editor
from EditorLib import EditUtil
from EditorLib import EditorLib

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

    # Get the location and initialize the DICOM DB
    settings = qt.QSettings()
    self.__dbFileName = settings.value("DatabaseDirectory","")
    if self.__dbFileName == "":
      Helper.Warning("DICOM Database is not accessible.")
    else:
      self.__dbFileName = self.__dbFileName+"/ctkDICOM.sql"

      if self.__logic.InitializeDICOMDatabase(self.__dbFileName):
        Helper.Info('DICOM database initialized correctly!')
      else:
        Helper.Error('Failed to initialize DICOM database at '+self.__dbFileName)

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
      compNode.SetReferenceCount(compNode.GetReferenceCount() - 1)
      nodeid = None
      if compNode.GetModuleName() == 'Reporting':
        self.__parameterNode = compNode
        'Found existing Reporting parameter node'
        break
    if self.__parameterNode == None:
      self.__parameterNode = slicer.vtkMRMLScriptedModuleNode()
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
    
    # TODO: figure out why module/class hierarchy is different
    # between developer builds ans packages
    try:
      # for developer build...
      self.editUtil = EditorLib.EditUtil.EditUtil()
    except AttributeError:
      # for release package...
      self.editUtil = EditorLib.EditUtil()

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
    self.__reportSelector.removeEnabled = 0
    
    inputFrameLayout.addRow(label, self.__reportSelector)

    self.__reportSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    self.__reportSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onReportNodeChanged)
 
    # Volume being annotated (only one is allowed for the report)
    label = qt.QLabel('NOTE: Only volumes loaded from DICOM can be annotated!')
    inputFrameLayout.addRow(label)
    label = qt.QLabel('Annotated volume: ')
    self.__volumeSelector = slicer.qMRMLNodeComboBox()
    self.__volumeSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    # only allow volumes with the attribute DICOM.instanceUIDs
    self.__volumeSelector.addAttribute('vtkMRMLScalarVolumeNode','DICOM.instanceUIDs')
    self.__volumeSelector.setMRMLScene(slicer.mrmlScene)
    self.__volumeSelector.addEnabled = False
    
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
        
    self.__markupSliceText = qt.QLabel()
    markupFrameLayout.addRow(self.__markupSliceText)
    markupFrameLayout.addRow(self.__markupTreeView)

    # Editor frame
    self.__editorFrame = ctk.ctkCollapsibleButton()
    self.__editorFrame.text = 'Segmentation'
    self.__editorFrame.collapsed = 0
    editorFrameLayout = qt.QFormLayout(self.__editorFrame)

    label = qt.QLabel('Segmentation volume: ')
    self.__segmentationSelector = slicer.qMRMLNodeComboBox()
    self.__segmentationSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    self.__segmentationSelector.setMRMLScene(slicer.mrmlScene)
    self.__segmentationSelector.addEnabled = 1
    self.__segmentationSelector.noneEnabled = 1
    self.__segmentationSelector.removeEnabled = 0
    self.__segmentationSelector.showHidden = 0
    self.__segmentationSelector.showChildNodeTypes = 0
    self.__segmentationSelector.selectNodeUponCreation = 1
    self.__segmentationSelector.addAttribute('vtkMRMLScalarVolumeNode','LabelMap',1)

    editorFrameLayout.addRow(label, self.__segmentationSelector)

    editorWidgetParent = slicer.qMRMLWidget()
    editorWidgetParent.setLayout(qt.QVBoxLayout())
    editorWidgetParent.setMRMLScene(slicer.mrmlScene)
    self.__editorWidget = EditorWidget(parent=editorWidgetParent,showVolumesFrame=False)
    self.__editorWidget.setup()
    editorFrameLayout.addRow(editorWidgetParent)

    markupFrameLayout.addRow(self.__editorFrame)

    self.__segmentationSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onSegmentationNodeChanged)
    self.__segmentationSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)

    # IO frame
    self.__ioFrame = ctk.ctkCollapsibleButton()
    self.__ioFrame.text = 'Import/Export'
    self.__ioFrame.collapsed = 1
    ioFrameLayout = qt.QGridLayout(self.__ioFrame)

    self.layout.addWidget(self.__ioFrame)

    # Buttons to save/load report using AIM XML serialization
    label = qt.QLabel('Export folder')
    self.__exportFolderPicker = ctk.ctkDirectoryButton()
    exportButton = qt.QPushButton('Export')
    exportButton.connect('clicked()', self.onReportExport)
    ioFrameLayout.addWidget(label,0,0)
    ioFrameLayout.addWidget(self.__exportFolderPicker,0,1)
    ioFrameLayout.addWidget(exportButton,0,2)

    label = qt.QLabel('AIM file to import')
    self.__aimFilePicker = qt.QPushButton('N/A')
    self.__aimFilePicker.connect('clicked()',self.onSelectAIMFile)
    button = qt.QPushButton('Import')
    button.connect('clicked()', self.onReportImport)
    ioFrameLayout.addWidget(label,1,0)
    ioFrameLayout.addWidget(self.__aimFilePicker,1,1)
    ioFrameLayout.addWidget(button,1,2)
    self.__importAIMFile = None

    self.__reportSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.updateWidgets)
    self.__volumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.updateWidgets)
    self.updateWidgets()

    self.layout.addStretch(1)

    self.__editorParameterNode = self.editUtil.getParameterNode()

    self.__editorParameterNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onEditorParameterNodeChanged)

  def onEditorParameterNodeChanged(self,caller,event):
    print('Editor parameter node changed')
    label = self.__editorParameterNode.GetParameter('label')
    if self.__rNode:
      print("Updating report label")
      self.__rNode.SetFindingLabel(int(label))

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

    self.__editorWidget.enter()


  def exit(self):
    self.updateParametersFromWidget()

    Helper.Debug("Reporting Exit. Letting logic know that module has been exited")
    # let the module logic know that the GUI is hidden, so that fiducials can go elsewehre
    self.__logic.GUIHiddenOn()
    # disconnect observation
    self.__logic.RemoveObservers(vtk.vtkCommand.ErrorEvent)

    self.__editorWidget.exit()

  # respond to error events from the logic
  def respondToErrorMessage(self, caller, event):
    errorMessage = self.__logic.GetErrorMessage()
    # inform user only if the message is not empty since vtkErrorMacro invokes this event as well
    if errorMessage != None:
      Helper.Debug('respondToErrorMessage, event = '+str(event)+', message =\n\t'+str(errorMessage))
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
      self.__markupTreeView.setRootNode(None)
      return
    else:
      # the tree root node has to be a hierarchy node, so get the associated hierarchy node for the active report node
      rootNode = slicer.vtkMRMLHierarchyNode().GetAssociatedHierarchyNode(self.__rNode.GetScene(), self.__rNode.GetID())
      if rootNode:
        self.__markupTreeView.setRootNode(rootNode)
        Helper.Debug("Setting tree view root to be " + rootNode.GetID())
        self.__markupTreeView.expandAll()
      else:
        Helper.Debug("Setting tree view root to be None")
        self.__markupTreeView.setRootNode(None)

  def onAnnotatedVolumeNodeChanged(self):
    Helper.Debug("onAnnotatedVolumeNodeChanged()")

    # get the current volume node
    selectedVolume = self.__volumeSelector.currentNode()

    # do the error checks
    if selectedVolume == None or self.__rNode == None:
      self.__volumeSelector.setCurrentNode(None)
      return

    uids = selectedVolume.GetAttribute('DICOM.instanceUIDs')
    if uids == None:
      Helper.ErrorPopup("Volume \""+selectedVolume.GetName()+"\" was not loaded from DICOM. Only volumes loaded from DICOM data can be annotated in the Reporting module.")
      self.__volumeSelector.setCurrentNode(None)
      return

    nSlices = selectedVolume.GetImageData().GetExtent()[-1]+1
    if nSlices != len(string.split(uids)):
      Helper.ErrorPopup("Volume \""+selectedVolume.GetName()+"\" was loaded from multi-frame DICOM. Multi-frame DICOM is currently not supported by the Reporting module")
      self.__volumeSelector.setCurrentNode(None)
      return

    # volume node is valid!
    self.__vNode = selectedVolume

    # update the report node
    if self.__rNode != None:
      self.__rNode.SetVolumeNodeID(self.__vNode.GetID())
      self.__rNode.SetName('Report for Volume '+self.__vNode.GetName())

    Helper.SetBgFgVolumes(self.__vNode.GetID(), '')
    Helper.RotateToVolumePlanes()

    # go over all label nodes in the scene
    # if there is a label that has the selected volume as associated node, 
    #   initialize label selector to show that label
    volumeNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLScalarVolumeNode')
    volumeNodes.SetReferenceCount(volumeNodes.GetReferenceCount()-1)
    associatedLabelFound = False
    for i in range(volumeNodes.GetNumberOfItems()):
      vol = volumeNodes.GetItemAsObject(i)
      associatedNodeID = vol.GetAttribute('AssociatedNodeID')
      label = vol.GetAttribute('LabelMap')
      if associatedNodeID == self.__vNode.GetID() and label == '1':
        Helper.SetLabelVolume(vol.GetID())
        associatedLabelFound = True

    # if there is no associated label node, set the selector to none
    if associatedLabelFound == False:
      Helper.SetLabelVolume("")

    orientation = Helper.GetScanOrderSliceName(self.__vNode)
    message = "Slice viewers to be used for markup: "
    for sliceViewer in orientation:
      message = message + sliceViewer
      if orientation.index(sliceViewer) < (len(orientation) - 1 ):
        message = message + ", "
    Helper.Debug(message)
    self.__markupSliceText.text = message

    # take the first one
    self.__parameterNode.SetParameter('acquisitionSliceViewer',orientation[0])

    # print "Calling logic to set up hierarchy"
    self.__logic.InitializeHierarchyForVolume(self.__vNode)
    self.updateTreeView()

  def onSegmentationNodeChanged(self):
    Helper.Debug('onSegmentationNodeChanged()')

    if self.__vNode == None:
      Helper.Error('Should not be possible to select segmentation unless annotated volume is initialized!')
      return

    # get the current segmentation (label) node
    sNode = self.__segmentationSelector.currentNode()
    if sNode == None:
      return

    # if it's a new label, it should have/will be added to the report
    # automatically
    image = sNode.GetImageData()
    if image == None:
      Helper.initializeNewLabel(sNode, self.__vNode)
    else:
      # if it's an existing label, we need to check that the geometry matches
      # the annotated label geometry, and if so, add it to the hierarchy
      if Helper.GeometriesMatch(sNode, self.__vNode) == False:
        Helper.ErrorPopup('The geometry of the segmentation label you attempted to select does not match the geometry of the volume being annotated! Please select a different label or create a new one.')
        self.__segmentationSelector.setCurrentNode(None)
        return

    # assign the color LUT we use
    dNode = sNode.GetDisplayNode()
    dNode.SetAndObserveColorNodeID(self.__defaultColorNode.GetID())

    sNode.SetAttribute('AssociatedNodeID',self.__vNode.GetID())
    self.__logic.AddNodeToReport(sNode)

    # assign the volume and the selected color to the editor parameter node
    Helper.SetLabelVolume(sNode.GetID())

    # TODO: disable adding new label node to the hierarchy if it was added
    # outside the reporting module

    self.__segmentationSelector.setCurrentNode(sNode)

    self.__editorWidget.setMasterNode(self.__vNode)
    self.__editorWidget.setMergeNode(sNode)

    self.__editorParameterNode.Modified()
  
  def onReportNodeChanged(self):
    Helper.Debug("onReportNodeChanged()")
    # TODO
    #  -- initialize annotations and markup frames based on the report node
    #  content
    self.__rNode = self.__reportSelector.currentNode()
      
    self.__segmentationSelector.setCurrentNode(None)

    if self.__rNode != None:
    
      Helper.Debug("Selected report has changed to " + self.__rNode.GetID())

      if self.__rNode.GetDICOMDatabaseFileName() == "":
        self.__rNode.SetDICOMDatabaseFileName(self.__dbFileName)

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
        Helper.Debug('Have a volume node id in the report ' + vID + ', setting current volume node selector')
        self.__vNode = slicer.mrmlScene.GetNodeByID(vID)      
        self.__volumeSelector.setCurrentNode(self.__vNode)
      else:
        Helper.Debug('Do not have a volume id in the report, setting current volume node selector to none')
        # set the volume to be none
        self.__vNode = None
        self.__volumeSelector.setCurrentNode(None)

      # hide the markups that go with other report nodes
      self.__logic.HideAnnotationsForOtherReports(self.__rNode)

      # update the GUI annotation name/label/color
      self.updateWidgets()

      # initialize the label used by the EditorWidget
      if self.__editorParameterNode:
        self.__editorParameterNode.SetParameter('label',str(self.__rNode.GetFindingLabel()))

  '''
  Load report and initialize GUI based on .xml report file content
  '''
  def onReportImport(self):

    print('onReportImport here!!!')
    # TODO
    #  -- popup file open dialog to choose the .xml AIM file
    #  -- warn the user if the selected report node is not empty
    #  -- populate the selected report node, initializing annotation template,
    #  content, markup hierarchy and content
    if not self.__importAIMFile:
      Helper.Debug('onReportImport: import file name not specified')
      return

    Helper.Debug('onReportImport')    

    # For now, always create a new report node
    newReport = slicer.modulemrml.vtkMRMLReportingReportNode()

    # always use the default color map
    newReport.SetColorNodeID(self.__defaultColorNode.GetID())

    slicer.mrmlScene.AddNode(newReport)
    self.__reportSelector.setCurrentNode(newReport)
    self.onReportNodeChanged()

    # initialize the report hierarchy
    #  -- assume that report node has been created and is in the selector

    Helper.LoadAIMFile(newReport,self.__importAIMFile)

    # update the GUI
    Helper.Debug('onReportImport --> calling onReportNodeChanged()')
    self.onReportNodeChanged()
    
  def onSelectAIMFile(self):
    #  -- popup file dialog prompting output file
    if not self.__importAIMFile:
      fileName = qt.QFileDialog.getOpenFileName(self.parent, "Choose AIM report","/","XML Files (*.xml)")
    else:
      lastDir = self.__importAIMFile[0:string.rfind(self.__importAIMFile,'/')]
      fileName = qt.QFileDialog.getOpenFileName(self.parent, "Choose AIM report",lastDir,"XML Files (*.xml)")

    if fileName == '':
      return
    
    self.__importAIMFile = fileName
    try:
      label = string.split(fileName,'/')[-1]
    except:
      label = fileName
    self.__aimFilePicker.text = label

  '''
  Save report to an xml file
  '''
  def onReportExport(self):
    if self.__rNode == None:
      return

    Helper.Debug('onReportExport')
    
    exportDirectory = self.__exportFolderPicker.directory
    self.__rNode.SetStorageDirectoryName(exportDirectory)

    Helper.Debug('Will export to '+exportDirectory)

    # use the currently selected report
    self.__rNode = self.__reportSelector.currentNode()
    if self.__rNode == None:
      return

    #  -- traverse markup hierarchy and translate
    retval = self.__logic.SaveReportToAIM(self.__rNode)
    if retval == EXIT_FAILURE:
      Helper.Error("Failed to save report to '"+exportDirectory+"'")
    else:
      Helper.Debug("Saved report to '"+exportDirectory+"'")

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
