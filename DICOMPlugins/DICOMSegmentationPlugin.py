import glob
import os
import json
import vtk
import logging
import getpass

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

  def examine(self,fileLists):
    """ Returns a list of DICOMLoadable instances
    corresponding to ways of interpreting the
    fileLists parameter.
    """
    loadables = []
    for files in fileLists:
      loadables += self.examineFiles(files)
    return loadables

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
        loadable.name = desc + ' - as a DICOM SEG object'
        loadable.tooltip = loadable.name
        loadable.selected = True
        loadable.confidence = 0.95
        loadable.uid = uid
        self.addReferences(loadable)
        refName = self.referencedSeriesName(loadable)
        if refName != "":
          loadable.name = refName + " " + desc + " - Segmentations"

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
      logging.debug('in load(): uid = ', uid)
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
          # load each of the segments' segmentations
          # Initialize color and terminology from .info file
          # See SEG2NRRD.cxx and EncodeSEG.cxx for how it's written.
          # Format of the .info file (no leading spaces, labelNum, RGBColor, SegmentedPropertyCategory and
          # SegmentedPropertyCategory are required):
          # labelNum;RGB:R,G,B;SegmentedPropertyCategory:code,scheme,meaning;SegmentedPropertyType:code,scheme,meaning;SegmentedPropertyTypeModifier:code,scheme,meaning;AnatomicRegion:code,scheme,meaning;AnatomicRegionModifier:code,scheme,meaning
          # R, G, B are 0-255 in file, but mapped to 0-1 for use in color node
          # set defaults in case of missing fields, modifiers are optional

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

          dummyTerminologyWidget = slicer.qSlicerTerminologyNavigatorWidget() # Still cannot call static methods from python
          segmentTerminologyTag = dummyTerminologyWidget.serializeTerminologyEntry(
                                          loadable.name,
                                          categoryCode, categoryCodingScheme, categoryCodeMeaning,
                                          typeCode, typeCodingScheme, typeCodeMeaning,
                                          typeModCode, typeModCodingScheme, typeModCodeMeaning,
                                          loadable.name,
                                          regionCode, regionCodingScheme, regionCodeMeaning,
                                          regionModCode, regionModCodingScheme, regionModCodeMeaning)
          # end of processing a line of terminology

          # TODO: Create logic class that both CLI and this plugin uses so that we don't need to have temporary NRRD files and labelmap nodes
          # if not hasattr(slicer.modules, 'segmentations'):

          # load the segmentation volume file and name it for the reference series and segment color
          labelFileName = os.path.join(self.tempDir, str(segmentId) + ".nrrd")
          segmentName = seriesName + "-" + typeCodeMeaning + "-label"
          (success, labelNode) = slicer.util.loadLabelVolume(labelFileName,
                                                             properties={'name': segmentName},
                                                             returnNode=True)
          if not success:
            raise ValueError("{} could not be loaded into Slicer!".format(labelFileName))
          segmentLabelNodes.append(labelNode)
          
          # Set terminology properties as attributes to the label node (which is a temporary node)
          #TODO: This is a quick solution, maybe there is a better one
          labelNode.SetAttribute("Terminology", segmentTerminologyTag)
          labelNode.SetAttribute("ColorR", str(rgb[0]))
          labelNode.SetAttribute("ColorG", str(rgb[1]))
          labelNode.SetAttribute("ColorB", str(rgb[2]))

          # Create subject hierarchy for the loaded series
          self.addSeriesInSubjectHierarchy(loadable, labelNode)

      metaFile.close()

    self.cleanup()

    import vtkSegmentationCorePython as vtkSegmentationCore

    segmentationNode = slicer.vtkMRMLSegmentationNode()
    segmentationNode.SetName(seriesName)
    slicer.mrmlScene.AddNode(segmentationNode)

    segmentationDisplayNode = slicer.vtkMRMLSegmentationDisplayNode()
    slicer.mrmlScene.AddNode(segmentationDisplayNode)
    segmentationNode.SetAndObserveDisplayNodeID(segmentationDisplayNode.GetID())

    segmentation = vtkSegmentationCore.vtkSegmentation()
    segmentation.SetMasterRepresentationName(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName())

    segmentationNode.SetAndObserveSegmentation(segmentation)
    self.addSeriesInSubjectHierarchy(loadable, segmentationNode)

    for segmentLabelNode in segmentLabelNodes:
      segment = vtkSegmentationCore.vtkSegment()
      segment.SetName(segmentLabelNode.GetName())

      segmentColor = [float(segmentLabelNode.GetAttribute("ColorR")), float(segmentLabelNode.GetAttribute("ColorG")), float(segmentLabelNode.GetAttribute("ColorB"))]
      segment.SetColor(segmentColor)
      
      segment.SetTag(vtkSegmentationCore.vtkSegment.GetTerminologyEntryTagName(), segmentLabelNode.GetAttribute("Terminology"))

      #TODO: when the logic class is created, this will need to be changed
      orientedImage = slicer.vtkSlicerSegmentationsModuleLogic.CreateOrientedImageDataFromVolumeNode(segmentLabelNode)
      segment.AddRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName(), orientedImage)
      segmentation.AddSegment(segment)

      segmentDisplayNode = segmentLabelNode.GetDisplayNode()
      if segmentDisplayNode is not None:
        slicer.mrmlScene.RemoveNode(segmentDisplayNode)
      slicer.mrmlScene.RemoveNode(segmentLabelNode)

    segmentation.CreateRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName(), True)

    return True

  def examineForExport(self, subjectHierarchyItemID):
    exportable = None

    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    dataNode = shNode.GetItemDataNode(subjectHierarchyItemID)
    if dataNode and dataNode.IsA('vtkMRMLSegmentationNode'):
      # Check to make sure all referenced UIDs exist in the database.
      instanceUIDs = shNode.GetItemAttribute(subjectHierarchyItemID, "DICOM.ReferencedInstanceUIDs").split()
      if instanceUIDs == "":
          return []

      for instanceUID in instanceUIDs:
        inputDICOMImageFileName = slicer.dicomDatabase.fileForInstance(instanceUID)
        if inputDICOMImageFileName == "":
          return []

      exportable = slicer.qSlicerDICOMExportable()
      exportable.confidence = 1.0
      exportable.setTag('Modality', 'SEG')

    if exportable is not None:
      exportable.name = self.loadType
      exportable.tooltip = "Create DICOM files from segmentation"
      exportable.subjectHierarchyItemID = subjectHierarchyItemID
      exportable.pluginClass = self.__module__
      # Define common required tags and default values
      exportable.setTag('SeriesDescription', 'No series description')
      exportable.setTag('SeriesNumber', '1')
      return [exportable]

    return []

  def export(self, exportables):
    exportablesCollection = vtk.vtkCollection()
    for exportable in exportables:
      vtkExportable = slicer.vtkSlicerDICOMExportable()
      exportable.copyToVtkExportable(vtkExportable)
      exportablesCollection.AddItem(vtkExportable)

    return self.exportAsDICOMSEG(exportablesCollection)

  def exportAsDICOMSEG(self, exportablesCollection):
    """Export the given node to a segmentation object and load it in the DICOM database

    This function was copied and modified from the EditUtil.py function of the same name in Slicer.
    """

    if hasattr(slicer.modules, 'segmentations'):
      exportable = exportablesCollection.GetItemAsObject(0)
      shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
      subjectHierarchyItemID = exportable.GetSubjectHierarchyItemID()
      segmentationNode = shNode.GetItemDataNode(subjectHierarchyItemID)

      exporter = DICOMSegmentationExporter(segmentationNode)

      try:
        segFileName = "subject_hierarchy_export.SEG" + exporter.currentDateTime + ".dcm"
        segFilePath = os.path.join(slicer.app.temporaryPath, segFileName)
        exporter.export(segFilePath)

        slicer.dicomDatabase.insert(segFilePath)
        logging.info("Added segmentation to DICOM database (%s)", segFilePath)
      except ValueError as exc:
        return exc.message
      finally:
        exporter.cleanup()
    return ""


