from __main__ import vtk, qt, ctk, slicer

import xml.dom.minidom

from Helper import *

import DICOMLib # for loading a volume on AIM import

EXIT_SUCCESS=0

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
    if self.__logic.InitializeDICOMDatabase():
      print 'DICOM database initialized correctly!'
    else:
      print 'Failed to initialize DICOM database'

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

      # keep active report and volume
      self.__rNode = None
      self.__vNode = None
 

  def setup( self ):
    # Use the logic associated with the module
    #if not self.__logic:
    #  self.__logic = self.parent.module().logic()

    self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    
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
    self.__annotationsFrame.text = "Annotation"
    self.__annotationsFrame.collapsed = 0
    annotationsFrameLayout = qt.QFormLayout(self.__annotationsFrame)
    
    self.layout.addWidget(self.__annotationsFrame)

    label = qt.QLabel('Annotation name')
    self.__annotationName = qt.QLineEdit()
    self.__annotationName.connect('textChanged(QString)',self.annotationNameChanged)

    annotationsFrameLayout.addRow(label, self.__annotationName)

    self.__markupFrame = ctk.ctkCollapsibleButton()
    self.__markupFrame.text = "Markup"
    self.__markupFrame.collapsed = 0
    markupFrameLayout = qt.QFormLayout(self.__markupFrame)
    
    self.layout.addWidget(self.__markupFrame)

    # Add a flag to switch between different tree view models
    self.__useNewTreeView = 1

    # Add the tree widget
    if self.__useNewTreeView == 1:
      self.__markupTreeView = slicer.qMRMLReportingTreeView()
      self.__markupTreeView.sceneModelType = "DisplayableHierarchy"
    else:
      self.__markupTreeView = slicer.qMRMLTreeView()
      self.__markupTreeView.sceneModelType = "Displayable"
    self.__markupTreeView.setMRMLScene(self.__logic.GetMRMLScene())
        

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
    # switch to Two-over-Two layout
    lm = slicer.app.layoutManager()
    lm.setLayout(26) # two over two

    # print "Reporting Enter"
    # update the logic active markup
    self.updateWidgetFromParameters()

    vnode = self.__volumeSelector.currentNode()
    if vnode != None:
      # print "Enter: setting active hierarchy from node ",vnode.GetID()
      self.__logic.SetActiveMarkupHierarchyIDFromNode(vnode)
      self.updateTreeView()


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
    
  def annotationNameChanged(self, newName):
    if self.__rNode != None:
      self.__rNode.SetDescription(newName)

  def updateTreeView(self):
    # print "updateTreeView()"
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
      print "updateTreeView: report node is not initialized!"
      return
    else:
      # the tree root node has to be a hierarchy node, so get the associated hierarchy node for the active report node
      rootNode = slicer.vtkMRMLHierarchyNode().GetAssociatedHierarchyNode(self.__rNode.GetScene(), self.__rNode.GetID())
      if rootNode:
        self.__markupTreeView.setRootNode(rootNode)
        # print " setting tree view root to be ",rootNode.GetID()
        self.__markupTreeView.expandAll()

  def onAnnotatedVolumeNodeChanged(self):
    print "onAnnotatedVolumeNodeChanged()"
    # get the current volume node
    self.__vNode = self.__volumeSelector.currentNode()
    if self.__vNode != None:
      Helper.SetBgFgVolumes(self.__vNode.GetID(), '')
      Helper.RotateToVolumePlanes()

      # print "Calling logic to set up hierarchy"
      self.__logic.InitializeHierarchyForVolume(self.__vNode)
      # AF: do we need this call here?
      self.updateTreeView()


  def onReportNodeChanged(self):
    print "onReportNodeChanged()"
    # TODO
    #  -- initialize annotations and markup frames based on the report node
    #  content
    self.__rNode = self.__reportSelector.currentNode()
    # print 'Selected report has changed to ',self.__rNode
    # set the volume to be none
    self.__vNode = None
    self.__volumeSelector.setCurrentNode(None)
    if self.__rNode != None:

      self.__annotationName.text = self.__rNode.GetDescription()

      self.__logic.InitializeHierarchyForReport(self.__rNode)
      self.updateTreeView()
      vID = self.__logic.GetVolumeIDForReportNode(self.__rNode)
      if vID:
        self.__vNode = slicer.mrmlScene.GetNodeByID(vID)      
        self.__volumeSelector.setCurrentNode(self.__vNode)

      # hide the markups that go with other report nodes
      self.__logic.HideAnnotationsForOtherReports(self.__rNode)

      # update the parameter node
      self.__parameterNode.SetParameter("reportID", self.__rNode.GetID())

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

    # For now, always create a new report node
    newReport = slicer.mrmlScene.CreateNodeByClass('vtkMRMLReportingReportNode')
    slicer.mrmlScene.AddNode(newReport)
    self.__reportSelector.setCurrentNode(newReport)
    self.onReportNodeChanged()

    # initialize the report hierarchy
    #  -- assume that report node has been created and is in the selector

    fileName = qt.QFileDialog.getOpenFileName(self.parent, "Open AIM report","/","XML Files (*.xml)")
    if fileName == '':
      return

    dom = xml.dom.minidom.parse(fileName)

    print 'Read AIM report:'
    print dom.toxml()

    volumeList = []
    volumesLogic = slicer.modules.volumes.logic()

    ddb = slicer.dicomDatabase
    volId = 1
    volume = None
  
    # get the annotation element and retrieve its name
    annotations = dom.getElementsByTagName('ImageAnnotation')
    if len(annotations) == 0:
      print 'AIM file does not contain any annotations!'
      return
    ann = annotations[0]
    newReport.SetDescription(ann.getAttribute('name'))

    # pull all the volumes that are referenced into the scene
    for node in dom.getElementsByTagName('ImageSeries'):
      instanceUID = node.getAttribute('instanceUID')
      filelist = ddb.filesForSeries(instanceUID)

      volName = 'AIM volume '+str(volId)

      loader = DICOMLib.DICOMLoader(filelist, volName)
      volume = loader.volumeNode

      if volume == None:
        print 'Failed to read series!'
        return

      volumeList.append(volume)
      self.__logic.InitializeHierarchyForVolume(volume)

    if len(volumeList) != 1:
      print 'ERROR: AIM does not allow to have more than one volume per file!'
      return

    #if volume != None:
    #  self.__volumeSelector.setCurrentNode(volume)

    instanceUIDs = volume.GetAttribute('DICOM.instanceUIDs')
    instanceUIDList = instanceUIDs.split()

    # AF: GeometricShape is inside geometricShapeCollection, but
    # there's no need to parse at that level, I think 
    # 
    # geometricShapeCollection
    #  |
    #  +-spatialCoordinateCollection
    #     |
    #     +-SpatialCoordinate
    #

    for node in dom.getElementsByTagName('GeometricShape'):

      ijCoordList = []
      rasPointList = []
      uidList = []
      elementType = node.getAttribute('xsi:type')
 
      for child in node.childNodes:
        if child.nodeName == 'spatialCoordinateCollection':
          for coord in child.childNodes:
            if coord.nodeName == 'SpatialCoordinate':
              ijCoordList.append(float(coord.getAttribute('x')))
              ijCoordList.append(float(coord.getAttribute('y')))
              uid = coord.getAttribute('imageReferenceUID')
              uidList.append(uid)
   
      print 'Coordinate list: ', ijCoordList

      ijk2ras = vtk.vtkMatrix4x4()
      volume.GetIJKToRASMatrix(ijk2ras)


      # convert each point from IJ to RAS
      for ij in range(len(uidList)):
        pointUID = uidList[ij]
        # locate the UID in the list assigned to the volume
        totalSlices = len(instanceUIDList)
        for k in range(len(instanceUIDList)):
          if pointUID == instanceUIDList[k]:
            break

        # AF: hack -- need to detect scan direction
        pointIJK = [ijCoordList[ij*2], ijCoordList[ij*2+1], totalSlices-k, 1.]
        pointRAS = ijk2ras.MultiplyPoint(pointIJK)
        print 'Input point: ',pointIJK
        print 'Converted point: ',pointRAS
        rasPointList.append(pointRAS[0:3])

      # instantiate the markup elements
      if elementType == 'Point':
        print "Importing a fiducial!"
        if len(ijCoordList) != 2:
          print 'Number of coordinates not good for a fiducial'
          return
        fiducial = slicer.mrmlScene.CreateNodeByClass('vtkMRMLAnnotationFiducialNode')
        # ??? Why the API is so inconsistent -- there's no SetPosition1() ???
        fiducial.SetFiducialCoordinates(rasPointList[0])
        fiducial.Initialize(slicer.mrmlScene)

      if elementType == 'MultiPoint':
        print "Importing a ruler!"
        if len(ijCoordList) != 4:
          print 'Number of coordinates not good for a ruler'

        ruler = slicer.mrmlScene.CreateNodeByClass('vtkMRMLAnnotationRulerNode')
        print 'Initializing with points ',rasPointList[0],' and ',rasPointList[1]
        ruler.SetPosition1(rasPointList[0])
        ruler.SetPosition2(rasPointList[1])
        ruler.Initialize(slicer.mrmlScene)
        # AF: Initialize() adds to the scene ...

    # update the GUI
    self.onReportNodeChanged()
    

  '''
  Save report to an xml file
  '''
  def onReportExport(self):
    print 'onReportingReportExport'
    
    #  -- popup file dialog prompting output file
    fileName = qt.QFileDialog.getSaveFileName(self.parent, "Save AIM report","/","XML Files (*.xml)")
    if fileName == '':
      return

    print 'Will export to ', fileName

    # use the currently selected report
    self.__rNode = self.__reportSelector.currentNode()
    if self.__rNode == None:
      return

    #  -- traverse markup hierarchy and translate
    retval = self.__logic.SaveReportToAIM(self.__rNode, fileName)
    if retval == EXIT_FAILURE:
      print "Failed to save report to file '",fileName,"'"
    else:
      print "Saved report to file '",fileName,"'"

  def updateWidgetFromParameters(self):
    pn = self.__parameterNode
    if pn == None:
      return
    reportID = pn.GetParameter('reportID')

    if reportID != None:
      self.__reportSelector.setCurrentNode(Helper.getNodeByID(reportID))

  def updateParametersFromWidget(self):
    pn = self.__parameterNode
    if pn == None:
      return

    report = self.__reportSelector.currentNode()
  
    if report != None:
      pn.SetParameter('reportID', report.GetID())


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
