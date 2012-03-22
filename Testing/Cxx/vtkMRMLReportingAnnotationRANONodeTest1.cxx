
// Reporting/MRML includes
#include "vtkMRMLReportingAnnotationRANONode.h"

// MRML includes
#include <vtkMRMLCoreTestingMacros.h>
#include <vtkMRMLScene.h>

// STD includes
#include <sstream>

int vtkMRMLReportingAnnotationRANONodeTest1(int , char * [] )
{

  // ======================
  // Basic Setup
  // ======================

  vtkSmartPointer< vtkMRMLReportingAnnotationRANONode > node2 = vtkSmartPointer< vtkMRMLReportingAnnotationRANONode >::New();
  vtkSmartPointer<vtkMRMLScene> mrmlScene = vtkSmartPointer<vtkMRMLScene>::New();
  // node2->Initialize(mrmlScene);

  {

    vtkSmartPointer< vtkMRMLReportingAnnotationRANONode > node1 = vtkSmartPointer< vtkMRMLReportingAnnotationRANONode >::New();
    // node1->Initialize(mrmlScene);

    EXERCISE_BASIC_OBJECT_METHODS( node1 );

    node1->UpdateReferences();
    node2->Copy( node1 );

    mrmlScene->RegisterNodeClass(node1);
    mrmlScene->AddNode(node2);
  }

  // ======================
  // Modify Properties
  // ======================
  node2->Reset();
  node2->StartModify();
  // node2->Initialize(mrmlScene);


  node2->SetName("ReportingAnnotationRANONodeTest") ;

  std::string nodeTagName = node2->GetNodeTagName();
  std::cout << "Node Tag Name = " << nodeTagName << std::endl;

  vtkIndent ind;

  cout << "Passed Adding and Deleting Data" << endl;

  node2->Modified();

  // ======================
  // Test WriteXML and ReadXML
  // ======================

  mrmlScene->SetURL("ReportingAnnotationRANONodeTest.mrml");
  mrmlScene->Commit();

  // Now Read in File to see if ReadXML works - it first disconnects from node2 !
  mrmlScene->Connect();
  vtkIndent ij;

  if (mrmlScene->GetNumberOfNodesByClass("vtkMRMLReportingAnnotationRANONode") != 1)
    {
        std::cerr << "Error in ReadXML() or WriteXML() - Did not create a class called vtkMRMLReportingAnnotationRANONode" << std::endl;
    return EXIT_FAILURE;
    }

  vtkMRMLReportingAnnotationRANONode *node1 = dynamic_cast < vtkMRMLReportingAnnotationRANONode *> (mrmlScene->GetNthNodeByClass(0,"vtkMRMLReportingAnnotationRANONode"));
  if (!node2)
      {
    std::cerr << "Error in ReadXML() or WriteXML(): could not find vtkMRMLReportingAnnotationRANONode" << std::endl;
    return EXIT_FAILURE;
      }

  std::stringstream node1str, node2str;


  node2->PrintSelf(cout,ind);
  node2->PrintSelf(node2str, ind);
  node1->PrintSelf(node1str, ind);

  while(!node1str.eof() && !node2str.eof())
    {
    char str1[255], str2[255];
    node1str.getline(str1, 255);
    node2str.getline(str2, 255);
    if(std::string(str1).find("Modified Time:")!=std::string::npos)
      continue;
    if(strcmp(str1, str2)!=0)
      {
      std::cerr << "Error in ReadXML() or WriteXML()" << std::endl;
      std::cerr << "Before:" << std::endl << node1str.str() <<std::endl;
      std::cerr << "After:" << std::endl << node2str.str() <<std::endl;
      return EXIT_FAILURE;
      }
    }
  cout << "Passed XML" << endl;

  return EXIT_SUCCESS;

}


