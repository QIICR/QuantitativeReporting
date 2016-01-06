import os
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

    for file in files:

      uid = slicer.dicomDatabase.fileValue(file, self.tags['instanceUID'])
      if uid == '':
        return []

      desc = slicer.dicomDatabase.fileValue(file, self.tags['seriesDescription'])
      if desc == "":
        name = "Unknown"

      number = slicer.dicomDatabase.fileValue(file, self.tags['seriesNumber'])
      if number == '':
        number = "Unknown"

      isDicomSeg = (slicer.dicomDatabase.fileValue(file, self.tags['modality']) == 'SEG')

      if isDicomSeg:
        loadable = DICOMLoadable()
        loadable.files = [file]
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
    """Puts a list of the referened UID into the loadable for use
    in the node if this is loaded."""
    import dicom
    dcm = dicom.read_file(loadable.files[0])
    if hasattr(dcm, "ReferencedSeriesSequence"):
      if hasattr(dcm.ReferencedSeriesSequence[0], "ReferencedInstanceSequence"):
        # set the referenced UID list for the loadable
        loadable.referencedInstanceUIDs = []
        for ref in dcm.ReferencedSeriesSequence[0].ReferencedInstanceSequence:
          loadable.referencedInstanceUIDs.append(ref.ReferencedSOPInstanceUID)
        # cache the referenced seriesUID for use in looking up the series name
        # - use the last referenced instance in the list - they should all be the same series
        refUID = str(ref.ReferencedSOPInstanceUID)
        refFilePath = slicer.dicomDatabase.fileForInstance(refUID)
        if refFilePath != '':
          refDCM = dicom.read_file(refFilePath)
          loadable.referencedSeriesUID = str(refDCM.SeriesInstanceUID)

  def load(self,loadable):
    """ Load the DICOM SEG object
    """
    print('DICOM SEG load()')
    labelNodes = vtk.vtkCollection()

    uid = None

    try:
      uid = loadable.uid
      print ('in load(): uid = ', uid)
    except AttributeError:
      return False

    res = False
    # make the output directory
    outputDir = os.path.join(slicer.app.temporaryPath,"QIICR","SEG",loadable.uid)
    try:
      os.makedirs(outputDir)
    except:
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
    seg2nrrd = None
    try:
      seg2nrrd = slicer.modules.seg2nrrd
    except AttributeError:
      print 'Unable to find CLI module SEG2NRRD, unable to load DICOM Segmentation object'
      return False
    cliNode = None
    cliNode = slicer.cli.run(seg2nrrd, cliNode, parameters, wait_for_completion=True)
    if cliNode.GetStatusString() != 'Completed':
      print 'SEG2NRRD did not complete successfully, unable to load DICOM Segmentation'
      return False

    # create a new color node to be set up with the colors in these segments
    colorLogic = slicer.modules.colors.logic()
    segmentationColorNode = slicer.vtkMRMLColorTableNode()
    segmentationColorNode.SetName(loadable.name)
    segmentationColorNode.SetTypeToUser();
    segmentationColorNode.SetHideFromEditors(0)
    segmentationColorNode.SetAttribute("Category", "File")
    segmentationColorNode.NamesInitialisedOff()
    slicer.mrmlScene.AddNode(segmentationColorNode)

    # also create a new terminology and associate it with this color node
    colorLogic.CreateNewTerminology(segmentationColorNode.GetName())

    import glob
    numberOfSegments = len(glob.glob(os.path.join(outputDir,'*.nrrd')))

    # resize the color table to include the segments plus 0 for the background
    print ('number of segments = ',numberOfSegments)
    segmentationColorNode.SetNumberOfColors(numberOfSegments + 1)
    segmentationColorNode.SetColor(0, 'background', 0.0, 0.0, 0.0, 0.0)

    seriesName = self.referencedSeriesName(loadable)
    segmentNodes = []
    for segmentId in range(numberOfSegments):
      # load each of the segments' segmentations
      # Initialize color and terminology from .info file
      # See SEG2NRRD.cxx and EncodeSEG.cxx for how it's written.
      # Format of the .info file (no leading spaces, labelNum, RGBColor, SegmentedPropertyCategory and
      # SegmentedPropertyCategory are required):
      # labelNum;RGB:R,G,B;SegmentedPropertyCategory:code,scheme,meaning;SegmentedPropertyType:code,scheme,meaning;SegmentedPropertyTypeModifier:code,scheme,meaning;AnatomicRegion:code,scheme,meaning;AnatomicRegionModifier:code,scheme,meaning
      # R, G, B are 0-255 in file, but mapped to 0-1 for use in color node
      # set defaults in case of missing fields, modifiers are optional
      rgb = (0., 0., 0.)
      colorIndex = segmentId + 1
      categoryCode = 'T-D0050'
      categoryCodingScheme = 'SRT'
      categoryCodeMeaning = 'Tissue'
      typeCode = 'T-D0050'
      typeCodeMeaning = 'Tissue'
      typeCodingScheme = 'SRT'
      typeModCode = ''
      typeModCodingScheme = ''
      typeModCodeMeaning = ''
      regionCode = 'T-D0010'
      regionCodingScheme = 'SRT'
      regionCodeMeaning = 'Entire Body'
      regionModCode = ''
      regionModCodingScheme = ''
      regionModCodeMeaning = ''
      infoFileName = os.path.join(outputDir,str(segmentId+1)+".info")
      print ('Parsing info file', infoFileName)
      with open(infoFileName, 'r') as infoFile:
        for line in infoFile:
          line = line.rstrip()
          if len(line) == 0:
            # empty line
            continue
          terms = line.split(';')
          for term in terms:
            # label number is the first thing, no key
            if len(term.split(':')) == 1:
              colorIndex = int(term)
            else:
              key = term.split(':')[0]
              if key == "RGB":
                rgb255 = term.split(':')[1].split(',')
                rgb = map(lambda c: float(c) / 255., rgb255)
              elif key == "AnatomicRegion":
                # Get the Region information
                region = term.split(':')[1]
                # use partition to deal with any commas in the meaning
                regionCode, sep, regionCodingSchemeAndCodeMeaning = region.partition(',')
                regionCodingScheme, sep, regionCodeMeaning = regionCodingSchemeAndCodeMeaning.partition(',')
              elif key == "AnatomicRegionModifier":
                regionMod = term.split(':')[1]
                regionModCode, sep, regionModCodingSchemeAndCodeMeaning = regionMod.partition(',')
                regionModCodingScheme, sep, regionModCodeMeaning = regionModCodingSchemeAndCodeMeaning.partition(',')
              elif key == "SegmentedPropertyCategory":
                # Get the Category information
                category = term.split(':')[1]
                categoryCode, sep, categoryCodingSchemeAndCodeMeaning = category.partition(',')
                categoryCodingScheme, sep, categoryCodeMeaning = categoryCodingSchemeAndCodeMeaning.partition(',')
              elif key == "SegmentedPropertyType":
                # Get the Type information
                types = term.split(':')[1]
                typeCode, sep, typeCodingSchemeAndCodeMeaning = types.partition(',')
                typeCodingScheme, sep, typeCodeMeaning = typeCodingSchemeAndCodeMeaning.partition(',')
              elif key == "SegmentedPropertyTypeModifier":
                typeMod = term.split(':')[1]
                typeModCode, sep, typeModCodingSchemeAndCodeMeaning = typeMod.partition(',')
                typeModCodingScheme, sep, typeModCodeMeaning = typeModCodingSchemeAndCodeMeaning.partition(',')

        # set the color name from the terminology
        colorName = typeCodeMeaning
        segmentationColorNode.SetColor(colorIndex, colorName, *rgb)

        colorLogic.AddTermToTerminology(segmentationColorNode.GetName(), colorIndex,
                                        categoryCode, categoryCodingScheme, categoryCodeMeaning,
                                        typeCode, typeCodingScheme, typeCodeMeaning,
                                        typeModCode, typeModCodingScheme, typeModCodeMeaning,
                                        regionCode, regionCodingScheme, regionCodeMeaning,
                                        regionModCode, regionModCodingScheme, regionModCodeMeaning)
        # end of processing a line of terminology
      infoFile.close()

      #TODO: Create logic class that both CLI and this plugin uses so that we don't need to have temporary NRRD files and labelmap nodes
      #if not hasattr(slicer.modules, 'segmentations'):

      # load the segmentation volume file and name it for the reference series and segment color
      labelFileName = os.path.join(outputDir,str(segmentId+1)+".nrrd")
      segmentName = seriesName + "-" + colorName + "-label"
      (success,labelNode) = slicer.util.loadLabelVolume(labelFileName,
                                                        properties = {'name' : segmentName},
                                                        returnNode=True)
      segmentNodes.append(labelNode)

      # point the label node to the color node we're creating
      labelDisplayNode = labelNode.GetDisplayNode()
      if labelDisplayNode == None:
        print ('Warning: no label map display node for segment ',segmentId,', creating!')
        labelNode.CreateDefaultDisplayNodes()
        labelDisplayNode = labelNode.GetDisplayNode()
      labelDisplayNode.SetAndObserveColorNodeID(segmentationColorNode.GetID())

      # TODO: initialize referenced UID (and segment number?) attribute(s)

      # create Subject hierarchy nodes for the loaded series
      self.addSeriesInSubjectHierarchy(loadable, labelNode)

    # create a combined (merge) label volume node (only if a segment was created)
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

      import vtkSlicerSegmentationsModuleLogic
      import vtkSlicerSegmentationsModuleMRML
      import vtkSegmentationCore

      segmentationNode = vtkSlicerSegmentationsModuleMRML.vtkMRMLSegmentationNode()
      segmentationNode.SetName(seriesName)
      slicer.mrmlScene.AddNode(segmentationNode)

      segmentationDisplayNode = vtkSlicerSegmentationsModuleMRML.vtkMRMLSegmentationDisplayNode()
      segmentationNode.SetAndObserveDisplayNodeID(segmentationDisplayNode.GetID())
      slicer.mrmlScene.AddNode(segmentationDisplayNode)

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
        logic = vtkSlicerSegmentationsModuleLogic.vtkSlicerSegmentationsModuleLogic()
        orientedImage = logic.CreateOrientedImageDataFromVolumeNode(segmentNode)
        segment.AddRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName(), orientedImage)
        segmentation.AddSegment(segment)

        segmentDisplayNode = segmentNode.GetDisplayNode()
        slicer.mrmlScene.RemoveNode(segmentDisplayNode)
        slicer.mrmlScene.RemoveNode(segmentNode)

      segmentation.CreateRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName(), True)
      slicer.mrmlScene.RemoveNode(segmentationColorNode)
      slicer.mrmlScene.RemoveNode(mergeNode)

    return True

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
