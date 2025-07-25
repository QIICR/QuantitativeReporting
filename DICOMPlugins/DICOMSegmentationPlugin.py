from __future__ import absolute_import
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
from six.moves import range


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
      "mergeSegments": True,
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

    numberOfSegmentations = len(glob.glob(os.path.join(self.tempDir,'*.nrrd')))

    # resize the color table to include the segments plus 0 for the background

    seriesName = self.referencedSeriesName(loadable)
    segmentLabelNodes = []
    metaFileName = os.path.join(self.tempDir,"meta.json")

    # Load terminology in the metafile into context
    terminologiesLogic = slicer.modules.terminologies.logic()

    categoryContextName = loadable.name
    if not terminologiesLogic.LoadTerminologyFromSegmentDescriptorFile(categoryContextName, metaFileName):
      categoryContextName = "Segmentation category and type - DICOM master list"

    anatomicContextName = loadable.name
    try:
      if not terminologiesLogic.LoadRegionContextFromSegmentDescriptorFile(anatomicContextName, metaFileName):
        anatomicContextName = "Anatomic codes - DICOM master list"
    except AttributeError:
      # backward compatibility with Slicer 5.8.1
      if not terminologiesLogic.LoadAnatomicContextFromSegmentDescriptorFile(anatomicContextName, metaFileName):
        anatomicContextName = "Anatomic codes - DICOM master list"

    with open(metaFileName) as metaFile:
      data = json.load(metaFile)
      logging.debug('Loaded segmentation metadata from ' + metaFileName)

      logging.debug('number of segmentation files = ' + str(numberOfSegmentations))
      if numberOfSegmentations != len(data["segmentAttributes"]):
        logging.error('Loading failed: Inconsistent number of segments in the descriptor file and on disk')
        return

      for segmentationId,segmentAttributes in enumerate(data["segmentAttributes"]):

        # TODO: Create logic class that both CLI and this plugin uses so that we don't need to have temporary NRRD
        # files and labelmap nodes
        # if not hasattr(slicer.modules, 'segmentations'):

        labelFileName = os.path.join(self.tempDir, str(segmentationId+1) + ".nrrd")
        # The temporary folder contains 1.nrrd, 2.nrrd,... files. We must specify singleFile=True to ensure
        # they are not loaded as an image stack (could happen if each image file has a single slice only).
        labelNode = slicer.util.loadLabelVolume(labelFileName, {'singleFile': True})

        labelNode.labelAttributes = []

        for segment in segmentAttributes:
          try:
            rgb255 = segment["recommendedDisplayRGBValue"]
            rgb = [float(c) / 255. for c in rgb255]
          except KeyError:
            rgb = (150., 150., 0.)

          segmentId = segment["labelID"]

          categoryCode, categoryCodingScheme, categoryCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "SegmentedPropertyCategoryCodeSequence")

          typeCode, typeCodingScheme, typeCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "SegmentedPropertyTypeCodeSequence")

          typeModCode, typeModCodingScheme, typeModCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "SegmentedPropertyTypeModifierCodeSequence")

          regionCode, regionCodingScheme, regionCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "AnatomicRegionSequence")

          regionModCode, regionModCodingScheme, regionModCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "AnatomicRegionModifierSequence")

          segmentTerminologyTag = terminologiesLogic.SerializeTerminologyEntry(
                                    categoryContextName,
                                    categoryCode, categoryCodingScheme, categoryCodeMeaning,
                                    typeCode, typeCodingScheme, typeCodeMeaning,
                                    typeModCode, typeModCodingScheme, typeModCodeMeaning,
                                    anatomicContextName,
                                    regionCode, regionCodingScheme, regionCodeMeaning,
                                    regionModCode, regionModCodingScheme, regionModCodeMeaning)


          # Set terminology properties as attributes to the label node (which is a temporary node)
          segmentNameAutoGenerated = False  # automatically generated from terminology
          if segment["SegmentLabel"]:
            segmentName = segment["SegmentLabel"]
          elif segment["SegmentDescription"]:
            segmentName = segment["SegmentDescription"]
          else:
            segmentName = typeCodeMeaning
            segmentNameAutoGenerated = True

          labelAttributes = {}
          labelAttributes["Name"] = segmentName
          labelAttributes["NameAutoGenerated"] = segmentNameAutoGenerated
          labelAttributes["Description"] = segment["SegmentDescription"]
          labelAttributes["Terminology"] = segmentTerminologyTag
          labelAttributes["ColorR"] = rgb[0]
          labelAttributes["ColorG"] = rgb[1]
          labelAttributes["ColorB"] = rgb[2]
          labelAttributes["DICOM.SegmentAlgorithmType"] = segment["SegmentAlgorithmType"] if "SegmentAlgorithmType" in segment else None
          labelAttributes["DICOM.SegmentAlgorithmName"] = segment["SegmentAlgorithmName"] if "SegmentAlgorithmName" in segment else None

          labelNode.labelAttributes.append(labelAttributes)

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

    segmentationNode.SetAttribute("DICOM.instanceUIDs", loadable.uid)

  def _importSegmentAndRemoveLabel(self, segmentLabelNode, segmentationNode):
    segmentationsLogic = slicer.modules.segmentations.logic()
    segmentation = segmentationNode.GetSegmentation()
    numberOfSegmentsBeforeImport = segmentation.GetNumberOfSegments()
    success = segmentationsLogic.ImportLabelmapToSegmentationNode(segmentLabelNode, segmentationNode)

    if not success:
      logging.error("Failed to import segment from labelmap!")
      return

    if segmentation.GetNumberOfSegments() == 0:
        logging.warning("Empty segment loaded from DICOM SEG!")

    thisLabelSegmentID = 0
    for segmentId in range(numberOfSegmentsBeforeImport, segmentation.GetNumberOfSegments()):
      logging.info(f"Setting attributes for segment {segmentId} ...")

      segment = segmentation.GetNthSegment(segmentId)
      segment.SetName(segmentLabelNode.labelAttributes[thisLabelSegmentID]["Name"])
      segment.SetNameAutoGenerated(segmentLabelNode.labelAttributes[thisLabelSegmentID]["NameAutoGenerated"])
      segment.SetTag("Description", segmentLabelNode.labelAttributes[thisLabelSegmentID]["Description"])
      segment.SetColor([float(segmentLabelNode.labelAttributes[thisLabelSegmentID]["ColorR"]),
                        float(segmentLabelNode.labelAttributes[thisLabelSegmentID]["ColorG"]),
                        float(segmentLabelNode.labelAttributes[thisLabelSegmentID]["ColorB"])])
      segment.SetTag(vtkSegmentationCore.vtkSegment.GetTerminologyEntryTagName(),
                     segmentLabelNode.labelAttributes[thisLabelSegmentID]["Terminology"])
      algorithmName = segmentLabelNode.labelAttributes[thisLabelSegmentID]["DICOM.SegmentAlgorithmName"]
      if algorithmName is not None:
        segment.SetTag("DICOM.SegmentAlgorithmName", algorithmName)
      algorithmType = segmentLabelNode.labelAttributes[thisLabelSegmentID]["DICOM.SegmentAlgorithmType"]
      if algorithmType is not None:
        segment.SetTag("DICOM.SegmentAlgorithmType", algorithmType)
      thisLabelSegmentID += 1

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
    segmentation.SetSourceRepresentationName(vtkSegConverter.GetSegmentationBinaryLabelmapRepresentationName())
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
    segmentData.update(self.createJSONFromRegionContext(terminologyEntry))
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

  def createJSONFromRegionContext(self, terminologyEntry):
    segmentData = dict()

    try:
      regionObject = terminologyEntry.GetRegionObject()
    except AttributeError:
      # backward compatibility with Slicer 5.8.1
      regionObject = terminologyEntry.GetAnatomicRegionObject()

    if regionObject is None or not self.isTerminologyInformationValid(regionObject):
      return {}
    segmentData["AnatomicRegionSequence"] = self.getJSONFromVtkSlicerTerminology(regionObject)

    try:
      regionModifierObject = terminologyEntry.GetRegionModifierObject()
    except AttributeError:
      # backward compatibility with Slicer 5.8.1
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
