import logging

import slicer
from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin
from SegmentStatistics import SegmentStatisticsLogic
from DICOMSegmentationPlugin import DICOMSegmentationExporter


class CustomSegmentStatisticsLogic(SegmentStatisticsLogic):

  @staticmethod
  def getDICOMTriplet(codeValue, codingSchemeDesignator, codeMeaning):
    return {'CodeValue':codeValue,
            'CodingSchemeDesignator': codingSchemeDesignator,
            'CodeMeaning': codeMeaning}

  @property
  def statistics(self):
    return self.getStatistics()

  @property
  def segmentationNode(self):
    return slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("Segmentation"))

  def __init__(self):
    SegmentStatisticsLogic.__init__(self)
    self.terminologyLogic = slicer.modules.terminologies.logic()

  def exportToTable(self, table=None, nonEmptyKeysOnly=True):
    if not table:
      table = slicer.vtkMRMLTableNode()
      table.SetName(slicer.mrmlScene.GenerateUniqueName(self.grayscaleNode.GetName() + ' statistics'))
      slicer.mrmlScene.AddNode(table)
    table.SetUseColumnNameAsColumnHeader(True)
    SegmentStatisticsLogic.exportToTable(self, table, nonEmptyKeysOnly)
    return table

  def isSegmentValid(self, segmentID):
    for key in self.getNonEmptyKeys():
      if isinstance(self.statistics[segmentID, key], str):
        continue
      if self.statistics[segmentID, key] != 0:
        return True
    return False

  def createJSONFromTerminologyContext(self, terminologyEntry):
    segmentData = dict()

    categoryObject = terminologyEntry.GetCategoryObject()
    if categoryObject is None or not self.isTerminologyInformationValid(categoryObject):
      return {}
    segmentData["SegmentedPropertyCategoryCodeSequence"] = self.getJSONFromVTKSlicerTerminology(categoryObject)

    typeObject = terminologyEntry.GetTypeObject()
    if typeObject is None or not self.isTerminologyInformationValid(typeObject):
      return {}
    segmentData["SegmentedPropertyTypeCodeSequence"] = self.getJSONFromVTKSlicerTerminology(typeObject)

    modifierObject = terminologyEntry.GetTypeModifierObject()
    if modifierObject is not None and self.isTerminologyInformationValid(modifierObject):
      segmentData["SegmentedPropertyTypeModifierCodeSequence"] = self.getJSONFromVTKSlicerTerminology(modifierObject)

    return segmentData

  def createJSONFromAnatomicContext(self, terminologyEntry):
    segmentData = dict()

    regionObject = terminologyEntry.GetAnatomicRegionObject()
    if regionObject is None or not self.isTerminologyInformationValid(regionObject):
      return {}
    segmentData["AnatomicRegionSequence"] = self.getJSONFromVTKSlicerTerminology(regionObject)

    regionModifierObject = terminologyEntry.GetAnatomicRegionModifierObject()
    if regionModifierObject is not None and self.isTerminologyInformationValid(regionModifierObject):
      segmentData["AnatomicRegionModifierSequence"] = self.getJSONFromVTKSlicerTerminology(regionModifierObject)
    return segmentData

  def isTerminologyInformationValid(self, termTypeObject):
    return all(t is not None for t in [termTypeObject.GetCodeValue(), termTypeObject.GetCodingSchemeDesignator(),
                                       termTypeObject.GetCodeMeaning()])

  def getJSONFromVTKSlicerTerminology(self, termTypeObject):
    return self.getDICOMTriplet(termTypeObject.GetCodeValue(), termTypeObject.GetCodingSchemeDesignator(),
                                termTypeObject.GetCodeMeaning())

  def generateJSON4DcmSR(self, dcmSegmentationFile, sourceVolumeNode):
    measurements = []

    sourceImageSeriesUID = ModuleLogicMixin.getDICOMValue(sourceVolumeNode, "0020,000E")
    logging.debug("SourceImageSeriesUID: {}".format(sourceImageSeriesUID))
    segmentationSOPInstanceUID = ModuleLogicMixin.getDICOMValue(dcmSegmentationFile, "0008,0018")
    logging.debug("SegmentationSOPInstanceUID: {}".format(segmentationSOPInstanceUID))

    for segmentID in self.statistics["SegmentIDs"]:
      if not self.isSegmentValid(segmentID):
        continue

      data = dict()
      data["TrackingIdentifier"] = self.statistics[segmentID, "Segment"]
      data["ReferencedSegment"] = len(measurements)+1
      data["SourceSeriesForImageSegmentation"] = sourceImageSeriesUID
      data["segmentationSOPInstanceUID"] = segmentationSOPInstanceUID
      segment = self.segmentationNode.GetSegmentation().GetSegment(segmentID)

      terminologyEntry = DICOMSegmentationExporter.getDeserializedTerminologyEntry(segment)

      data["Finding"] = self.createJSONFromTerminologyContext(terminologyEntry)["SegmentedPropertyTypeCodeSequence"]
      anatomicContext = self.createJSONFromAnatomicContext(terminologyEntry)
      if anatomicContext.has_key("AnatomicRegionSequence"):
        data["FindingSite"] = anatomicContext["AnatomicRegionSequence"]
      data["measurementItems"] = self.createMeasurementItemsForLabelValue(segmentID)
      measurements.append(data)

    return measurements

  def createMeasurementItemsForLabelValue(self, segmentValue):
    measurementItems = []
    for key in self.getNonEmptyKeys():
      measurementInfo = self.getMeasurementInfo(key)
      if measurementInfo:
        item = dict()
        item["value"] = str(self.statistics[segmentValue, key])
        item["quantity"] = self._createCodeSequence(measurementInfo["DICOM.QuantityCode"])
        item["units"] = self._createCodeSequence(measurementInfo["DICOM.UnitsCode"])
        if measurementInfo.has_key("DICOM.DerivationCode"):
          item["derivationModifier"] = self._createCodeSequence(measurementInfo["DICOM.DerivationCode"])
        measurementItems.append(item)
    return measurementItems

  def _createCodeSequence(self, vtkStringifiedCodedEntry):
    codeSequence = dict()
    for each in vtkStringifiedCodedEntry.split('|'):
      key, value = each.split(":")
      codeSequence[key] = value
    return codeSequence