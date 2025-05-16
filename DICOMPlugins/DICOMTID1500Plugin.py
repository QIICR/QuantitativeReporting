import json
import logging
import os
import vtk
import datetime
from collections import Counter

import numpy
import numpy as np 
import random
import pydicom

import slicer
from DICOMLib import DICOMLoadable
from base.DICOMPluginBase import DICOMPluginBase
from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin

try:
    import highdicom as hd
except ModuleNotFoundError:
    slicer.util.pip_install("highdicom")
    import highdicom as hd 


class DICOMTID1500PluginClass(DICOMPluginBase, ModuleLogicMixin):

  UID_EnhancedSRStorage = "1.2.840.10008.5.1.4.1.1.88.22"
  UID_ComprehensiveSRStorage = "1.2.840.10008.5.1.4.1.1.88.33"
  UID_Comprehensive3DSRStorage = "1.2.840.10008.5.1.4.1.1.88.34"
  UID_SegmentationStorage = "1.2.840.10008.5.1.4.1.1.66.4"
  UID_RealWorldValueMappingStorage = "1.2.840.10008.5.1.4.1.1.67"

  def __init__(self):
    DICOMPluginBase.__init__(self)
    self.loadType = "DICOM Structured Report TID1500"

    self.codings = {
      "imagingMeasurementReport": { "scheme": "DCM", "value": "126000" },
      "personObserver": { "scheme": "DCM", "value": "121008" },
      "imagingMeasurements": { "scheme": "DCM", "value": "126010" },
      "measurementGroup": { "scheme": "DCM", "value": "125007" },
      "trackingIdentifier": { "scheme": "DCM", "value": "112039" },
      "trackingUniqueIdentifier": { "scheme": "DCM", "value": "112040" },
      "findingSite": { "scheme": "SRT", "value": "G-C0E3" },
      "length": { "scheme": "SRT", "value": "G-D7FE" },
    }


  def examineFiles(self, files):
    loadables = []

    for cFile in files:
      dataset = pydicom.read_file(cFile)

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
                        self.getDICOMValue(dataset, "SOPClassUID") == self.UID_ComprehensiveSRStorage or 
                        self.getDICOMValue(dataset, "SOPClassUID") == self.UID_Comprehensive3DSRStorage) and \
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
    dataset = pydicom.read_file(filename)
    if hasattr(dataset, 'SeriesDate') and hasattr(dataset, "SeriesTime"):
      date = dataset.SeriesDate
      time = dataset.SeriesTime
    elif hasattr(dataset, 'StudyDate') and hasattr(dataset, "StudyTime"):
      date = dataset.StudyDate
      time = dataset.StudyDate
    else:
      date = ""
      time = ""
    try:
      dateTime = datetime.datetime.strptime(date+time, '%Y%m%d%H%M%S')
    except ValueError:
      dateTime = ""
    return dateTime
  
  def checkUsePlugin(self, srFileName):
    """ 
    Checks if the original plugin should be used (tid1500reader) to read the SR, or if specialized 
    highdicom code should be utilized, in the case of point, bounding box, etc. 
    """

    # default to use the plugin 
    checkUsePlugin = 1 

    # read the SR using highdicom 
    sr = hd.sr.srread(srFileName)

    planar_roi_measurement_groups = sr.content.get_planar_roi_measurement_groups()
    num_planar_roi_measurement_groups = len(planar_roi_measurement_groups)
    if (num_planar_roi_measurement_groups > 0): 
      for planar_roi_measurement_group in planar_roi_measurement_groups: 
        if (planar_roi_measurement_group.reference_type.value=="111030" and \
            planar_roi_measurement_group.reference_type.scheme_designator=="DCM" and \
            planar_roi_measurement_group.reference_type.meaning=="Image Region"):
          if (planar_roi_measurement_group.roi.value_type == hd.sr.ValueTypeValues('SCOORD') or 
              planar_roi_measurement_group.roi.value_type == hd.sr.ValueTypeValues('SCOORD3D')):
            checkUsePlugin = 0 
    else:
      checkUsePlugin = 1 

    return checkUsePlugin
  
  def checkIfSRContainsBbox(self, srFileName):
    """
    Checks if the SR contains a bounding box or not. 
    """

    # default is that SR does not contain a bounding box 
    checkIfSRContainsBbox = 0 

    # read the SR using highdicom 
    sr = hd.sr.srread(srFileName)

    # First get the planar roi measurement groups 
    groups = sr.content.get_planar_roi_measurement_groups()
    num_groups = len(groups)
    # Then we check if the SR contains a bounding box or not 
    for group in groups: 
      qual_evals = group.get_qualitative_evaluations()
      for qual_eval in qual_evals: 
        if qual_eval.name.CodeValue == "130400" and \
          qual_eval.name.CodingSchemeDesignator == "DCM" and \
          qual_eval.name.CodeMeaning == "Geometric purpose of region" and \
          qual_eval.value.CodeValue == "75958009" and \
          qual_eval.value.CodingSchemeDesignator == "SCT" and \
          qual_eval.value.CodeMeaning == "Bounded by": 
          checkIfSRContainsBbox = 1 
        else: 
          checkIfSRContainsBbox = 0 

    return checkIfSRContainsBbox 
  
  def checkIfSRContainsPoint(self, srFileName): 
    """
    Checks if the SR contains a point. 
    """

    # default is that the SR does not contain a point 
    checkIfSRContainsPoint = 0 

    # read the SR using highdicom 
    sr = hd.sr.srread(srFileName)

    # create the ImageRegion3D code 
    image_region_code = hd.sr.value_types.Code(
        value='111030',
        scheme_designator='DCM',
        meaning='Image Region'
    )

    # First get the planar roi measurement groups 
    groups = sr.content.get_planar_roi_measurement_groups()
    num_groups = len(groups)

    # Then we check if the SR contains a point or not 
    # Iterate through the groups 
    for group in groups: 
      # group.reference_type = Code(value='111030', scheme_designator='DCM', meaning='Image Region', scheme_version=None)
      # Check if there is a reference_type, should be ImageRegion
      try: 
        reference_type = group.reference_type
      except: 
        print('reference_type does not exist for group')
      # If it does equal image_region_code, then check if it's a POINT
      if (reference_type == image_region_code):
        try: 
          # type(group.roi) = highdicom.sr.content.ImageRegion3D
          graphic_type = group.roi.GraphicType
        except: 
          print('GraphicType does not exist for group.roi')
        if (graphic_type == "POINT"): 
          checkIfSRContainsPoint = 1 
 
    return checkIfSRContainsPoint 
  
  def checkIfSRContainsPolyline(self, srFileName): 
    """
    Checks if the SR contains a polyline. 
    """

    # default is that the SR contains a polyline 
    checkIfSRContainsPolyline  = 0 

    # read the SR using highdicom 
    sr = hd.sr.srread(srFileName)

    # create the ImageRegion3D code 
    image_region_code = hd.sr.value_types.Code(
        value='111030',
        scheme_designator='DCM',
        meaning='Image Region'
    )

    # First get the planar roi measurement groups 
    groups = sr.content.get_planar_roi_measurement_groups()
    num_groups = len(groups)

    # Then we check if the SR contains a polyline or not 
    # Iterate through the groups 
    for group in groups: 
      # group.reference_type = Code(value='111030', scheme_designator='DCM', meaning='Image Region', scheme_version=None)
      # Check if there is a reference_type, should be ImageRegion
      try: 
        reference_type = group.reference_type
      except: 
        print('reference_type does not exist for group')
      # If it does equal image_region_code, then check if it's a POINT
      if (reference_type == image_region_code):
        try: 
          # type(group.roi) = highdicom.sr.content.ImageRegion3D
          graphic_type = group.roi.GraphicType
        except: 
          print('GraphicType does not exist for group.roi')
        if (graphic_type == "POLYLINE"): 
          checkIfSRContainsPolyline = 1 
 
    return checkIfSRContainsPolyline 
  
  def getIPPFromSOP(self, referenced_sop_instance_uid, referenced_series_instance_uid):
    """
    In order to display the bounding box markups in Slicer, 
    we need the IPP corresponding to the referenced 
    SOPInstanceUID. We get this from the Slicer dicom database. 
    """

    # Get the dicom database 
    db = slicer.dicomDatabase 

    # Get the files for the series 
    fileList = db.filesForSeries(referenced_series_instance_uid)

    # Use pydicom to read the files, get the SOPInstanceUID and the IPP for each 
    num_files = len(fileList)
    SOPInstanceUID_list = [] 
    IPP_list = [] 
    for file in fileList: 
      ds = pydicom.dcmread(file)
      SOPInstanceUID_list.append(ds.SOPInstanceUID)
      IPP_list.append(ds.ImagePositionPatient)

    # Get the index of the SOPInstanceUID we want 
    index = SOPInstanceUID_list.index(referenced_sop_instance_uid)

    # Now get the IPP for the corresponding SOPInstanceUID 
    ipp = IPP_list[index]

    # instance_uids = db.instancesForSeries(referenced_series_instance_uid) # this gets the SOPInstanceUIDs, but we need the filenames 
    # print(slicer.dicomDatabase.instanceValue(instUids[0], '0010,0010')) # patient name

    return ipp 
  
  def showTable(self, table):
    """
      Display a table in the scene. 
    """
    currentLayout = slicer.app.layoutManager().layout
    layoutWithTable = slicer.modules.tables.logic().GetLayoutWithTable(currentLayout)
    slicer.mrmlScene.AddNode(table)
    slicer.app.layoutManager().setLayout(layoutWithTable)
    slicer.app.applicationLogic().GetSelectionNode().SetActiveTableID(table.GetID())
    slicer.app.applicationLogic().PropagateTableSelection()

    return 
  
  def createBboxTable(self, poly_infos):
    """
    Create and display a table for the bbox info. 
    """

    tableNode = slicer.vtkMRMLTableNode()
    # slicer.mrmlScene.AddNode(tableNode)
    tableNode.SetAttribute("readonly", "Yes") 
    tableNode.SetName("Table for bounding boxes")

    # Add columns 
    col = tableNode.AddColumn()
    col.SetName("Tracking Identifier")
    col = tableNode.AddColumn()
    col.SetName("FindingType")
    col = tableNode.AddColumn()
    col.SetName("FindingSite")
    col = tableNode.AddColumn()
    col.SetName("Bounding box points")
    col = tableNode.AddColumn()
    col.SetName("width")
    col = tableNode.AddColumn()
    col.SetName("height")
    col = tableNode.AddColumn()
    col.SetName("center_RAS")

    # Order p by TrackingIdentifier?
    # poly_infos = sorted(poly_infos, key=lambda x: x['TrackingIdentifier'])
    # poly_infos = dict(sorted(data.items(),key=lambda item: int(item[1]['TrackingIdentifier'])))
    # Or, order by IPP2 
    poly_infos = sorted(poly_infos, key=lambda x: x['center_z'])

    for i,p in enumerate(poly_infos):
      # get values 
      tracking_identifier = p['TrackingIdentifier']
      finding_type = p['FindingType']
      finding_site = p['FindingSite'][0] # check this later. 
      polyline = p['polyline']
      polyline_str = ', '.join(f"({np.round(a,2)}, {np.round(b,2)})" for a, b in polyline)
      width = np.round(p['width'],2)
      height = np.round(p['height'],2)
      center_x = np.round(p['center_x'],2)
      center_y = np.round(p['center_y'],2)
      center_z = np.round(p['center_z'],2)
      center = list([str(center_x), str(center_y), str(center_z)])
      # add tracking info and finding site info 
      rowIndex = tableNode.AddEmptyRow()
      tableNode.SetCellText(rowIndex, 0, tracking_identifier)
      tableNode.SetCellText(rowIndex, 1, finding_type[2])
      tableNode.SetCellText(rowIndex, 2, finding_site[2])
      # tableNode.SetCellText(rowIndex, 2, f"({', '.join(finding_type)})") 
      # tableNode.SetCellText(rowIndex, 3, f"({', '.join(finding_site)})")
      # add bbox points 
      tableNode.SetCellText(rowIndex, 3, polyline_str) 
      # add width, height and center in RAS 
      tableNode.SetCellText(rowIndex, 4, str(width))
      tableNode.SetCellText(rowIndex, 5, str(height))
      tableNode.SetCellText(rowIndex, 6, f"({', '.join(center)})")


    return tableNode 
  
    
  def createPointTable(self, point_infos):
    """
    Create and display a table for the point info. 
    """

    tableNode = slicer.vtkMRMLTableNode()
    # slicer.mrmlScene.AddNode(tableNode)
    tableNode.SetAttribute("readonly", "Yes") 
    tableNode.SetName("Table for points")

    # Add columns 
    col = tableNode.AddColumn()
    col.SetName("Tracking Identifier")
    col = tableNode.AddColumn()
    col.SetName("FindingType")
    col = tableNode.AddColumn()
    col.SetName("FindingSite")
    col = tableNode.AddColumn()
    col.SetName("Point")

    # Order by IPP2 
    point_infos = sorted(point_infos, key=lambda x: x['point'][2])

    for i,p in enumerate(point_infos):
      # get values 
      tracking_identifier = p['TrackingIdentifier']
      tracking_uid = p['TrackingUID']
      finding_type = p['FindingType']
      finding_site = p['FindingSite'][0] # check this later. 
      point = p["point"]
      point = [str(np.round(f,2)) for f in point]
      point_str = f"({', '.join(point)})"
      # qual_eval_names = p['QualitativeEvaluationNames']
      # qual_eval_values = p['QualitativeEvaluationValues']
      content_sequence_names = p['ContentSequenceNames']
      content_sequence_values = p['ContentSequenceValues']
      # add tracking info and finding site info 
      rowIndex = tableNode.AddEmptyRow()
      tableNode.SetCellText(rowIndex, 0, tracking_identifier)
      # tableNode.SetCellText(rowIndex, 1, f"({', '.join(finding_type)})") 
      # tableNode.SetCellText(rowIndex, 2, f"({', '.join(finding_site)})")
      tableNode.SetCellText(rowIndex, 1, finding_type[2]) # CodeMeaning
      tableNode.SetCellText(rowIndex, 2, finding_site[2]) # CodeMeaning
      # add point
      tableNode.SetCellText(rowIndex, 3, point_str) 
      # now add the names CodeMeaning as the column name, and the values CodeMeaning as the actual value 
      # first do for qualitative evaluations 
      num_rows = 4
      # for j, qual_eval_name in enumerate(qual_eval_names):
      #   col = tableNode.AddColumn()
      #   colName = str(qual_eval_name[2])
      #   colValue = str(qual_eval_values[j][2])
      #   rowIndexValue = num_rows+j 
      #   print('rowIndexValue: ' + str(rowIndexValue))
      #   print('colName: ' + str(colName))
      #   print('colValue: ' + str(colValue))
      #   col.SetName(colName) 
      #   tableNode.SetCellText(rowIndex, rowIndexValue, colValue) 
      # then add for content sequence
      # num_rows = num_rows + len(qual_eval_names)
      for j, content_sequence_name in enumerate(content_sequence_names): 
        col = tableNode.AddColumn() 
        rowIndexValue = num_rows + j
        colName = str(content_sequence_name[2])
        colValue = str(content_sequence_values[j][2])
        col.SetName(colName) 
        tableNode.SetCellText(rowIndex, rowIndexValue, colValue) 


    return tableNode 
  
  def createPolylineTable(self, point_infos):
    """
    Create and display a table for the polyline info 
    """

    tableNode = slicer.vtkMRMLTableNode()
    # slicer.mrmlScene.AddNode(tableNode)
    tableNode.SetAttribute("readonly", "Yes") 
    tableNode.SetName("Table for lines")

    # Add columns 
    col = tableNode.AddColumn()
    col.SetName("Tracking Identifier")
    col = tableNode.AddColumn()
    col.SetName("FindingType")
    col = tableNode.AddColumn()
    col.SetName("FindingSite")
    col = tableNode.AddColumn()
    col.SetName("PolyLine")

    for i,p in enumerate(point_infos):
      # get values 
      tracking_identifier = p['TrackingIdentifier']
      tracking_uid = p['TrackingUID']
      finding_type = p['FindingType']
      finding_site = p['FindingSite'][0] # check this later. 
      polyline = p["polyline"]
      polyline = [str(np.round(f,2)) for f in polyline]
      polyline_str = f"({', '.join(polyline)})"
      # add tracking info and finding site info 
      rowIndex = tableNode.AddEmptyRow()
      tableNode.SetCellText(rowIndex, 0, tracking_identifier)
      tableNode.SetCellText(rowIndex, 1, finding_type[2]) # CodeMeaning
      tableNode.SetCellText(rowIndex, 2, finding_site[2]) # CodeMeaning
      # add polyline
      tableNode.SetCellText(rowIndex, 3, polyline_str) 

    return tableNode 

  def extractBboxMetadataToVtkTableNode(self, srFileName): 
    """
    Extracts the bounding box metadata from the SR using highdicom, 
    and creates a table node. 
    """
    # read SR using highdicom 
    sr = hd.sr.srread(srFileName)

    # get the referenced SeriesInstanceUID 
    referenced_series_instance_uid = sr.CurrentRequestedProcedureEvidenceSequence[0].ReferencedSeriesSequence[0].SeriesInstanceUID

    # will store the info needed for table too. 
    poly_infos = [] 

    # First get the planar roi measurement gorups 
    groups = sr.content.get_planar_roi_measurement_groups()

    for group in groups: 

      # Get the tracking ids 
      tracking_identifier = group.tracking_identifier
      tracking_uid = group.tracking_uid

      # Get the findings and finding_sites 
      finding_type = [group.finding_type.CodeValue, group.finding_type.CodingSchemeDesignator, group.finding_type.CodeMeaning]
      finding_sites = []
      for finding_site in group.finding_sites:
        if hasattr(finding_site, 'ConceptCodeSequence') and finding_site.ConceptCodeSequence:
          finding_sites.append([finding_site.ConceptCodeSequence[0].CodeValue, 
                                finding_site.ConceptCodeSequence[0].CodingSchemeDesignator,
                                finding_site.ConceptCodeSequence[0].CodeMeaning])

      # if (group.reference_type.meaning == "Image Region"): # why meaning instead of CodeMeaning? 
      if (group.reference_type.value=="111030" and \
          group.reference_type.scheme_designator=="DCM" and \
          group.reference_type.meaning=="Image Region"):

        roi = group.roi # should exist if Image Region is present      
        try: 
          referenced_sop_instance_uid = roi.ContentSequence[0].referenced_sop_instance_uid
        except: 
          print('Cannot access referenced SOPInstanceUID')

        if (roi.GraphicType=="POLYLINE"):
          bbox = roi.GraphicData 
          extracted_data_type = roi.PixelOriginInterpretation # Could be frame, or volume, interpretation of points is different then! 
          # calculate the width, height and center, as these are needed for display 
          min_x = np.min([bbox[0], bbox[2], bbox[4], bbox[6]])
          max_x = np.max([bbox[0], bbox[2], bbox[4], bbox[6]])
          min_y = np.min([bbox[1], bbox[3], bbox[5], bbox[7]])
          max_y = np.max([bbox[1], bbox[3], bbox[5], bbox[7]])
          width = max_x - min_x 
          height = max_y - min_y 
          center_x = min_x + width/2
          center_y = min_y + height/2 
          center_z = self.getIPPFromSOP(referenced_sop_instance_uid, 
                                        referenced_series_instance_uid)[2] 
      
      # append to poly_infos
      poly_infos.append({
                         "TrackingIdentifier": tracking_identifier, 
                         "TrackingUID" : tracking_uid,
                         "SOPInstanceUID" : referenced_sop_instance_uid, 
                         "FindingType": finding_type, 
                         "FindingSite": finding_sites,
                         "polyline": [[bbox[0],bbox[1]], [bbox[2],bbox[3]], [bbox[4],bbox[5]], [bbox[6],bbox[7]]], 
                         "width": width, 
                         "height": height,
                         "center_x": -center_x, # for display in Slicer, negate this. 
                         "center_y": -center_y,  # for display in Slicer, negate this. 
                         "center_z": center_z
                        })

      # create and display tableNode 
      tableNode = self.createBboxTable(poly_infos)

    return poly_infos, tableNode 
  
  def extractPointMetadataToVtkTableNode(self, srFileName):
    """
    Extracts the point metadata from the SR using highdicom, 
    and creates a table node. 
    """

    # read SR using highdicom 
    sr = hd.sr.srread(srFileName)

    # will store the info needed for table too. 
    point_infos = [] 

    # First get the planar roi measurement gorups 
    groups = sr.content.get_planar_roi_measurement_groups()

    for group in groups: 

      # Get the tracking ids 
      tracking_identifier = group.tracking_identifier
      tracking_uid = group.tracking_uid

      # Get the findings and finding_sites 
      finding_type = [group.finding_type.CodeValue, group.finding_type.CodingSchemeDesignator, group.finding_type.CodeMeaning]
      finding_sites = []
      for finding_site in group.finding_sites:
        if hasattr(finding_site, 'ConceptCodeSequence') and finding_site.ConceptCodeSequence:
          finding_sites.append([finding_site.ConceptCodeSequence[0].CodeValue, 
                                finding_site.ConceptCodeSequence[0].CodingSchemeDesignator,
                                finding_site.ConceptCodeSequence[0].CodeMeaning])

      # # list of QualitativeEvaluation 
      # if (len(group.get_qualitative_evaluations())>0): 
      #   qual_eval = group.get_qualitative_evaluations()[0] 
      #   num_qual_eval = len(qual_eval)
      #   qual_eval_names = [] 
      #   qual_eval_values = [] 
      #   for n in range(0,num_qual_eval):
      #     qual_eval_name_CodeValue = qual_eval[n].name.CodeValue 
      #     qual_eval_name_CodingSchemeDesignator = qual_eval[n].name.CodingSchemeDesignator 
      #     qual_eval_name_CodeMeaning = qual_eval[n].name.CodeMeaning 
      #     qual_eval_value_CodeValue = qual_eval[n].value.CodeValue 
      #     qual_eval_value_CodingSchemeDesignator = qual_eval[n].value.CodingSchemeDesignator 
      #     qual_eval_value_CodeMeaning = qual_eval[n].value.CodeMeaning 
      #     qual_eval_name = [qual_eval_name_CodeValue, 
      #                       qual_eval_name_CodingSchemeDesignator, 
      #                       qual_eval_name_CodeMeaning]
      #     qual_eval_value = [qual_eval_value_CodeValue, 
      #                        qual_eval_value_CodingSchemeDesignator, 
      #                        qual_eval_value_CodeMeaning]
      #     qual_eval_names.append(qual_eval_name)
      #     qual_eval_values.append(qual_eval_value)

      # findings, clinically significant cancer, ggg 
      if (len(group)>0): 
        # group[0] = highdicom.sr.value_types.ContainerContentItem
        content_sequence_names = [] 
        content_sequence_values = [] 
        for n in range(0,len(group[0])): 
            ContentSequence = group[0].ContentSequence[n]
            if ContentSequence.RelationshipType=="CONTAINS":
              content_sequence_name_CodeValue = ContentSequence.name.CodeValue 
              content_sequence_name_CodingSchemeDesignator = ContentSequence.name.CodingSchemeDesignator 
              content_sequence_name_CodeMeaning = ContentSequence.name.CodeMeaning
              content_sequence_value_CodeValue = ContentSequence.value.CodeValue 
              content_sequence_value_CodingSchemeDesignator = ContentSequence.value.CodingSchemeDesignator 
              content_sequence_value_CodeMeaning = ContentSequence.value.CodeMeaning 
              content_sequence_name = [content_sequence_name_CodeValue, 
                                       content_sequence_name_CodingSchemeDesignator, 
                                       content_sequence_name_CodeMeaning]
              content_sequence_value = [content_sequence_value_CodeValue, 
                                        content_sequence_value_CodingSchemeDesignator, 
                                        content_sequence_value_CodeMeaning]
              content_sequence_names.append(content_sequence_name)
              content_sequence_values.append(content_sequence_value)

      # if (group.reference_type.meaning == "Image Region"): # why meaning instead of CodeMeaning? 
      if (group.reference_type.value=="111030" and \
          group.reference_type.scheme_designator=="DCM" and \
          group.reference_type.meaning=="Image Region"):
        roi = group.roi # should exist if Image Region is present
        referenced_frame_of_reference_uid = group.roi.ReferencedFrameOfReferenceUID

        if (roi.GraphicType=="POINT"):
          extracted_data = roi.GraphicData 

      # append to poly_infos
      point_infos.append({
                         "TrackingIdentifier": tracking_identifier, 
                         "TrackingUID" : tracking_uid,
                         "FindingType": finding_type, 
                         "FindingSite": finding_sites,
                         "ReferencedFrameOfReferenceUID": referenced_frame_of_reference_uid, 
                        #  "QualitativeEvaluationNames": qual_eval_names, 
                        #  "QualitativeEvaluationValues": qual_eval_values, 
                         "ContentSequenceNames": content_sequence_names, 
                         "ContentSequenceValues": content_sequence_values,
                         "point": extracted_data 
                        })
      
    # create and display tableNode 
    tableNode = self.createPointTable(point_infos)

    return point_infos, tableNode 
  
  def extractLineMetadataToVtkTableNode(self, srFileName):

    """
    Extracts the point metadata from the SR using highdicom, 
    and creates a table node. 
    """

    # read SR using highdicom 
    sr = hd.sr.srread(srFileName)

    # get the referenced SeriesInstanceUID 
    referenced_series_instance_uid = sr.CurrentRequestedProcedureEvidenceSequence[0].ReferencedSeriesSequence[0].SeriesInstanceUID

    # will store the info needed for table too. 
    line_infos = [] 

    # First get the planar roi measurement gorups 
    groups = sr.content.get_planar_roi_measurement_groups()

    for group in groups: 

      # Get the tracking ids 
      tracking_identifier = group.tracking_identifier
      tracking_uid = group.tracking_uid

      # Get the findings and finding_sites 
      finding_type = [group.finding_type.CodeValue, group.finding_type.CodingSchemeDesignator, group.finding_type.CodeMeaning]
      finding_sites = []
      for finding_site in group.finding_sites:
        if hasattr(finding_site, 'ConceptCodeSequence') and finding_site.ConceptCodeSequence:
          finding_sites.append([finding_site.ConceptCodeSequence[0].CodeValue, 
                                finding_site.ConceptCodeSequence[0].CodingSchemeDesignator,
                                finding_site.ConceptCodeSequence[0].CodeMeaning])

      # if (group.reference_type.meaning == "Image Region"): # why meaning instead of CodeMeaning? 
      if (group.reference_type.value=="111030" and \
          group.reference_type.scheme_designator=="DCM" and \
          group.reference_type.meaning=="Image Region"):

        roi = group.roi # should exist if Image Region is present      
        try: 
          referenced_sop_instance_uid = roi.ContentSequence[0].referenced_sop_instance_uid
        except: 
          print('Cannot access referenced SOPInstanceUID')

        if (roi.GraphicType=="POLYLINE"):
          polyline = roi.GraphicData 
          extracted_data_type = roi.PixelOriginInterpretation # Could be frame, or volume, interpretation of points is different then! 
          # get the points 
          num_points = np.int32(len(polyline)/2)
          point_line = [] 
          for n in range(0,num_points): 
            pointx = polyline[(n*2)] 
            pointy = polyline[((n*2)+1)]
            pointz = self.getIPPFromSOP(referenced_sop_instance_uid,
                                        referenced_series_instance_uid)[2] 
            point_line.append([-pointx, -pointy, pointz]) # negate for display in Slicer 
          # append to poly_infos
          line_infos.append({
                            "TrackingIdentifier": tracking_identifier, 
                            "TrackingUID" : tracking_uid,
                            "SOPInstanceUID" : referenced_sop_instance_uid, 
                            "FindingType": finding_type, 
                            "FindingSite": finding_sites,
                            "polyline": point_line
                            })

    # create and display tableNode 
    tableNode = self.createPolylineTable(line_infos)

    return line_infos, tableNode 
   
  def create_2d_roi(self, loadable, center_ras, width, height, slice_normal=(0, 0, 1), thickness=1.0, bbox_name="2D_BoundingBox"):
    """
    Create a Markups ROI as a thin 2D bounding box on a specified slice plane.
    
    Args:
        loadable             - loadable of the corresponding SR 
        center_ras (tuple)   - (x, y, z) center in RAS coordinates.
        width (float)        - Width of the box (in mm).
        height (float)       - Height of the box (in mm).
        slice_normal (tuple) - Normal vector of the slice plane (e.g., (0,0,1) for axial).
        thickness (float)    - Depth of the box (in mm), small for a 2D box.
    
    Returns:
        vtkMRMLMarkupsROINode - The ROI node created.
    """
    # Create ROI node
    roi_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", bbox_name)
    self.addSeriesInSubjectHierarchy(loadable, roi_node)
    
    # Set the size (width, height, thickness)
    size = [width, height, thickness]
    roi_node.SetSize(size)
    
    # Set the center position
    roi_node.SetCenter(center_ras)
    
    # Align ROI orientation to slice normal
    transform_matrix = vtk.vtkMatrix4x4()
    
    # Build a local coordinate system with normal as Z
    z = np.array(slice_normal)
    z = z / np.linalg.norm(z)
    x = np.cross([0, 1, 0], z)
    if np.linalg.norm(x) < 1e-3:
        x = np.cross([1, 0, 0], z)
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)

    for i in range(3):
        transform_matrix.SetElement(i, 0, x[i])
        transform_matrix.SetElement(i, 1, y[i])
        transform_matrix.SetElement(i, 2, z[i])
        transform_matrix.SetElement(i, 3, center_ras[i])
    roi_node.SetAndObserveObjectToNodeMatrix(transform_matrix)

    # change size of glyph 
    display_node = roi_node.GetDisplayNode() 
    if (display_node):
        display_node.SetGlyphScale(1.0)
    
    return roi_node 

  def displayBboxMarkups(self, loadable, poly_infos): 
    """
    Displays the bounding box markups. 
    """

    # Order by IPP2 
    poly_infos = sorted(poly_infos, key=lambda x: x['center_z'])

    for i,p in enumerate(poly_infos):
      # get values 
      polyline = p['polyline']
      tracking_identifier = p['TrackingIdentifier']
      width = p['width']
      height = p['height']
      center_x = p['center_x'] # already negated 
      center_y = p['center_y'] # already negated 
      center_z = p['center_z']
      center_ras = np.asarray([center_x, center_y, center_z])
      bbox_name = tracking_identifier # for now 
      # create roi 
      self.create_2d_roi(loadable, center_ras, width, height, slice_normal=(0, 0, 1), thickness=1.0, bbox_name=bbox_name) 
      if (i==0):
        slicer.modules.markups.logic().JumpSlicesToLocation(center_x, center_y, center_z, True)

    return 
  
  def create_3d_point(self, loadable, point_index, point_x, point_y, point_z, point_text): 
    """
    Create the point markup 
    """

    markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", point_text)
    markupsNode.CreateDefaultDisplayNodes()
    markupsNode.SetLocked(True)
    markupsNode.AddControlPoint([point_x, point_y, point_z])
    markupsNode.SetName(point_text)
    markupsNode.SetNthControlPointLabel(point_index, point_text)

    self.addSeriesInSubjectHierarchy(loadable, markupsNode)

    # displayNode = markupsNode.GetDisplayNode()
    # displayNode.SetUseFiducialLabels(True)

    return 
  
  def displayPointMarkups(self, loadable, point_infos): 
    """
    Display the point markups. 
    """

    for i,p in enumerate(point_infos):
      point_text = p['TrackingIdentifier']
      point_x = -p['point'][0]
      point_y = -p['point'][1] 
      point_z = p['point'][2]
      self.create_3d_point(loadable, i, point_x, point_y, point_z, point_text)
      # jump to the first point 
      if (i==0):
        slicer.modules.markups.logic().JumpSlicesToLocation(point_x, point_y, point_z, True)
    
    return 
  
  def displayLineMarkups(self, loadable, line_infos):
    """
    Display the line markups. 
    """

    # # Get the subject hierarchy
    # shNode = slicer.modules.subjecthierarchy.logic().GetSubjectHierarchyNode()
    # # linesFolderID = shNode.CreateFolderItem(shNode.GetSceneItemID(), "lines") 
    # # get the StudyInstanceUID of the loadable 
    # dicomFilePath = loadable.files[0]  # Use the first file in the loadable
    # StudyInstanceUID = slicer.dicomDatabase.fileValue(dicomFilePath, "0020,000D") 
    # # Get the SeriesDescription of the loadable 
    # # SeriesDescription = slicer.dicomDatabase.fileValue(dicomFilePath, "0008,103E") # this is the SeriesDescription of the SR, need the reference. 
    # ReferencedSeriesInstanceUID =  slicer.dicomDatabase.fileValue(dicomFilePath,"referencedSeriesUID")
    # # for now 
    # SeriesDescription = ReferencedSeriesInstanceUID

    # # Get the studyNode 
    # studyNode = shNode.GetItemByUID(slicer.vtkMRMLSubjectHierarchyConstants.GetDICOMUIDName(), StudyInstanceUID)
    # # Now create the folder 
    # linesFolderID = shNode.CreateFolderItem(studyNode, 'lines for: ' + SeriesDescription)

    # Create all the line nodes 
    for i,p in enumerate(line_infos):
      line_text = p['TrackingIdentifier']
      polyline = p['polyline']
      # add new node 
      lineNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", line_text)
      self.addSeriesInSubjectHierarchy(loadable, lineNode)
      # get number of points 
      num_points = len(polyline)
      # add each as a control point 
      for n in range(0,num_points): 
        point_x = polyline[n][0] # already negated 
        point_y = polyline[n][1] # already negated 
        point_z = polyline[n][2]
        lineNode.AddControlPoint(point_x, point_y, point_z)
        # jump to the first line 
        if (i==0 and n==0):
          slicer.modules.markups.logic().JumpSlicesToLocation(point_x, point_y, point_z, True)
      # do not display the length measurement 
      lineNode.GetMeasurement('length').SetEnabled(False)
      # # Get the Subject Hierarchy item ID for the markup node
      # markupItemID = shNode.GetItemByDataNode(lineNode)
      # # Set the parent to the folder
      # shNode.SetItemParent(markupItemID, linesFolderID)

    return 

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
      
      # check if the plugin (tid1500reader) should be used or specialized highdicom code
      # sets the self.usePlugin = 0 or 1. 
      checkUsePlugin = self.checkUsePlugin(srFileName) 
      print('checkUsePlugin: ' + str(checkUsePlugin))

      # use plugin to read the SR 
      if (checkUsePlugin):

        param = {
          "inputSRFileName": srFileName,
          "metaDataFileName": outputFile,
          }

        try:
          tid1500reader = slicer.modules.tid1500reader
        except AttributeError as exc:
          logging.debug('Unable to find CLI module tid1500reader, unable to load SR TID1500 object: %s ' % str(exc))
          self.cleanup()
          return False

        cliNode = slicer.cli.run(tid1500reader, None, param, wait_for_completion=True)
        if cliNode.GetStatusString() != 'Completed':
          logging.debug('tid1500reader did not complete successfully, unable to load DICOM SR TID1500')
          self.cleanup()
          return False

        table = self.metadata2vtkTableNode(outputFile)
        if table:
          self.addSeriesInSubjectHierarchy(loadable, table)
          with open(outputFile, 'r') as srMetadataFile:
            srMetadataJSON = json.loads(srMetadataFile.read())
            table.SetName(srMetadataJSON["SeriesDescription"])

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

        self.loadAdditionalMeasurements(uid, loadable)

        self.cleanup()

      # use highdicom code to read the SR 
      else: 

        # check if contains a point, bbox, polyline 
        checkIfSRContainsBbox = self.checkIfSRContainsBbox(srFileName)
        checkIfSRContainsPoint = self.checkIfSRContainsPoint(srFileName)
        checkIfSRContainsPolyline = self.checkIfSRContainsPolyline(srFileName)

        # if bbox 
        if (checkIfSRContainsBbox): 
          print('SR contains bounding box')
          bboxInfo, bboxTableNode = self.extractBboxMetadataToVtkTableNode(srFileName)
          self.showTable(bboxTableNode)
          self.addSeriesInSubjectHierarchy(loadable, bboxTableNode)
          self.displayBboxMarkups(loadable, bboxInfo)

        # if point 
        if (checkIfSRContainsPoint):
            print('SR contains point')
            pointInfo, pointTableNode = self.extractPointMetadataToVtkTableNode(srFileName)
            self.showTable(pointTableNode)
            self.addSeriesInSubjectHierarchy(loadable, pointTableNode)
            self.displayPointMarkups(loadable, pointInfo)

        # if polyline but not bbox 
        if (checkIfSRContainsPolyline==1 and checkIfSRContainsBbox==0):
            print('SR contains a polyline but not a bbox')
            lineInfo, lineTableNode = self.extractLineMetadataToVtkTableNode(srFileName)
            self.showTable(lineTableNode)
            self.addSeriesInSubjectHierarchy(loadable, lineTableNode)
            self.displayLineMarkups(loadable, lineInfo)
            # create folder in subject hierarchy
            # shNode = slicer.modules.subjecthierarchy.logic().GetSubjectHierarchyNode()
            # linesDirectory = shNode.CreateFolderItem(shNode.GetSceneItemID(), "lines") # later use a better descriptor 
            # add markups to folder 
            # Get the Subject Hierarchy item ID for the markup node
            # markupItemID = shNode.GetItemByDataNode(markupNode)
            # Set the parent to the folder
            # shNode.SetItemParent(markupItemID, folderItemID)




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
      rwvmDataset = pydicom.read_file(rwvmFile)
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
      if "Measurements" not in data:
        # Invalid file, just return instead of throw an exception to allow loading
        # other data.
        return None

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

  def loadAdditionalMeasurements(self, srUID, loadable):
    """
    Loads length measements as annotation rulers
    TODO: need to generalize to other report contents
    """

    srFilePath = slicer.dicomDatabase.fileForInstance(srUID)
    sr = pydicom.read_file(srFilePath)

    if not self.isConcept(sr, "imagingMeasurementReport"):
      return sr

    contents = {}
    measurements = []
    contents['measurements'] = measurements
    for item in sr.ContentSequence:
      if self.isConcept(item, "personObserver"):
        contents['personObserver'] = item.PersonName
      if self.isConcept(item, "imagingMeasurements"):
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
      if not 'polyline' in measurement:
        # only polyline measurements are loaded as nodes
        continue

      markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode")
      markupsNode.SetName(str(contents['personObserver']))
      self.addSeriesInSubjectHierarchy(loadable, markupsNode)

      # Instead of calling markupsNode.SetLocked(True), lock each control point.
      # This allows interacting with the points but not change their position.
      slicer.modules.markups.logic().SetAllMarkupsLocked(markupsNode, True)

      colorIndex = 1 + slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLMarkupsLineNode')
      colorNode = slicer.mrmlScene.GetNodeByID("vtkMRMLColorTableNodeFileGenericAnatomyColors.txt")
      color = numpy.zeros(4)
      colorNode.GetColor(colorIndex, color)
      markupsNode.GetDisplayNode().SetSelectedColor(*color[:3])

      referenceFilePath = slicer.dicomDatabase.fileForInstance(measurement['referencedSOPInstanceUID'])
      if not referenceFilePath:
        raise Exception(f"Referenced image is not found in the database (referencedSOPInstanceUID={measurement['referencedSOPInstanceUID']}). Polyline point positions cannot be determined in 3D.")

      reference = pydicom.read_file(referenceFilePath)
      origin = numpy.array(reference.ImagePositionPatient)
      alongColumnVector = numpy.array(reference.ImageOrientationPatient[:3])
      alongRowVector = numpy.array(reference.ImageOrientationPatient[3:])
      alongColumnVector *= reference.PixelSpacing[1]
      alongRowVector *= reference.PixelSpacing[0]
      col1,row1,col2,row2 = measurement['polyline']
      lpsToRAS = numpy.array([-1,-1,1])
      p1 = (origin + col1 * alongColumnVector + row1 * alongRowVector) * lpsToRAS
      p2 = (origin + col2 * alongColumnVector + row2 * alongRowVector) * lpsToRAS
      markupsNode.AddControlPoint(vtk.vtkVector3d(p1))
      markupsNode.AddControlPoint(vtk.vtkVector3d(p2))

class DICOMLongitudinalTID1500PluginClass(DICOMTID1500PluginClass):

  def __init__(self):
    super(DICOMLongitudinalTID1500PluginClass, self).__init__()
    self.loadType = "Longitudinal DICOM Structured Report TID1500"

  def examineFiles(self, files):
    loadables = []

    for cFile in files:
      dataset = pydicom.read_file(cFile)

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
        tempDCM = pydicom.read_file(srFile)
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
