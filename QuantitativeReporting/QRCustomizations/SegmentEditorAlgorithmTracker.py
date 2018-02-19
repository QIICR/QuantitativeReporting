import slicer
import vtk
import vtkSegmentationCorePython as vtkSegmentationCore

class SegmentEditorAlgorithmTracker(object):

  def __init__(self):
    self.manualTools =  ['Paint','Draw','Erase']
    self.automaticTools = [] # no 'standard' editor effect can be considered fully automatic
    self.segmentEditorWidget = None
    self.observedSegmentation = None
    self.segmentationObservers = []
    self.observedSegmentEditorWidget = None
    self.updatingSegmentTags = False

  def __del__(self):
    self._removeSegmentEditorWidgetObservers()
    self._removeSegmentationObservers()

  def setSegmentEditorWidget(self, editor):
    # set the segment editor to be observe
    self._removeSegmentEditorWidgetObservers()
    self._removeSegmentationObservers()
    self.segmentEditorWidget = editor
    if not self.segmentEditorWidget:
      return
    self.segmentEditorWidget.selectParameterNode()
    self._setupSegmentEditorWidgetObservers()
    self._setupSegmentationObservers()

  def addAppliedToolToSegment(self, segment, toolName, toolType=None):
    self.updatingSegmentTags = True

    # append list of applied tools
    tools = vtk.mutable('')
    tools = str(tools).split(';') if segment.GetTag('QuantitativeReporting.AppliedTools', tools) else []
    if not toolName in tools:
      tools.append(toolName)
      segment.SetTag('QuantitativeReporting.AppliedTools',";".join(tools))

    segmentWasImported = tools[0]!='Add'

    # determine algorithm type (if not specified by user)
    if not toolType:
      if toolName in self.manualTools:
        toolType = 'MANUAL'
      elif toolName in self.automaticTools:
        toolType = 'AUTOMATIC'
      else: # default tool type
        toolType = 'SEMIAUTOMATIC'

    # update DICOM algorithm type
    oldAlgorithmType = vtk.mutable('')
    segment.GetTag('DICOM.SegmentAlgorithmType', oldAlgorithmType)
    updatedAlgorithmType = oldAlgorithmType
    if oldAlgorithmType=='': # no other editor effect was applied before
      if segmentWasImported:
        updatedAlgorithmType = 'SEMIAUTOMATIC'
      else:
        updatedAlgorithmType = toolType
    elif oldAlgorithmType=='MANUAL' and toolType!='MANUAL':
      updatedAlgorithmType = 'SEMIAUTOMATIC'
    elif oldAlgorithmType=='AUTOMATIC':
      updatedAlgorithmType = 'SEMIAUTOMATIC'
    if oldAlgorithmType!=updatedAlgorithmType:
      segment.SetTag('DICOM.SegmentAlgorithmType' ,updatedAlgorithmType)

    # update DICOM algorithm name
    GenericSlicerAlgorithmName = slicer.app.applicationName+' '+slicer.app.applicationVersion
    GenericSegmentEditorAlgorithmName = GenericSlicerAlgorithmName+' Segment Editor'
    ToolSegmentEditorAlgorithmName = GenericSlicerAlgorithmName+' '+toolName+' Effect'
    oldAlgorithmName = vtk.mutable('')
    segment.GetTag('DICOM.SegmentAlgorithmName', oldAlgorithmName)
    updatedAlgorithmName = oldAlgorithmName
    if oldAlgorithmName=='': # no other editor tool was applied before
      if segmentWasImported:
        updatedAlgorithmName = GenericSlicerAlgorithmName
      else:
        updatedAlgorithmName = ToolSegmentEditorAlgorithmName
    elif oldAlgorithmName!=ToolSegmentEditorAlgorithmName:
      if oldAlgorithmName.startswith(GenericSegmentEditorAlgorithmName):
        updatedAlgorithmName = GenericSegmentEditorAlgorithmName
      else:
        updatedAlgorithmName = GenericSlicerAlgorithmName
    if oldAlgorithmName!=updatedAlgorithmName:
      segment.SetTag('DICOM.SegmentAlgorithmName', updatedAlgorithmName)

    self.updatingSegmentTags = False

    #print('segment name: '+str(segment.GetName()))
    #print('imported: '+str(segmentWasImported))
    #print('applied tools: '+str(tools))
    #print('updated DICOM algorithm type and name: '+str(updatedAlgorithmType)+' '+str(updatedAlgorithmName))

  def segmentation(self):
    if not self.segmentEditorWidget:
      return None
    if not self.segmentEditorWidget.editor.segmentationNode():
      return None
    return self.segmentEditorWidget.editor.segmentationNode().GetSegmentation()

  def _setupSegmentEditorWidgetObservers(self):
    if self.observedSegmentEditorWidget:
      self._removeEditorParameterSetObservers()
    self.segmentEditorWidget.editor.connect(
      'segmentationNodeChanged(vtkMRMLSegmentationNode *)',self._setupSegmentationObservers)
    self.observedSegmentEditorWidget = self.segmentEditorWidget

  def _removeSegmentEditorWidgetObservers(self):
    if self.observedSegmentEditorWidget:
      self.segmentEditorWidget.editor.disconnect(
        'segmentationNodeChanged(vtkMRMLSegmentationNode *)',self._setupSegmentationObservers)
    self.observedSegmentEditorWidget = None

  def _setupSegmentationObservers(self):
    segNode = self.segmentation()
    if self.observedSegmentation==segNode:
      return
    self._removeSegmentationObservers()
    self.observedSegmentation = segNode
    if not segNode:
      return
    self._updateSegmentationSignature(segNode)
    self.segmentationObservers.append(
      segNode.AddObserver(vtkSegmentationCore.vtkSegmentation.MasterRepresentationModified,
      self._onMasterRepresentationModified))
    self.segmentationObservers.append(
      segNode.AddObserver(vtkSegmentationCore.vtkSegmentation.SegmentModified,
      self._onSegmentModified))
    events = [vtkSegmentationCore.vtkSegmentation.RepresentationModified,
              vtkSegmentationCore.vtkSegmentation.SegmentAdded,
              vtkSegmentationCore.vtkSegmentation.SegmentRemoved,
              vtkSegmentationCore.vtkSegmentation.SegmentsOrderModified]
    for event in events:
      self.segmentationObservers.append(segNode.AddObserver(event,
        self._updateSegmentationSignature))

  def _removeSegmentationObservers(self):
    if self.observedSegmentation and len(self.segmentationObservers):
      while len(self.segmentationObservers):
        observer = self.segmentationObservers.pop()
        self.observedSegmentation.RemoveObserver(observer)
    self.observedSegmentation = None

  def _onMasterRepresentationModified(self, segNode=None, caller=None):
    oldSignature = self.segmenationSignature
    newSignature = self._updateSegmentationSignature(segNode)
    effect = self.segmentEditorWidget.editor.activeEffect()
    if len(newSignature)==len(self.segmenationSignature) and effect:
      for i in range(len(newSignature)):
        if newSignature[i]['mtime']!=oldSignature[i]['mtime'] or \
          newSignature[i]['data']!=oldSignature[i]['data']:
          #print ('Segment '+str(i)+' was modified with '+str(effect.name))
          self.addAppliedToolToSegment(segNode.GetNthSegment(i),str(effect.name))

  def _onSegmentModified(self, segNode=None, caller=None):
    oldSignature = self.segmenationSignature
    newSignature = self._updateSegmentationSignature(segNode)
    # if a segment gets modified before it has been added to the segmentation,
    # it means that an empty segment was added
    if len(newSignature)>len(oldSignature):
      oldSegmentsData = [d['data'] for d in oldSignature]
      for i in range(len(newSignature)):
        if newSignature[i]['data'] not in oldSegmentsData:
          #print ('Segment '+str(i)+' was added as empty segment')
          segment = segNode.GetNthSegment(i)
          if not segment.HasTag('QuantitativeReporting.AppliedTools'):
            segment.SetTag('QuantitativeReporting.AppliedTools','Add')

  def _updateSegmentationSignature(self, segNode=None, caller=None):
    signature = []
    if not segNode: segNode = self.segmentation()
    if not segNode: return signature
    representationType = segNode.GetMasterRepresentationName()
    for i in range(segNode.GetNumberOfSegments()):
      segment = segNode.GetNthSegment(i)
      segmentationData = segment.GetRepresentation(representationType)
      segmentSignature = {'data': segmentationData, \
                          'mtime': segmentationData.GetMTime()}
      signature.append(segmentSignature)
    self.segmenationSignature = signature
    return signature
