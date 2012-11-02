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
      self.__parameterNode.SetSingletonTag('Reporting')
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
    self.__reportSelector.addEnabled = True
    self.__reportSelector.removeEnabled = True
    
    inputFrameLayout.addRow(label, self.__reportSelector)

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

    self.__markupSliceText = qt.QLabel()
    markupFrameLayout.addRow(self.__markupSliceText)

    self.__markupTreeView = ReportingMarkupWidget(self.layout)
    markupFrameLayout.addRow(self.__markupTreeView.widget)
        
    
    

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
    self.__editorWidget.toolsColor.frame.setVisible(False)
    editorFrameLayout.addRow(editorWidgetParent)

    markupFrameLayout.addRow(self.__editorFrame)

    self.__segmentationSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onSegmentationNodeChanged)

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
    label = self.__editorParameterNode.GetParameter('label')
    if self.__rNode:
      self.__rNode.SetFindingLabel(int(label))
      self.__logic.PropagateFindingUpdateToMarkup()
      self.updateTreeView()

  def enter(self):
    # switch to Two-over-Two layout
    lm = slicer.app.layoutManager()
    if lm != None:
      lm.setLayout(26) # two over two

    # update the logic to know that the module has been entered
    self.__logic.GUIHiddenOff()
    self.updateWidgetFromParameters()

    # respond to error events
    Helper.Info('Enter: Setting up connection to respond to logic events')
    hasObserver = self.__logic.HasObserver(self.__logic.ErrorEvent)
    if hasObserver == 0:
      tag = self.__logic.AddObserver(self.__logic.ErrorEvent, self.respondToErrorMessage)
      # print '\tobserver tag = ',tag
    else:
      Helper.Debug('Logic already has an observer on the ErrorEvent')
    # respond to logic annotation added events
    hasObserver = self.__logic.HasObserver(self.__logic.AnnotationAdded)
    if hasObserver == 0:
      tag = self.__logic.AddObserver(self.__logic.AnnotationAdded, self.respondToAnnotationAdded)
    vnode = self.__volumeSelector.currentNode()
    if vnode != None:
      # print "Enter: updating the tree view"
      self.updateTreeView()

    self.__editorWidget.enter()


  def exit(self):
    self.updateParametersFromWidget()

    Helper.Debug("Reporting Exit. Letting logic know that module has been exited")
    # let the module logic know that the GUI is hidden, so that fiducials can go elsewehre
    self.__logic.GUIHiddenOn()
    # disconnect observation
    self.__logic.RemoveObservers(self.__logic.ErrorEvent)
    self.__logic.RemoveObservers(self.__logic.AnnotationAdded)

    self.__editorWidget.exit()

  # respond to error events from the logic
  def respondToErrorMessage(self, caller, event):
    errorMessage = self.__logic.GetErrorMessage()
    # inform user only if the message is not empty since vtkErrorMacro invokes this event as well
    if errorMessage != None:
      Helper.Debug('respondToErrorMessage, event = '+str(event)+', message =\n\t'+str(errorMessage))
      errorDialog = qt.QErrorMessage(self.parent)
      errorDialog.showMessage(errorMessage)

  # respond to an annotation added event from the logic
  def respondToAnnotationAdded(self, caller, event):
    Helper.Debug("respondToAnnotationAdded: updating the tree view")
    self.updateTreeView()

  def onMRMLSceneChanged(self, mrmlScene):
    if mrmlScene != self.__logic.GetMRMLScene():
      self.__logic.SetMRMLScene(mrmlScene)
      self.__logic.RegisterNodes()
    self.__reportSelector.setMRMLScene(slicer.mrmlScene)
    
  def updateTreeView(self):
    Helper.Debug('updateTreeView')
    # make the view update
    self.populateTreeView()

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
      label = vol.GetAttribute('LabelMap')
      if label == '1' and self.__logic.IsInReport(vol):
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
    self.__logic.AddVolumeToReport(self.__vNode)
    self.updateTreeView()

  def onSegmentationNodeChanged(self):
    Helper.Debug('onSegmentationNodeChanged()')

    if self.__vNode == None:
      Helper.Error('Should not be possible to select segmentation unless annotated volume is initialized!')
      return

    # get the current segmentation (label) node
    sNode = self.__segmentationSelector.currentNode()
    if sNode == None:
      self.updateWidgets()
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
        self.updateWidgets()
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

    self.updateWidgets()

    self.updateTreeView()
  
  def onReportNodeChanged(self):
    Helper.Debug("onReportNodeChanged()")

    # cancel the active effect in Editor
    if self.__editorWidget:
      self.__editorWidget.toolsBox.defaultEffect()
    # TODO
    #  -- initialize annotations and markup frames based on the report node
    #  content
    self.__rNode = self.__reportSelector.currentNode()
      
    Helper.Debug("onReportNodeChanged: changing segmentation selector to None")
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

      # self.__logic.InitializeHierarchyForReport(self.__rNode)

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

      # update the tree
      self.updateTreeView()

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

    Helper.LoadAIMFile(newReport.GetID(),self.__importAIMFile)

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

    # This code is commented out because repeated insertion into the database
    # leads to database lockout (illustrated in Testing/RepeatInsertTest.py).
    # For now, the solution will be to import the created DICOM objects
    # manually.
    # attempt to insert each of the saved items into the database
    #filesToInsert = glob.glob(exportDirectory+'/*')
    #for f in filesToInsert:
    #  Helper.Debug('Inserting '+f+' into DICOM database...')
    #  slicer.dicomDatabase.insert(f)
    #  Helper.Debug('Done')

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
    label = self.__segmentationSelector.currentNode()

    if report != None:
      self.__reportSelector.setCurrentNode(self.__rNode)
      volume = slicer.mrmlScene.GetNodeByID(report.GetVolumeNodeID())
      # TODO: get the label node from volume hieararchy

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
      
    if not label:
      self.__editorWidget.editLabelMapsFrame.collapsed = True
      self.__editorWidget.editLabelMapsFrame.setEnabled(False)
    else:      
      self.__editorWidget.editLabelMapsFrame.collapsed = False
      self.__editorWidget.editLabelMapsFrame.setEnabled(True)

  #
  # Fill in the GUI element with the volume from the report node, 
  # and it's associated markups
  #
  def populateTreeView(self):
    Helper.Debug('populateTreeView')
    self.__markupTreeView.setHeader(self.__rNode)
    return
    Helper.Debug('populateTreeView')
    if self.__rNode == None:
      Helper.Debug('populateTreeView: no report node set!')
      return

    volumeID = self.__rNode.GetVolumeNodeID()     
    if volumeID == "":
      Helper.Debug('populateTreeView: no active volume node id on report ' + self.__rNode.GetName())
      return
    volumeNode = Helper.getNodeByID(volumeID)   
    Helper.Debug('volumeID = ' + volumeID)

    # find displayble nodes that are associated with this volume
    numDisplayableNodes = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLDisplayableNode")
    nodeIDList = []
    for n in range(numDisplayableNodes): 
      displayableNode = slicer.mrmlScene.GetNthNodeByClass(n, "vtkMRMLDisplayableNode")
      inReport = self.__logic.IsInReport(displayableNode)
      if inReport:
        Helper.Debug('Found node associated with the volume node: ' + displayableNode.GetName())
        nodeIDList.append(displayableNode.GetID())

    print "Report: " + self.__rNode.GetName()
    print "Volume: " + volumeNode.GetName()

    row = 0
    # volume name
    item = qt.QStandardItem()
    item.setEditable(False)
    item.setText(volumeNode.GetName())
    self.__markupsModel.setItem(row,0,item)
    self.items.append(item)
    row += 1

    # get the associated markups
    for nodeID in nodeIDList:
       node = Helper.getNodeByID(nodeID)
       if node != None and node.IsA("vtkMRMLVolumeNode") and node.GetLabelMap() == 1:
         Helper.Debug('Segmentation: ' + node.GetName())
         item = qt.QStandardItem()
         item.setEditable(False)
         item.setText(node.GetName())
         self.__markupsModel.setItem(row,0,item)
         self.items.append(item)
         row += 1
       if node != None and node.IsA("vtkMRMLAnnotationNode"):
         Helper.Debug('Annotation: ' + node.GetName())
         # annotation name
         item = qt.QStandardItem()
         item.setEditable(False)
         item.setText(node.GetName())
         self.__markupsModel.setItem(row,0,item)
         self.items.append(item)
         # annotation visibility
         item = qt.QStandardItem()
         # todo: allow click to toggle visib
         item.setEditable(False)
         if node.GetDisplayVisibility() == 1:
           item.setData(qt.QPixmap(":/Icons/Small/SlicerVisible.png"),qt.Qt.DecorationRole)
         else:
           item.setData(qt.QPixmap(":/Icons/Small/SlicerInvisible.png"),qt.Qt.DecorationRole)
         self.__markupsModel.setItem(row,1,item)
         self.items.append(item)
         row += 1