class DICOMSegmentationExporter(ModuleLogicMixin):
  """This class can be used for exporting a segmentation into DICOM """

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

    import vtkSegmentationCorePython as vtkSegmentationCore

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
    self.contentCreatorName = contentCreatorName if contentCreatorName else getpass.getuser()

  def cleanup(self):
    try:
      import shutil
      logging.debug("Cleaning up temporarily created directory {}".format(self.tempDir))
      shutil.rmtree(self.tempDir)
    except AttributeError:
      pass

  def export(self, segFilePath, segmentIDs=None):
    data = self._getSeriesAttributes()
    data["SeriesDescription"] = "Segmentation"
    data.update(self._getAdditionalSeriesAttributes())

    segmentIDs = segmentIDs if segmentIDs else self.getSegmentIDs(self.segmentationNode)

    # NB: for now segments are filter if they are empty and only the non empty ones are returned
    segmentIDs = self.getNonEmptySegmentIDs(segmentIDs)

    if not len(segmentIDs):
      raise ValueError("No non empty segments found.")

    data["segmentAttributes"] = self.generateJSON4DcmSEGExport(segmentIDs)

    logging.debug("DICOM SEG Metadata output:")
    logging.debug(data)

    self.tempDir = os.path.join(slicer.util.tempDirectory(), self.currentDateTime)
    os.mkdir(self.tempDir)


    metaFilePath = self.saveJSON(data, os.path.join(self.tempDir, "seg_meta.json"))

    segmentFiles = self.createAndGetLabelMapsFromSegments(segmentIDs)
    inputDICOMImageFileNames = self.getDICOMFileList(self.getReferencedVolumeFromSegmentationNode(self.segmentationNode),
                                                     absolutePaths=True)

    params = {
      "dicomImageFiles": ', '.join(inputDICOMImageFileNames).replace(', ', ","),
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

    if cliNode.GetStatusString() != 'Completed':
      raise RuntimeError("itkimage2segimage CLI did not complete cleanly")

    if not os.path.exists(segFilePath):
      raise RuntimeError("DICOM Segmentation was not created. Check Error Log for further information.")

    logging.debug("Saved DICOM Segmentation to {}".format(segFilePath))
    return True

  def getNonEmptySegmentIDs(self, segmentIDs):
    segmentation = self.segmentationNode.GetSegmentation()
    return [segmentID for segmentID in segmentIDs if not self.isSegmentEmpty(segmentation.GetSegment(segmentID))]

  def isSegmentEmpty(self, segment):
    bounds = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    segment.GetBounds(bounds)
    return bounds[1] < 0 and bounds[3] < 0 and bounds[5] < 0

  def createAndGetLabelMapsFromSegments(self, segmentIDs):
    segmentFiles = []
    for segmentID in segmentIDs:
      segmentLabelmap = self.createLabelNodeFromSegment(self.segmentationNode, segmentID)
      filename = os.path.join(self.tempDir, "{}.nrrd".format(segmentLabelmap.GetName()))
      slicer.util.saveNode(segmentLabelmap, filename)
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

  def _getSeriesAttributes(self):
    attributes = dict()
    volumeNode = self.getReferencedVolumeFromSegmentationNode(self.segmentationNode)
    seriesNumber = ModuleLogicMixin.getDICOMValue(volumeNode, DICOMTAGS.SERIES_NUMBER)
    attributes["SeriesNumber"] = "100" if seriesNumber in [None,''] else str(int(seriesNumber)+100)
    attributes["InstanceNumber"] = "1"
    return attributes

  def _getAdditionalSeriesAttributes(self):
    return {"ContentCreatorName": self.contentCreatorName,
            "ClinicalTrialSeriesID": "1",
            "ClinicalTrialTimePointID": "1",
            "ClinicalTrialCoordinatingCenterName": "QIICR"}

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
    segmentData["SegmentAlgorithmType"] = "MANUAL"
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

  def getDeserializedTerminologyEntry(self, vtkSegment):
    terminologyWidget = slicer.qSlicerTerminologyNavigatorWidget()
    terminologyEntry = slicer.vtkSlicerTerminologyEntry()
    tag = vtk.mutable("")
    vtkSegment.GetTag(vtkSegment.GetTerminologyEntryTagName(), tag)
    terminologyWidget.deserializeTerminologyEntry(tag, terminologyEntry)
    return terminologyEntry

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
    parent.dependencies = ['DICOM', 'Colors']
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
