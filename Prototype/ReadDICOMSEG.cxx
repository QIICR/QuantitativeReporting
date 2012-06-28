// DCMTK includes
#include <dcmtk/dcmdata/dcmetinf.h>
#include <dcmtk/dcmdata/dcfilefo.h>
#include <dcmtk/dcmdata/dcuid.h>
#include <dcmtk/dcmdata/dcdict.h>
#include <dcmtk/dcmdata/cmdlnarg.h>
#include <dcmtk/ofstd/ofconapp.h>
#include <dcmtk/ofstd/ofstd.h>
#include <dcmtk/ofstd/ofdatime.h>
#include <dcmtk/dcmdata/dcuid.h>         /* for dcmtk version name */
#include <dcmtk/dcmdata/dcdeftag.h>      /* for DCM_StudyInstanceUID */
#include <dcmtk/dcmdata/dcvrda.h>        /* for DcmDate */
#include <dcmtk/dcmdata/dcvrtm.h>        /* for DcmTime */
#include <dcmtk/dcmdata/dcvrat.h>        /* for DcmAttribute */
#include <dcmtk/dcmdata/dctagkey.h>        /* for DcmTagKey */


// Slicer
#include "vtkMRMLScene.h"
#include "vtkMRMLScalarVolumeNode.h"
#include "vtkMRMLVolumeArchetypeStorageNode.h"
#include "vtkMRMLScalarVolumeNode.h"
#include "vtkSmartPointer.h"
#include "vtkMatrix4x4.h"

// CTK
#include "ctkDICOMDatabase.h"

// Qt
#include <QSqlQuery>

// VTK
#include <vtkImageData.h>

ctkDICOMDatabase* InitializeDICOMDatabase(const char*);

/* 
 * Take single DICOM segmentation object file, initialize a label volume node
 * to keep the content label and add it to the scene.
 *
 * Assume there is only one label, and that segmentation is always represented
 * as a multiframe, geometry of the segmented label coincides with the
 * geometry of the referenced frames (SourceImageSequence must be present
 * in the SharedFunctionalGroup sequence), the referenced UIDs must be present
 * in the DICOM database.
 *
 * Input: DICOM SEG object and a Slicer scene.
 *
 */


