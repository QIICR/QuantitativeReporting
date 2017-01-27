import glob, os, json
import string
import vtk, qt, ctk, slicer
from DICOMPluginBase import DICOMPluginBase
from DICOMLib import DICOMLoadable
import logging

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
      "inputDICOM": segFileName,
      "outputDirectory": self.tempDir,
      "outputType": "nrrd"
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

          # create Subject hierarchy nodes for the loaded series
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

  def examineForExport(self, node):

    # Not implemented at the moment
    
    exportable = None

    return []

  def export(self, exportables):

    exportablesCollection = vtk.vtkCollection()
    for exportable in exportables:
      vtkExportable = slicer.vtkSlicerDICOMExportable()
      exportable.copyToVtkExportable(vtkExportable)
      exportablesCollection.AddItem(vtkExportable)

    self.exportAsDICOMSEG(exportablesCollection)

  def exportAsDICOMSEG(self, exportablesCollection):
    """Export the given node to a segmentation object and load it in the
    DICOM database
    """
    return

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
    parent.contributors = ["Andrey Fedorov, BWH, Christian Herz, BWH"]
    parent.helpText = """
    Plugin to the DICOM Module to parse and load DICOM SEG modality.
    No module interface here, only in the DICOM module
    """
    parent.dependencies = ['DICOM', 'Colors']
    parent.acknowledgementText = """
    This DICOM Plugin was developed by Andrey Fedorov, BWH and Christian Herz, BWH.
    and was partially funded by NIH grant U01CA151261 and U24 CA180918.
    """

    # Add this extension to the DICOM module's list for discovery when the module
    # is created.  Since this module may be discovered before DICOM itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.dicomPlugins
    except AttributeError:
      slicer.modules.dicomPlugins = {}
    slicer.modules.dicomPlugins['DICOMSegmentationPlugin'] = DICOMSegmentationPluginClass
