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

// Slicer
#include "vtkMRMLScene.h"
#include "vtkMRMLScalarVolumeNode.h"
#include "vtkSmartPointer.h"

// CTK
#include "ctkDICOMDatabase.h"

// Qt
#include <QSqlQuery>

ctkDICOMDatabase* InitializeDICOMDatabase();

int main(int argc, char** argv)
{
    if(argc<2)
      return 0;
      
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

    vtkSmartPointer<vtkMRMLScalarVolumeNode> lab = 
      vtkMRMLScalarVolumeNode::SafeDownCast(scene->GetNodeByID("vtkMRMLScalarVolumeNode2"));

    ctkDICOMDatabase *db = InitializeDICOMDatabase();
    if(!db)
      {
      std::cerr << "Failed to initialize DICOM db!" << std::endl;
      return -1;
      }

    /*
      std::string uidsString = srcNode->GetAttribute("DICOM.instanceUIDs");
      std::vector<QString> uidVector;
      std::vector<DcmDataset*> dcmDatasetVector;
      char *uids = new char[uidsString.size()+1];
      strcpy(uids,uidsString.c_str());
      char *ptr;
      ptr = strtok(uids, " ");
      while (ptr != NULL)
        {
        vtkDebugMacro("Parsing UID = " << ptr);
        uidVector.push_back(QString(ptr));
        ptr = strtok(NULL, " ");
        }

      if(!this->DICOMDatabase)
        {
        this->InitializeDICOMDatabase();
        }
        */

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
          dcmDatasetVector.push_back(fileFormat.getDataset());
          }
        }
      }

    // create a DICOM dataset (see
    // http://support.dcmtk.org/docs/mod_dcmdata.html#Examples)
    DcmDataset *dataset = dcmDatasetVector[0];

    DcmFileFormat fileformatOut;
    //DcmDataset *datasetOut = fileformatOut.getDataset(), *datasetIn;
    
    DcmFileFormat fileformatIn;

#if 0
    DcmStack stack;
    datasetIn->print(std::cout);
    while (datasetIn->nextObject(stack, true) == EC_Normal)
      {
      DcmObject *dO = stack.top();
      /*
      QString tag = QString("%1,%2").arg(
          dO->getGTag(),4,16,QLatin1Char('0')).arg(
          dO->getETag(),4,16,QLatin1Char('0'));
      */
      std::ostringstream s;
      dO->print(s);
      
      //d->LoadedHeader[tag] = QString(s.str().c_str());
      }
#endif

    DcmElement* element;
    OFCondition res = dataset->findAndGetElement(DCM_SOPClassUID, element);
    //OFCondition res = dataset->findAndGetElement(DCM_StudyDate, element);
    if(res.bad())
      {
      std::cerr << "Error: " << res.text() << std::endl;
      return -1;
      }

    std::cout << "Got element" << std::endl;
    char *str;
    element->getString(str);

    //datasetOut->putAndInsertString(DCM_SOPClassUID, str);
    std::cout << "Tag value " << str << std::endl;
    //OFCondition status = fileformatOut.saveFile("output.dcm", EXS_LittleEndianExplicit);
    //if(status.bad())
    //  std::cout << "Error writing: " << status.text() << std::endl;

    return 0;
}

ctkDICOMDatabase* InitializeDICOMDatabase()
{
    std::cout << "Reporting will use database at this location: /Users/fedorov/DICOM_db" << std::endl;

    bool success = false;

    const char *dbPath = "/Users/fedorov/DICOM_db/ctkDICOM.sql";

      {
      ctkDICOMDatabase* DICOMDatabase = new ctkDICOMDatabase();
      DICOMDatabase->openDatabase(dbPath,"Reporting");
      if(DICOMDatabase->isOpen())
        return DICOMDatabase;
      }
    return NULL;
}
