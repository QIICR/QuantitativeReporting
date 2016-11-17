import os, json
import slicer
import dicom
from DICOMLib import DICOMPlugin
from DICOMLib import DICOMLoadable


class DICOMTID1500PluginClass(DICOMPlugin):

  UID_EnhancedSRStorage = "1.2.840.10008.5.1.4.1.1.88.22"
  UID_SegmentationStorage = "1.2.840.10008.5.1.4.1.1.66.4"

  def __init__(self, epsilon=0.01):
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

    for file in files:
      dataset = dicom.read_file(file)

      uid = self.getDICOMValue(dataset, "SOPInstanceUID", default=None)
      if not uid:
        return []

      seriesDescription = self.getDICOMValue(dataset, "SeriesDescription", "Unknown")

      try:
        isDicomTID1500 = self.getDICOMValue(dataset, "Modality") == 'SR' and \
                         self.getDICOMValue(dataset, "SOPClassUID") == self.UID_EnhancedSRStorage and \
                         self.getDICOMValue(dataset, "ContentTemplateSequence")[0].TemplateIdentifier == '1500'
      except (AttributeError, IndexError):
        isDicomTID1500 = False

      if isDicomTID1500:
        loadable = self.createLoadableAndAddReferences(dataset)
        loadable.files = [file]
        loadable.name = seriesDescription + ' - as a DICOM SR TID1500 object'
        loadable.tooltip = loadable.name
        loadable.selected = True
        loadable.confidence = 0.95
        loadable.uid = uid
        refName = self.referencedSeriesName(loadable)
        if refName != "":
          loadable.name = refName + " " + seriesDescription + " - SR TID1500"

        loadables.append(loadable)

        print('DICOM SR TID1500 modality found')
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
      # dataset.CurrentRequestedProcedureEvidenceSequence[0].ReferencedSeriesSequence[0].ReferencedSOPSequence[0]
      loadable.referencedSeriesInstanceUIDs = []
      loadable.referencedSOPInstanceUIDs = []
      for refSeriesSequence in dataset.CurrentRequestedProcedureEvidenceSequence:
        for referencedSeriesSequence in refSeriesSequence.ReferencedSeriesSequence:
          for refSOPSequence in referencedSeriesSequence.ReferencedSOPSequence:
            if refSOPSequence.ReferencedSOPClassUID == self.UID_SegmentationStorage: # TODO: differentiate between SR, SEG and other volumes
              print "Found referenced segmentation"
              loadable.referencedSeriesInstanceUIDs.append(referencedSeriesSequence.SeriesInstanceUID)
            else:
              # print "Found other reference"
              for sopInstanceUID in slicer.dicomDatabase.fileForInstance(refSOPSequence.ReferencedSOPInstanceUID):
                loadable.referencedSOPInstanceUIDs.append(sopInstanceUID)
                # loadable.referencedSOPInstanceUID = refSOPSequence.ReferencedSOPInstanceUID
    return loadable

  def loadSeries(self, seriesUID):
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
    dicomWidget.detailsPopup.offerLoadables(seriesUID, 'Series')
    dicomWidget.detailsPopup.examineForLoading()
    dicomWidget.detailsPopup.loadCheckedLoadables()

  def load(self, loadable):
    print('DICOM SR TID1500 load()')

    segPlugin = slicer.modules.dicomPlugins["DICOMSegmentationPlugin"]()
    for seriesInstanceUID in loadable.referencedSeriesInstanceUIDs:
      # segLoadables = segPlugin.examine([slicer.dicomDatabase.filesForSeries(seriesInstanceUID)])
      # for segLoadable in segLoadables:
      #   segPlugin.load(segLoadable)
      self.loadSeries(seriesInstanceUID)

    try:
      uid = loadable.uid
      print ('in load(): uid = ', uid)
    except AttributeError:
      return False

    outputDir = os.path.join(slicer.app.temporaryPath, "QIICR", "SR", loadable.uid)
    try:
      os.makedirs(outputDir)
    except:
      pass

    outputFile = os.path.join(outputDir, loadable.uid+".json")

    srFileName = slicer.dicomDatabase.fileForInstance(uid)
    if srFileName is None:
      print 'Failed to get the filename from the DICOM database for ', uid
      return False

    param = {
      "inputSRFileName": srFileName,
      "metaDataFileName": outputFile,
      }

    try:
      tid1500reader = slicer.modules.tid1500reader
    except AttributeError:
      print 'Unable to find CLI module tid1500reader, unable to load SR TID1500 object'
      return False

    cliNode = None
    cliNode = slicer.cli.run(tid1500reader, cliNode, param, wait_for_completion=True)
    if cliNode.GetStatusString() != 'Completed':
      print 'tid1500reader did not complete successfully, unable to load DICOM SR TID1500'
      return False

    return self.metadata2vtkTableNode(outputFile)

  def metadata2vtkTableNode(self, metafile):
    with open(metafile) as datafile:
      table = slicer.vtkMRMLTableNode()
      slicer.mrmlScene.AddNode(table)
      table.SetAttribute("Reporting", "Yes")
      table.SetAttribute("readonly", "Yes")
      table.SetUseColumnNameAsColumnHeader(True)

      data = json.load(datafile)

      tableWasModified = table.StartModify()

      measurement = data["Measurements"][0]
      col = table.AddColumn()
      col.SetName("Segment Name")

      for measurementItem in measurement["measurementItems"]:
        col = table.AddColumn()
        if "derivationModifier" in measurementItem.keys():
          col.SetName(measurementItem["derivationModifier"]["CodeMeaning"])
        else:
          col.SetName(measurementItem["quantity"]["CodeMeaning"]+" "+measurementItem["units"]["CodeValue"])

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

    return table is not None


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
    Plugin to the DICOM Module to parse and load DICOM SR TID1500 modality.
    No module interface here, only in the DICOM module
    """
    parent.dependencies = ['DICOM', 'Colors']  # TODO: Colors needed???
    parent.acknowledgementText = """
    This DICOM Plugin was developed by
    Christian Herz, BWH.
    and was partially funded by NIH grant U01CA151261.
    """

    # Add this extension to the DICOM module's list for discovery when the module
    # is created.  Since this module may be discovered before DICOM itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.dicomPlugins
    except AttributeError:
      slicer.modules.dicomPlugins = {}
    slicer.modules.dicomPlugins['DICOMTID1500Plugin'] = DICOMTID1500PluginClass
