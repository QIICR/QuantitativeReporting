import os, json
import slicer
import dicom
import logging
from DICOMPluginBase import DICOMPluginBase
from DICOMLib import DICOMLoadable


class DICOMTID1500PluginClass(DICOMPluginBase):

  UID_EnhancedSRStorage = "1.2.840.10008.5.1.4.1.1.88.22"
  UID_ComprehensiveSRStorage = "1.2.840.10008.5.1.4.1.1.88.33"
  UID_SegmentationStorage = "1.2.840.10008.5.1.4.1.1.66.4"
  UID_RealWorldValueMappingStorage = "1.2.840.10008.5.1.4.1.1.67"

  def __init__(self):
    super(DICOMTID1500PluginClass, self).__init__()
    self.loadType = "DICOM Structured Report TID1500"

  def examine(self, fileLists):
    loadables = []
    for files in fileLists:
      loadables += self.examineFiles(files)
    return loadables

  def getDICOMValue(self, dataset, tagName, default=""):
    try:
      value = getattr(dataset, tagName)
    except AttributeError:
      value = default
    return value

  def examineFiles(self, files):
    loadables = []

    for cFile in files:
      dataset = dicom.read_file(cFile)

      uid = self.getDICOMValue(dataset, "SOPInstanceUID")
      if uid == "":
        return []

      seriesDescription = self.getDICOMValue(dataset, "SeriesDescription", "Unknown")

      try:
        isDicomTID1500 = self.getDICOMValue(dataset, "Modality") == 'SR' and \
                         (self.getDICOMValue(dataset, "SOPClassUID") == self.UID_EnhancedSRStorage or \
                         self.getDICOMValue(dataset, "SOPClassUID") == self.UID_ComprehensiveSRStorage) and \
                         self.getDICOMValue(dataset, "ContentTemplateSequence")[0].TemplateIdentifier == '1500'
      except (AttributeError, IndexError):
        isDicomTID1500 = False

      if isDicomTID1500:
        loadable = self.createLoadableAndAddReferences(dataset)
        loadable.files = [cFile]
        loadable.name = seriesDescription + ' - as a DICOM SR TID1500 object'
        loadable.tooltip = loadable.name
        loadable.selected = True
        loadable.confidence = 0.95
        loadable.uid = uid
        refName = self.referencedSeriesName(loadable)
        if refName != "":
          loadable.name = refName + " " + seriesDescription + " - SR TID1500"

        loadables.append(loadable)

        logging.debug('DICOM SR TID1500 modality found')
    return loadables

  def referencedSeriesName(self, loadable):
    """Returns the default series name for the given loadable"""
    referencedName = "Unnamed Reference"
    if hasattr(loadable, "referencedSOPInstanceUID"):
      referencedName = self.defaultSeriesNodeName(loadable.referencedSOPInstanceUID)
    return referencedName

  def createLoadableAndAddReferences(self, dataset):
    loadable = DICOMLoadable()
    loadable.selected = True
    loadable.confidence = 0.95

    if hasattr(dataset, "CurrentRequestedProcedureEvidenceSequence"):
      loadable.referencedSeriesInstanceUIDs = []
      loadable.referencedSOPInstanceUIDs = []

      # store lists of UIDs separately to avoid re-parsing later
      loadable.ReferencedSegmentationInstanceUIDs = []
      loadable.ReferencedRWVMSeriesInstanceUIDs = []
      loadable.ReferencedOtherInstanceUIDs = []

      for refSeriesSequence in dataset.CurrentRequestedProcedureEvidenceSequence:
        for referencedSeriesSequence in refSeriesSequence.ReferencedSeriesSequence:
          for refSOPSequence in referencedSeriesSequence.ReferencedSOPSequence:
            if refSOPSequence.ReferencedSOPClassUID == self.UID_SegmentationStorage: # TODO: differentiate between SR, SEG and other volumes
              logging.debug("Found referenced segmentation")
              loadable.ReferencedSegmentationInstanceUIDs.append(referencedSeriesSequence.SeriesInstanceUID)
            elif refSOPSequence.ReferencedSOPClassUID == self.UID_RealWorldValueMappingStorage: # handle SUV mapping
              logging.debug("Found referenced RWVM")
              loadable.ReferencedRWVMSeriesInstanceUIDs.append(referencedSeriesSequence.SeriesInstanceUID)
            else:
              logging.debug( "Found other reference")
              for sopInstanceUID in slicer.dicomDatabase.fileForInstance(refSOPSequence.ReferencedSOPInstanceUID):
                loadable.ReferencedOtherInstanceUIDs.append(sopInstanceUID)

    if len(loadable.ReferencedSegmentationInstanceUIDs)>1:
      logging.warning("SR references more than one SEG. This has not been tested!")
    for segUID in loadable.ReferencedSegmentationInstanceUIDs:
      loadable.referencedSeriesInstanceUIDs.append(segUID)

    if len(loadable.ReferencedRWVMSeriesInstanceUIDs)>1:
      logging.warning("SR references more than one RWVM. This has not been tested!")
    # not adding RWVM instances to referencedSeriesInstanceUIDs

    return loadable

  def load(self, loadable):
    logging.debug('DICOM SR TID1500 load()')

    segPlugin = slicer.modules.dicomPlugins["DICOMSegmentationPlugin"]()
    scalarVolumePlugin = slicer.modules.dicomPlugins["DICOMScalarVolumePlugin"]()
    rwvmPlugin = slicer.modules.dicomPlugins["DICOMRWVMPlugin"]()

    for segSeriesInstanceUID in loadable.referencedSeriesInstanceUIDs:
      segLoadables = segPlugin.examine([slicer.dicomDatabase.filesForSeries(segSeriesInstanceUID)])
      for segLoadable in segLoadables:
        segPlugin.load(segLoadable)
        if hasattr(segLoadable, "referencedSeriesUID") and len(loadable.ReferencedRWVMSeriesInstanceUIDs)>0:
          # determine if RWVM needs to be applied to the series referenced from SEG
          loadRWVM = False
          rwvmUID = loadable.ReferencedRWVMSeriesInstanceUIDs[0]
          logging.debug("Looking up series %s from database" % rwvmUID)
          rwvmFiles = slicer.dicomDatabase.filesForSeries(rwvmUID)
          if len(rwvmFiles)>0:
            # consider only the first item on the list - there should be only
            # one anyway, for the cases we are handling at the moment
            rwvmFile = rwvmFiles[0]
            logging.debug("Reading RWVM from "+rwvmFile)
            rwvmDataset = dicom.read_file(rwvmFile)
            if hasattr(rwvmDataset,"ReferencedSeriesSequence"):
              if hasattr(rwvmDataset.ReferencedSeriesSequence[0],"SeriesInstanceUID"):
                if rwvmDataset.ReferencedSeriesSequence[0].SeriesInstanceUID == segLoadable.referencedSeriesUID:
                  logging.debug("SEG references the same image series that is referenced by the RWVM series referenced from SR. Will load via RWVM.")
                  loadRWVM = True
          else:
            logging.warning("RWVM is referenced from SR, but is not found in the DICOM database!")

          if loadRWVM:
            logging.debug("Examining "+rwvmFile)
            rwvmLoadables = rwvmPlugin.examine([[rwvmFile]])
            rwvmPlugin.load(rwvmLoadables[0])
          else:
            scalarLoadables = scalarVolumePlugin.examine([slicer.dicomDatabase.filesForSeries(segLoadable.referencedSeriesUID)])
            scalarLoadables.sort(key=lambda x: (len(x.files), x.confidence), reverse=True)
            if len(scalarLoadables):
              scalarVolumePlugin.load(scalarLoadables[0])

    # if there is a RWVM object referenced from SEG, assume it contains the
    # scaling that needs to be applied to the referenced series. Assign
    # referencedSeriesUID from the image series, but load using the RWVM plugin


    try:
      uid = loadable.uid
      logging.debug('in load(): uid = ', uid)
    except AttributeError:
      return False

    self.tempDir = os.path.join(slicer.app.temporaryPath, "QIICR", "SR", self.currentDateTime, loadable.uid)
    try:
      os.makedirs(self.tempDir)
    except OSError:
      pass

    outputFile = os.path.join(self.tempDir, loadable.uid+".json")

    srFileName = slicer.dicomDatabase.fileForInstance(uid)
    if srFileName is None:
      logging.debug('Failed to get the filename from the DICOM database for ', uid)
      return False

    param = {
      "inputDICOM": srFileName,
      "outputMetadata": outputFile
      }

    try:
      tid1500reader = slicer.modules.tid1500reader
    except AttributeError:
      logging.debug('Unable to find CLI module tid1500reader, unable to load SR TID1500 object')
      self.cleanup()
      return False

    cliNode = None
    cliNode = slicer.cli.run(tid1500reader, cliNode, param, wait_for_completion=True)
    if cliNode.GetStatusString() != 'Completed':
      logging.debug('tid1500reader did not complete successfully, unable to load DICOM SR TID1500')
      self.cleanup()
      return False

    table = self.metadata2vtkTableNode(outputFile)
    if table:
      segmentationNodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSegmentationNode")
      segmentationNodeID = segmentationNodes.GetItemAsObject(segmentationNodes.GetNumberOfItems()-1).GetID()
      table.SetAttribute("ReferencedSegmentationNodeID", segmentationNodeID)
    self.cleanup()
    return table is not None

  def metadata2vtkTableNode(self, metafile):
    with open(metafile) as datafile:
      table = slicer.vtkMRMLTableNode()
      slicer.mrmlScene.AddNode(table)
      table.SetAttribute("QuantitativeReporting", "Yes")
      table.SetAttribute("readonly", "Yes")
      table.SetUseColumnNameAsColumnHeader(True)

      data = json.load(datafile)

      tableWasModified = table.StartModify()

      measurement = data["Measurements"][0]
      col = table.AddColumn()
      col.SetName("Segment")

      for measurementItem in measurement["measurementItems"]:
        col = table.AddColumn()

        if "derivationModifier" in measurementItem.keys():
          col.SetName(SegmentStatisticsDICOMMeaningMapping.getKeyForValue(measurementItem["derivationModifier"]["CodeMeaning"]))
        else:
          col.SetName(SegmentStatisticsDICOMMeaningMapping.getKeyForValue(measurementItem["quantity"]["CodeMeaning"] +" "+measurementItem["units"]["CodeValue"]))

      for measurement in data["Measurements"]:
        name = measurement["TrackingIdentifier"]
        value = measurement["ReferencedSegment"]
        rowIndex = table.AddEmptyRow()
        table.SetCellText(rowIndex, 0, name)
        for columnIndex, measurementItem in enumerate(measurement["measurementItems"]):
          table.SetCellText(rowIndex, columnIndex+1, measurementItem["value"])

      table.EndModify(tableWasModified)
      slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveTableID(table.GetID())
      slicer.app.applicationLogic().PropagateTableSelection()
    return table


