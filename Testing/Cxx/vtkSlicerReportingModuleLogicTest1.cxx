
// Reporting/Logic includes
#include "vtkSlicerReportingModuleLogic.h"

// Annotation/MRML includes
#include <vtkMRMLAnnotationRulerNode.h>
#include <vtkMRMLAnnotationFiducialNode.h>
#include <vtkMRMLAnnotationTextDisplayNode.h>
#include <vtkMRMLAnnotationPointDisplayNode.h>
#include <vtkMRMLAnnotationLineDisplayNode.h>

// MRML includes
#include <vtkMRMLCoreTestingMacros.h>
#include <vtkMRMLScalarVolumeNode.h>

// Qt includes
#include <QString>
#include <QDomDocument>
#include <QDomElement>

bool testUID(std::string uid)
{
  if (uid.compare("") == 0)
    {
    std::cerr << "UID is an empty string" << std::endl;
    return false;
    }
  if (uid.compare("NONE") == 0)
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

  std::string uid = node2->GetSliceUIDFromMarkUp(NULL);
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
    std::cerr << "Expected a NONE uid string when associated node doesn't have a UID attribute, got " << uid << std::endl;
    return EXIT_FAILURE;
    }

  // now set some attributes
  const char *uids = "id1 id2 id3 id4";
  std::cout << "Testing with associated volume node, with uid list '" << uids << "'" << std::endl;
  volumeNode->SetAttribute("DICOM.instanceUIDs", uids);
//  node2->DebugOn();
  uid = node2->GetSliceUIDFromMarkUp(rnode1);
  std::cout << "UID = " << uid.c_str() << std::endl;
  if (testUID(uid))
    {
    // no points, should be an invalid string
    std::cerr << "Expected an invalid uid string since associated node has a UID attributebut ruler node has no points, got '" << uid << "'" << std::endl;
    return EXIT_FAILURE;
    }

  std::cout << "With no ruler points, got a UID of " << uid << std::endl;

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
    std::cerr << "Expected an valid uid string since associated node has a UID attribute, got '" << uid << "'" << std::endl;
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
  if (testUID(uid))
    {
    // should be an invalid id string
    std::cerr << "Expected an invalid uid string since associated node has a UID attributebut the ruler end points are on different slices, got '" << uid << "'" << std::endl;
    return EXIT_FAILURE;
    }
  std::cout << "Got expected uid of " << uid << " with ruler end points on different slices " << std::endl;

  // test the ruler length print out
  QDomDocument doc;
  QDomProcessingInstruction xmlDecl = doc.createProcessingInstruction("xml","version=\"1.0\"");
  doc.appendChild(xmlDecl);
  QDomElement root = doc.createElement("ImageAnnotation");
  // add a few attributes
  root.setAttribute("xmlns","gme://caCORE.caCORE/3.2/edu.northwestern.radiology.AIM");
  root.setAttribute("aimVersion","3.0");
  root.setAttribute("cagridId","0");
  doc.appendChild(root);
  
  double pos1[4], pos2[4];
  rnode1->GetPositionWorldCoordinates1(pos1);
  rnode1->GetPositionWorldCoordinates2(pos2);
  double distanceMeasurement = sqrt(vtkMath::Distance2BetweenPoints(pos1,pos2));
  QString rulerLength;
  rulerLength.sprintf("%g", distanceMeasurement);
  QString uidStr = "1.2.3.4.5.5.6";
  rnode1->SetAttribute("ShapeIdentifier","889977");
  QString shapeID = rnode1->GetAttribute("ShapeIdentifier");
  node2->AddCalculationCollectionElement(doc, root, rulerLength, shapeID, uidStr);
  QString xml = doc.toString();
  std::cout << "Adding distance measurement of " << qPrintable(rulerLength) << " to a CalculationCollection:" << std::endl;
  std::cout << qPrintable(xml);
  
  return EXIT_SUCCESS;
}



