import json
import logging
import os
import vtk
import datetime
from collections import Counter
import dicom
import numpy
import random

import slicer
from DICOMLib import DICOMLoadable
from base.DICOMPluginBase import DICOMPluginBase
from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin


class DICOMTID1500PluginClass(DICOMPluginBase, ModuleLogicMixin):

  UID_EnhancedSRStorage = "1.2.840.10008.5.1.4.1.1.88.22"
  UID_ComprehensiveSRStorage = "1.2.840.10008.5.1.4.1.1.88.33"
  UID_SegmentationStorage = "1.2.840.10008.5.1.4.1.1.66.4"
  UID_RealWorldValueMappingStorage = "1.2.840.10008.5.1.4.1.1.67"

  def __init__(self):
    DICOMPluginBase.__init__(self)
    self.loadType = "DICOM Structured Report TID1500"

    self.codings = {
      "imagingMeasurementReport": { "scheme": "DCM", "value": "126000" },
      "personObserver": { "scheme": "DCM", "value": "121008" },
      "imagingMeasuremnts": { "scheme": "DCM", "value": "126010" },
      "measurementGroup": { "scheme": "DCM", "value": "125007" },
      "trackingIdentifier": { "scheme": "DCM", "value": "112039" },
      "trackingUniqueIdentifier": { "scheme": "DCM", "value": "112040" },
      "findingSite": { "scheme": "SRT", "value": "G-C0E3" },
      "length": { "scheme": "SRT", "value": "G-D7FE" },
    }


  def examineFiles(self, files):
    loadables = []

    for cFile in files:
      dataset = dicom.read_file(cFile)

      uid = self.getDICOMValue(dataset, "SOPInstanceUID")
      if uid == "":
        return []

      seriesDescription = self.getDICOMValue(dataset, "SeriesDescription", "Unknown")

      isDicomTID1500 = self.isDICOMTID1500(dataset)

      if isDicomTID1500:
        loadable = self.createLoadableAndAddReferences([dataset])
        loadable.files = [cFile]
        loadable.name = seriesDescription + ' - as a DICOM SR TID1500 object'
        loadable.tooltip = loadable.name
        loadable.selected = True
        loadable.confidence = 0.95
        loadable.uids = [uid]
        refName = self.referencedSeriesName(loadable)
        if refName != "":
          loadable.name = refName + " " + seriesDescription + " - SR TID1500"

        loadables.append(loadable)

        logging.debug('DICOM SR TID1500 modality found')
    return loadables

  def isDICOMTID1500(self, dataset):
    try:
      isDicomTID1500 = self.getDICOMValue(dataset, "Modality") == 'SR' and \
                       (self.getDICOMValue(dataset, "SOPClassUID") == self.UID_EnhancedSRStorage or
                        self.getDICOMValue(dataset, "SOPClassUID") == self.UID_ComprehensiveSRStorage) and \
                       self.getDICOMValue(dataset, "ContentTemplateSequence")[0].TemplateIdentifier == '1500'
    except (AttributeError, IndexError):
      isDicomTID1500 = False
    return isDicomTID1500

  def referencedSeriesName(self, loadable):
    """Returns the default series name for the given loadable"""
    referencedName = "Unnamed Reference"
    if hasattr(loadable, "referencedSOPInstanceUID"):
      referencedName = self.defaultSeriesNodeName(loadable.referencedSOPInstanceUID)
    return referencedName

  def createLoadableAndAddReferences(self, datasets):
    loadable = DICOMLoadable()
    loadable.selected = True
    loadable.confidence = 0.95

    loadable.referencedSegInstanceUIDs = []
    # store lists of UIDs separately to avoid re-parsing later
    loadable.ReferencedSegmentationInstanceUIDs = {}
    loadable.ReferencedRWVMSeriesInstanceUIDs = []
    loadable.ReferencedOtherInstanceUIDs = []
    loadable.referencedInstanceUIDs = []

    segPlugin = slicer.modules.dicomPlugins["DICOMSegmentationPlugin"]()

    for dataset in datasets:
      uid = self.getDICOMValue(dataset, "SOPInstanceUID")
      loadable.ReferencedSegmentationInstanceUIDs[uid] = []
      if hasattr(dataset, "CurrentRequestedProcedureEvidenceSequence"):
        for refSeriesSequence in dataset.CurrentRequestedProcedureEvidenceSequence:
          for referencedSeriesSequence in refSeriesSequence.ReferencedSeriesSequence:
            for refSOPSequence in referencedSeriesSequence.ReferencedSOPSequence:
              if refSOPSequence.ReferencedSOPClassUID == self.UID_SegmentationStorage:
                logging.debug("Found referenced segmentation")
                loadable.ReferencedSegmentationInstanceUIDs[uid].append(referencedSeriesSequence.SeriesInstanceUID)

              elif refSOPSequence.ReferencedSOPClassUID == self.UID_RealWorldValueMappingStorage: # handle SUV mapping
                logging.debug("Found referenced RWVM")
                loadable.ReferencedRWVMSeriesInstanceUIDs.append(referencedSeriesSequence.SeriesInstanceUID)
              else:
                # TODO: those are not used at all
                logging.debug( "Found other reference")
                loadable.ReferencedOtherInstanceUIDs.append(refSOPSequence.ReferencedSOPInstanceUID)

      for segSeriesInstanceUID in loadable.ReferencedSegmentationInstanceUIDs[uid]:
        segLoadables = segPlugin.examine([slicer.dicomDatabase.filesForSeries(segSeriesInstanceUID)])
        for segLoadable in segLoadables:
          loadable.referencedInstanceUIDs += segLoadable.referencedInstanceUIDs

    loadable.referencedInstanceUIDs = list(set(loadable.referencedInstanceUIDs))

    if len(loadable.ReferencedSegmentationInstanceUIDs[uid])>1:
      logging.warning("SR references more than one SEG. This has not been tested!")
    for segUID in loadable.ReferencedSegmentationInstanceUIDs:
      loadable.referencedSegInstanceUIDs.append(segUID)

    if len(loadable.ReferencedRWVMSeriesInstanceUIDs)>1:
      logging.warning("SR references more than one RWVM. This has not been tested!")
    # not adding RWVM instances to referencedSeriesInstanceUIDs
    return loadable

  def sortReportsByDateTime(self, uids):
    return sorted(uids, key=lambda uid: self.getDateTime(uid))

  def getDateTime(self, uid):
    filename = slicer.dicomDatabase.fileForInstance(uid)
    dataset = dicom.read_file(filename)
    if hasattr(dataset, 'SeriesDate') and hasattr(dataset, "SeriesTime"):
      date = dataset.SeriesDate
      time = dataset.SeriesTime
    elif hasattr(dataset, 'StudyDate') and hasattr(dataset, "StudyTime"):
      date = dataset.StudyDate
      time = dataset.StudyDate
    else:
      date = "19630524"
      time = "000000"
    try:
      dateTime = datetime.datetime.strptime(date+time, '%Y%m%d%H%M%S')
    except ValueError:
      dateTime = "19630524000000"
    return dateTime

  def load(self, loadable):
    logging.debug('DICOM SR TID1500 load()')

    # if there is a RWVM object referenced from SEG, assume it contains the
    # scaling that needs to be applied to the referenced series. Assign
    # referencedSeriesUID from the image series, but load using the RWVM plugin

    logging.debug("before sorting: %s" % loadable.uids)
    sortedUIDs = self.sortReportsByDateTime(loadable.uids)
    logging.debug("after sorting: %s" % sortedUIDs)

    segPlugin = slicer.modules.dicomPlugins["DICOMSegmentationPlugin"]()

    tables = []

    for idx, uid in enumerate(sortedUIDs):

      for segSeriesInstanceUID in loadable.ReferencedSegmentationInstanceUIDs[uid]:
        segLoadables = segPlugin.examine([slicer.dicomDatabase.filesForSeries(segSeriesInstanceUID)])
        for segLoadable in segLoadables:
          if hasattr(segLoadable, "referencedSegInstanceUIDs"):
            segLoadable.referencedSegInstanceUIDs = list(set(segLoadable.referencedSegInstanceUIDs) -
                                                         set(loadable.referencedInstanceUIDs))
          segPlugin.load(segLoadable)
          if hasattr(segLoadable, "referencedSeriesUID") and len(loadable.ReferencedRWVMSeriesInstanceUIDs) > 0:
            self.determineAndApplyRWVMToReferencedSeries(loadable, segLoadable)

      self.tempDir = os.path.join(slicer.app.temporaryPath, "QIICR", "SR", self.currentDateTime, uid)
      try:
        os.makedirs(self.tempDir)
      except OSError:
        pass

      outputFile = os.path.join(self.tempDir, uid+".json")

      srFileName = slicer.dicomDatabase.fileForInstance(uid)
      if srFileName is None:
        logging.debug('Failed to get the filename from the DICOM database for ', uid)
        return False

      param = {
        "inputSRFileName": srFileName,
        "metaDataFileName": outputFile,
        }

      try:
        tid1500reader = slicer.modules.tid1500reader
      except AttributeError as exc:
        logging.debug('Unable to find CLI module tid1500reader, unable to load SR TID1500 object: %s ' % exc.message)
        self.cleanup()
        return False

      cliNode = slicer.cli.run(tid1500reader, None, param, wait_for_completion=True)
      if cliNode.GetStatusString() != 'Completed':
        logging.debug('tid1500reader did not complete successfully, unable to load DICOM SR TID1500')
        self.cleanup()
        return False

      table = self.metadata2vtkTableNode(outputFile)
      if table:
        # TODO: think about the following...
        if len(slicer.util.getNodesByClass('vtkMRMLSegmentationNode')) > 0:
          segmentationNode = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')[-1]
          segmentationNodeID = segmentationNode.GetID()
          table.SetAttribute("ReferencedSegmentationNodeID", segmentationNodeID)

          # TODO: think about a better solution for finding related reports
          if idx-1 > -1:
            table.SetAttribute("PriorReportUID", sortedUIDs[idx-1])
            tables[idx-1].SetAttribute("FollowUpReportUID", uid)
          table.SetAttribute("SOPInstanceUID", uid)
          self.assignTrackingUniqueIdentifier(outputFile, segmentationNode)

      tables.append(table)

      self.loadAdditionalMeasurements(uid)

      self.cleanup()

    return len(tables) > 0

  def getSegmentIDs(self, segmentationNode):
    segmentIDs = vtk.vtkStringArray()
    segmentation = segmentationNode.GetSegmentation()
    segmentation.GetSegmentIDs(segmentIDs)
    return [segmentIDs.GetValue(idx) for idx in range(segmentIDs.GetNumberOfValues())]

  def assignTrackingUniqueIdentifier(self, metafile, segmentationNode):

    with open(metafile) as datafile:
      data = json.load(datafile)

      segmentation = segmentationNode.GetSegmentation()
      segments = [segmentation.GetSegment(segmentID) for segmentID in self.getSegmentIDs(segmentationNode)]

      for idx, measurement in enumerate(data["Measurements"]):
        tagName = "TrackingUniqueIdentifier"
        trackingUID = measurement[tagName]
        segment = segments[idx]
        segment.SetTag(tagName, trackingUID)
        logging.debug("Setting tag '{}' to {} for segment with name {}".format(tagName, trackingUID, segment.GetName()))

  def determineAndApplyRWVMToReferencedSeries(self, loadable, segLoadable):
    rwvmUID = loadable.ReferencedRWVMSeriesInstanceUIDs[0]
    logging.debug("Looking up series %s from database" % rwvmUID)
    rwvmFiles = slicer.dicomDatabase.filesForSeries(rwvmUID)
    if len(rwvmFiles) > 0:
      # consider only the first item on the list - there should be only
      # one anyway, for the cases we are handling at the moment
      rwvmPlugin = slicer.modules.dicomPlugins["DICOMRWVMPlugin"]()
      rwvmFile = rwvmFiles[0]
      logging.debug("Reading RWVM from " + rwvmFile)
      rwvmDataset = dicom.read_file(rwvmFile)
      if hasattr(rwvmDataset, "ReferencedSeriesSequence"):
        if hasattr(rwvmDataset.ReferencedSeriesSequence[0], "SeriesInstanceUID"):
          if rwvmDataset.ReferencedSeriesSequence[0].SeriesInstanceUID == segLoadable.referencedSeriesUID:
            logging.debug("SEG references the same image series that is referenced by the RWVM series referenced from "
                          "SR. Will load via RWVM.")
            logging.debug("Examining " + rwvmFile)
            rwvmLoadables = rwvmPlugin.examine([[rwvmFile]])
            rwvmPlugin.load(rwvmLoadables[0])
    else:
      logging.warning("RWVM is referenced from SR, but is not found in the DICOM database!")

  def metadata2vtkTableNode(self, metafile):
    with open(metafile) as datafile:
      data = json.load(datafile)
      measurement = data["Measurements"][0]

      table = self.createAndConfigureTable()

      tableWasModified = table.StartModify()
      self.setupTableInformation(measurement, table)
      self.addMeasurementsToTable(data, table)
      table.EndModify(tableWasModified)

      slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveTableID(table.GetID())
      slicer.app.applicationLogic().PropagateTableSelection()
    return table

  def addMeasurementsToTable(self, data, table):
    for measurement in data["Measurements"]:
      name = measurement["TrackingIdentifier"]
      rowIndex = table.AddEmptyRow()
      table.SetCellText(rowIndex, 0, name)
      for columnIndex, measurementItem in enumerate(measurement["measurementItems"]):
        table.SetCellText(rowIndex, columnIndex + 1, measurementItem["value"])

  def createAndConfigureTable(self):
    table = slicer.vtkMRMLTableNode()
    slicer.mrmlScene.AddNode(table)
    table.SetAttribute("QuantitativeReporting", "Yes")
    table.SetAttribute("readonly", "Yes")
    table.SetUseColumnNameAsColumnHeader(True)
    return table

  def setupTableInformation(self, measurement, table):
    col = table.AddColumn()
    col.SetName("Tracking Identifier")

    infoItems = self.enumerateDuplicateNames(self.generateMeasurementInformation(measurement["measurementItems"]))

    for info in infoItems:
      col = table.AddColumn()
      col.SetName(info["name"])
      table.SetColumnLongName(info["name"], info["name"])
      table.SetColumnUnitLabel(info["name"], info["unit"])
      table.SetColumnDescription(info["name"], info["description"])

  def generateMeasurementInformation(self, measurementItems):
    infoItems = []
    for measurementItem in measurementItems:

      crntInfo = dict()

      unit = measurementItem["units"]["CodeValue"]
      crntInfo["unit"] = measurementItem["units"]["CodeMeaning"]

      if "derivationModifier" in measurementItem.keys():
        description = crntInfo["name"] = measurementItem["derivationModifier"]["CodeMeaning"]
      else:
        description = measurementItem["quantity"]["CodeMeaning"]

      crntInfo["name"] = "%s [%s]" % (description, unit.replace("[", "").replace("]", ""))
      crntInfo["description"] = description

      infoItems.append(crntInfo)
    return infoItems

  def enumerateDuplicateNames(self, items):
    names = [item["name"] for item in items]
    counts = {k: v for k, v in Counter(names).items() if v > 1}
    nameListCopy = names[:]

    for i in reversed(range(len(names))):
      item = names[i]
      if item in counts and counts[item]:
        nameListCopy[i] += " (%s)" % str(counts[item])
        counts[item] -= 1

    for idx, item in enumerate(nameListCopy):
      items[idx]["name"] = item
    return items

  def isConcept(self, item, coding):
    code = item.ConceptNameCodeSequence[0]
    return code.CodingSchemeDesignator == self.codings[coding]["scheme"] and code.CodeValue == self.codings[coding]["value"]

  def loadAdditionalMeasurements(self, srUID):
    """
    Loads length measements as annotation rulers
    TODO: need to generalize to other report contents
    """

    srFilePath = slicer.dicomDatabase.fileForInstance(srUID)
    sr = dicom.read_file(srFilePath)

    if not self.isConcept(sr, "imagingMeasurementReport"):
      return sr

    contents = {}
    measurements = []
    contents['measurements'] = measurements
    for item in sr.ContentSequence:
      if self.isConcept(item, "personObserver"):
        contents['personObserver'] = item.PersonName
      if self.isConcept(item, "imagingMeasuremnts"):
        for contentItem in item.ContentSequence:
          if self.isConcept(contentItem, "measurementGroup"):
            measurement = {}
            for measurementItem in contentItem.ContentSequence:
              if self.isConcept(measurementItem, "trackingIdentifier"):
                measurement['trackingIdentifier'] = measurementItem.TextValue
              if self.isConcept(measurementItem, "trackingUniqueIdentifier"):
                measurement['trackingUniqueIdentifier'] = measurementItem.UID
              if self.isConcept(measurementItem, "findingSite"):
                measurement['findingSite'] = measurementItem.ConceptCodeSequence[0].CodeMeaning
              if self.isConcept(measurementItem, "length"):
                for lengthItem in measurementItem.ContentSequence:
                  measurement['polyline'] = lengthItem.GraphicData
                  for selectionItem in lengthItem.ContentSequence:
                    if selectionItem.RelationshipType == "SELECTED FROM":
                      for reference in selectionItem.ReferencedSOPSequence:
                        measurement['referencedSOPInstanceUID'] = reference.ReferencedSOPInstanceUID
                        if hasattr(reference, "ReferencedFrameNumber") and reference.ReferencedFrameNumber != "1":
                          print('Error - only single frame references supported')
            measurements.append(measurement)

    for measurement in contents['measurements']:
      rulerNode = slicer.vtkMRMLAnnotationRulerNode()
      rulerNode.SetLocked(True)
      rulerNode.SetName(contents['personObserver'])

      referenceFilePath = slicer.dicomDatabase.fileForInstance(measurement['referencedSOPInstanceUID'])
      reference = dicom.read_file(referenceFilePath)
      origin = numpy.array(reference.ImagePositionPatient)
      alongColumnVector = numpy.array(reference.ImageOrientationPatient[:3])
      alongRowVector = numpy.array(reference.ImageOrientationPatient[3:])
      alongColumnVector *= reference.PixelSpacing[1]
      alongRowVector *= reference.PixelSpacing[0]
      col1,row1,col2,row2 = measurement['polyline']
      lpsToRAS = numpy.array([-1,-1,1])
      p1 = (origin + col1 * alongColumnVector + row1 * alongRowVector) * lpsToRAS
      p2 = (origin + col2 * alongColumnVector + row2 * alongRowVector) * lpsToRAS
      rulerNode.SetPosition1(*p1)
      rulerNode.SetPosition2(*p2)

      rulerNode.Initialize(slicer.mrmlScene)
      colorIndex = 1 + len(slicer.util.getNodesByClass('vtkMRMLAnnotationRulerNode'))
      colorNode = slicer.util.getNode("GenericAnatomyColors")
      color = [0,]*4
      colorNode.GetColor(colorIndex, color)
      rulerNode.GetDisplayNode().SetColor(*color[:3])
      rulerNode.GetAnnotationTextDisplayNode().SetColor(*color[:3])
      rulerNode.GetAnnotationPointDisplayNode().SetColor(*color[:3])
      rulerNode.GetAnnotationPointDisplayNode().SetGlyphScale(2)
      rulerNode.GetAnnotationLineDisplayNode().SetLabelPosition(random.random())


