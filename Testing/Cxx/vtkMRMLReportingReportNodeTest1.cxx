// MRML includes
#include "vtkMRMLCoreTestingMacros.h"
#include "vtkMRMLReportingReportNode.h"

// VTK includes
#include <vtkNew.h>

int vtkMRMLReportingReportNodeTest1(int , char * [] )
{

  vtkSmartPointer<vtkMRMLReportingReportNode> node1 = vtkSmartPointer<vtkMRMLReportingReportNode>::New();
  EXERCISE_BASIC_MRML_METHODS(vtkMRMLReportingReportNode, node1);

  std::string volumeID = std::string("testingID");
  node1->SetVolumeNodeID(volumeID);
  std::string testValue = node1->GetVolumeNodeID();
  if (testValue.compare(volumeID))
    {
    std::cerr << "Failed to set volume id to " << volumeID.c_str() << ", got: " << testValue.c_str() << std::endl;
    return EXIT_FAILURE;
    }

  TEST_SET_GET_INT_RANGE(node1, FindingLabel, 0, 255);
  
  std::string colorID = std::string("vtkMRMLColorNodeID");
  node1->SetColorNodeID(colorID);
  testValue = node1->GetColorNodeID();
  if (testValue.compare(colorID))
    {
    std::cerr << "Failed to set color id to " << colorID.c_str() << ", got: " << testValue.c_str() << std::endl;
    return EXIT_FAILURE;
    }

  std::string aimFileName = "/tmp/testFile.xml";
  node1->SetAIMFileName(aimFileName);
  testValue = node1->GetAIMFileName();
  if (testValue.compare(aimFileName))
    {
    std::cerr << "Failed to set aim file name to " << aimFileName.c_str() << ", got: " << testValue.c_str() << std::endl;
    return EXIT_FAILURE;
    }

  TEST_SET_GET_BOOLEAN( node1, AllowOutOfPlaneMarkups);
  
  return EXIT_SUCCESS;
}
