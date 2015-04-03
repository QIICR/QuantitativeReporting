

import unittest
# import slicer
from  __main__ import vtk, qt, ctk, slicer
import time
import os, sys
import logging

import DICOMLib # for loading a volume on AIM import

from SlicerReportingModuleWidgetHelper import SlicerReportingModuleWidgetHelper as Helper

initializedSegmentationVoxels = [10, 23, 44, 123]

class ReportingRoundTripTest(unittest.TestCase):
  def setUp(self):
    pass

  def test_RoundTrip(self):
    """
    Test fiducial round trip to and from AIM XML file on disk
    """

    logging.info("ctest, please don't truncate my output: CTEST_FULL_OUTPUT")

    # enter the module
    mainWindow = slicer.util.mainWindow()
    mainWindow.moduleSelector().selectModule('Reporting')

    # l = slicer.modulelogic.vtkSlicerReportingModuleLogic()
    l = slicer.modules.reporting.logic() 
    l.GUIHiddenOff()

    # testDataPath = os.path.normpath(os.path.join(os.path.realpath(__file__), "..", "..", "Prototype/TestData/DICOM.CT/")   
    logging.info("Reporting round trip test, current working directory = "+os.getcwd())
    testDataPath = os.path.join(os.getcwd(),"../../Testing/Temporary/DICOM.CT")
    # testDataPath = "/projects/birn/nicole/Slicer4/Reporting/Prototype/TestData/DICOM.CT"
    logging.info("test data path = "+testDataPath)
 
    # set up a new DICOM database
    logging.info("Creating a dicomDatabase!")
    ddb = ctk.ctkDICOMDatabase()
    if not ddb:
      logging.error("ERROR: failed to create a new dicom database!")
      return   
    dbpath = slicer.app.slicerHome + '/Testing/Temporary/TestingDCMDB/ctkDICOM.sql'
    logging.info('database path set to '+dbpath)
    if not os.path.exists(os.path.dirname(dbpath)):
      logging.info('Creating dir '+os.path.dirname(dbpath))
      os.makedirs(os.path.dirname(dbpath))
    ddb.openDatabase(dbpath,"ReportingTesting")
    if not ddb.isOpen:
      logging.error("ERROR: failed to open a new dicom database at path "+dbpath)
      return
    retval = ddb.initializeDatabase()
    if not retval:
      logging.error("ERROR: failed to init database")
      return

    l.InitializeDICOMDatabase(dbpath)

    testFileNames = []
    for n in [487, 488, 489]:
      filename = os.path.join(testDataPath, "instance_" + str(n) + ".dcm")
      logging.info("Adding file "+filename)
      testFileNames.append(filename)

    # check to see if the test data is already in it
    patients = ddb.patients()
    if len(patients) == 0:
      # add the files
      for filename in testFileNames:
        logging.info("Inserting file "+filename)
        retval = ddb.insert(filename)
      patients = ddb.patients()
      if len(patients) == 0:
        logging.error("ERROR: unable to add test files to database!"+str(testFileNames))
        return

    # get the UID for the series
    study = ddb.studiesForPatient(patients[0])
    series = ddb.seriesForStudy(study[0])
    seriesUID = series[0]
        
    # seriesUID = "1.2.392.200103.20080913.113635.2.2009.6.22.21.43.10.23432.1"
    # seriesUID = "2.16.840.1.114362.1.759508.1251415878280.192"
    # seriesUID = "1.3.12.2.1107.5.1.4.53031.30000011032906120157800000219"
    logging.info("For test, using the AIM sample volume with series UID of "+seriesUID)
    fileList = ddb.filesForSeries(seriesUID)
    logging.info("fileList = "+str(fileList))
    if not fileList:
      logging.error("ERROR: sample series with id "+seriesUID+" not found in database!")
      return

    # add a parameter node
    parameterNode = slicer.vtkMRMLScriptedModuleNode()
    parameterNode.SetModuleName('Reporting')
    slicer.mrmlScene.AddNode(parameterNode)
    # set it to be the active parameter node
    l.SetActiveParameterNodeID(parameterNode.GetID())

    #
    # create a new report, make it the report in the parameter node, set up hierarchy
    #
    reportNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLReportingReportNode")
    reportNode.SetReferenceCount(reportNode.GetReferenceCount() - 1)
    
    # set the color id
    colorID = 'vtkMRMLColorTableNodeFileGenericAnatomyColors.txt'
    reportNode.SetColorNodeID(colorID)
    reportNode.SetDICOMDatabaseFileName(dbpath)

    slicer.mrmlScene.AddNode(reportNode)
    parameterNode.SetParameter("reportID", reportNode.GetID())

    #
    # get some sample data from the database
    #
    volId = 1
    volumeNode = None
    volName = 'AIM volume '+str(volId)

    slicer.dicomDatabase = ddb
    scalarVolumePlugin = slicer.modules.dicomPlugins['DICOMScalarVolumePlugin']()
    scalarVolumeLoadables = scalarVolumePlugin.examine([fileList])
    volumeNode = scalarVolumePlugin.load(scalarVolumeLoadables[0])
    volumeNode.SetName(volName)

    logging.info("Adding to Report: Volume with id "+volumeNode.GetID())
    l.AddVolumeToReport(volumeNode)
    # set it on the report
    reportNode.SetVolumeNodeID(volumeNode.GetID())

    logging.info("adding a fiducial")

    #
    # define a fiducial
    #
    fidNode = slicer.vtkMRMLAnnotationFiducialNode()
    fidName = "AIM Round Trip Test Fiducial"
    fidNode.SetName(fidName)
    fidNode.SetSelected(1)
    fidNode.SetDisplayVisibility(1)
    fidNode.SetLocked(0)
    logging.info("Calling set fid coords")
    startCoords = [15.8, 70.8, -126.7]    
    fidNode.SetFiducialCoordinates(startCoords[0],startCoords[1],startCoords[2])
    logging.info("Starting fiducial coordinates: "+str(startCoords))
    # point it to the volume
    fidNode.SetAttribute("AssociatedNodeID", volumeNode.GetID())
    # point it to the report
    fidNode.SetAttribute("ReportingReportNodeID", reportNode.GetID())
    fidNode.SetScene(slicer.mrmlScene)
    logging.info("Adding text disp node")
    fidNode.CreateAnnotationTextDisplayNode()
    logging.info("Adding point display node")
    fidNode.CreateAnnotationPointDisplayNode()

    # slicer.mrmlScene.DebugOn()
    # l.DebugOn()
    slicer.mrmlScene.AddNode(fidNode) 
   
    logging.info("getting slice uid")
    uid = l.GetSliceUIDFromMarkUp(fidNode)
    logging.info("fidNode uid = "+uid)

    #
    # create a label volume
    #
    volumesLogic = slicer.modules.volumes.logic()
    labelNode = volumesLogic.CreateAndAddLabelVolume(slicer.mrmlScene, volumeNode, "Segmentation")
    labelDisplayNode = labelNode.GetDisplayNode()
    labelDisplayNode.SetAndObserveColorNodeID('vtkMRMLColorTableNodeFileGenericAnatomyColors.txt')
    l.AddNodeToReport(labelNode)

    # initialize image content
    labelImage = labelNode.GetImageData()
    extent = labelImage.GetExtent()
    pixelCounter = 0
    for k in range(extent[5]):
      for j in range(extent[3]):
        for i in range(extent[1]):
          if pixelCounter in initializedSegmentationVoxels:
            labelImage.SetScalarComponentFromFloat(i,j,k,0,1)
          else:
            labelImage.SetScalarComponentFromFloat(i,j,k,0,0)
          pixelCounter = pixelCounter + 1


    # test save to mrml
    # slicer.mrmlScene.SetURL('/spl/tmp/nicole/Testing/aim/RoundTripTest.mrml')
    # slicer.mrmlScene.Commit()

    #
    # output AIM XML
    #
    dirName = slicer.app.slicerHome + '/Testing/Temporary/'
    reportNode.SetStorageDirectoryName(dirName)

    logging.info("Saving report to "+dirName)
    retval = l.SaveReportToAIM(reportNode)

    if (retval != 0):
      logging.error("ERROR: unable to save report to aim file "+dirName+", retval="+retval)
    else:
      logging.info("Saved report to "+dirName+" in file "+reportNode.GetAIMFileName())

    self.assertEqual(retval, 0)

    logging.info("\n\n\nReloading aim file"+reportNode.GetAIMFileName())

    #
    # now clear the scene so can read in
    #
    # TBD: this causes a crash
    # slicer.mrmlScene.Clear(0)

    #
    # load in the aim file
    #
    newReport = slicer.mrmlScene.CreateNodeByClass("vtkMRMLReportingReportNode")
    newReport.SetReferenceCount(newReport.GetReferenceCount()-1)
    # set the default color map
    newReport.SetColorNodeID(colorID)
    newReport.SetDICOMDatabaseFileName(dbpath)
    slicer.mrmlScene.AddNode(newReport)
    parameterNode.SetParameter("reportID", newReport.GetID())

    Helper.LoadAIMFile(newReport.GetID(),reportNode.GetAIMFileName())

    # check the fiducial
    endCoords = [0,0,0]
    col = slicer.mrmlScene.GetNodesByClass("vtkMRMLAnnotationFiducialNode")
    col.SetReferenceCount(col.GetReferenceCount() - 1)

    # if the scene is not cleared, we should have 2 fiducials
    nFiducials = col.GetNumberOfItems()

    if nFiducials != 2:
      logging.error("Failed to read a fiducial from the saved report! Expect 2 in the non cleared scene, have " + str(nFiducials))
      self.assertTrue(False)
    
    f = col.GetItemAsObject(1)
    f.GetFiducialCoordinates(endCoords)

    logging.info("Start Coords = "+str(startCoords[0])+","+str(startCoords[1])+","+str(startCoords[2]))
    logging.info("End Coords = "+str(endCoords))

    xdiff = endCoords[0] - startCoords[0]
    ydiff = endCoords[1] - startCoords[1]
    zdiff = endCoords[2] - startCoords[2]
    diffTotal = xdiff + ydiff + zdiff

    logging.info("Difference between coordinates after loaded the aim file and value from before stored the aim file: "+str(xdiff)+","+str(ydiff)+","+str(zdiff)+". Total difference = "+str(diffTotal))

    if diffTotal > 0.1:
      logging.error("Fiducial coordinates error exceeds the allowed bounds")
      self.assertTrue(False)


    # check the label node
    sceneVolumes = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode")
    sceneVolumes.SetReferenceCount(sceneVolumes.GetReferenceCount() - 1)

    sceneLabels = []

    for i in range(sceneVolumes.GetNumberOfItems()):
      vol = sceneVolumes.GetItemAsObject(i)
      if vol.GetLabelMap():
        sceneLabels.append(vol)

    if len(sceneLabels) != 2:
      logging.error("Scene does not have two label nodes after reloading from AIM!")
      self.assertTrue(False)

    newLabelNode = sceneLabels[1]
    newLabelImage = newLabelNode.GetImageData()
    extent = newLabelImage.GetExtent()
    pixelCounter = 0
    for k in range(extent[5]):
      for j in range(extent[3]):
        for i in range(extent[1]):
          pixel = newLabelImage.GetScalarComponentAsFloat(i,j,k,0)
          if ((pixelCounter in initializedSegmentationVoxels) and pixel != 1) or (not(pixelCounter in initializedSegmentationVoxels) and pixel != 0):
            logging.error("Segmentation content not recovered correctly!")
            logging.error("Pixel counter "+str(pixelCounter)+" is set to "+str(pixel))
            self.assertTrue(False)
          pixelCounter = pixelCounter + 1

    self.assertTrue(True)
