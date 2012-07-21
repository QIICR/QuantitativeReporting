import slicer
from __main__ import qt
from __main__ import vtk
import ColorBox

#########################################################
#
# 
comment = """

  EditColor is a wrapper around a set of Qt widgets and other
  structures to manage the current paint color

  This class is borrowed from Editor module. It takes a vtkMRMLColorNode on
  initialization, and allows to query back the label that was selected by the
  user, for the needs of the Reporting module.

# TODO : 
"""
#
#########################################################

class EditColor(object):

  def __init__(self, parent=0, colorNode=None, reportNode=None):

    self.reportNode = reportNode
    self.colorNode = colorNode

    self.colorBox = None
    if parent == 0:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
      self.create()
      self.parent.show()
    else:
      self.parent = parent
      self.create()

  def __del__(self):
    self.cleanup()

  def cleanup(self, QObject=None):
    if self.reportNode:
      self.reportNode.RemoveObserver(self.observerTag)

  def create(self):
    self.frame = qt.QFrame(self.parent)
    self.frame.setLayout(qt.QHBoxLayout())
    self.parent.layout().addWidget(self.frame)

    self.label = qt.QLabel(self.frame)
    self.label.setText("Label: ")
    self.frame.layout().addWidget(self.label)

    self.labelName = qt.QLabel(self.frame)
    self.labelName.setText("")
    self.frame.layout().addWidget(self.labelName)

    self.colorSpin = qt.QSpinBox(self.frame)
    if self.reportNode != None:
      self.colorSpin.setValue(self.reportNode.GetFindingLabel())
    else:
      self.colorSpin.setValue(1)

    self.colorSpin.setToolTip( "Click colored patch at right to bring up color selection pop up window." )
    self.frame.layout().addWidget(self.colorSpin)
    self.colorSpin.enabled = 0

    self.colorPatch = qt.QPushButton(self.frame)
    self.colorPatch.setObjectName('colorPatch')
    self.frame.layout().addWidget(self.colorPatch)

    # self.updateParameterNode(slicer.mrmlScene, vtk.vtkCommand.ModifiedEvent)
    if self.reportNode:
      self.updateGUIFromMRML(self.reportNode, vtk.vtkCommand.ModifiedEvent)

    self.frame.connect( 'destroyed(QObject)', self.cleanup)
    self.colorSpin.connect( 'valueChanged(int)', self.updateMRMLFromGUI)
    self.colorPatch.connect( 'clicked()', self.showColorBox )

    # TODO: remove observer properly
    self.observerTag = None
    if self.reportNode:
      self.observerTag = self.reportNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

    '''
    # TODO: change this to look for specfic events (added, removed...)
    # but this requires being able to access events by number from wrapped code
    tag = slicer.mrmlScene.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateParameterNode)
    self.observerTags.append( (slicer.mrmlScene, tag) )
    '''

  #
  # update the parameter node when the scene changes
  #
  '''
  def updateReportNode(self, caller, event):
    #
    # observe the scene to know when to get the parameter node
    #
    if node != self.parameterNode:
      if self.parameterNode:
        self.parameterNode.RemoveObserver(self.parameterNodeTag)
      self.parameterNodeTag = node.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)
      self.parameterNode = node
  '''

  #
  # update the GUI for the given label
  #
  def updateMRMLFromGUI(self, label):
    # self.parameterNode.SetParameter(self.parameter, str(label))
    if self.reportNode:
      self.reportNode.SetFindingLabel(int(label))

  #
  # update the GUI from MRML
  #
  def updateGUIFromMRML(self,caller,event):
    if self.reportNode == None:
      # parameter does not exist - probably intializing
      return
    label = self.reportNode.GetFindingLabel()
    try:
      self.colorSpin.setValue(label)
    except ValueError:
      # TODO: why does the python class still exist if the widget is destroyed?
      # - this only happens when reloading the module.  The owner of the 
      # instance is gone and the widgets are gone, but this instance still
      # has observer on the parameter node - this indicates memory leaks
      # that need to be fixed
      self.cleanup()
      return

    if self.colorNode:
      self.frame.setDisabled(0)
      self.labelName.setText( self.colorNode.GetColorName( label ) )
      lut = self.colorNode.GetLookupTable()
      rgb = lut.GetTableValue( label )
      self.colorPatch.setStyleSheet( 
          "background-color: rgb(%s,%s,%s)" % (rgb[0]*255, rgb[1]*255, rgb[2]*255) )
      self.colorSpin.setMaximum( self.colorNode.GetNumberOfColors()-1 )
    else:
      self.frame.setDisabled(1)


  def showColorBox(self):
    if not self.colorBox:
      self.colorBox = ColorBox.ColorBox(reportNode=self.reportNode, colorNode=self.colorNode)

    print 'Will show color box'
    self.colorBox.show(reportNode=self.reportNode, colorNode=self.colorNode)

  def setReportNode(self,reportNode):
    if self.reportNode:
      self.reportNode.RemoveObserver(self.observerTag)

    self.reportNode = reportNode
    self.updateGUIFromMRML(self.reportNode, vtk.vtkCommand.ModifiedEvent)
    self.observerTag = self.reportNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)
