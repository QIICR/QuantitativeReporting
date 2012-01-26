#include "vtkSlicerReportingModuleLogic.h"
#include "vtkMRMLAnnotationRulerNode.h"
#include "vtkMRMLAnnotationFiducialNode.h"
#include "vtkMRMLAnnotationTextDisplayNode.h"
#include "vtkMRMLAnnotationPointDisplayNode.h"
#include "vtkMRMLAnnotationLineDisplayNode.h"
#include "vtkMRMLScalarVolumeNode.h"
#include "TestingMacros.h"

bool testUID(const char *uid)
{
  if (uid == NULL)
    {
    std::cerr << "UID is null" << std::endl;
    return false;
    }
  if (strcmp(uid, "") == 0)
    {
    std::cerr << "UID is an empty string" << std::endl;
    return false;
    }
   if (strcmp(uid, "NONE") == 0)
    {
    std::cerr << "UID is NONE" << std::endl;
    return false;
    }
  return true;
}

int vtkSlicerReportingModuleLogicTest1(int , char * [] )
{

  // ======================
  // Basic Setup 
  // ======================
  vtkSmartPointer<vtkSlicerReportingModuleLogic > node2 = vtkSmartPointer< vtkSlicerReportingModuleLogic >::New();
  vtkSmartPointer<vtkMRMLScene> mrmlScene = vtkSmartPointer<vtkMRMLScene>::New();
  node2->SetMRMLScene(mrmlScene);
  
  EXERCISE_BASIC_OBJECT_METHODS( node2 );

  // add an annotation node
  vtkSmartPointer<vtkMRMLAnnotationRulerNode> rnode1 = vtkSmartPointer<vtkMRMLAnnotationRulerNode>::New();
  mrmlScene->AddNode(rnode1);

  const char *uid = node2->GetSliceUIDFromMarkUp(NULL);
  if (testUID(uid))
    {
    // should be NONE string
    std::cerr << "Expected an NONE uid string from null markup, got " << uid << std::endl;
    return EXIT_FAILURE;
    }

  uid = node2->GetSliceUIDFromMarkUp(rnode1);
  if (testUID(uid))
    {
    // should be NONE string
    std::cerr << "Expected an NONE uid string, no associated node id, got " << uid << std::endl;
    return EXIT_FAILURE;
    }

  rnode1->SetAttribute("AssociatedNodeID", "invalid");
  uid = node2->GetSliceUIDFromMarkUp(rnode1);
  if (testUID(uid))
    {
    // should be NONE string
    std::cerr << "Expected an NONE uid string when associated node with an invalid node id, got " << uid << std::endl;
    return EXIT_FAILURE;
    }

  // now add a scalar volume node
  vtkSmartPointer<vtkMRMLScalarVolumeNode> volumeNode = vtkSmartPointer<vtkMRMLScalarVolumeNode>::New();
  mrmlScene->AddNode(volumeNode);
  char *vid = volumeNode->GetID();
  rnode1->SetAttribute("AssociatedNodeID", vid);

  std::cout << "Testing with associated volume node, no uid list" << std::endl;
  uid = node2->GetSliceUIDFromMarkUp(rnode1);
  if (testUID(uid))
    {
    // should be NONE string
    std::cerr << "Expected an NONE uid string when associated node doesn't have a UID attribute, got " << uid << std::endl;
    return EXIT_FAILURE;
    }

  // now set some attributes
  std::cout << "Testing with associated volume node, with uid list" << std::endl;
  volumeNode->SetAttribute("DICOM.instanceUIDs", "id1 id2 id3 id4");
  uid = node2->GetSliceUIDFromMarkUp(rnode1);
  if (!testUID(uid))
    {
    // should be a valid id string
    std::cerr << "Expected an valid uid string since associated node has a UID attribute, got " << uid << std::endl;
    return EXIT_FAILURE;
    }
  else
    {
    std::cout << "Got a UID of " << uid << std::endl;
    // with no end points set, hope to get uid1
    if (strcmp(uid, "id1") != 0)
      {
      std::cerr << "Expected id1, got " << uid << std::endl;
      return EXIT_FAILURE;
      }
    }

  // now set ruler end points
  double pos[3] = {0.0, 0.0, 0.0};
  rnode1->SetPosition1(pos);
  pos[1] = 1.0;
  rnode1->SetPosition2(pos);
  std::cout << "Testing with valid ruler end points" << std::endl;
  uid = node2->GetSliceUIDFromMarkUp(rnode1);
  if (!testUID(uid))
    {
    // should be a valid id string
    std::cerr << "Expected an valid uid string since associated node has a UID attribute, got " << uid << std::endl;
    return EXIT_FAILURE;
    }
  else
    {
    std::cout << "Got valid uid of " <<  uid << std::endl;
    }

  // now move the ruler to slice2
  pos[2] = 1.0;
  rnode1->SetPosition1(pos);
  std::cout << "Testing with valid ruler end points, on second slice" << std::endl;
  uid = node2->GetSliceUIDFromMarkUp(rnode1);
  if (!testUID(uid))
    {
    // should be a valid id string
    std::cerr << "Expected an valid uid string since associated node has a UID attribute, got " << uid << std::endl;
    return EXIT_FAILURE;
    }
  else
    {
    if (strcmp(uid, "id2") != 0)
      {
      std::cerr << "Expected id2, got " << uid << std::endl;
      return EXIT_FAILURE;
      }
    else
      {
      std::cout << "Got expected uid of " << uid << std::endl;
      }
    }
  return EXIT_SUCCESS;  
}