int main(int argc, char** argv)
{
    if(argc<4)
      {
      std::cerr << "Usage: " << argv[0] << " DICOM_SEG_name Slicer_scene_name DICOM_DB_path" << std::endl;
      std::cerr << "  It is expected that local DICOM DB has the referenced UIDs" << std::endl;
      return 0;
      }
      
    // Step 1: load the input DICOM, find the referenced frames in the DICOM db
    DcmFileFormat fileFormat;
    DcmDataset *segDataset;
    OFCondition status = fileFormat.loadFile(argv[1]);
    if(status.good())
      {
      std::cout << "Loaded dataset for " << argv[1] << std::endl;
      segDataset = fileFormat.getAndRemoveDataset();
      }
 
    // No go if this is not a SEG modality
      {
      DcmElement *el;
      char* str;
      OFCondition status =
        segDataset->findAndGetElement(DCM_SOPClassUID, el);
      if(status.bad())
        {
        std::cout << "Failed to get class UID" << std::endl;
        return -1;
        }
      status = el->getString(str);
      if(status.bad())
        return -1;
      if(strcmp(str, UID_SegmentationStorage))
        {
        std::cerr << "Input DICOM should be a SEG object!" << std::endl;
        return -1;
        }
      }

    // Step 2: get the UIDs of the source sequence to initialize the geometry
    std::vector<std::string> referenceFramesUIDs;
    {
      DcmItem *item1, *item2, *item3;
      DcmElement *el;
      OFCondition status;
      char* str;
      status = segDataset->findAndGetSequenceItem(DCM_SharedFunctionalGroupsSequence, item1);
      if(status.bad())
        return -2;
      status = item1->findAndGetSequenceItem(DCM_DerivationImageSequence, item2);
      if(status.bad())
        return -2;
      //status = item2->findAndGetSequenceItem(DCM_SourceImageSequence, item3);
      // TODO: how to get the number of items in sequence?
      for(int i=0;;i++)
      {
        status = item2->findAndGetSequenceItem(DCM_SourceImageSequence, item3, i);
        if(status.bad())
          break;
        status = item3->findAndGetElement(DCM_ReferencedSOPInstanceUID, el);
        if(status.bad())
          return -3;
        status = el->getString(str);
        if(status.bad())
          return -4;
        std::cout << "Next UID: " << str << std::endl;
        referenceFramesUIDs.push_back(str);
      }
    }

  std::cout << referenceFramesUIDs.size() << " reference UIDs found" << std::endl;

  ctkDICOMDatabase *db = InitializeDICOMDatabase(argv[3]);
  if(!db)
    {
    std::cerr << "Failed to initialize DICOM db!" << std::endl;
    return -1;
    }

  std::vector<std::string> framesFileList;
  std::cout << "Reference file names: " << std::endl;
  vtkSmartPointer<vtkMRMLVolumeArchetypeStorageNode> sNode = vtkSmartPointer<vtkMRMLVolumeArchetypeStorageNode>::New();
  sNode->ResetFileNameList();

  for(std::vector<std::string>::const_iterator uidIt=referenceFramesUIDs.begin();
    uidIt!=referenceFramesUIDs.end();++uidIt)
    {
    QSqlQuery query(db->database());
    query.prepare("SELECT Filename FROM Images WHERE SOPInstanceUID=?");
    query.bindValue(0, QString((*uidIt).c_str()));
    query.exec();
    if(query.next())
      {
      QString fileName = query.value(0).toString();
      DcmFileFormat fileFormat;
      char *frameFileName = fileName.toLatin1().data();
      framesFileList.push_back(frameFileName);
      std::cout << frameFileName << std::endl;
      sNode->AddFileName(frameFileName);
      if(uidIt == referenceFramesUIDs.begin())
        sNode->SetFileName(frameFileName);
      }
    else
      {
      std::cerr << "Failed to get file pointer from DICOM db!" << std::endl;
      return -1;
      }
    }


  vtkSmartPointer<vtkMRMLScalarVolumeNode> vNode = vtkSmartPointer<vtkMRMLScalarVolumeNode>::New();
  sNode->SetSingleFile(0);
  sNode->ReadData(vNode);

  std::cout << "Read succeeded!" << std::endl;

  // Step 3: read in the scene
  vtkSmartPointer<vtkMRMLScene> scene = vtkSmartPointer<vtkMRMLScene>::New();
  scene->SetURL(argv[2]);
  if(!scene->Import())
    {
    std::cerr << "Error loading the scene!" << std::endl;
    return -1;
    }
  std::cout << "Test scene loaded!" << std::endl;

  vNode->SetScene(scene);
  vtkIndent indent;

  std::cout << "Volume node read: " << std::endl;
  vNode->PrintSelf(std::cout, indent);

  // Step 4: Initialize the image
  const Uint8 *pixelArray;
    {
    unsigned long count;
    const DcmTagKey pdTag = DCM_PixelData;
    OFCondition status = 
      segDataset->findAndGetUint8Array(pdTag, pixelArray, &count, false);
    if(!status.good())
      return -5;
    std::cout << "Pixel array length is " << count << std::endl;

    }

  vtkImageData *imageData = vNode->GetImageData();
  int extent[6];
  imageData->GetExtent(extent);

  int total = 0;
  for(int k=0;k<extent[5]+1;k++)
    {
    for(int j=0;j<extent[3]+1;j++)
      {
      for(int i=0;i<extent[1]+1;i++)
        {
        int byte = total/8, bit = total % 8;
        int value = (pixelArray[byte] >> bit) & 1;
        imageData->SetScalarComponentFromFloat(i,j,k,0,value);
        total++;
        }
      }
    }

  sNode->SetFileName("seg.nrrd");
  sNode->SetWriteFileFormat("nrrd");
  sNode->SetURI(NULL);
  sNode->WriteData(vNode);

  return 0;

}

ctkDICOMDatabase* InitializeDICOMDatabase(const char* dbPath)
{
    std::cout << "Reporting will use database in " << dbPath << std::endl;
    ctkDICOMDatabase* DICOMDatabase = new ctkDICOMDatabase();
    DICOMDatabase->openDatabase(dbPath,"Reporting");
    if(DICOMDatabase->isOpen())
      return DICOMDatabase;
    return NULL;
}


