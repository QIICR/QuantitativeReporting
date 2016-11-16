import glob, os, json
from datetime import datetime
import string
import vtk, qt, ctk, slicer
from DICOMLib import DICOMPlugin
from DICOMLib import DICOMLoadable

#
# This is the plugin to handle translation of DICOM SEG objects
#

class DICOMSegmentationPluginClass(DICOMPlugin):

  def __init__(self,epsilon=0.01):
    super(DICOMSegmentationPluginClass,self).__init__()
    self.loadType = "DICOMSegmentation"

    self.tags['seriesInstanceUID'] = "0020,000E"
    self.tags['seriesDescription'] = "0008,103E"
    self.tags['seriesNumber'] = "0020,0011"
    self.tags['modality'] = "0008,0060"
    self.tags['instanceUID'] = "0008,0018"

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

      number = slicer.dicomDatabase.fileValue(cFile, self.tags['seriesNumber'])
      if number == '':
        number = "Unknown"

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

        print('DICOM SEG modality found')

    return loadables

  def referencedSeriesName(self,loadable):
    """Returns the default series name for the given loadable"""
    referencedName = "Unnamed Reference"
    if hasattr(loadable, "referencedSeriesUID"):
      referencedName = self.defaultSeriesNodeName(loadable.referencedSeriesUID)
    return referencedName

  def addReferences(self,loadable):
    """Puts a list of the referenced UID into the loadable for use
    in the node if this is loaded."""
    import dicom
    dcm = dicom.read_file(loadable.files[0])

    if hasattr(dcm, "ReferencedSeriesSequence"):
      # look up all of the instances in the series, since segmentation frames
      #  may be non-contiguous
      if hasattr(dcm.ReferencedSeriesSequence[0], "SeriesInstanceUID"):
        loadable.referencedInstanceUIDs = []
        for f in slicer.dicomDatabase.filesForSeries(dcm.ReferencedSeriesSequence[0].SeriesInstanceUID):
          refDCM = dicom.read_file(f)
          # this is a hack that should probably fixed in Slicer core - not all
          #  of those instances are truly referenced!
          loadable.referencedInstanceUIDs.append(refDCM.SOPInstanceUID)
          loadable.referencedSeriesUID = dcm.ReferencedSeriesSequence[0].SeriesInstanceUID

  def getValuesFromCodeSequence(self, segment, codeSequenceName, defaults=None):
    try:
      cs = segment[codeSequenceName]
      return cs["CodeValue"], cs["CodingSchemeDesignator"], cs["CodeMeaning"]
    except KeyError:
      return defaults if defaults else ['', '', '']

  def load(self,loadable):
    """ Load the DICOM SEG object
    """
    print('DICOM SEG load()')
    try:
      uid = loadable.uid
      print ('in load(): uid = ', uid)
    except AttributeError:
      return False

    # make the output directory
    currentDateTime = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    outputDir = os.path.join(slicer.app.temporaryPath, "QIICR", "SEG", currentDateTime, loadable.uid)
    try:
      os.makedirs(outputDir)
    except OSError:
      pass

    # produces output label map files, one per segment, and information files with
    # the terminology information for each segment
    segFileName = slicer.dicomDatabase.fileForInstance(uid)
    if segFileName is None:
      print 'Failed to get the filename from the DICOM database for ', uid
      return False

    parameters = {
      "inputSEGFileName": segFileName,
      "outputDirName": outputDir,
      }

    try:
      segimage2itkimage = slicer.modules.segimage2itkimage
    except AttributeError:
      print 'Unable to find CLI module segimage2itkimage, unable to load DICOM Segmentation object'
      return False

    cliNode = None
    cliNode = slicer.cli.run(segimage2itkimage, cliNode, parameters, wait_for_completion=True)
    if cliNode.GetStatusString() != 'Completed':
      print 'SEG2NRRD did not complete successfully, unable to load DICOM Segmentation'
      return False

    # create a new color node to be set up with the colors in these segments
    #TODO: Revise after new terminology support added
    colorLogic = slicer.modules.colors.logic()
    segmentationColorNode = slicer.vtkMRMLColorTableNode()
    segmentationColorNode.SetName(loadable.name)
    segmentationColorNode.SetTypeToUser()
    segmentationColorNode.SetHideFromEditors(0)
    segmentationColorNode.SetAttribute("Category", "File")
    segmentationColorNode.NamesInitialisedOff()
    slicer.mrmlScene.AddNode(segmentationColorNode)

    # also create a new terminology and associate it with this color node
    colorLogic.CreateNewTerminology(segmentationColorNode.GetName())

    numberOfSegments = len(glob.glob(os.path.join(outputDir,'*.nrrd')))

    # resize the color table to include the segments plus 0 for the background

    seriesName = self.referencedSeriesName(loadable)
    segmentNodes = []
    labelNode = None
    metaFileName = os.path.join(outputDir,"meta.json")

    with open(metaFileName) as metaFile:
      data = json.load(metaFile)
      print ('number of segmentation files = ', numberOfSegments)
      assert numberOfSegments == len(data["segmentAttributes"])
      for segmentAttributes in data["segmentAttributes"]:
        # TODO: only handles the first item of lists
        segmentationColorNode.SetNumberOfColors(numberOfSegments + 1)
        segmentationColorNode.SetColor(0, 'background', 0.0, 0.0, 0.0, 0.0)
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

          segmentId = segment["LabelID"]

          defaults = ['T-D0050', 'Tissue', 'SRT']
          categoryCode, categoryCodingScheme, categoryCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "SegmentedPropertyCategoryCodeSequence", defaults)

          typeCode, typeCodeMeaning, typeCodingScheme = \
            self.getValuesFromCodeSequence(segment, "SegmentedPropertyTypeCodeSequence", defaults)

          typeModCode, typeModCodingScheme, typeModCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "SegmentedPropertyTypeModifierCodeSequence")

          anatomicRegionDefaults = ['T-D0010', 'SRT', 'Entire Body']
          regionCode, regionCodingScheme, regionCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "AnatomicRegionSequence", anatomicRegionDefaults)

          regionModCode, regionModCodingScheme, regionModCodeMeaning = \
            self.getValuesFromCodeSequence(segment, "AnatomicRegionModifierSequence")

          colorName = typeCodeMeaning
          segmentationColorNode.SetColor(segmentId, colorName, *rgb)

          colorLogic.AddTermToTerminology(segmentationColorNode.GetName(), segmentId,
                                          categoryCode, categoryCodingScheme, categoryCodeMeaning,
                                          typeCode, typeCodingScheme, typeCodeMeaning,
                                          typeModCode, typeModCodingScheme, typeModCodeMeaning,
                                          regionCode, regionCodingScheme, regionCodeMeaning,
                                          regionModCode, regionModCodingScheme, regionModCodeMeaning)
        # end of processing a line of terminology

          # TODO: Create logic class that both CLI and this plugin uses so that we don't need to have temporary NRRD files and labelmap nodes
          # if not hasattr(slicer.modules, 'segmentations'):

          # load the segmentation volume file and name it for the reference series and segment color
          labelFileName = os.path.join(outputDir, str(segmentId) + ".nrrd")
          segmentName = seriesName + "-" + colorName + "-label"
          (success, labelNode) = slicer.util.loadLabelVolume(labelFileName,
                                                             properties={'name': segmentName},
                                                             returnNode=True)
          if not success:
            raise ValueError("{} could not be loaded into Slicer!".format(labelFileName))
          segmentNodes.append(labelNode)

          # point the label node to the color node we're creating
          labelDisplayNode = labelNode.GetDisplayNode()
          if labelDisplayNode is None:
            print ('Warning: no label map display node for segment ', segmentId, ', creating!')
            labelNode.CreateDefaultDisplayNodes()
            labelDisplayNode = labelNode.GetDisplayNode()
          labelDisplayNode.SetAndObserveColorNodeID(segmentationColorNode.GetID())

          # TODO: initialize referenced UID (and segment number?) attribute(s)
          # dataset = dicom.read_file(segFileName)
          # referencedSeries = dict()
          # for refSeriesItem in dataset.ReferencedSeriesSequence:
          #   refSOPInstanceUIDs = []
          #   for refSOPInstanceItem in refSeriesItem.ReferencedInstanceSequence:
          #     refSOPInstanceUIDs.append(refSOPInstanceItem.ReferencedSOPInstanceUID)
          #   referencedSeries[refSeriesItem.SeriesInstanceUID] = refSOPInstanceUIDs
          # segmentationNode.SetAttribute("DICOM.referencedInstanceUIDs", str(referencedSeries))

          # create Subject hierarchy nodes for the loaded series
          self.addSeriesInSubjectHierarchy(loadable, labelNode)

      metaFile.close()

    # create a combined (merge) label volume node (only if a segment was created)
    mergeNode = None
    if labelNode:
      volumeLogic = slicer.modules.volumes.logic()
      mergeNode = volumeLogic.CloneVolume(labelNode, seriesName + "-label")
      combiner = slicer.vtkImageLabelCombine()
      for segmentNode in segmentNodes:
        combiner.SetInputConnection(0, mergeNode.GetImageDataConnection() )
        combiner.SetInputConnection(1, segmentNode.GetImageDataConnection() )
        combiner.Update()
        mergeNode.GetImageData().DeepCopy( combiner.GetOutput() )
      for segmentNode in segmentNodes:
        segmentNode.Modified() # sets the MTime so the editor won't think they are older than mergeNode
      # display the mergeNode
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActiveLabelVolumeID( mergeNode.GetID() )
      slicer.app.applicationLogic().PropagateVolumeSelection(0)

    # finalize the color node
    segmentationColorNode.NamesInitialisedOn()

    # TODO: the outputDir should be cleaned up

    if hasattr(slicer.modules, 'segmentations'):

      import vtkSegmentationCorePython as vtkSegmentationCore

      segmentationNode = slicer.vtkMRMLSegmentationNode()
      segmentationNode.SetName(seriesName)
      slicer.mrmlScene.AddNode(segmentationNode)
      segmentationNode.AddNodeReferenceID('colorNodeID', segmentationColorNode.GetID())

      segmentationDisplayNode = slicer.vtkMRMLSegmentationDisplayNode()
      slicer.mrmlScene.AddNode(segmentationDisplayNode)
      segmentationNode.SetAndObserveDisplayNodeID(segmentationDisplayNode.GetID())

      segmentation = vtkSegmentationCore.vtkSegmentation()
      segmentation.SetMasterRepresentationName(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName())

      segmentationNode.SetAndObserveSegmentation(segmentation)
      self.addSeriesInSubjectHierarchy(loadable, segmentationNode)

      colorID = 1
      for segmentNode in segmentNodes:
        segment = vtkSegmentationCore.vtkSegment()
        segment.SetName(segmentNode.GetName())

        segmentColor = [0,0,0,0]
        segmentationColorNode.GetColor(colorID, segmentColor)
        segment.SetDefaultColor(segmentColor[0:3])

        colorID += 1

        #TODO: when the logic class is created, this will need to be changed
        logic = slicer.vtkSlicerSegmentationsModuleLogic()
        orientedImage = logic.CreateOrientedImageDataFromVolumeNode(segmentNode)
        segment.AddRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName(), orientedImage)
        segmentation.AddSegment(segment)

        segmentDisplayNode = segmentNode.GetDisplayNode()
        slicer.mrmlScene.RemoveNode(segmentDisplayNode)
        slicer.mrmlScene.RemoveNode(segmentNode)

      segmentation.CreateRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName(), True)
      slicer.mrmlScene.RemoveNode(mergeNode)

    return True

  def examineForExport(self, node):

    exportable = None

    if node.GetAssociatedNode() and node.GetAssociatedNode().IsA('vtkMRMLSegmentationNode'):

      # Check to make sure all referenced UIDs exist in the database.
      instanceUIDs = node.GetAttribute("DICOM.ReferencedInstanceUIDs").split()
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
      exportable.nodeID = node.GetID()
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

    self.exportAsDICOMSEG(exportablesCollection)

  def exportAsDICOMSEG(self, exportablesCollection):
    """Export the given node to a segmentation object and load it in the
    DICOM database

    This function was copied and modified from the EditUtil.py function of the same name in Slicer.
    """

    import logging

    if hasattr(slicer.modules, 'segmentations'):

      exportable = exportablesCollection.GetItemAsObject(0)
      subjectHierarchyNode = slicer.mrmlScene.GetNodeByID(exportable.GetNodeID())

      instanceUIDs = subjectHierarchyNode.GetAttribute("DICOM.ReferencedInstanceUIDs").split()

      if instanceUIDs == "":
        raise Exception("Editor master node does not have DICOM information")

      # get the list of source DICOM files
      inputDICOMImageFileNames = ""
      for instanceUID in instanceUIDs:
        inputDICOMImageFileNames += slicer.dicomDatabase.fileForInstance(instanceUID) + ","
      inputDICOMImageFileNames = inputDICOMImageFileNames[:-1] # strip last comma

      # save the per-structure volumes in the temp directory
      inputSegmentationsFileNames = ""

      import random # TODO: better way to generate temp file names?
      import vtkITK
      writer = vtkITK.vtkITKImageWriter()
      rasToIJKMatrix = vtk.vtkMatrix4x4()

      import vtkSegmentationCore
      import vtkSlicerSegmentationsModuleLogic
      logic = vtkSlicerSegmentationsModuleLogic.vtkSlicerSegmentationsModuleLogic()

      segmentationNode = subjectHierarchyNode.GetAssociatedNode()

      mergedSegmentationImageData = segmentationNode.GetImageData()
      mergedSegmentationLabelmapNode = slicer.vtkMRMLLabelMapVolumeNode()

      segmentationNode.GetRASToIJKMatrix(rasToIJKMatrix)
      mergedSegmentationLabelmapNode.SetRASToIJKMatrix(rasToIJKMatrix)
      mergedSegmentationLabelmapNode.SetAndObserveImageData(mergedSegmentationImageData)
      mergedSegmentationOrientedImageData = logic.CreateOrientedImageDataFromVolumeNode(mergedSegmentationLabelmapNode)

      segmentation = segmentationNode.GetSegmentation()

      segmentIDs = vtk.vtkStringArray()
      segmentation.GetSegmentIDs(segmentIDs)
      segmentationName = segmentationNode.GetName()

      for i in range(0, segmentIDs.GetNumberOfValues()):
        segmentID = segmentIDs.GetValue(i)
        segment = segmentation.GetSegment(segmentID)

        segmentName = segment.GetName()
        structureName = segmentName[len(segmentationName)+1:-1*len('-label')]

        structureFileName = structureName + str(random.randint(0,vtk.VTK_INT_MAX)) + ".nrrd"
        filePath = os.path.join(slicer.app.temporaryPath, structureFileName)
        writer.SetFileName(filePath)

        segmentImageData = segment.GetRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName())
        paddedImageData = vtkSegmentationCore.vtkOrientedImageData()
        vtkSegmentationCore.vtkOrientedImageDataResample.PadImageToContainImage(segmentImageData, mergedSegmentationOrientedImageData, paddedImageData)

        labelmapImageData = slicer.vtkMRMLLabelMapVolumeNode()
        logic.CreateLabelmapVolumeFromOrientedImageData(paddedImageData, labelmapImageData)

        writer.SetInputDataObject(labelmapImageData.GetImageData())

        labelmapImageData.GetRASToIJKMatrix(rasToIJKMatrix)
        writer.SetRasToIJKMatrix(rasToIJKMatrix)
        logging.debug("Saving to %s..." % filePath)
        writer.Write()
        inputSegmentationsFileNames += filePath + ","
      inputSegmentationsFileNames = inputSegmentationsFileNames[:-1] # strip last comma

      # save the per-structure volumes label attributes
      colorNode = segmentationNode.GetNodeReference('colorNodeID')

      terminologyName = colorNode.GetAttribute("TerminologyName")
      colorLogic = slicer.modules.colors.logic()
      if not terminologyName or not colorLogic:
        raise Exception("No terminology or color logic - cannot export")

      inputLabelAttributesFileNames = ""

      for i in range(0, segmentIDs.GetNumberOfValues()):
        segmentID = segmentIDs.GetValue(i)
        segment = segmentation.GetSegment(segmentID)

        segmentName = segment.GetName()
        structureName = segmentName[len(segmentationName)+1:-1*len('-label')]
        labelIndex = colorNode.GetColorIndexByName( structureName )

        rgbColor = [0,]*4
        colorNode.GetColor(labelIndex, rgbColor)
        rgbColor = map(lambda e: e*255., rgbColor)

        # get the attributes and convert to format CodeValue,CodeMeaning,CodingSchemeDesignator
        # or empty strings if not defined
        propertyCategoryWithColons = colorLogic.GetSegmentedPropertyCategory(labelIndex, terminologyName)
        if propertyCategoryWithColons == '':
          logging.debug ('ERROR: no segmented property category found for label ',str(labelIndex))
          # Try setting a default as this section is required
          propertyCategory = "C94970,NCIt,Reference Region"
        else:
          propertyCategory = propertyCategoryWithColons.replace(':',',')

        propertyTypeWithColons = colorLogic.GetSegmentedPropertyType(labelIndex, terminologyName)
        propertyType = propertyTypeWithColons.replace(':',',')

        propertyTypeModifierWithColons = colorLogic.GetSegmentedPropertyTypeModifier(labelIndex, terminologyName)
        propertyTypeModifier = propertyTypeModifierWithColons.replace(':',',')

        anatomicRegionWithColons = colorLogic.GetAnatomicRegion(labelIndex, terminologyName)
        anatomicRegion = anatomicRegionWithColons.replace(':',',')

        anatomicRegionModifierWithColons = colorLogic.GetAnatomicRegionModifier(labelIndex, terminologyName)
        anatomicRegionModifier = anatomicRegionModifierWithColons.replace(':',',')

        structureFileName = structureName + str(random.randint(0,vtk.VTK_INT_MAX)) + ".info"
        filePath = os.path.join(slicer.app.temporaryPath, structureFileName)

        # EncodeSEG is expecting a file of format:
        # labelNum;SegmentedPropertyCategory:codeValue,codeScheme,codeMeaning;SegmentedPropertyType:v,m,s etc
        attributes = "%d" % labelIndex
        attributes += ";SegmentedPropertyCategory:"+propertyCategory
        if propertyType != "":
          attributes += ";SegmentedPropertyType:" + propertyType
        if propertyTypeModifier != "":
          attributes += ";SegmentedPropertyTypeModifier:" + propertyTypeModifier
        if anatomicRegion != "":
          attributes += ";AnatomicRegion:" + anatomicRegion
        if anatomicRegionModifier != "":
          attributes += ";AnatomicRegionModifier:" + anatomicRegionModifier
        attributes += ";SegmentAlgorithmType:AUTOMATIC"
        attributes += ";SegmentAlgorithmName:SlicerSelfTest"
        attributes += ";RecommendedDisplayRGBValue:%g,%g,%g" % tuple(rgbColor[:-1])
        fp = open(filePath, "w")
        fp.write(attributes)
        fp.close()
        logging.debug ("filePath: %s", filePath)
        logging.debug ("attributes: %s", attributes)
        inputLabelAttributesFileNames += filePath + ","
      inputLabelAttributesFileNames = inputLabelAttributesFileNames[:-1] # strip last comma'''

      try:
        user = os.environ['USER']
      except KeyError:
        user = "Unspecified"
      segFileName = "editor_export.SEG" + str(random.randint(0,vtk.VTK_INT_MAX)) + ".dcm"
      segFilePath = os.path.join(slicer.app.temporaryPath, segFileName)
      # TODO: define a way to set parameters like description
      # TODO: determine a good series number automatically by looking in the database
      parameters = {
        "inputDICOMImageFileNames": inputDICOMImageFileNames,
        "inputSegmentationsFileNames": inputSegmentationsFileNames,
        "inputLabelAttributesFileNames": inputLabelAttributesFileNames,
        "readerId": user,
        "sessionId": "1",
        "timePointId": "1",
        "seriesDescription": "SlicerEditorSEGExport",
        "seriesNumber": "100",
        "instanceNumber": "1",
        "bodyPart": "HEAD",
        "algorithmDescriptionFileName": "Editor",
        "outputSEGFileName": segFilePath,
        "skipEmptySlices": False,
        "compress": False,
        }

      encodeSEG = slicer.modules.encodeseg
      cliNode = None

      cliNode = slicer.cli.run(encodeSEG, cliNode, parameters, delete_temporary_files=False)
      waitCount = 0
      while cliNode.IsBusy() and waitCount < 20:
        slicer.util.delayDisplay( "Running SEG Encoding... %d" % waitCount, 1000 )
        waitCount += 1

      if cliNode.GetStatusString() != 'Completed':
        raise Exception("encodeSEG CLI did not complete cleanly")

      logging.info("Added segmentation to DICOM database (%s)", segFilePath)
      slicer.dicomDatabase.insert(segFilePath)


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