#
# implement Qt code for a table of markups
#
class ReportingMarkupWidget(object):
  def __init__(self,parent):
    self.widget = qt.QTableWidget()
    self.widget.setSelectionBehavior(1) # qt.Qt.QAbstractItemView.SelectRows)
    self.widget.connect('itemClicked(QTableWidgetItem*)', self.onItemClicked)
    self.items = []
    self.setHeader(None)

  def setHeader(self,reportNode):
    """Load the table widget with annotations for the report
    """
    self.widget.clearContents()
    self.widget.setColumnCount(2)
    self.widget.setHorizontalHeaderLabels(['Markup','Visibility'])
    self.widget.horizontalHeader().setResizeMode(0, qt.QHeaderView.Stretch)
    self.widget.horizontalHeader().setResizeMode(1, qt.QHeaderView.Fixed)
    self.widget.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)

    if not reportNode:
      return
    if reportNode == None:
      return
    # get the volume node associated with this report
    volumeID = reportNode.GetVolumeNodeID()     
    if volumeID == "":
      return
    volumeNode = slicer.mrmlScene.GetNodeByID(volumeID)

    # get the annotations associated with this report
    # find displayble nodes that are associated with this volume
    numDisplayableNodes = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLDisplayableNode")
    nodeIDList = [volumeID]
    for n in range(numDisplayableNodes): 
      displayableNode = slicer.mrmlScene.GetNthNodeByClass(n, "vtkMRMLDisplayableNode")
      # how best to get at module widget logic?
      inReport = slicer.modules.reporting.logic().IsInReport(displayableNode)
      if inReport:
        Helper.Debug('Found node associated with the report node: ' + displayableNode.GetName())
        nodeIDList.append(displayableNode.GetID())

    self.widget.setRowCount(len(nodeIDList))
    row = 0
    for nodeID in nodeIDList:
      node = Helper.getNodeByID(nodeID)
      item = qt.QTableWidgetItem(node.GetName())
      self.widget.setItem(row,0,item)
      self.items.append(item)
      if node.IsA("vtkMRMLAnnotationNode"):
        item = qt.QTableWidgetItem()
        # save the id for toggling visibility on the node
        # TODO: make this more elegant instead of overloading the what's this role with the id
        item.setData(qt.Qt.WhatsThisRole, node.GetID())
        if node.GetDisplayVisibility() == 1:
          item.setData(qt.Qt.DecorationRole,qt.QPixmap(":/Icons/Small/SlicerVisible.png"))
        else:
          item.setData(qt.Qt.DecorationRole,qt.QPixmap(":/Icons/Small/SlicerInvisible.png"))
        self.widget.setItem(row,1,item)
        self.items.append(item)
      row += 1

  def onItemClicked(self, item):
    # column 0 is the name, do jump to annotation
    if item.column() == 0:
      # get the id from the item in column 1
      idItem = self.widget.item(item.row(), 1)
      if idItem == None:
         # volumes don't have anything in this column
         return
      nodeID = idItem.data(qt.Qt.WhatsThisRole)
      if nodeID == None:
        return
      controlPointsNode = slicer.mrmlScene.GetNodeByID(nodeID)
      if controlPointsNode == None:
        return
      # is it an annotation?
      if controlPointsNode.IsA('vtkMRMLAnnotationControlPointsNode') == 0:
        return
      # get the coordinates of this annotation
      rasCoordinates = [0,0,0]
      if controlPointsNode.IsA('vtkMRMLAnnotationFiducialNode'):
        controlPointsNode.GetFiducialCoordinates(rasCoordinates)
      if controlPointsNode.IsA('vtkMRMLAnnotationRulerNode'):
        controlPointsNode.GetPosition1(rasCoordinates)
      sliceNode = slicer.mrmlScene.GetNthNodeByClass(0, 'vtkMRMLSliceNode')
      if sliceNode != None:
        Helper.Debug("Jumping to first point in annotation")
        # jump the other slices and then this slice
        sliceNode.JumpAllSlices(rasCoordinates[0],rasCoordinates[1],rasCoordinates[2])
        sliceNode.JumpSlice(rasCoordinates[0],rasCoordinates[1],rasCoordinates[2])
    # column 1 is the visibility column
    if item.column() == 1:
      # is it a displayable?
      nodeID = item.data(qt.Qt.WhatsThisRole)
      if id == None:
        return
      node = slicer.mrmlScene.GetNodeByID(nodeID)
      if node == None:
        return
      # update the visibility and the eye icon
      if node.GetDisplayVisibility() == 0:
        node.SetDisplayVisibility(1)
        item.setData(qt.Qt.DecorationRole,qt.QPixmap(":/Icons/Small/SlicerVisible.png"))
      else:
        node.SetDisplayVisibility(0)
        item.setData(qt.Qt.DecorationRole,qt.QPixmap(":/Icons/Small/SlicerInvisible.png"))
