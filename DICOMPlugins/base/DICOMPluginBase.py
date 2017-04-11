import slicer
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

  def addReferences(self, loadable):
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
