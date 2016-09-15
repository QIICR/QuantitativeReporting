import getpass

from slicer.ScriptedLoadableModule import *

from SlicerProstateUtils.mixins import *
from SlicerProstateUtils.helpers import WatchBoxAttribute, DICOMBasedInformationWatchBox
from SlicerProstateUtils.constants import DICOMTAGS

class Reporting(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Reporting" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Examples"]
    self.parent.dependencies = ["SlicerProstate"]
    self.parent.contributors = ["Andrey Fedorov (SPL, BWH), Nicole Aucoin (SPL, BWH), "
                                "Steve Pieper (Isomics), Christian Herz (SPL)"]
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    It performs a simple thresholding on the input volume and optionally captures a screenshot.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class ReportingWidget(ModuleWidgetMixin, ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)

  def cleanup(self):
    pass

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.setupWatchbox()
    self.setupSelectionArea()
    self.setupViewSettingsArea()
    self.setupSegmentationsArea()
    self.setupMeasurementsArea()
    self.setupActionButtons()
    self.setupConnections()
    self.layout.addStretch(1)

  def setupWatchbox(self):
    self.watchBoxInformation = [
      WatchBoxAttribute('StudyID', 'Study ID: ', DICOMTAGS.PATIENT_BIRTH_DATE),
      WatchBoxAttribute('PatientName', 'Patient Name: ', DICOMTAGS.PATIENT_NAME),
      WatchBoxAttribute('DOB', 'Date of Birth: ', DICOMTAGS.PATIENT_BIRTH_DATE),
      WatchBoxAttribute('Reader', 'Reader Name: ', callback=getpass.getuser)]
    self.watchBox = DICOMBasedInformationWatchBox(self.watchBoxInformation)
    self.layout.addWidget(self.watchBox)

  def setupSelectionArea(self):
    self.imageVolumeSelector = self.createComboBox(nodeTypes=["vtkMRMLScalarVolumeNode", ""], showChildNodeTypes=False,
                                                   selectNodeUponCreation=True, toolTip="Select image volume to annotate")
    self.measurementReportSelector = self.createComboBox(nodeTypes=["vtkMRMLScriptedModuleNode", ""], showChildNodeTypes=False,
                                                         selectNodeUponCreation=True, toolTip="Select measurement report")
    self.layout.addWidget(self.createHLayout([qt.QLabel("Image volume to annotate"), self.imageVolumeSelector]))
    self.layout.addWidget(self.createHLayout([qt.QLabel("Measurement report"), self.measurementReportSelector]))

  def setupViewSettingsArea(self):
    pass

  def setupSegmentationsArea(self):
    pass

  def setupMeasurementsArea(self):
    pass

  def setupActionButtons(self):
    self.saveReportButton = self.createButton("Save Report")
    self.completeReportButton = self.createButton("Complete Report")
    self.layout.addWidget(self.createHLayout([self.saveReportButton, self.completeReportButton]))

  def setupConnections(self):

    def setupSelectorConnections():
      self.imageVolumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onImageVolumeSelectorChanged)

    def setupButtonConnections():
      self.saveReportButton.clicked.connect(self.onSaveReportButtonClicked)
      self.completeReportButton.clicked.connect(self.onCompleteReportButtonClicked)

    setupSelectorConnections()
    setupButtonConnections()

  def onImageVolumeSelectorChanged(self, node):
    # TODO: save, cleanup open sessions
    try:
      dicomFileName = node.GetStorageNode().GetFileName()
      self.watchBox.sourceFile = dicomFileName if os.path.exists(dicomFileName) else None
    except AttributeError:
      self.watchBox.sourceFile = None

  def onSaveReportButtonClicked(self):
    print "on save report button clicked"

  def onCompleteReportButtonClicked(self):
    print "on complete report button clicked"


class ReportingLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def hasImageData(self, volumeNode):
    """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      logging.debug('hasImageData failed: no volume node')
      return False
    if volumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in volume node')
      return False
    return True

  def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
    """Validates if the output is not the same as input
    """
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False
    if not outputVolumeNode:
      logging.debug('isValidInputOutputData failed: no output volume node defined')
      return False
    if inputVolumeNode.GetID()==outputVolumeNode.GetID():
      logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
      return False
    return True


class ReportingTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_Reporting1()

  def test_Reporting1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
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
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = ReportingLogic()
    self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
