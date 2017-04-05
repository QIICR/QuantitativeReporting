import json
import os

import logging
import slicer
from DICOMLib import DICOMLoadable
from base.DICOMPluginBase import DICOMPluginBase

#
# This is the plugin to handle translation of DICOM SEG objects
#

class DICOMParametricMapPluginClass(DICOMPluginBase):

  def __init__(self):
    super(DICOMParametricMapPluginClass,self).__init__()
    self.loadType = "DICOMParametricMap"

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

        logging.debug('DICOM Parametric Map found')

    return loadables

  def referencedSeriesName(self,loadable):
    """Returns the default series name for the given loadable"""
    referencedName = "Unnamed Reference"
    if hasattr(loadable, "referencedSeriesUID"):
      referencedName = self.defaultSeriesNodeName(loadable.referencedSeriesUID)
    return referencedName

  def load(self,loadable):
    """ Load the DICOM PM object
    """
    logging.debug('DICOM PM load()')
    try:
      uid = loadable.uid
      logging.debug('in load(): uid = ', uid)
    except AttributeError:
      return False

    self.tempDir = os.path.join(slicer.app.temporaryPath, "QIICR", "PM", self.currentDateTime, loadable.uid)
    try:
      os.makedirs(self.tempDir)
    except OSError:
      pass

    pmFileName = slicer.dicomDatabase.fileForInstance(uid)
    if pmFileName is None:
      logging.debug('Failed to get the filename from the DICOM database for ', uid)
      self.cleanup()
      return False

    parameters = {
      "inputFileName": pmFileName,
      "outputDirName": self.tempDir,
      }
    try:
      pm2nrrd = slicer.modules.paramap2itkimage
    except AttributeError:
      logging.debug('Unable to find CLI module paramap2itkimage, unable to load DICOM ParametricMap object')
      self.cleanup()
      return False

    cliNode = None
    cliNode = slicer.cli.run(pm2nrrd, cliNode, parameters, wait_for_completion=True)
    if cliNode.GetStatusString() != 'Completed':
      logging.debug('PM converter did not complete successfully, unable to load DICOM ParametricMap')
      self.cleanup()
      return False

    (_,pmNode) = slicer.util.loadVolume(os.path.join(self.tempDir,"pmap.nrrd"), returnNode=True)

    # load the metadata JSON to retrieve volume semantics (quantity stored and units)
    with open(os.path.join(self.tempDir,"meta.json")) as metafile:
      meta = json.load(metafile)
      pmNode.SetAttribute("DICOM.QuantityValueCode",str(meta["QuantityValueCode"]))
      pmNode.SetAttribute("DICOM.MeasurementUnitsCode",str(meta["MeasurementUnitsCode"]))
      pmNode.SetAttribute("DICOM.instanceUIDs", uid)

    # create Subject hierarchy nodes for the loaded series
    self.addSeriesInSubjectHierarchy(loadable, pmNode)

    self.cleanup()
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
