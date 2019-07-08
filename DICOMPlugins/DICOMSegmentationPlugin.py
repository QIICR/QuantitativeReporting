import glob
import os
import json
import vtk
import vtkSegmentationCorePython as vtkSegmentationCore
import logging

from base.DICOMPluginBase import DICOMPluginBase

import slicer
from DICOMLib import DICOMLoadable

from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS


#
# This is the plugin to handle translation of DICOM SEG objects
#
class DICOMSegmentationPluginClass(DICOMPluginBase):

  def __init__(self):
    super(DICOMSegmentationPluginClass,self).__init__()
    self.loadType = "DICOMSegmentation"

  def examineFiles(self,files):
    """ Returns a list of DICOMLoadable instances
    corresponding to ways of interpreting the
    files parameter.
    """
    loadables = []

    # just read the modality type; need to go to reporting logic, since DCMTK
    #   is not wrapped ...

    for cFile in files:

      uid = slicer.dicomDatabase.fileValue(cFile, self.tags['instanceUID'])
      if uid == '':
        return []

      desc = slicer.dicomDatabase.fileValue(cFile, self.tags['seriesDescription'])
      if desc == '':
        desc = "Unknown"

      isDicomSeg = (slicer.dicomDatabase.fileValue(cFile, self.tags['modality']) == 'SEG')

      if isDicomSeg:
        loadable = DICOMLoadable()
        loadable.files = [cFile]
        loadable.name = desc
        loadable.tooltip = loadable.name + ' - as a DICOM SEG object'
        loadable.selected = True
        loadable.confidence = 0.95
        loadable.uid = uid
        self.addReferences(loadable)

        loadables.append(loadable)

        logging.debug('DICOM SEG modality found')

    return loadables

  def referencedSeriesName(self,loadable):
    """Returns the default series name for the given loadable"""
    referencedName = "Unnamed Reference"
    if hasattr(loadable, "referencedSeriesUID"):
      referencedName = self.defaultSeriesNodeName(loadable.referencedSeriesUID)
    return referencedName

  def getValuesFromCodeSequence(self, segment, codeSequenceName, defaults=None):
    try:
      cs = segment[codeSequenceName]
      return cs["CodeValue"], cs["CodingSchemeDesignator"], cs["CodeMeaning"]
    except KeyError:
      return defaults if defaults else ['', '', '']

  def load(self,loadable):
    """ Load the DICOM SEG object
    """
    logging.debug('DICOM SEG load()')
    try:
      uid = loadable.uid
      logging.debug('in load(): uid = '+uid)
    except AttributeError:
      return False

    self.tempDir = os.path.join(slicer.app.temporaryPath, "QIICR", "SEG", self.currentDateTime, loadable.uid)
    try:
      os.makedirs(self.tempDir)
    except OSError:
      pass

    # produces output label map files, one per segment, and information files with
    # the terminology information for each segment
    segFileName = slicer.dicomDatabase.fileForInstance(uid)
    if segFileName is None:
      logging.error('Failed to get the filename from the DICOM database for ' + uid)
      self.cleanup()
      return False

    parameters = {
      "inputSEGFileName": segFileName,
      "outputDirName": self.tempDir,
      }

    try:
      segimage2itkimage = slicer.modules.segimage2itkimage
    except AttributeError:
      logging.error('Unable to find CLI module segimage2itkimage, unable to load DICOM Segmentation object')
      self.cleanup()
      return False

    cliNode = None
    cliNode = slicer.cli.run(segimage2itkimage, cliNode, parameters, wait_for_completion=True)
    if cliNode.GetStatusString() != 'Completed':
      logging.error('SEG2NRRD did not complete successfully, unable to load DICOM Segmentation')
      self.cleanup()
      return False

    numberOfSegments = len(glob.glob(os.path.join(self.tempDir,'*.nrrd')))

    # resize the color table to include the segments plus 0 for the background

    seriesName = self.referencedSeriesName(loadable)
    segmentLabelNodes = []
    metaFileName = os.path.join(self.tempDir,"meta.json")

    # Load terminology in the metafile into context
    terminologiesLogic = slicer.modules.terminologies.logic()
    terminologiesLogic.LoadTerminologyFromSegmentDescriptorFile(loadable.name, metaFileName)
    terminologiesLogic.LoadAnatomicContextFromSegmentDescriptorFile(loadable.name, metaFileName)

    with open(metaFileName) as metaFile:
      data = json.load(metaFile)
      logging.debug('number of segmentation files = ' + str(numberOfSegments))
      if numberOfSegments != len(data["segmentAttributes"]):
        logging.error('Loading failed: Inconsistent number of segments in the descriptor file and on disk')
        return
      for segmentAttributes in data["segmentAttributes"]:
        # TODO: only handles the first item of lists
        for segment in segmentAttributes:
          try:
            rgb255 = segment["recommendedDisplayRGBValue"]
            rgb = map(lambda c: float(c) / 255., rgb255)
          except KeyError:
            rgb = (0., 0., 0.)

          segmentId = segment["labelID"]

          defaults = ['T-D0050', 'Tissue', 'SRT']
          categoryCode, categoryCodingScheme, categoryCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "SegmentedPropertyCategoryCodeSequence", defaults)

          typeCode, typeCodingScheme, typeCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "SegmentedPropertyTypeCodeSequence", defaults)

          typeModCode, typeModCodingScheme, typeModCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "SegmentedPropertyTypeModifierCodeSequence")

          anatomicRegionDefaults = ['T-D0010', 'SRT', 'Entire Body']
          regionCode, regionCodingScheme, regionCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "AnatomicRegionSequence", anatomicRegionDefaults)

          regionModCode, regionModCodingScheme, regionModCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "AnatomicRegionModifierSequence")

          segmentTerminologyTag = terminologiesLogic.SerializeTerminologyEntry(
                                    loadable.name,
                                    categoryCode, categoryCodingScheme, categoryCodeMeaning,
                                    typeCode, typeCodingScheme, typeCodeMeaning,
                                    typeModCode, typeModCodingScheme, typeModCodeMeaning,
                                    loadable.name,
                                    regionCode, regionCodingScheme, regionCodeMeaning,
                                    regionModCode, regionModCodingScheme, regionModCodeMeaning)

          # TODO: Create logic class that both CLI and this plugin uses so that we don't need to have temporary NRRD
          # files and labelmap nodes
          # if not hasattr(slicer.modules, 'segmentations'):

          # load the segmentation volume file and name it for the reference series and segment color
          labelFileName = os.path.join(self.tempDir, str(segmentId) + ".nrrd")
          if segment["SegmentDescription"] is None:
            segmentName = seriesName + "-" + typeCodeMeaning + "-label"
          else:
            segmentName = segment["SegmentDescription"]

          success, labelNode = slicer.util.loadLabelVolume(labelFileName,properties={'name': segmentName},
                                                           returnNode=True)
          if not success:
            raise ValueError("{} could not be loaded into Slicer!".format(labelFileName))

          # Set terminology properties as attributes to the label node (which is a temporary node)
          #TODO: This is a quick solution, maybe there is a better one
          labelNode.SetAttribute("Terminology", segmentTerminologyTag)
          labelNode.SetAttribute("ColorR", str(rgb[0]))
          labelNode.SetAttribute("ColorG", str(rgb[1]))
          labelNode.SetAttribute("ColorB", str(rgb[2]))
          if "SegmentAlgorithmType" in segment:
            labelNode.SetAttribute("DICOM.SegmentAlgorithmType", segment["SegmentAlgorithmType"])
          if "SegmentAlgorithmName" in segment:
            labelNode.SetAttribute("DICOM.SegmentAlgorithmName", segment["SegmentAlgorithmName"])

          segmentLabelNodes.append(labelNode)

    self.cleanup()

    self._createSegmentationNode(loadable, segmentLabelNodes)

    return True

  def _createSegmentationNode(self, loadable, segmentLabelNodes):
    segmentationNode = self._initializeSegmentation(loadable)

    for segmentLabelNode in segmentLabelNodes:
      self._importSegmentAndRemoveLabel(segmentLabelNode, segmentationNode)

    self.addSeriesInSubjectHierarchy(loadable, segmentationNode)
    if hasattr(loadable, "referencedSeriesUID"):
      self._findAndSetGeometryReference(loadable.referencedSeriesUID, segmentationNode)

  def _importSegmentAndRemoveLabel(self, segmentLabelNode, segmentationNode):
    segmentationsLogic = slicer.modules.segmentations.logic()
    segmentation = segmentationNode.GetSegmentation()
    success = segmentationsLogic.ImportLabelmapToSegmentationNode(segmentLabelNode, segmentationNode)
    if success:
      segment = segmentation.GetNthSegment(segmentation.GetNumberOfSegments() - 1)
      segment.SetColor([float(segmentLabelNode.GetAttribute("ColorR")),
                        float(segmentLabelNode.GetAttribute("ColorG")),
                        float(segmentLabelNode.GetAttribute("ColorB"))])

      segment.SetTag(vtkSegmentationCore.vtkSegment.GetTerminologyEntryTagName(),
                     segmentLabelNode.GetAttribute("Terminology"))
      algorithmName = segmentLabelNode.GetAttribute("DICOM.SegmentAlgorithmName")
      if algorithmName:
        segment.SetTag("DICOM.SegmentAlgorithmName", algorithmName)
      algorithmType = segmentLabelNode.GetAttribute("DICOM.SegmentAlgorithmType")
      if algorithmType:
        segment.SetTag("DICOM.SegmentAlgorithmType", algorithmType)

      self._removeLabelNode(segmentLabelNode)
    return segmentation

  def _removeLabelNode(self, labelNode):
    dNode = labelNode.GetDisplayNode()
    if dNode is not None:
      slicer.mrmlScene.RemoveNode(dNode)
    slicer.mrmlScene.RemoveNode(labelNode)

  def _initializeSegmentation(self, loadable):
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    segmentationNode.SetName(loadable.name)

    segmentationDisplayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationDisplayNode")
    segmentationNode.SetAndObserveDisplayNodeID(segmentationDisplayNode.GetID())

    vtkSegConverter = vtkSegmentationCore.vtkSegmentationConverter
    segmentation = vtkSegmentationCore.vtkSegmentation()
    segmentation.SetMasterRepresentationName(vtkSegConverter.GetSegmentationBinaryLabelmapRepresentationName())
    segmentation.CreateRepresentation(vtkSegConverter.GetSegmentationClosedSurfaceRepresentationName(), True)
    segmentationNode.SetAndObserveSegmentation(segmentation)

    return segmentationNode

  def _findAndSetGeometryReference(self, referencedSeriesUID, segmentationNode):
    shn = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    segID = shn.GetItemByDataNode(segmentationNode)
    parentID = shn.GetItemParent(segID)
    childIDs = vtk.vtkIdList()
    shn.GetItemChildren(parentID, childIDs)
    uidName = slicer.vtkMRMLSubjectHierarchyConstants.GetDICOMUIDName()
    matches = []
    for childID in reversed([childIDs.GetId(id) for id in range(childIDs.GetNumberOfIds()) if segID]):
      if childID == segID:
        continue
      if shn.GetItemUID(childID, uidName) == referencedSeriesUID:
        if shn.GetItemDataNode(childID):
          matches.append(shn.GetItemDataNode(childID))

    reference = None
    if len(matches):
      if any(x.GetAttribute("DICOM.RWV.instanceUID") is not None for x in matches):
        for x in matches:
          if x.GetAttribute("DICOM.RWV.instanceUID") is not None:
            reference = x
            break
      else:
        reference = matches[0]

    if reference:
      segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(reference)

  def examineForExport(self, subjectHierarchyItemID):
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

    exportable = self._examineExportableForSegmentationNode(shNode, subjectHierarchyItemID)
    return self._setupExportable(exportable, subjectHierarchyItemID)

  def _examineExportableForSegmentationNode(self, shNode, subjectHierarchyItemID):
    dataNode = shNode.GetItemDataNode(subjectHierarchyItemID)
    exportable = None
    if dataNode and dataNode.IsA('vtkMRMLSegmentationNode'):
      # Check to make sure all referenced UIDs exist in the database.
      instanceUIDs = shNode.GetItemAttribute(subjectHierarchyItemID, "DICOM.ReferencedInstanceUIDs").split()
      if instanceUIDs != "" and all(slicer.dicomDatabase.fileForInstance(uid) != "" for uid in instanceUIDs):
        exportable = slicer.qSlicerDICOMExportable()
        exportable.confidence = 1.0
        exportable.setTag('Modality', 'SEG')
    return exportable

  def _setupExportable(self, exportable, subjectHierarchyItemID):
    if not exportable:
      return []
    exportable.name = self.loadType
    exportable.tooltip = "Create DICOM files from segmentation"
    exportable.subjectHierarchyItemID = subjectHierarchyItemID
    exportable.pluginClass = self.__module__
    # Define common required tags and default values
    exportable.setTag('SeriesDescription', 'No series description')
    exportable.setTag('SeriesNumber', '1')
    return [exportable]

  def export(self, exportables):
    try:
      slicer.modules.segmentations
    except AttributeError as exc:
      return exc.message

    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    if shNode is None:
      error = "Invalid subject hierarchy"
      logging.error(error)
      return error

    for exportable in exportables:
      subjectHierarchyItemID = exportable.subjectHierarchyItemID
      segmentationNode = shNode.GetItemDataNode(subjectHierarchyItemID)

      exporter = DICOMSegmentationExporter(segmentationNode)

      try:
        segFileName = "subject_hierarchy_export.SEG" + exporter.currentDateTime + ".dcm"
        segFilePath = os.path.join(exportable.directory, segFileName)
        try:
          exporter.export(exportable.directory, segFileName)
        except DICOMSegmentationExporter.EmptySegmentsFoundError as exc:
          if slicer.util.confirmYesNoDisplay(exc.message):
            exporter.export(exportable.directory, segFileName, skipEmpty=True)
          else:
            raise ValueError("Export canceled")
        slicer.dicomDatabase.insert(segFilePath)
        logging.info("Added segmentation to DICOM database (" +segFilePath+")")
      except (DICOMSegmentationExporter.NoNonEmptySegmentsFoundError, ValueError) as exc:
        return exc.message
      finally:
        exporter.cleanup()
    return ""


