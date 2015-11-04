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

    print("DICOMSegmentationPlugin::examine files: ")
    print files

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
        loadable.uid = uid
        loadables.append(loadable)
        print('DICOM SEG modality found')

    return loadables

  def load(self,loadable):
    """ Call Reporting logic to load the DICOM SEG object
    """
    print('DICOM SEG load()')
    labelNodes = vtk.vtkCollection()

    uid = None

    try:
      reportingLogic = slicer.modules.reporting.logic()
      uid = loadable.uid
      print 'in load(): uid = ', uid
    except AttributeError:
      return False

    res = False
    # make the output directory
    outputDir = os.path.join(slicer.app.temporaryPath,"QIICR","SEG",loadable.uid)
    try:
      os.makedirs(outputDir)
    except:
      pass

    # default color node will be used
    res = reportingLogic.DicomSegRead(labelNodes, uid)

    defaultColorNode = reportingLogic.GetDefaultColorNode()
    import glob
    for segmentId in range(len(glob.glob(os.path.join(outputDir,'*.nrrd')))):
      # load each of the segments' segmentations
      labelFileName = os.path.join(outputDir,str(segmentId+1)+".nrrd")
      (success,labelNode) = slicer.util.loadLabelVolume(labelFileName, returnNode=True)

      # TODO: initialize color and terminology from .info file
      # Format of the .info file:
      #    RGBColor:128,174,128
      #    AnatomicRegion:T-C5300,SRT,pharyngeal tonsil (adenoid)
      #    SegmentedPropertyCategory:M-01000,SRT,Morphologically Altered Structure
      #     SegmentedPropertyType:M-80003,SRT,Neoplasm, Primary
      infoFileName = os.path.join(outputDir,str(segmentId+1)+".info")


      # TODO: initialize referenced UID (and segment number?) attribute(s)

      # create Subject hierarchy nodes for the loaded series
      self.addSeriesInSubjectHierarchy(loadable, labelNode)

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