#if 0

    vtkSmartPointer<vtkMRMLScene> scene = vtkSmartPointer<vtkMRMLScene>::New();
    scene->SetURL(argv[1]);
    if(!scene->Import())
      {
      std::cerr << "Error loading the scene!" << std::endl;
      return -1;
      }
    std::cout << "Test scene loaded!" << std::endl;

    vtkSmartPointer<vtkMRMLScalarVolumeNode> vol = 
      vtkMRMLScalarVolumeNode::SafeDownCast(scene->GetNodeByID("vtkMRMLScalarVolumeNode1"));

    vtkSmartPointer<vtkMRMLScalarVolumeNode> labelNode = 
      vtkMRMLScalarVolumeNode::SafeDownCast(scene->GetNodeByID("vtkMRMLScalarVolumeNode2"));
    vtkImageData* labelImage = labelNode->GetImageData();
    int extent[6];
    labelImage->GetExtent(extent);

    ctkDICOMDatabase *db = InitializeDICOMDatabase();
    if(!db)
      {
      std::cerr << "Failed to initialize DICOM db!" << std::endl;
      return -1;
      }

    // create a DICOM dataset (see
    // http://support.dcmtk.org/docs/mod_dcmdata.html#Examples)
    std::string uidsString = vol->GetAttribute("DICOM.instanceUIDs");
    std::vector<std::string> uidVector;
    std::vector<DcmDataset*> dcmDatasetVector;
    char *uids = new char[uidsString.size()+1];
    strcpy(uids,uidsString.c_str());
    char *ptr;
    ptr = strtok(uids, " ");
    while (ptr != NULL)
      {
      std::cout << "Parsing UID = " << ptr << std::endl;
      uidVector.push_back(std::string(ptr));
      ptr = strtok(NULL, " ");
      }

    for(std::vector<std::string>::const_iterator uidIt=uidVector.begin();
      uidIt!=uidVector.end();++uidIt)
      {
      QSqlQuery query(db->database());
      query.prepare("SELECT Filename FROM Images WHERE SOPInstanceUID=?");
      query.bindValue(0, QString((*uidIt).c_str()));
      query.exec();
      if(query.next())
        {
        QString fileName = query.value(0).toString();
        DcmFileFormat fileFormat;
        OFCondition status = fileFormat.loadFile(fileName.toLatin1().data());
        if(status.good())
          {
          std::cout << "Loaded dataset for " << fileName.toLatin1().data() << std::endl;
          dcmDatasetVector.push_back(fileFormat.getAndRemoveDataset());
          //DcmElement *element;
          //OFCondition res = fileFormat.getDataset()->findAndGetElement(DCM_SOPClassUID, element);
          //std::cout << "findAndGetElement is ok" << std::endl;
          }
        else
          {
          std::cerr << "Failed to query the database! Exiting." << std::endl;
          return -1;
          }
        }
      }

    std::cout << "DcmDatasetVector size: " << dcmDatasetVector.size() << std::endl;

    std::cout << "Deriving image orientation" << std::endl;

    // Get the image orientation information
    vtkSmartPointer<vtkMatrix4x4> IJKtoRAS = vtkSmartPointer<vtkMatrix4x4>::New();
    vtkSmartPointer<vtkMatrix4x4> RAStoIJK = vtkSmartPointer<vtkMatrix4x4>::New();
    vtkSmartPointer<vtkMatrix4x4> RAStoLPS = vtkSmartPointer<vtkMatrix4x4>::New();
    vtkSmartPointer<vtkMatrix4x4> IJKtoLPS = vtkSmartPointer<vtkMatrix4x4>::New();
    double spacing[3], origin[3], colDir[3], rowDir[3];

    labelNode->GetRASToIJKMatrix(RAStoIJK);
    vtkMatrix4x4::Invert(RAStoIJK, IJKtoRAS);
    IJKtoRAS->Transpose();

    for(int i=0;i<3;i++)
      {
      spacing[i]=0;
      for(int j=0;j<3;j++)
        {
        spacing[i]+=IJKtoRAS->GetElement(i,j)*IJKtoRAS->GetElement(i,j);
        }
      if(spacing[i]==0.)
        spacing[i] = 1.;
      spacing[i]=sqrt(spacing[i]);
      }

    for(int i=0;i<3;i++)
      {
      for(int j=0;j<3;j++)
        {
        IJKtoRAS->SetElement(i, j, IJKtoRAS->GetElement(i,j)/spacing[i]);
        }
      }

    RAStoLPS->Identity();
    RAStoLPS->SetElement(0,0,-1);
    RAStoLPS->SetElement(1,1,-1);
    vtkMatrix4x4::Multiply4x4(IJKtoRAS, RAStoLPS, IJKtoLPS);

    origin[0] = IJKtoLPS->GetElement(3,0);
    origin[1] = IJKtoLPS->GetElement(3,1);
    origin[2] = IJKtoLPS->GetElement(3,2);

    colDir[0] = IJKtoLPS->GetElement(0,0);
    colDir[1] = IJKtoLPS->GetElement(0,1);
    colDir[2] = IJKtoLPS->GetElement(0,2);

    rowDir[0] = IJKtoLPS->GetElement(1,0);
    rowDir[1] = IJKtoLPS->GetElement(1,1);
    rowDir[2] = IJKtoLPS->GetElement(1,2);

    // Patient orientation definition:
    //   http://dabsoft.ch/dicom/3/C.7.6.1.1.1/

    char patientOrientationStr[64];
    sprintf(patientOrientationStr, "%f\\%f\\%f\\%f\\%f\\%f",
      IJKtoLPS->GetElement(0,0), IJKtoLPS->GetElement(1,0),
      IJKtoLPS->GetElement(2,0), IJKtoLPS->GetElement(0,1),
      IJKtoLPS->GetElement(1,1), IJKtoLPS->GetElement(2,1));

    char patientPositionStr[64];
    sprintf(patientPositionStr, "%f\\%f\\%f",
      origin[0], origin[1], origin[2]);

    char pixelSpacingStr[64];
    sprintf(pixelSpacingStr, "%f\\%f",
      spacing[0], spacing[1]);

    char sliceThicknessStr[64];
    sprintf(sliceThicknessStr, "%f",
      spacing[2]);


    std::cout << "Creating the dataset" << std::endl;
    // create a DICOM dataset (see
    // http://support.dcmtk.org/docs/mod_dcmdata.html#Examples)
    DcmDataset *dcm0 = dcmDatasetVector[0];

    DcmFileFormat fileformatOut;
    DcmDataset *dataset = fileformatOut.getDataset(), *datasetIn;
    
    // writeSegHeader
    //
    // Patient IE
    //  Patient module
    copyDcmElement(DCM_PatientName, dcm0, dataset);
    copyDcmElement(DCM_PatientID, dcm0, dataset);
    copyDcmElement(DCM_PatientBirthDate, dcm0, dataset);
    copyDcmElement(DCM_PatientSex, dcm0, dataset);
 
    // Study IE
    //  General Study module
    copyDcmElement(DCM_StudyInstanceUID, dcm0, dataset);
    copyDcmElement(DCM_StudyDate, dcm0, dataset);
    copyDcmElement(DCM_StudyTime, dcm0, dataset);
    copyDcmElement(DCM_ReferringPhysicianName, dcm0, dataset);
    copyDcmElement(DCM_StudyID, dcm0, dataset);
    dataset->putAndInsertString(DCM_StudyID, "1"); // David Clunie: should be initialized (not required, but good idea)
    copyDcmElement(DCM_AccessionNumber, dcm0, dataset);

    OFString contentDate, contentTime;    // David Clunie: must be present and initialized
    DcmDate::getCurrentDate(contentDate);
    DcmTime::getCurrentTime(contentTime);
    dataset->putAndInsertString(DCM_ContentDate, contentDate.c_str());
    dataset->putAndInsertString(DCM_ContentTime, contentTime.c_str());

    // Series IE
    //  General Series module
    dataset->putAndInsertString(DCM_Modality,"SEG");
    char uid[128];
    char *seriesUIDStr = dcmGenerateUniqueIdentifier(uid, SITE_SERIES_UID_ROOT);
    dataset->putAndInsertString(DCM_SeriesInstanceUID,seriesUIDStr);
    
    //  Segmentation Series module 
    dataset->putAndInsertString(DCM_SeriesNumber,"1000");

    // Frame Of Reference IE
    dataset->putAndInsertString(DCM_FrameOfReferenceUID, seriesUIDStr);
    dataset->putAndInsertString(DCM_PositionReferenceIndicator, ""); // David Clunie: must be present, may be empty
    
    // Equipment IE
    //  General Equipment module
    dataset->putAndInsertString(DCM_Manufacturer, "3D Slicer Community");

    //  Enhanced General Equipment module
    dataset->putAndInsertString(DCM_ManufacturerModelName, "AndreyTestDICOMSegWriter v.0.0.1");
    dataset->putAndInsertString(DCM_DeviceSerialNumber, "0.0.1");
    dataset->putAndInsertString(DCM_SoftwareVersions, "0.0.1");

    // Segmentation IE

    dataset->putAndInsertString(DCM_InstanceNumber,"1");
    dataset->putAndInsertString(DCM_InstanceNumber,"1");
    dataset->putAndInsertUint16(DCM_FileMetaInformationVersion,0x0001);
    dataset->putAndInsertString(DCM_SOPClassUID, UID_SegmentationStorage);

    //  General Image module
    dataset->putAndInsertString(DCM_InstanceNumber, "1");
    dataset->putAndInsertString(DCM_SOPInstanceUID, dcmGenerateUniqueIdentifier(uid, SITE_INSTANCE_UID_ROOT));
    dataset->putAndInsertString(DCM_ImageType,"DERIVED\\PRIMARY");

    dataset->putAndInsertString(DCM_InstanceCreatorUID,OFFIS_UID_ROOT);


    //  Image Pixel module
    dataset->putAndInsertString(DCM_SamplesPerPixel,"1");
    dataset->putAndInsertString(DCM_PhotometricInterpretation,"MONOCHROME2");

    char buf[16] = {0};
    sprintf(buf,"%d", extent[1]+1);
    dataset->putAndInsertString(DCM_Columns,buf);
    sprintf(buf,"%d", extent[3]+1);
    dataset->putAndInsertString(DCM_Rows,buf);
 
    dataset->putAndInsertString(DCM_BitsAllocated,"1"); // XIP: 8
    dataset->putAndInsertString(DCM_BitsStored,"1"); // XIP: 8
    dataset->putAndInsertString(DCM_HighBit,"0");
    dataset->putAndInsertString(DCM_PixelRepresentation,"0");

    sprintf(buf,"%d", extent[5]+1);
    dataset->putAndInsertString(DCM_NumberOfFrames,buf);


    dataset->putAndInsertString(DCM_LossyImageCompression,"00");

    // writeSegFrames
    //dataset->putAndInsertString(DCM_ImageOrientationPatient, patientOrientationStr);
    //dataset->putAndInsertString(DCM_ImagePositionPatient, patientPositionStr);
    dataset->putAndInsertString(DCM_PixelSpacing, pixelSpacingStr);
    dataset->putAndInsertString(DCM_SliceThickness, sliceThicknessStr);

    //   Segmentation Image module
    dataset->putAndInsertString(DCM_SegmentationType, "BINARY");
    dataset->putAndInsertString(DCM_ContentLabel, "ROI"); // CS
    dataset->putAndInsertString(DCM_ContentDescription, "3D Slicer segmentation result");
    dataset->putAndInsertString(DCM_ContentCreatorName, "3DSlicer");

    // segment sequence [0062,0002]
    DcmItem *Item = NULL, *subItem = NULL, *subItem2 = NULL, *subItem3 = NULL;
    dataset->findOrCreateSequenceItem(DCM_SegmentSequence, Item);

    // AF TODO: go over all labels and insert separate item for each one
    Item->putAndInsertString(DCM_SegmentNumber, "1");
    Item->putAndInsertString(DCM_SegmentLabel, "Segmentation"); // AF TODO: this should be initialized based on the label value!
    Item->putAndInsertString(DCM_SegmentAlgorithmType, "SEMIAUTOMATIC");
    Item->putAndInsertString(DCM_SegmentAlgorithmName, "Editor");

    // general anatomy mandatory macro
    Item->findOrCreateSequenceItem(DCM_AnatomicRegionSequence, subItem);
    subItem->putAndInsertString(DCM_CodeValue, "T-D0050");
    subItem->putAndInsertString(DCM_CodingSchemeDesignator,"SRT");
    subItem->putAndInsertString(DCM_CodeMeaning,"Tissue");

    //segmentation properties - category
    Item->findOrCreateSequenceItem(DCM_SegmentedPropertyCategoryCodeSequence, subItem);
    subItem->putAndInsertString(DCM_CodeValue,"T-D0050");
    subItem->putAndInsertString(DCM_CodingSchemeDesignator,"SRT");
    subItem->putAndInsertString(DCM_CodeMeaning,"Tissue");

    //segmentation properties - type
    Item->findOrCreateSequenceItem(DCM_SegmentedPropertyTypeCodeSequence, subItem);
    subItem->putAndInsertString(DCM_CodeValue,"M-03010");
    subItem->putAndInsertString(DCM_CodingSchemeDesignator,"SRT");
    subItem->putAndInsertString(DCM_CodeMeaning,"Nodule");

    //  Multi-frame Functional Groups Module
    //   Shared functional groups sequence
    std::cout << "Before initializing SharedFunctionalGroupsSequence" << std::endl;
    dataset->findOrCreateSequenceItem(DCM_SharedFunctionalGroupsSequence, Item);
    Item->findOrCreateSequenceItem(DCM_DerivationImageSequence, subItem);
    const unsigned long itemNum = extent[5];
    for(int i=0;i<itemNum+1;i++)
      {

      subItem->findOrCreateSequenceItem(DCM_SourceImageSequence, subItem2, i);
      char *str;
      DcmElement *element;
      DcmDataset *dataset = dcmDatasetVector[i];
      dataset->findAndGetElement(DCM_SOPClassUID, element, i);
      element->getString(str);
      subItem2->putAndInsertString(DCM_ReferencedSOPClassUID, str);
      dataset->findAndGetElement(DCM_SOPInstanceUID, element);
      element->getString(str);
      subItem2->putAndInsertString(DCM_ReferencedSOPInstanceUID, str);
      subItem2->putAndInsertString(DCM_ReferencedFrameNumber, "1");

      subItem2->findOrCreateSequenceItem(DCM_PurposeOfReferenceCodeSequence, subItem3);
      subItem3->putAndInsertString(DCM_CodeValue, "121322");
      subItem3->putAndInsertString(DCM_CodingSchemeDesignator, "DCM");
      subItem3->putAndInsertString(DCM_CodeMeaning, "Source image for image processing operation");

      }
    
    subItem->findOrCreateSequenceItem(DCM_DerivationCodeSequence, subItem2);
    subItem2->putAndInsertString(DCM_CodeValue, "113076");
    subItem2->putAndInsertString(DCM_CodingSchemeDesignator, "DCM");
    subItem2->putAndInsertString(DCM_CodeMeaning, "Segmentation");

      {
      // Elements identical for each frame should be in shared group
      char buf[64], *str;
      DcmElement *element;
      dcmDatasetVector[0]->findAndGetElement(DCM_ImageOrientationPatient, element);
      element->getString(str);
      Item->findOrCreateSequenceItem(DCM_PlaneOrientationSequence, subItem);
      subItem->putAndInsertString(DCM_ImageOrientationPatient, str);

      Item->findOrCreateSequenceItem(DCM_PixelMeasuresSequence, subItem);
      subItem->putAndInsertString(DCM_SliceThickness, sliceThicknessStr);
      subItem->putAndInsertString(DCM_PixelSpacing, pixelSpacingStr);
      }

    /*
    //segmentation macro - attributes
    Item->findOrCreateSequenceItem(DCM_SegmentIdentificationSequence, subItem);
    subItem->putAndInsertString(DCM_ReferencedSegmentNumber,"1");

    //segmentation functional group macros
    Item->putAndInsertString(DCM_SliceThickness, sliceThicknessStr);
    Item->putAndInsertString(DCM_PixelSpacing, pixelSpacingStr);
    */


    //Derivation Image functional group
    for(int i=0;i<itemNum+1;i++)
      {
      dataset->findOrCreateSequenceItem(DCM_PerFrameFunctionalGroupsSequence, Item, i);

      char buf[64], *str;
      DcmElement *element;

      Item->findOrCreateSequenceItem(DCM_FrameContentSequence, subItem);
      subItem->putAndInsertString(DCM_StackID, "1");
      sprintf(buf, "%d", i+1);
      subItem->putAndInsertString(DCM_InStackPositionNumber, buf);
      sprintf(buf, "1\\%d", i+1); 
      subItem->putAndInsertString(DCM_DimensionIndexValues, buf);
      
      dcmDatasetVector[i]->findAndGetElement(DCM_ImagePositionPatient, element);
      element->getString(str);
      Item->findOrCreateSequenceItem(DCM_PlanePositionSequence, subItem);
      subItem->putAndInsertString(DCM_ImagePositionPatient, str);

      /* David Clunie: items that are identical should not be shared per-frame
      dcmDatasetVector[i]->findAndGetElement(DCM_ImageOrientationPatient, element);
      element->getString(str);
      Item->findOrCreateSequenceItem(DCM_PlaneOrientationSequence, subItem);
      subItem->putAndInsertString(DCM_ImageOrientationPatient, str);

      Item->findOrCreateSequenceItem(DCM_PixelMeasuresSequence, subItem);
      subItem->putAndInsertString(DCM_SliceThickness, sliceThicknessStr);
      subItem->putAndInsertString(DCM_PixelSpacing, pixelSpacingStr);
      */

      Item->findOrCreateSequenceItem(DCM_SegmentIdentificationSequence, subItem);
      subItem->putAndInsertString(DCM_ReferencedSegmentNumber, "1");

      /*
      DcmDataset *sliceDataset = dcmDatasetVector[i];
      char *str;
      DcmElement *element;
      sliceDataset->findAndGetElement(DCM_SOPClassUID, element);
      element->getString(str);
      subItem->putAndInsertString(DCM_SOPClassUID, str);

      sliceDataset->findAndGetElement(DCM_SOPInstanceUID, element);
      element->getString(str);
      subItem->putAndInsertString(DCM_SOPInstanceUID, str);
      */
      }


    // Multi-frame Dimension module
      {
      dataset->findOrCreateSequenceItem(DCM_DimensionOrganizationSequence, Item);
      char dimensionuid[128];
      char *dimensionUIDStr = dcmGenerateUniqueIdentifier(dimensionuid, SITE_SERIES_UID_ROOT);
      Item->putAndInsertString(DCM_DimensionOrganizationUID, dimensionUIDStr);

      dataset->findOrCreateSequenceItem(DCM_DimensionIndexSequence, Item, 0);

      Item->putAndInsertString(DCM_DimensionOrganizationUID, dimensionUIDStr);

      DcmAttributeTag dimAttr(DCM_StackID);
      Uint16 *dimAttrArray = new Uint16[2];

      dimAttr.putTagVal(DCM_StackID);
      dimAttr.getUint16Array(dimAttrArray);
      Item->putAndInsertUint16Array(DCM_DimensionIndexPointer, dimAttrArray, 1);

      dimAttr.putTagVal(DCM_FrameContentSequence);
      dimAttr.getUint16Array(dimAttrArray);
      Item->putAndInsertUint16Array(DCM_FunctionalGroupPointer, dimAttrArray, 1);

      dataset->findOrCreateSequenceItem(DCM_DimensionIndexSequence, Item, 1);

      Item->putAndInsertString(DCM_DimensionOrganizationUID, dimensionUIDStr);

      dimAttr.putTagVal(DCM_InStackPositionNumber);
      dimAttr.getUint16Array(dimAttrArray);
      Item->putAndInsertUint16Array(DCM_DimensionIndexPointer, dimAttrArray, 1);

      dimAttr.putTagVal(DCM_FrameContentSequence);
      dimAttr.getUint16Array(dimAttrArray);
      Item->putAndInsertUint16Array(DCM_FunctionalGroupPointer, dimAttrArray, 1);

      //delete [] dimAttrArray;
      }


    /*
    // per-frame functional groups
    dataset->findOrCreateSequenceItem(DCM_PerFrameFunctionalGroupsSequence, Item, itemNum);
	
    for (int i=0;i<itemNum+1;i++)
      {
      char buf[64];

      // get ImagePositionPatient and ImageOrientationPatient from the
      // original DICOM
      char *str, *orientation, *position;
      DcmElement *element;
      dcmDatasetVector[i]->findAndGetElement(DCM_ImagePositionPatient, element);
      element->getString(position);
      std::cout << "Read position patient: " << position << std::endl;
      dcmDatasetVector[i]->findAndGetElement(DCM_ImageOrientationPatient, element);
      element->getString(orientation);
      std::cout << "Read orientation patient: " << orientation << std::endl;


      dataset->findAndGetSequenceItem(DCM_PerFrameFunctionalGroupsSequence,Item,i);

      Item->findOrCreateSequenceItem(DCM_FrameContentSequence, subItem);
      subItem->putAndInsertString(DCM_StackID,"1"); 

      sprintf(buf, "%d", i+1);
      subItem->putAndInsertString(DCM_InStackPositionNumber,buf);

      DcmItem *seqItem = NULL;

      sprintf(buf, "%f\\%f\\%f", origin[0], origin[1], origin[2]+i*spacing[2]);
      Item->findOrCreateSequenceItem(DCM_PlanePositionSequence, seqItem, -2);
      seqItem->putAndInsertString(DCM_ImagePositionPatient, position);

      sprintf(buf, "%f\\%f\\%f\\%f\\%f\\%f", colDir[0], colDir[1], colDir[2], rowDir[0], rowDir[1], rowDir[2]);
      Item->findOrCreateSequenceItem(DCM_PlaneOrientationSequence, seqItem, -2);
      seqItem->putAndInsertString(DCM_ImageOrientationPatient, orientation);

      Item->findOrCreateSequenceItem(DCM_PixelMeasuresSequence, seqItem, -2);
      seqItem->putAndInsertString(DCM_SliceThickness, sliceThicknessStr);
      seqItem->putAndInsertString(DCM_PixelSpacing, pixelSpacingStr);

      }//Per-Frame Functional Groups Sequence information

    */

    // pixel data
    //
    std::cout << "Preparing pixel data" << std::endl;
    int nbytes = (int) (float((extent[1]+1)*(extent[3]+1)*(extent[5]+1))/8.);
    int total = 0;
    unsigned char *pixelArray = new unsigned char[nbytes];
    for(int i=0;i<nbytes;i++)
      pixelArray[i] = 0;

    for(int i=0;i<extent[1]+1;i++)
      {
      for(int j=0;j<extent[3]+1;j++)
        {
        for(int k=0;k<extent[5]+1;k++)
          {
          int byte = total / 8, bit = total % 8;
          total++;
          pixelArray[byte] |= ((unsigned char) labelImage->GetScalarComponentAsFloat(i,j,k,0)) << bit;
          }
        }
      }

    
    dataset->putAndInsertUint8Array(DCM_PixelData, pixelArray, nbytes);//write pixels

    delete [] pixelArray;

    OFCondition status = fileformatOut.saveFile("output.dcm", EXS_LittleEndianExplicit);
    if(status.bad())
      std::cout << "Error writing: " << status.text() << std::endl;

    return 0;
}

// if the requested tag is not available, insert an empty one
void copyDcmElement(const DcmTag& tag, DcmDataset* dcmIn, DcmDataset* dcmOut)
{
  char *str;
  DcmElement* element;
  DcmTag copy = tag;
  std::cout << "Copying tag " << copy.getTagName() << std::endl;
  OFCondition cond = dcmIn->findAndGetElement(tag, element);
  if(cond.good())
    {
    element->getString(str);
    dcmOut->putAndInsertString(tag, str);
    }
  else
    {
    dcmOut->putAndInsertString(tag, "");
    }
}

#endif // 0
