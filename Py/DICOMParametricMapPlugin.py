import os
import string
import vtk, qt, ctk, slicer
from DICOMLib import DICOMPlugin
from DICOMLib import DICOMLoadable

#
# This is the plugin to handle translation of DICOM SEG objects
#

class DICOMParametricMapPluginClass(DICOMPlugin):

  def __init__(self,epsilon=0.01):
    super(DICOMParametricMapPluginClass,self).__init__()
    self.loadType = "DICOMParametricMap"

    self.tags['seriesInstanceUID'] = "0020,000E"
    self.tags['seriesDescription'] = "0008,103E"
    self.tags['seriesNumber'] = "0020,0011"
    self.tags['modality'] = "0008,0060"
    self.tags['instanceUID'] = "0008,0018"
    self.tags['classUID'] = "0008,0016"

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

      isDicomPM = (slicer.dicomDatabase.fileValue(cFile, self.tags['classUID']) == '1.2.840.10008.5.1.4.1.1.30')

      if isDicomPM:
        loadable = DICOMLoadable()
        loadable.files = [cFile]
        loadable.name = desc + ' - as a DICOM Parametric Map object'
        loadable.tooltip = loadable.name
        loadable.selected = True
        loadable.confidence = 0.95
        loadable.uid = uid
        self.addReferences(loadable)
        refName = self.referencedSeriesName(loadable)
        if refName != "":
          loadable.name = refName + " " + desc + " - ParametricMap"

        loadables.append(loadable)

        print('DICOM Parametric Map found')

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

  def load(self,loadable):
    """ Load the DICOM PM object
    """
    print('DICOM PM load()')
    try:
      uid = loadable.uid
      print ('in load(): uid = ', uid)
    except AttributeError:
      return False

    # make the output directory
    outputDir = os.path.join(slicer.app.temporaryPath,"QIICR","PM",loadable.uid)
    try:
      os.makedirs(outputDir)
    except OSError:
      pass

    pmFileName = slicer.dicomDatabase.fileForInstance(uid)
    if pmFileName is None:
      print 'Failed to get the filename from the DICOM database for ', uid
      return False

    parameters = {
      "inputFileName": pmFileName,
      "outputDirName": outputDir,
      }
    try:
      pm2nrrd = slicer.modules.paramap2itkimage
    except AttributeError:
      print 'Unable to find CLI module paramap2itkimage, unable to load DICOM ParametricMap object'
      return False

    cliNode = None
    cliNode = slicer.cli.run(pm2nrrd, cliNode, parameters, wait_for_completion=True)
    if cliNode.GetStatusString() != 'Completed':
      print 'PM converter did not complete successfully, unable to load DICOM ParametricMap'
      return False

    (_,pmNode) = slicer.util.loadVolume(os.path.join(outputDir,"pmap.nrrd"), returnNode=True)

    # create Subject hierarchy nodes for the loaded series
    self.addSeriesInSubjectHierarchy(loadable, pmNode)

    # TODO: the outputDir should be cleaned up

    return True


#
# DICOMParametricMapPlugin
#

class DICOMParametricMapPlugin:
  """
  This class is the 'hook' for slicer to detect and recognize the plugin
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "DICOM ParametricMap Object Import Plugin"
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
    slicer.modules.dicomPlugins['DICOMParametricMapPlugin'] = DICOMParametricMapPluginClass