class SegmentStatisticsDICOMMeaningMapping(object):

  mapping = {"GS min": "Minimum",
             "GS max": "Maximum",
             "GS mean": "Mean",
             "GS stdev": "Standard Deviation",
             "GS volume cc": ("cm3", "Volume cm3"),
             "GS volume mm3": ("mm3", "Volume mm3")}

  @staticmethod
  def getValueForKey(name, longVersion=False):
    try:
      value = SegmentStatisticsDICOMMeaningMapping.mapping[name]
      if type(value) is tuple:
        return value[1 if longVersion else 0]
      return value
    except KeyError:
      return name

  @staticmethod
  def getKeyForValue(name):
    for index, value in enumerate(SegmentStatisticsDICOMMeaningMapping.mapping.values()):
      if name in value:
        return SegmentStatisticsDICOMMeaningMapping.mapping.keys()[index]
    return name


class DICOMTID1500Plugin:
  """
  This class is the 'hook' for slicer to detect and recognize the plugin
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "DICOM SR TID1500 Object Import Plugin"
    parent.categories = ["Developer Tools.DICOM Plugins"]
    parent.contributors = ["Christian Herz (BWH), Andrey Fedorov (BWH)"]
    parent.helpText = """
    Plugin to the DICOM Module to parse and load DICOM SR TID1500 instances.
    No module interface here, only in the DICOM module
    """
    parent.dependencies = ['DICOM', 'Colors', 'DICOMRWVMPlugin']
    parent.acknowledgementText = """
    This DICOM Plugin was developed by
    Christian Herz and Andrey Fedorov, BWH.
    and was partially funded by NIH grant U24 CA180918 (QIICR).
    """

    # Add this extension to the DICOM module's list for discovery when the module
    # is created.  Since this module may be discovered before DICOM itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.dicomPlugins
    except AttributeError:
      slicer.modules.dicomPlugins = {}
    slicer.modules.dicomPlugins['DICOMTID1500Plugin'] = DICOMTID1500PluginClass
