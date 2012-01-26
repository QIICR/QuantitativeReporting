/*==============================================================================

  Program: 3D Slicer

  Portions (c) Copyright Brigham and Women's Hospital (BWH) All Rights Reserved.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

==============================================================================*/

// ModuleTemplate includes
#include "vtkSlicerReportingModuleLogic.h"

// MRML includes
#include <vtkMRMLAnnotationNode.h>
#include <vtkMRMLAnnotationControlPointsNode.h>
#include <vtkMRMLAnnotationHierarchyNode.h>
#include <vtkMRMLDisplayableHierarchyNode.h>
#include <vtkMRMLScalarVolumeNode.h>

// VTK includes
#include <vtkMatrix4x4.h>
#include <vtkNew.h>
#include <vtkSmartPointer.h>

// STD includes
#include <cassert>

//----------------------------------------------------------------------------
vtkStandardNewMacro(vtkSlicerReportingModuleLogic);

//----------------------------------------------------------------------------
vtkSlicerReportingModuleLogic::vtkSlicerReportingModuleLogic()
{
  this->ActiveMarkupHierarchyID = NULL;
}

//----------------------------------------------------------------------------
vtkSlicerReportingModuleLogic::~vtkSlicerReportingModuleLogic()
{
  if (this->ActiveMarkupHierarchyID)
    {
    delete [] this->ActiveMarkupHierarchyID;
    this->ActiveMarkupHierarchyID = NULL;
    }
}

//----------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::PrintSelf(ostream& os, vtkIndent indent)
{
  this->Superclass::PrintSelf(os, indent);

  os << indent << "Active Markeup Hierarchy ID = " << (this->GetActiveMarkupHierarchyID() ? this->GetActiveMarkupHierarchyID() : "null") << "\n";

}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::InitializeEventListeners()
{
  vtkDebugMacro("InitializeEventListeners");
  
  vtkNew<vtkIntArray> events;
  events->InsertNextValue(vtkMRMLScene::NodeAddedEvent);
  events->InsertNextValue(vtkMRMLScene::NodeRemovedEvent);
  events->InsertNextValue(vtkMRMLScene::EndBatchProcessEvent);
  this->SetAndObserveMRMLSceneEventsInternal(this->GetMRMLScene(), events.GetPointer());
}

//-----------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::RegisterNodes()
{
  assert(this->GetMRMLScene() != 0);
}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::ProcessMRMLNodesEvents(vtkObject *vtkNotUsed(caller),
                                                            unsigned long event,
                                                            void *callData)
{
  vtkDebugMacro("ProcessMRMLNodesEvents");

  vtkMRMLNode* node = reinterpret_cast<vtkMRMLNode*> (callData);
  vtkMRMLAnnotationNode* annotationNode = vtkMRMLAnnotationNode::SafeDownCast(node);
  if (annotationNode)
    {
    switch (event)
      {
      case vtkMRMLScene::NodeAddedEvent:
        this->OnMRMLSceneNodeAdded(annotationNode);
        break;
      case vtkMRMLScene::NodeRemovedEvent:
        this->OnMRMLSceneNodeRemoved(annotationNode);
        break;
      }
    }
}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::UpdateFromMRMLScene()
{
  assert(this->GetMRMLScene() != 0);
}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::OnMRMLSceneNodeAdded(vtkMRMLNode* node)
{ 
  if (!node)
    {
    return;
    }
  if (!node->IsA("vtkMRMLAnnotationFiducialNode") &&
      !node->IsA("vtkMRMLAnnotationRulerNode"))
    {
    return;
    }
  // only want to grab annotation nodes if there's an active markeup
  // hierarchy
  if (!this->GetActiveMarkupHierarchyID())
    {
    return;
    }
  vtkDebugMacro("OnMRMLSceneNodeAdded: got an annotation node with id " << node->GetID());

  /// make a new hierarchy node to create a parallel tree?
  /// for now, just reasign it
  vtkMRMLHierarchyNode *hnode = vtkMRMLHierarchyNode::GetAssociatedHierarchyNode(node->GetScene(), node->GetID());
  if (hnode)
    {
    hnode->SetParentNodeID(this->GetActiveMarkupHierarchyID());
    }
}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::OnMRMLSceneNodeRemoved(vtkMRMLNode* vtkNotUsed(node))
{
}

