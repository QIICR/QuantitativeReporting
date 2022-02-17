from __future__ import absolute_import
import qt
import slicer
import vtk
import os


from QRCustomizations.CustomSegmentStatistics import CustomSegmentStatisticsLogic
from SlicerDevelopmentToolboxUtils.decorators import onExceptionReturnNone, onModuleSelected
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic

from SegmentEditor import SegmentEditorWidget

import vtkSegmentationCorePython as vtkSegmentationCore
from six.moves import range


class CustomSegmentEditorWidget(SegmentEditorWidget, ModuleWidgetMixin):

  @property
  def segmentationNode(self):
    return self.editor.segmentationNode()

  @property
  def masterVolumeNode(self):
    return self.editor.masterVolumeNode()

  @property
  @onExceptionReturnNone
  def segmentation(self):
    return self.segmentationNode.GetSegmentation()

  @property
  def segments(self):
    if not self.segmentationNode:
      return []
    return self.logic.getAllSegments(self.segmentationNode)

  @property
  def enabled(self):
    return self.editor.enabled

  @enabled.setter
  def enabled(self, enabled):
    self.editor.setReadOnly(not enabled)

  def __init__(self, parent):
    SegmentEditorWidget.__init__(self, parent)
    self.logic = CustomSegmentEditorLogic()

  def resourcePath(self, filename):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath("QuantitativeReporting"))
    return os.path.join(scriptedModulesPath, 'Resources', filename)

  def setup(self):
    super(CustomSegmentEditorWidget, self).setup()
    self.editor.switchToSegmentationsButtonVisible = False
    self.editor.segmentationNodeSelectorVisible = False
    self.editor.setEffectButtonStyle(qt.Qt.ToolButtonIconOnly)
    self.clearSegmentationEditorSelectors()
  
  def setupDeveloperSection(self):
    return

  def onSegmentSelected(self, selectedRow):
    try:
      segment = self.segments[selectedRow]
      self.jumpToSegmentCenter(segment)
    except IndexError:
      pass

  def jumpToSegmentCenter(self, segment):
    centroid = self.logic.getSegmentCentroid(self.segmentationNode, segment)
    if centroid:
      markupsLogic = slicer.modules.markups.logic()
      markupsLogic.JumpSlicesToLocation(centroid[0], centroid[1], centroid[2], False)

  def clearSegmentationEditorSelectors(self):
    self.editor.setSegmentationNode(None)
    self.editor.setMasterVolumeNode(None)

  def enter(self):
    # overridden because SegmentEditorWidget automatically creates a new Segmentation upon instantiation
    self.turnOffLightboxes()
    self.installShortcutKeys()

    # Set parameter set node if absent
    self.selectParameterNode()
    self.editor.updateWidgetFromMRML()

  @onModuleSelected(moduleName="QuantitativeReporting")
  def onSceneEndClose(self, caller, event):
    self.selectParameterNode()
    self.editor.updateWidgetFromMRML()

  @onModuleSelected(moduleName="QuantitativeReporting")
  def onSceneEndImport(self, caller, event):
    self.selectParameterNode()
    self.editor.updateWidgetFromMRML()

  def calculateSegmentStatistics(self, tableNode, visibleOnly):
    if not self.segmentationNode or not self.masterVolumeNode:
      return None
    return self.logic.calculateSegmentStatistics(self.segmentationNode, self.masterVolumeNode, visibleOnly, tableNode)

  def hiddenSegmentsAvailable(self):
    return len(self.logic.getAllSegments(self.segmentationNode)) \
           != len(self.logic.getVisibleSegments(self.segmentationNode))

  def getSegmentIndexByID(self, segmentID):
    return self.logic.getSegmentIndexByID(self.segmentationNode, segmentID)

  def getSegmentIDByIndex(self, index):
    return self.logic.getSegmentIDs(self.segmentationNode, False)[index]


class CustomSegmentEditorLogic(ScriptedLoadableModuleLogic):

  def __init__(self, parent=None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    self.parent = parent
    self.volumesLogic = slicer.modules.volumes.logic()
    self.segmentStatisticsLogic = CustomSegmentStatisticsLogic()

  @staticmethod
  def getSegmentIDs(segmentationNode, visibleOnly):
    if not segmentationNode:
      return []
    segmentIDs = vtk.vtkStringArray()
    segmentation = segmentationNode.GetSegmentation()
    command = segmentationNode.GetDisplayNode().GetVisibleSegmentIDs if visibleOnly else segmentation.GetSegmentIDs
    command(segmentIDs)
    return [segmentIDs.GetValue(idx) for idx in range(segmentIDs.GetNumberOfValues())]

  @staticmethod
  def getAllSegments(segmentationNode):
    segmentation = segmentationNode.GetSegmentation()
    return [segmentation.GetSegment(segmentID)
            for segmentID in CustomSegmentEditorLogic.getSegmentIDs(segmentationNode, False)]

  @staticmethod
  def getVisibleSegments(segmentationNode):
    segmentation = segmentationNode.GetSegmentation()
    return [segmentation.GetSegment(segmentID)
            for segmentID in CustomSegmentEditorLogic.getSegmentIDs(segmentationNode, True)]

  @staticmethod
  def getSegmentIndexByID(segmentationNode, segmentID):
    segmentIDs = CustomSegmentEditorLogic.getSegmentIDs(segmentationNode, False)
    return segmentIDs.index(segmentID)

  @staticmethod
  def getSegmentCentroid(segmentationNode, segment):
    segmentID = segmentationNode.GetSegmentation().GetSegmentIdBySegment(segment)
    centroid = segmentationNode.GetSegmentCenterRAS(segmentID)
    return centroid

  @staticmethod
  def applyThreshold(labelNode, outValue):
    imageData = labelNode.GetImageData()
    backgroundValue = 0
    thresh = vtk.vtkImageThreshold()
    thresh.SetInputData(imageData)
    thresh.ThresholdByLower(0)
    thresh.SetInValue(backgroundValue)
    thresh.SetOutValue(outValue)
    thresh.SetOutputScalarType(vtk.VTK_UNSIGNED_CHAR)
    thresh.Update()
    labelNode.SetAndObserveImageData(thresh.GetOutput())

  def calculateSegmentStatistics(self, segNode, grayscaleNode, visibleSegmentsOnly, tableNode=None):
    self.segmentStatisticsLogic.getParameterNode().SetParameter("visibleSegmentsOnly", str(visibleSegmentsOnly))
    self.segmentStatisticsLogic.getParameterNode().SetParameter("Segmentation", segNode.GetID())
    if grayscaleNode:
      self.segmentStatisticsLogic.getParameterNode().SetParameter("ScalarVolume", grayscaleNode.GetID())
    else:
      self.segmentStatisticsLogic.getParameterNode().UnsetParameter("ScalarVolume")
    self.segmentStatisticsLogic.computeStatistics()
    tableNode = self.segmentStatisticsLogic.exportToTable(tableNode)
    return tableNode
