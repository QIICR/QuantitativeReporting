import os
import string
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

#
# This is the plugin to perform a test of dicom segmentation object export
#

class SEGExporterSelfTest(ScriptedLoadableModule):
  """
  This class is the 'hook' for slicer to detect and recognize the test
  as a loadable scripted module
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SEGExporterSelfTest" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Testing", "TestCases"]
    self.parent.dependencies = []
    self.parent.contributors = ["Steve Piepper (Isomics, Inc.)"]
    self.parent.helpText = """
        A module to perform a test of dicom segmentation object export.
    """
    self.parent.acknowledgementText = """
    This file was developed by Steve Pieper, Isomics, Inc.
    and was partially funded by NAC, NIH grant 3P41RR013218-12S1 and
    QIICR, NIH National Cancer Institute, award U24 CA180918.
""" # replace with organization, grant and thanks.

class SEGExporterSelfTestWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

class SEGExporterSelfTestLogic(ScriptedLoadableModuleLogic):

    pass

class SEGExporterSelfTestTest(ScriptedLoadableModuleTest):
  """
  This is the test case for the scripted module.
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SEGExporterSelfTest1()

  def test_SEGExporterSelfTest1(self):
    self.messageDelay = 50
    self.delayDisplay("hoot")
    pass