//---------------------------------------------------------------------------
const char *vtkSlicerReportingModuleLogic::GetSliceUIDFromMarkUp(vtkMRMLAnnotationNode *node)
{
  std::string UID = "NONE";

  if (!node)
    {
    vtkErrorMacro("GetSliceUIDFromMarkUp: no input node!");
    return  UID.c_str();
    }

  if (!this->GetMRMLScene())
    {
    vtkErrorMacro("GetSliceUIDFromMarkUp: No MRML Scene defined!");
    return UID.c_str();
    }
  
  vtkMRMLAnnotationControlPointsNode *cpNode = vtkMRMLAnnotationControlPointsNode::SafeDownCast(node);
  if (!node)
    {
    vtkErrorMacro("GetSliceUIDFromMarkUp: Input node is not a control points node!");
    return UID.c_str();
    }
  
  int numPoints = cpNode->GetNumberOfControlPoints();
  vtkDebugMacro("GetSliceUIDFromMarkUp: have a control points node with " << numPoints << " points");

  // get the associated node
  const char *associatedNodeID = cpNode->GetAttribute("AssociatedNodeID");
  if (!associatedNodeID)
    {
    vtkErrorMacro("GetSliceUIDFromMarkUp: No AssociatedNodeID on the annotation node");
    return UID.c_str();
    }
  vtkMRMLScalarVolumeNode *volumeNode = NULL;
  vtkMRMLNode *mrmlNode = this->GetMRMLScene()->GetNodeByID(associatedNodeID);
  if (!mrmlNode)
    {
    vtkErrorMacro("GetSliceUIDFromMarkUp: Associated node not found by id: " << associatedNodeID);
    return UID.c_str();
    }
  volumeNode = vtkMRMLScalarVolumeNode::SafeDownCast(mrmlNode);
  if (!volumeNode)
    {
    vtkErrorMacro("GetSliceUIDFromMarkUp: Associated node with id: " << associatedNodeID << " is not a volume node!");
    return UID.c_str();
    }

  // get the list of UIDs from the volume
  if (!volumeNode->GetAttribute("DICOM.instanceUIDs"))
    {
    vtkErrorMacro("GetSliceUIDFromMarkUp: Volume node with id: " << associatedNodeID << " doesn't have a list of UIDs under the attribute DICOM.instanceUIDs!");
    return UID.c_str();
    }
  std::string uidsString = volumeNode->GetAttribute("DICOM.instanceUIDs");
  // break them up into a vector, they're space separated
  std::vector<std::string> uidVector;
  char *uids = new char[uidsString.size()+1];
  strcpy(uids,uidsString.c_str());
  char *ptr;
  ptr = strtok(uids, " ");
  while (ptr != NULL)
    {
    vtkDebugMacro("Parsing UID = " << ptr);
    uidVector.push_back(std::string(ptr));
    ptr = strtok(NULL, " ");
    }
  
  // get the RAS to IJK matrix from the volume
  vtkSmartPointer<vtkMatrix4x4> ras2ijk = vtkSmartPointer<vtkMatrix4x4>::New();
  volumeNode->GetRASToIJKMatrix(ras2ijk);


//  for (int i = 0; i < numPoints; i++)
  int i = 0;
    {
    vtkDebugMacro("i " << " uid = " << uidVector[i].c_str());
    // get the RAS point
    double ras[4] = {0.0, 0.0, 0.0, 1.0};
    cpNode->GetControlPointWorldCoordinates(i, ras);
    // convert point from ras to ijk
    double ijk[4] = {0.0, 0.0, 0.0, 1.0};
    ras2ijk->MultiplyPoint(ras, ijk);
    vtkDebugMacro("Point " << i << " ras = " << ras[0] << ", " << ras[1] << ", " << ras[2] << " converted to ijk  = " << ijk[0] << ", " << ijk[1] << ", " << ijk[2] << ", getting uid at index " << ijk[2] << " (uid vector size = " << uidVector.size() << ")");
    if (uidVector.size() > ijk[2])
      {
      // assumption is that the dicom UIDs are in order by k
      UID = uidVector[ijk[2]];
      }
    }  
  return UID.c_str();

}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::InitializeHierarchyForVolume(vtkMRMLVolumeNode *node)
{
  if (!node)
    {
    vtkErrorMacro("InitializeHierarchyForVolume: null input volume");
    return;
    }

  if (!node->GetScene() || !node->GetID())
    {
    vtkErrorMacro("InitializeHierarchyForVolume: No MRML Scene defined on node, or else it doesn't have an id");
    return;
    }

  vtkWarningMacro("InitializeHierarchyForVolume: setting up hierarchy for volume " << node->GetID());

  /// does the node already have a hierarchy set up for it?
  vtkMRMLHierarchyNode *hnode = vtkMRMLHierarchyNode::GetAssociatedHierarchyNode(node->GetScene(), node->GetID());
  if (hnode)
    {
    vtkWarningMacro("InitializeHierarchyForVolume: volume " << node->GetID() << " already has a hierarhcy associated with it, " << hnode->GetID());
    return;
    }
  
  /// otherwise, create a 1:1 hierarchy for this node
  vtkMRMLDisplayableHierarchyNode *volumeHierarchyNode = vtkMRMLDisplayableHierarchyNode::New();
  /// it's a stealth node:
  volumeHierarchyNode->HideFromEditorsOn();
  std::string hnodeName = std::string("VolumeHierarchy") + std::string(node->GetName());
  volumeHierarchyNode->SetName(this->GetMRMLScene()->GetUniqueNameByString(hnodeName.c_str()));
  this->GetMRMLScene()->AddNode(volumeHierarchyNode);

  /// check for a top level hierarchy
  if (!this->GetMRMLScene()->GetFirstNodeByName("Reporting Hierarchy"))
    {
    vtkMRMLDisplayableHierarchyNode *reportingHierarchy = vtkMRMLDisplayableHierarchyNode::New();
    reportingHierarchy->HideFromEditorsOff();
    reportingHierarchy->SetName("Reporting Hierarchy");
    this->GetMRMLScene()->AddNode(reportingHierarchy);
    reportingHierarchy->Delete();
    }
  const char *topLevelID = this->GetMRMLScene()->GetFirstNodeByName("Reporting Hierarchy")->GetID();
  // make it the child of the top level reporting node
  volumeHierarchyNode->SetParentNodeID(topLevelID);
  
  // set the displayable node id to point to this volume node
  node->SetDisableModifiedEvent(1);
  volumeHierarchyNode->SetDisplayableNodeID(node->GetID());
  node->SetDisableModifiedEvent(0);

  /// add an annotations hierarchy
  vtkMRMLAnnotationHierarchyNode *ahnode =
    vtkMRMLAnnotationHierarchyNode::New();
  ahnode->HideFromEditorsOff();
  std::string ahnodeName = std::string("Markup ") + std::string(node->GetName());
  ahnode->SetName(this->GetMRMLScene()->GetUniqueNameByString(ahnodeName.c_str()));
  this->GetMRMLScene()->AddNode(ahnode);
  // make it a child of the report for now
  ahnode->SetParentNodeID(topLevelID);
  
  /// make the annotation hierarchy active so new ones will get added to it
  this->SetActiveMarkupHierarchyID(ahnode->GetID());

  /// need to trigger a tree redraw
  
  /// clean up
  volumeHierarchyNode->Delete();
  ahnode->Delete();
}
