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
    # Get the location and initialize the DICOM DB used by Reporting logic
    reportingLogic = slicer.modules.reporting.logic()
    settings = qt.QSettings()
    dbFileName = settings.value("DatabaseDirectory","")
    if dbFileName == "":
      print("DICOMSegmentationPlugin failed to initialize DICOM db location from settings")
    else:
      dbFileName = dbFileName+"/ctkDICOM.sql"
      if reportingLogic.InitializeDICOMDatabase(dbFileName):
        print("DICOMSegmentationPlugin initialized DICOM db OK")
      else:
        print('Failed to initialize DICOM database at '+dbFileName)

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

      reportingLogic = None
      reportingLogic = slicer.modules.reporting.logic()

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

        loadables.append(loadable)

        print('DICOM SEG modality found')

    return loadables

  def addReferences(self,loadable):
    import dicom
    dcm = dicom.read_file(loadable.files[0])
    if not hasattr(dcm, "ReferencedSeriesSequence"):
      return

    if not hasattr(dcm.ReferencedSeriesSequence[0], "ReferencedInstanceSequence"):
      return

    loadable.referencedInstanceUIDs = []
    for ref in dcm.ReferencedSeriesSequence[0].ReferencedInstanceSequence:
      loadable.referencedInstanceUIDs.append(ref.ReferencedSOPInstanceUID)

    return

  def load(self,loadable):
    """ Call Reporting logic to load the DICOM SEG object
    """
    print('DICOM SEG load()')
    labelNodes = vtk.vtkCollection()

    uid = None

    try:
      reportingLogic = slicer.modules.reporting.logic()
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
    res = reportingLogic.DicomSegRead(labelNodes, uid)

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

    for segmentId in range(numberOfSegments):
      # load each of the segments' segmentations
      labelFileName = os.path.join(outputDir,str(segmentId+1)+".nrrd")
      (success,labelNode) = slicer.util.loadLabelVolume(labelFileName, returnNode=True)

      # Initialize color and terminology from .info file
      # See SEG2NRRD.cxx and EncodeSEG.cxx for how it's written.
      # Format of the .info file (no leading spaces, labelNum, RGBColor, SegmentedPropertyCategory and
      # SegmentedPropertyCategory are required):
      # labelNum;RGB:R,G,B;SegmentedPropertyCategory:code,scheme,meaning;SegmentedPropertyType:code,scheme,meaning;SegmentedPropertyTypeModifier:code,scheme,meaning;AnatomicRegion:code,scheme,meaning;AnatomicRegionModifier:code,scheme,meaning
      # R, G, B are 0-255
      # set defaults in case of missing fields, modifiers are optional
      colorIndex = segmentId + 1
      red = '0'
      green = '0'
      blue = '0'
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

    # finalize the color node
    segmentationColorNode.NamesInitialisedOn()

    # TODO: the outputDir should be cleaned up

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
    parent.dependencies = ['DICOM', 'Colors', 'Reporting']
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
