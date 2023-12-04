from __future__ import absolute_import
import glob
import os
import json
import vtk
import io
import shutil
import vtkSegmentationCorePython as vtkSegmentationCore
import logging
import pydicom

from base.DICOMPluginBase import DICOMPluginBase

import slicer
from DICOMLib import DICOMLoadable

from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS
from six.moves import range


#
# This is the plugin to handle translation of DICOM M3D objects
# M3D stands for Model for 3D Manufacturing.
# DICOM M3D objects can be for example .STL files encoded into DICOM M3D.
#
class DICOMM3DPluginClass(DICOMPluginBase):

  def __init__(self):
    super(DICOMM3DPluginClass,self).__init__()
    self.loadType = "DICOMM3D"

  def examineFiles(self,files):
    """ Returns a list of DICOMLoadable instances
    corresponding to ways of interpreting the
    files parameter.
    """
    loadables = []

    for candidateFile in files:

      uid = slicer.dicomDatabase.fileValue(candidateFile, self.tags['instanceUID'])
      if uid == '':
        return []

      desc = slicer.dicomDatabase.fileValue(candidateFile, self.tags['seriesDescription'])
      if desc == '':
        desc = "Unknown"

      #read EncapsulatedDocument for candidateFile
      docFile = self.getEncapsulatedDocument(candidateFile)

      #read EncapsulatedDocumentLength for candidateFile
      docLengthFile = self.getEncapsulatedDocumentLength(candidateFile)

      #read modality type to flag M3D object.
      isDicomM3D = (slicer.dicomDatabase.fileValue(candidateFile, self.tags['modality']) == 'M3D')

      if isDicomM3D:
        loadable = DICOMLoadable()
        loadable.files = [candidateFile]
        loadable.name = desc
        loadable.tooltip = loadable.name + ' - as a DICOM M3D object'
        loadable.selected = True
        loadable.confidence = 0.95
        loadable.uid = uid
        loadable.doc = docFile
        loadable.docLength = docLengthFile
        self.addReferences(loadable)
        loadables.append(loadable)

        logging.debug('DICOM M3D modality found')

    return loadables

  def getFrameOfReferenceUID(self, candidateFile):
    """Returns the frame of referenceUID for the given loadable"""
    dcm = pydicom.read_file(candidateFile)
    if hasattr(dcm, "FrameOfReferenceUID"):
      return dcm.FrameOfReferenceUID
    else:
      return 'Unnamed FrameOfReferenceUID'
  
  def referencedSeriesName(self,loadable):
    """Returns the default series name for the given loadable"""
    referencedName = "Unnamed Reference"
    if hasattr(loadable, "referencedSeriesUID"):
      referencedName = self.defaultSeriesNodeName(loadable.referencedSeriesUID)
    return referencedName

  def getEncapsulatedDocument(self, candidateFile):
    dcm = pydicom.read_file(candidateFile)
    if hasattr(dcm, "EncapsulatedDocument"):
      return dcm.EncapsulatedDocument
    else:
      return b''
    
  def getEncapsulatedDocumentLength(self, candidateFile):
    dcm = pydicom.read_file(candidateFile)
    if hasattr(dcm, "EncapsulatedDocumentLength"):
      return dcm.EncapsulatedDocumentLength
    else:
      return 0

  def load(self,loadable):
    """ Load the DICOM M3D object
    """
    logging.debug('DICOM M3D load()')
    try:
      uid = loadable.uid
      logging.debug('in load(): uid = '+uid)
    except AttributeError:
      return False

    self.tempDir = slicer.util.tempDirectory()
    print(self.tempDir)
    try:
        os.makedirs(self.tempDir)
    except OSError:
      pass
    
    stlFileName = slicer.dicomDatabase.fileForInstance(uid)
    if stlFileName is None:
      logging.error('Failed to get the filename from the DICOM database for ' + uid)
      self.cleanup()
      return False
    
    read_buffer = io.BytesIO(loadable.doc)
    buffer_view = read_buffer.getbuffer()
    if (int(loadable.docLength) % 2) != 0:
      buffer_view = buffer_view[0:(read_buffer.getbuffer().nbytes -1)]
    
    stlFilePath = os.path.join(self.tempDir, "temp.STL")
    
    with open(stlFilePath, 'wb') as file: 
      shutil.copyfileobj(read_buffer, file)
    assert os.path.exists(stlFilePath)
    file.close()

    self._createSegmentationNode(loadable, stlFilePath)
    
    self.cleanup()
    
    return True

  def _createSegmentationNode(self, loadable, stlFilePath):
    #create modelNode
    modelNode = slicer.util.loadModel(stlFilePath)

    # Create segmentation
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    # segmentationNode.CreateDefaultDisplayNodes() # only needed for display
    # Initialize segmentation
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    segmentationNode.SetName(loadable.name)

    segmentationDisplayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationDisplayNode")
    segmentationNode.SetAndObserveDisplayNodeID(segmentationDisplayNode.GetID())

    vtkSegConverter = vtkSegmentationCore.vtkSegmentationConverter
    segmentation = vtkSegmentationCore.vtkSegmentation()
    segmentation.SetMasterRepresentationName(vtkSegConverter.GetSegmentationBinaryLabelmapRepresentationName())
    segmentation.CreateRepresentation(vtkSegConverter.GetSegmentationClosedSurfaceRepresentationName(), True)
    segmentationNode.SetAndObserveSegmentation(segmentation)
    #load model into segmentation node
    self._importModelToSegAndRemoveModel(modelNode, segmentationNode)
    self.addSeriesInSubjectHierarchy(loadable, segmentationNode)
    if hasattr(pydicom.read_file(loadable.files[0]), "FrameOfReferenceUID"):
      self._findAndSetGeometryReference(self.getFrameOfReferenceUID(loadable.files[0]), segmentationNode)
    else:
      print("no frame of referenceUID found in dcm file!")
    return segmentationNode
  
  def _importModelToSegAndRemoveModel(self, ModelNode, segmentationNode):
    segmentationsLogic = slicer.modules.segmentations.logic()
    segmentation = segmentationNode.GetSegmentation()
    numberOfSegmentsBeforeImport = segmentation.GetNumberOfSegments()
    success = segmentationsLogic.ImportModelToSegmentationNode(ModelNode, segmentationNode)
    if segmentation.GetNumberOfSegments() == 0:
        logging.warning("Empty segment loaded from DICOM SEG!")
    if segmentation.GetNumberOfSegments() - numberOfSegmentsBeforeImport > 1:
        logging.warning("Multiple segments were loaded from DICOM SEG labelmap. Only one label was expected.")
    if success and segmentation.GetNumberOfSegments()>0:
      segment = segmentation.GetNthSegment(segmentation.GetNumberOfSegments() - 1)
      segment.SetName("segment 1")
      segment.SetNameAutoGenerated(False)

      self._removeModelNode(ModelNode)
    return segmentation
  
  def _removeModelNode(self, modelNode):
    dNode = modelNode.GetDisplayNode()
    if dNode is not None:
      slicer.mrmlScene.RemoveNode(dNode)
    slicer.mrmlScene.RemoveNode(modelNode)

  def _findAndSetGeometryReference(self, FrameOfReferenceUID, segmentationNode):
    shn = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    segID = shn.GetItemByDataNode(segmentationNode)
    parentID = shn.GetItemParent(segID)
    childIDs = vtk.vtkIdList()
    shn.GetItemChildren(parentID, childIDs)
    uidName = slicer.vtkMRMLSubjectHierarchyConstants.GetDICOMFrameOfReferenceUIDAttributeName()
    matches = []
    for childID in reversed([childIDs.GetId(id) for id in range(childIDs.GetNumberOfIds()) if segID]):
      if childID == segID:
        continue
      if shn.GetItemUID(childID, uidName) == FrameOfReferenceUID:
        print('FOUND image dcm matching segmentation node!')
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
        # Define common required tags and default values
        exportable.setTag('Modality', 'SEG')
        exportable.setTag('SeriesDescription', dataNode.GetName())
        exportable.setTag('SeriesNumber', '100')
    return exportable

  def _setupExportable(self, exportable, subjectHierarchyItemID):
    if not exportable:
      return []
    exportable.name = self.loadType
    exportable.tooltip = "Create DICOM files from segmentation"
    exportable.subjectHierarchyItemID = subjectHierarchyItemID
    exportable.pluginClass = self.__module__
    return [exportable]

  def export(self, exportables):
    try:
      slicer.modules.segmentations
    except AttributeError as exc:
      return str(exc)

    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    if shNode is None:
      error = "Invalid subject hierarchy"
      logging.error(error)
      return error

    for exportable in exportables:
      subjectHierarchyItemID = exportable.subjectHierarchyItemID
      segmentationNode = shNode.GetItemDataNode(subjectHierarchyItemID)

      exporter = DICOMSegmentationExporter(segmentationNode)

      metadata = {}
      for attr in ["SeriesNumber", "SeriesDescription", "ContentCreatorName", "ClinicalTrialSeriesID", "ClinicalTrialTimePointID",
        "ClinicalTrialCoordinatingCenterName"]:
        if exportable.tag(attr) != "":
          metadata[attr] = exportable.tag(attr)

      try:
        segFileName = "subject_hierarchy_export.SEG" + exporter.currentDateTime + ".dcm"
        segFilePath = os.path.join(exportable.directory, segFileName)
        try:
          exporter.export(exportable.directory, segFileName, metadata)
        except DICOMSegmentationExporter.EmptySegmentsFoundError as exc:
          if slicer.util.confirmYesNoDisplay(str(exc)):
            exporter.export(exportable.directory, segFileName, metadata, skipEmpty=True)
          else:
            raise ValueError("Export canceled")
        slicer.dicomDatabase.insert(segFilePath)
        logging.info("Added segmentation to DICOM database (" +segFilePath+")")
      except (DICOMSegmentationExporter.NoNonEmptySegmentsFoundError, ValueError) as exc:
        return str(exc)
      except Exception as exc:
        # Generic error
        import traceback
        traceback.print_exc()
        return "Segmentation object export failed.\n{0}".format(str(exc))
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
      raise ValueError("Invalid segmentation node")
    referencedVolumeNode = segmentationNode.GetNodeReference(segmentationNode.GetReferenceImageGeometryReferenceRole())
    if not referencedVolumeNode:
      raise ValueError("Referenced volume is not found for the segmentation. Specify segmentation geometry using a volume node as source.")
    return referencedVolumeNode

  @property
  def currentDateTime(self, outputFormat='%Y-%m-%d_%H%M%S'):
    from datetime import datetime
    return datetime.now().strftime(outputFormat)

  def __init__(self, segmentationNode, contentCreatorName=None):
    self.segmentationNode = segmentationNode
    self.contentCreatorName = contentCreatorName if contentCreatorName else "Slicer"

    self.tempDir = slicer.util.tempDirectory()

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

    metadataDefaults = {}
    metadataDefaults["SeriesNumber"] = "100"
    metadataDefaults["SeriesDescription"] = "Segmentation"
    metadataDefaults["ContentCreatorName"] = self.contentCreatorName
    metadataDefaults["ClinicalTrialSeriesID"] = "1"
    metadataDefaults["ClinicalTrialTimePointID"] = "1"
    metadataDefaults["ClinicalTrialCoordinatingCenterName"] = "QIICR"

    for attr in ["SeriesNumber", "SeriesDescription", "ContentCreatorName", "ClinicalTrialSeriesID", "ClinicalTrialTimePointID",
                   "ClinicalTrialCoordinatingCenterName"]:
      try:
        if data[attr] == "":
          data[attr] = metadataDefaults[attr]

      except KeyError as exc:
        data[attr] = metadataDefaults[attr]

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

    # Check if referenced image files are found and raise exception with a descriptive message in case of an error.
    numberOfImageFilesNotFound = 0
    for inputDICOMImageFileName in inputDICOMImageFileNames:
      if not inputDICOMImageFileName:
        numberOfImageFilesNotFound += 1
    if numberOfImageFilesNotFound > 0:
      numberOfImageFilesTotal = len(inputDICOMImageFileNames)
      raise ValueError(f"Referenced volume files were not found in the DICOM database (missing {numberOfImageFilesNotFound} files out of {numberOfImageFilesTotal}).")

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
    segmentData["SegmentLabel"] = segment.GetName()
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
    categoryObject_invalid = categoryObject is None or not self.isTerminologyInformationValid(categoryObject)

    typeObject = terminologyEntry.GetTypeObject()
    typeObject_invalid = typeObject is None or not self.isTerminologyInformationValid(typeObject)

    if categoryObject_invalid or typeObject_invalid:
      logging.warning("Terminology information invalid or unset! This might lead to crashes during the conversion to "
                      "SEG objects. Make sure to select a terminology class for all segments in the Slicer scene.")
      return {}

    segmentData["SegmentedPropertyCategoryCodeSequence"] = self.getJSONFromVtkSlicerTerminology(categoryObject)
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


class DICOMM3DPlugin:
  """
  This class is the 'hook' for slicer to detect and recognize the plugin
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "DICOM M3D Object Import Plugin"
    parent.categories = ["Developer Tools.DICOM Plugins"]
    parent.contributors = ["Cosmin Ciausu, BWH"]
    parent.helpText = """
    Plugin to the DICOM Module to parse and load DICOM M3D modality.
    No module interface here, only in the DICOM module
    """
    parent.dependencies = ['DICOM', 'Colors', 'SlicerDevelopmentToolbox']
    parent.acknowledgementText = """
    This DICOM Plugin was developed by
    Cosmin Ciausu, BWH.
    """

    # Add this extension to the DICOM module's list for discovery when the module
    # is created.  Since this module may be discovered before DICOM itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.dicomPlugins
    except AttributeError:
      slicer.modules.dicomPlugins = {}
    slicer.modules.dicomPlugins['DICOMM3DPlugin'] = DICOMM3DPluginClass