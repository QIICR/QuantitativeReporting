from __main__ import vtk, qt, ctk, slicer

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
    print 'Logic is ',self.__logic

    if not parent:
      self.__logic = slicer.modulelogic.vtkSlicerReportingModuleLogic()
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
    Choose the volume being annotated.
    Will need to handle selection change:
      -- on new, update viewers, create storage node 
      -- on swich ask if the previous report should be saved
    '''
    label = qt.QLabel('Annotated volume: ')
    self.__volumeSelector = slicer.qMRMLNodeComboBox()
    self.__volumeSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    self.__volumeSelector.setMRMLScene(slicer.mrmlScene)
    #self.__volumeSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    #self.__volumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onInputChanged)
    self.__volumeSelector.addEnabled = 0
    
    inputFrameLayout.addRow(label, self.__volumeSelector)

    '''
    Report MRML node, will contain:
     -- template or pointer to it
     -- populated fields
     -- pointer to the markup elements hierarchy head
     -- storage node to handle file IO (can we do this in a module w/o
         changing the core?)
    On updates:
     -- reset the content of the widgets
     -- existing content repopulated from the node
    '''
    label = qt.QLabel('Report: ')
    self.__reportSelector = slicer.qMRMLNodeComboBox()
    self.__reportSelector.nodeTypes = ['vtkMRMLNode']
    self.__reportSelector.setMRMLScene(slicer.mrmlScene)
    #self.__reportSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    #self.__reportSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onInputChanged)
    self.__reportSelector.addEnabled = 1
    
    inputFrameLayout.addRow(label, self.__reportSelector)



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
 
    '''
    label = qt.QLabel('Input container:')
    self.__vcSelector = slicer.qMRMLNodeComboBox()
    self.__vcSelector.nodeTypes = ['vtkMRMLVectorImageContainerNode']
    self.__vcSelector.setMRMLScene(slicer.mrmlScene)
    self.__vcSelector.connect('mrmlSceneChanged(vtkMRMLScene*)', self.onMRMLSceneChanged)
    self.__vcSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onInputChanged)
    self.__vcSelector.addEnabled = 1

    ## self.layout.addRow(label, self.__vcSelector)
    self.layout.addWidget(label)
    self.layout.addWidget(self.__vcSelector)


    # TODO: initialize the slider based on the contents of the labels array
    # slider to scroll over metadata stored in the vector container being explored
    self.__mdSlider = ctk.ctkSliderWidget()
    #self.__mdSlider.setRange(0,10)
    #self.__mdSlider.setValue(5)

    label = qt.QLabel('Vector scroller:')
    ## self.layout.addRow(label, self.__mdSlider)
    self.layout.addWidget(label)
    self.layout.addWidget(self.__mdSlider)

    self.__mdSlider.connect('valueChanged(double)', self.onSliderChanged)

    label = qt.QLabel('Label for the element shown:')
    self.__mdValue = qt.QLabel()
    ## self.layout.addRow(label, self.__mdValue)
    self.layout.addWidget(label)
    self.layout.addWidget(self.__mdValue)

    label = qt.QLabel('Vector content:')
    self.__vcValue = qt.QLabel()
    ## self.layout.addRow(label, self.__vcValue)
    self.layout.addWidget(label)
    self.layout.addWidget(self.__vcValue)

    # initialize slice observers (from DataProbe.py)
    # keep list of pairs: [observee,tag] so they can be removed easily
    self.styleObserverTags = []
    # keep a map of interactor styles to sliceWidgets so we can easily get sliceLogic
    self.sliceWidgetsPerStyle = {}
    self.refreshObservers()

    self.playButton = qt.QPushButton('Play')
    self.playButton.toolTip = 'Iterate over vector image components'
    self.playButton.checkable = True
    self.layout.addWidget(self.playButton)
    self.playButton.connect('toggled(bool)', self.onPlayButtonToggled)

    # add chart container widget
    ##chartWidget = qt.QWidget()
    ##chartWidgetLayout = qt.QGridLayout()
    ##chartWidget.setLayout(chartWidgetLayout)
    ##self.__chartView = ctk.ctkVTKChartView(chartWidget)
    self.__chartView = ctk.ctkVTKChartView(w)
    ##self.layout.addRow(self.__chartView)
    self.layout.addWidget(self.__chartView)
    ##chartWidgetLayout.addWidget(self.__chartView)
    ##self.layout.addRow(chartWidget)
    ##chartWidget.show()

    self.__chart = self.__chartView.chart()
    self.__chartTable = vtk.vtkTable()
    self.__xArray = vtk.vtkFloatArray()
    self.__yArray = vtk.vtkFloatArray()
    # will crash if there is no name
    self.__xArray.SetName('X')
    self.__yArray.SetName('Y')
    self.__chartTable.AddColumn(self.__xArray)
    self.__chartTable.AddColumn(self.__yArray)
    '''
     
  def onMRMLSceneChanged(self, mrmlScene):
    '''
    self.__vcSelector.setMRMLScene(slicer.mrmlScene)
    self.onInputChanged()
    
    if mrmlScene != self.__logic.GetMRMLScene():
      self.__logic.SetMRMLScene(mrmlScene)
      self.__logic.RegisterNodes()
      self.__logic.InitializeEventListeners()
    self.__logic.GetMRMLManager().SetMRMLScene(mrmlScene)
    '''
    
  def onInputChanged(self):
    print 'onInputChanged() called'
    '''
    self.__vcNode = self.__vcSelector.currentNode()
    if self.__vcNode != None:
       self.__dwvNode = self.__vcNode.GetDWVNode()
       print 'Active DWV node: ', self.__dwvNode
       if self.__dwvNode != None:
         self.__mdSlider.minimum = 0
         self.__mdSlider.maximum = self.__dwvNode.GetNumberOfGradients()-1
         self.__chartTable.SetNumberOfRows(self.__dwvNode.GetNumberOfGradients())
    '''
