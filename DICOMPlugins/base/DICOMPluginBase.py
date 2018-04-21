import slicer
import dicom
import logging
from datetime import datetime
from DICOMLib import DICOMPlugin
import shutil


class DICOMPluginBase(DICOMPlugin):
  """
  It would probably make sense to propose this common functionality to the Slicer core itself.
  """

  @property
  def currentDateTime(self):
    try:
      return self._currentDateTime
    except AttributeError:
      self._currentDateTime = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    return self._currentDateTime

  def __init__(self):
    super(DICOMPluginBase, self).__init__()
    self.tags['seriesInstanceUID'] = "0020,000E"
    self.tags['modality'] = "0008,0060"
    self.tags['instanceUID'] = "0008,0018"
    self.tags['classUID'] = "0008,0016"
    self.tempDir = None

  def cleanup(self):
    if not self.tempDir:
      return
    try:
      logging.debug("Cleaning up temporarily created directory {}".format(self.tempDir))
      shutil.rmtree(self.tempDir)
      self.tempDir = None
    except OSError:
      pass

  def examineForImport(self, fileLists):
    """ Returns a sorted list of DICOMLoadable instances
    corresponding to ways of interpreting the
    fileLists parameter (list of file lists).
    """
    loadables = []
    for files in fileLists:
      cachedLoadables = self.getCachedLoadables(files)
      if cachedLoadables is not None:
        logging.debug("%s : Using cached files" % self.__class__.__name__)
        loadables += cachedLoadables
      else:
        logging.debug("%s : Caching files" % self.__class__.__name__)
        loadablesForFiles = self.examineFiles(files)
        loadables += loadablesForFiles
        self.cacheLoadables(files, loadablesForFiles)

    return loadables

  def addReferences(self, loadable):
    """Puts a list of the referenced UID into the loadable for use
    in the node if this is loaded."""
    dcm = dicom.read_file(loadable.files[0])
    loadable.referencedInstanceUIDs = []
    self._addReferencedSeries(loadable, dcm)
    self._addReferencedImages(loadable, dcm)
    loadable.referencedInstanceUIDs = list(set(loadable.referencedInstanceUIDs))

  def _addReferencedSeries(self, loadable, dcm):
    if hasattr(dcm, "ReferencedSeriesSequence"):
      if hasattr(dcm.ReferencedSeriesSequence[0], "SeriesInstanceUID"):
        for f in slicer.dicomDatabase.filesForSeries(dcm.ReferencedSeriesSequence[0].SeriesInstanceUID):
          refDCM = dicom.read_file(f)
          loadable.referencedInstanceUIDs.append(refDCM.SOPInstanceUID)
        loadable.referencedSeriesUID = dcm.ReferencedSeriesSequence[0].SeriesInstanceUID

  def _addReferencedImages(self, loadable, dcm):
    if hasattr(dcm, "ReferencedImageSequence"):
      for item in dcm.ReferencedImageSequence:
        if hasattr(item, "ReferencedSOPInstanceUID"):
          loadable.referencedInstanceUIDs.append(item.ReferencedSOPInstanceUID)
          # TODO: what to do with the SeriesInstanceUID?
          # refDCM = dicom.read_file(slicer.dicomDatabase.fileForInstance(item.ReferencedSOPInstanceUID))