class DICOMLongitudinalTID1500PluginClass(DICOMTID1500PluginClass):

  def __init__(self):
    super(DICOMLongitudinalTID1500PluginClass, self).__init__()
    self.loadType = "Longitudinal DICOM Structured Report TID1500"

  def examineFiles(self, files):
    loadables = []

    for cFile in files:
      dataset = dicom.read_file(cFile)

      uid = self.getDICOMValue(dataset, "SOPInstanceUID")
      if uid == "":
        return []

      if self.isDICOMTID1500(dataset):
        otherSRDatasets, otherSRFiles = self.getRelatedSRs(dataset)

        if len(otherSRFiles):
          allDatasets = otherSRDatasets + [dataset]
          loadable = self.createLoadableAndAddReferences(allDatasets)
          loadable.files = [cFile]+otherSRFiles
          seriesDescription = self.getDICOMValue(dataset, "SeriesDescription", "Unknown")
          loadable.name = seriesDescription + ' - as a Longitudinal DICOM SR TID1500 object'
          loadable.tooltip = loadable.name
          loadable.selected = True
          loadable.confidence = 0.96
          loadable.uids = [self.getDICOMValue(d, "SOPInstanceUID") for d in allDatasets]
          refName = self.referencedSeriesName(loadable)
          if refName != "":
            loadable.name = refName + " " + seriesDescription + " - SR TID1500"

          loadables.append(loadable)

          logging.debug('DICOM SR Longitudinal TID1500 modality found')

    return loadables

  def getRelatedSRs(self, dataset):
    otherSRFiles = []
    otherSRDatasets = []
    studyInstanceUID = self.getDICOMValue(dataset, "StudyInstanceUID")
    patient = slicer.dicomDatabase.patientForStudy(studyInstanceUID)
    studies = [s for s in slicer.dicomDatabase.studiesForPatient(patient) if studyInstanceUID not in s]
    for study in studies:
      series = slicer.dicomDatabase.seriesForStudy(study)
      foundSRs = []
      for s in series:
        srFile = self.fileForSeries(s)
        tempDCM = dicom.read_file(srFile)
        if self.isDICOMTID1500(tempDCM):
          foundSRs.append(srFile)
          otherSRDatasets.append(tempDCM)

      if len(foundSRs) > 1:
        logging.warn("Found more than one SR per study!! This is not supported right now")
      otherSRFiles += foundSRs
    return otherSRDatasets, otherSRFiles

  def fileForSeries(self, series):
    instance = slicer.dicomDatabase.instancesForSeries(series)
    return slicer.dicomDatabase.fileForInstance(instance[0])


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
    parent.dependencies = ['DICOM', 'Colors']
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
    # slicer.modules.dicomPlugins['DICOMLongitudinalTID1500Plugin'] = DICOMLongitudinalTID1500PluginClass