class DICOMSegmentationExporter(ModuleLogicMixin):
  """This class can be used for exporting a segmentation into DICOM """

  class EmptySegmentsFoundError(ValueError):
    pass

  class NoNonEmptySegmentsFoundError(ValueError):
    pass

  class MissingAttributeError(ValueError):
    pass

  @staticmethod
  def getDeserializedTerminologyEntry(vtkSegment):
    terminologyEntry = slicer.vtkSlicerTerminologyEntry()
    tag = vtk.mutable("")
    vtkSegment.GetTag(vtkSegment.GetTerminologyEntryTagName(), tag)
    terminologyLogic = slicer.modules.terminologies.logic()
    terminologyLogic.DeserializeTerminologyEntry(tag, terminologyEntry)
    return terminologyEntry

  @staticmethod
  def saveJSON(data, destination):
    with open(os.path.join(destination), 'w') as outfile:
      json.dump(data, outfile, indent=2)
    return destination

  @staticmethod
  def vtkStringArrayFromList(listToConvert):
    stringArray = vtk.vtkStringArray()
    for listElement in listToConvert:
      stringArray.InsertNextValue(listElement)
    return stringArray

  @staticmethod
  def createLabelNodeFromSegment(segmentationNode, segmentID):
    labelNode = slicer.vtkMRMLLabelMapVolumeNode()
    slicer.mrmlScene.AddNode(labelNode)
    segmentationsLogic = slicer.modules.segmentations.logic()

    mergedImageData = vtkSegmentationCore.vtkOrientedImageData()
    segmentationNode.GenerateMergedLabelmapForAllSegments(mergedImageData, 0, None,
                                                          DICOMSegmentationExporter.vtkStringArrayFromList([segmentID]))
    if not segmentationsLogic.CreateLabelmapVolumeFromOrientedImageData(mergedImageData, labelNode):
      slicer.mrmlScene.RemoveNode(labelNode)
      return None
    labelNode.SetName("{}_label".format(segmentID))
    return labelNode

  @staticmethod
  def getSegmentIDs(segmentationNode, visibleOnly=False):
    if not segmentationNode:
      raise AttributeError("SegmentationNode must not be None!")
    segmentIDs = vtk.vtkStringArray()
    segmentation = segmentationNode.GetSegmentation()
    command = segmentationNode.GetDisplayNode().GetVisibleSegmentIDs if visibleOnly else segmentation.GetSegmentIDs
    command(segmentIDs)
    return [segmentIDs.GetValue(idx) for idx in range(segmentIDs.GetNumberOfValues())]

  @staticmethod
  def getReferencedVolumeFromSegmentationNode(segmentationNode):
    if not segmentationNode:
      return None
    return segmentationNode.GetNodeReference(segmentationNode.GetReferenceImageGeometryReferenceRole())

  @property
  def currentDateTime(self, outputFormat='%Y-%m-%d_%H%M%S'):
    from datetime import datetime
    return datetime.now().strftime(outputFormat)

  def __init__(self, segmentationNode, contentCreatorName=None):
    self.segmentationNode = segmentationNode
    self.contentCreatorName = contentCreatorName if contentCreatorName else "Slicer"

    self.tempDir = os.path.join(slicer.util.tempDirectory(), self.currentDateTime)
    os.mkdir(self.tempDir)

  def cleanup(self):
    try:
      import shutil
      logging.debug("Cleaning up temporarily created directory {}".format(self.tempDir))
      shutil.rmtree(self.tempDir)
    except AttributeError:
      pass

  def formatMetaDataDICOMConform(self, metadata):
    metadata["ContentCreatorName"] = "^".join(metadata["ContentCreatorName"].split(" ")[::-1])

  def export(self, outputDirectory, segFileName, metadata, segmentIDs=None, skipEmpty=False):
    data = self.getSeriesAttributes()
    data.update(metadata)

    try:
      for attr in ["SeriesDescription", "ContentCreatorName", "ClinicalTrialSeriesID", "ClinicalTrialTimePointID",
                   "ClinicalTrialCoordinatingCenterName"]:
        data[attr]
    except KeyError as exc:
      raise self.MissingAttributeError(str(exc))

    self.formatMetaDataDICOMConform(data)

    segmentIDs = segmentIDs if segmentIDs else self.getSegmentIDs(self.segmentationNode)

    # NB: for now segments are filter if they are empty and only the non empty ones are returned

    nonEmptySegmentIDs = self.getNonEmptySegmentIDs(segmentIDs)

    if skipEmpty is False and len(nonEmptySegmentIDs) and len(segmentIDs) != len(nonEmptySegmentIDs):
      raise self.EmptySegmentsFoundError("Empty segments found in segmentation. Currently the export of empty segments "
                                         "is not supported. Do you want to skip empty segments and proceed exporting?")

    segmentIDs = nonEmptySegmentIDs

    if not len(segmentIDs):
      raise self.NoNonEmptySegmentsFoundError("No non empty segments found.")

    data["segmentAttributes"] = self.generateJSON4DcmSEGExport(segmentIDs)

    logging.debug("DICOM SEG Metadata output:")
    logging.debug(data)

    metaFilePath = self.saveJSON(data, os.path.join(self.tempDir, "seg_meta.json"))

    segmentFiles = self.createAndGetLabelMapsFromSegments(segmentIDs)
    inputDICOMImageFileNames = self.getDICOMFileList(self.getReferencedVolumeFromSegmentationNode(self.segmentationNode),
                                                     absolutePaths=True)

    segFilePath = os.path.join(outputDirectory, segFileName)

    # copy files to a temp location, since otherwise the command line can easily exceed
    #  the maximum on Windows (~8k characters)
    import tempfile, shutil
    cliTempDir = os.path.join(tempfile.mkdtemp())
    for inputFilePath in inputDICOMImageFileNames:
      destFile = os.path.join(cliTempDir,os.path.split(inputFilePath)[1])
      shutil.copyfile(inputFilePath, destFile)

    params = {
      #"dicomImageFiles": ', '.join(inputDICOMImageFileNames).replace(', ', ","),
      "dicomDirectory": cliTempDir,
      "segImageFiles": ', '.join(segmentFiles).replace(', ', ","),
      "metaDataFileName": metaFilePath,
      "outputSEGFileName": segFilePath
    }

    logging.debug(params)

    cliNode = slicer.cli.run(slicer.modules.itkimage2segimage, None, params, wait_for_completion=True)
    waitCount = 0
    while cliNode.IsBusy() and waitCount < 20:
      slicer.util.delayDisplay("Running SEG Encoding... %d" % waitCount, 1000)
      waitCount += 1

    shutil.rmtree(cliTempDir)

    if cliNode.GetStatusString() != 'Completed':
      raise RuntimeError("%s:\n\n%s" % (cliNode.GetStatusString(), cliNode.GetErrorText()))

    if not os.path.exists(segFilePath):
      raise RuntimeError("DICOM Segmentation was not created. Check Error Log for further information.")

    logging.debug("Saved DICOM Segmentation to {}".format(segFilePath))
    return True

  def getSeriesAttributes(self):
    attributes = dict()
    volumeNode = self.getReferencedVolumeFromSegmentationNode(self.segmentationNode)
    seriesNumber = ModuleLogicMixin.getDICOMValue(volumeNode, DICOMTAGS.SERIES_NUMBER)
    attributes["SeriesNumber"] = "100" if seriesNumber in [None,''] else str(int(seriesNumber)+100)
    attributes["InstanceNumber"] = "1"
    return attributes

  def getNonEmptySegmentIDs(self, segmentIDs):
    segmentation = self.segmentationNode.GetSegmentation()
    return [segmentID for segmentID in segmentIDs if not self.isSegmentEmpty(segmentation.GetSegment(segmentID))]

  def isSegmentEmpty(self, segment):
    import vtkSegmentationCorePython as vtkSegmentationCore
    vtkSegConverter = vtkSegmentationCore.vtkSegmentationConverter
    r = segment.GetRepresentation(vtkSegConverter.GetSegmentationBinaryLabelmapRepresentationName())
    imagescalars = r.GetPointData().GetArray("ImageScalars")

    if imagescalars is None:
      return True
    else:
      return imagescalars.GetValueRange() == (0,0)

  def createAndGetLabelMapsFromSegments(self, segmentIDs):
    segmentFiles = []
    for segmentID in segmentIDs:
      segmentLabelmap = self.createLabelNodeFromSegment(self.segmentationNode, segmentID)
      filename = os.path.join(self.tempDir, "{}.nrrd".format(segmentLabelmap.GetName()))
      slicer.util.saveNode(segmentLabelmap, filename)
      slicer.mrmlScene.RemoveNode(segmentLabelmap)
      segmentFiles.append(filename)
    return segmentFiles

  def getDICOMFileList(self, volumeNode, absolutePaths=False):
    # TODO: move to general class
    # duplicate in quantitative Reporting
    attributeName = "DICOM.instanceUIDs"
    instanceUIDs = volumeNode.GetAttribute(attributeName)
    if not instanceUIDs:
      raise ValueError("VolumeNode {0} has no attribute {1}".format(volumeNode.GetName(), attributeName))
    fileList = []
    rootDir = None
    for uid in instanceUIDs.split():
      rootDir, filename = self.getInstanceUIDDirectoryAndFileName(uid)
      fileList.append(str(filename if not absolutePaths else os.path.join(rootDir, filename)))
    if not absolutePaths:
      return rootDir, fileList
    return fileList

  def getInstanceUIDDirectoryAndFileName(self, uid):
    # TODO: move this method to a general class
    # duplicate in quantitative Reporting
    path = slicer.dicomDatabase.fileForInstance(uid)
    return os.path.dirname(path), os.path.basename(path)

  def generateJSON4DcmSEGExport(self, segmentIDs):
    self.checkTerminologyOfSegments(segmentIDs)
    segmentsData = []
    for segmentID in segmentIDs:
      segmentData = self._createSegmentData(segmentID)
      segmentsData.append([segmentData])
    if not len(segmentsData):
      raise ValueError("No segments with pixel data found.")
    return segmentsData

  def _createSegmentData(self, segmentID):
    segmentData = dict()
    segmentData["labelID"] = 1
    segment = self.segmentationNode.GetSegmentation().GetSegment(segmentID)
    terminologyEntry = self.getDeserializedTerminologyEntry(segment)
    category = terminologyEntry.GetCategoryObject()
    segmentData["SegmentDescription"] = category.GetCodeMeaning()
    algorithmType = vtk.mutable('')
    if not segment.GetTag("DICOM.SegmentAlgorithmType", algorithmType):
      algorithmType = "MANUAL"
    if not algorithmType in ["MANUAL","SEMIAUTOMATIC","AUTOMATIC"]:
      raise ValueError("Segment {} has invalid attribute for SegmentAlgorithmType."\
        +"Should be one of (MANUAL,SEMIAUTOMATIC,AUTOMATIC).".format(segment.GetName()))
    algorithmName = vtk.mutable('')
    if not segment.GetTag("DICOM.SegmentAlgorithmName", algorithmName):
        algorithmName = None
    if algorithmType!="MANUAL" and not algorithmName:
      raise ValueError("Segment {} has has missing SegmentAlgorithmName, which"\
        +"should be specified for non-manual segmentations.".format(segment.GetName()))
    segmentData["SegmentAlgorithmType"] = str(algorithmType)
    if algorithmName:
      segmentData["SegmentAlgorithmName"] = str(algorithmName)
    rgb = segment.GetColor()
    segmentData["recommendedDisplayRGBValue"] = [rgb[0] * 255, rgb[1] * 255, rgb[2] * 255]
    segmentData.update(self.createJSONFromTerminologyContext(terminologyEntry))
    segmentData.update(self.createJSONFromAnatomicContext(terminologyEntry))
    return segmentData

  def checkTerminologyOfSegments(self, segmentIDs):
    # TODO: not sure if this is still needed since there is always a terminology assigned by default
    for segmentID in segmentIDs:
      segment = self.segmentationNode.GetSegmentation().GetSegment(segmentID)
      terminologyEntry = self.getDeserializedTerminologyEntry(segment)
      category = terminologyEntry.GetCategoryObject()
      propType = terminologyEntry.GetTypeObject()
      if any(v is None for v in [category, propType]):
        raise ValueError("Segment {} has missing attributes. Make sure to set terminology.".format(segment.GetName()))

  def createJSONFromTerminologyContext(self, terminologyEntry):
    segmentData = dict()

    categoryObject = terminologyEntry.GetCategoryObject()
    if categoryObject is None or not self.isTerminologyInformationValid(categoryObject):
      return {}
    segmentData["SegmentedPropertyCategoryCodeSequence"] = self.getJSONFromVtkSlicerTerminology(categoryObject)

    typeObject = terminologyEntry.GetTypeObject()
    if typeObject is None or not self.isTerminologyInformationValid(typeObject):
      return {}
    segmentData["SegmentedPropertyTypeCodeSequence"] = self.getJSONFromVtkSlicerTerminology(typeObject)

    modifierObject = terminologyEntry.GetTypeModifierObject()
    if modifierObject is not None and self.isTerminologyInformationValid(modifierObject):
      segmentData["SegmentedPropertyTypeModifierCodeSequence"] = self.getJSONFromVtkSlicerTerminology(modifierObject)

    return segmentData

  def createJSONFromAnatomicContext(self, terminologyEntry):
    segmentData = dict()

    regionObject = terminologyEntry.GetAnatomicRegionObject()
    if regionObject is None or not self.isTerminologyInformationValid(regionObject):
      return {}
    segmentData["AnatomicRegionSequence"] = self.getJSONFromVtkSlicerTerminology(regionObject)

    regionModifierObject = terminologyEntry.GetAnatomicRegionModifierObject()
    if regionModifierObject is not None and self.isTerminologyInformationValid(regionModifierObject):
      segmentData["AnatomicRegionModifierSequence"] = self.getJSONFromVtkSlicerTerminology(regionModifierObject)
    return segmentData

  def isTerminologyInformationValid(self, termTypeObject):
    return all(t is not None for t in [termTypeObject.GetCodeValue(), termTypeObject.GetCodingSchemeDesignator(),
                                       termTypeObject.GetCodeMeaning()])

  def getJSONFromVtkSlicerTerminology(self, termTypeObject):
    return self.createCodeSequence(termTypeObject.GetCodeValue(), termTypeObject.GetCodingSchemeDesignator(),
                                   termTypeObject.GetCodeMeaning())

  def createCodeSequence(self, value, designator, meaning):
    return {"CodeValue": value,
            "CodingSchemeDesignator": designator,
            "CodeMeaning": meaning}

#
# DICOMSegmentationPlugin
#

class DICOMSegmentationPlugin:
  """
  This class is the 'hook' for slicer to detect and recognize the plugin
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "DICOM Segmentation Object Import Plugin"
    parent.categories = ["Developer Tools.DICOM Plugins"]
    parent.contributors = ["Andrey Fedorov, BWH"]
    parent.helpText = """
    Plugin to the DICOM Module to parse and load DICOM SEG modality.
    No module interface here, only in the DICOM module
    """
    parent.dependencies = ['DICOM', 'Colors', 'SlicerDevelopmentToolbox']
    parent.acknowledgementText = """
    This DICOM Plugin was developed by
    Andrey Fedorov, BWH.
    and was partially funded by NIH grant U01CA151261.
    """

    # Add this extension to the DICOM module's list for discovery when the module
    # is created.  Since this module may be discovered before DICOM itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.dicomPlugins
    except AttributeError:
      slicer.modules.dicomPlugins = {}
    slicer.modules.dicomPlugins['DICOMSegmentationPlugin'] = DICOMSegmentationPluginClass
