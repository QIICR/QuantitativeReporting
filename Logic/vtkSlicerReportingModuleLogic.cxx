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
#include <vtkMRMLReportingReportNode.h>
#include <vtkMRMLScalarVolumeNode.h>
#include <vtkMRMLReportingAnnotationRANONode.h>

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
  this->ActiveReportHierarchyID = NULL;
  this->ActiveMarkupHierarchyID = NULL;
}

//----------------------------------------------------------------------------
vtkSlicerReportingModuleLogic::~vtkSlicerReportingModuleLogic()
{
  if (this->ActiveReportHierarchyID)
    {
    delete [] this->ActiveReportHierarchyID;
    this->ActiveReportHierarchyID = NULL;
    }
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

  os << indent << "Active Report Hierarchy ID = " << (this->GetActiveReportHierarchyID() ? this->GetActiveReportHierarchyID() : "null") << "\n";
  os << indent << "Active Markup Hierarchy ID = " << (this->GetActiveMarkupHierarchyID() ? this->GetActiveMarkupHierarchyID() : "null") << "\n";

}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::SetMRMLSceneInternal(vtkMRMLScene* newScene)
{
  vtkDebugMacro("SetMRMLSceneInternal");
  
  vtkNew<vtkIntArray> events;
  events->InsertNextValue(vtkMRMLScene::NodeAddedEvent);
  events->InsertNextValue(vtkMRMLScene::NodeRemovedEvent);
  events->InsertNextValue(vtkMRMLScene::EndBatchProcessEvent);
  this->SetAndObserveMRMLSceneEventsInternal(newScene, events.GetPointer());
}

//-----------------------------------------------------------------------------
// Register all module-specific nodes here
void vtkSlicerReportingModuleLogic::RegisterNodes()
{
  if(!this->GetMRMLScene())
    return;
  vtkMRMLReportingReportNode *rn = vtkMRMLReportingReportNode::New();
  this->GetMRMLScene()->RegisterNodeClass(rn);
  vtkMRMLReportingAnnotationRANONode *rano = vtkMRMLReportingAnnotationRANONode::New();
  this->GetMRMLScene()->RegisterNodeClass(rano);
  rn->Delete();
  rano->Delete();
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
  vtkDebugMacro("OnMRMLSceneNodeAdded: active markup hierarchy, got an annotation node added with id " << node->GetID());

  /// make a new hierarchy node to create a parallel tree?
  /// for now, just reasign it
  vtkMRMLHierarchyNode *hnode = vtkMRMLHierarchyNode::GetAssociatedHierarchyNode(node->GetScene(), node->GetID());
  if (hnode)
    {
    hnode->SetParentNodeID(this->GetActiveMarkupHierarchyID());
    }
  // TODO: sanity check to make sure that the annotation's AssociatedNodeID
  // attribute points to the current volume
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
char *vtkSlicerReportingModuleLogic::GetTopLevelHierarchyNodeID()
{
  if (this->GetMRMLScene() == NULL)
    {
    return NULL;
    }
  const char *topLevelName = "Reporting Hierarchy";

  /// check for a top level hierarchy
  if (!this->GetMRMLScene()->GetFirstNodeByName(topLevelName))
    {
    vtkMRMLDisplayableHierarchyNode *reportingHierarchy = vtkMRMLDisplayableHierarchyNode::New();
    reportingHierarchy->HideFromEditorsOff();
    reportingHierarchy->SetName(topLevelName);
    this->GetMRMLScene()->AddNode(reportingHierarchy);
    reportingHierarchy->Delete();
    }
   
  char *toplevelNodeID =  this->GetMRMLScene()->GetFirstNodeByName(topLevelName)->GetID();;

  return toplevelNodeID;
}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::InitializeHierarchyForReport(vtkMRMLReportingReportNode *node)
{
  if (!node)
    {
    vtkErrorMacro("InitializeHierarchyForReport: null input report");
    return;
    }

  if (!node->GetScene() || !node->GetID())
    {
    vtkErrorMacro("InitializeHierarchyForReport: No MRML Scene defined on node, or else it doesn't have an id");
    return;
    }

  vtkDebugMacro("InitializeHierarchyForReport: setting up hierarchy for report " << node->GetID());

  /// does the node already have a hierarchy set up for it?
  vtkMRMLHierarchyNode *hnode = vtkMRMLHierarchyNode::GetAssociatedHierarchyNode(node->GetScene(), node->GetID());
  if (hnode)
    {
    vtkWarningMacro("InitializeHierarchyForReport: report " << node->GetID() << " already has a hierarchy associated with it, " << hnode->GetID());
    return;
    }
    /// otherwise, create a 1:1 hierarchy for this node
  vtkMRMLDisplayableHierarchyNode *reportHierarchyNode = vtkMRMLDisplayableHierarchyNode::New();
  /// it's a stealth node:
  reportHierarchyNode->HideFromEditorsOn();
  std::string hnodeName = std::string(node->GetName()) + std::string(" Hierarchy");
  reportHierarchyNode->SetName(this->GetMRMLScene()->GetUniqueNameByString(hnodeName.c_str()));
  this->GetMRMLScene()->AddNode(reportHierarchyNode);

  
  // make it the child of the top level reporting node
  const char *topLevelID = this->GetTopLevelHierarchyNodeID();
  vtkDebugMacro("InitializeHierarchyForReport: pointing report hierarchy node at top level id " << (topLevelID ? topLevelID : "null"));
  reportHierarchyNode->SetParentNodeID(topLevelID);
  
  // set the displayable node id to point to this report node
  node->SetDisableModifiedEvent(1);
  reportHierarchyNode->SetDisplayableNodeID(node->GetID());
  node->SetDisableModifiedEvent(0);

  /// make the report hierarchy active 
  this->SetActiveReportHierarchyID(reportHierarchyNode->GetID());
  vtkDebugMacro("Set the active report hierarchy id = " << (reportHierarchyNode->GetID() ? reportHierarchyNode->GetID() : "null"));
  
  /// clean up
  reportHierarchyNode->Delete();
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

  vtkDebugMacro("InitializeHierarchyForVolume: setting up hierarchy for volume " << node->GetID());

  /// does the node already have a hierarchy set up for it?
  vtkMRMLHierarchyNode *hnode = vtkMRMLHierarchyNode::GetAssociatedHierarchyNode(node->GetScene(), node->GetID());
  if (hnode)
    {
    vtkWarningMacro("InitializeHierarchyForVolume: volume " << node->GetID() << " already has a hierarchy associated with it, " << hnode->GetID());
    return;
    }
  
  /// otherwise, create a 1:1 hierarchy for this node
  vtkMRMLDisplayableHierarchyNode *volumeHierarchyNode = vtkMRMLDisplayableHierarchyNode::New();
  /// it's a stealth node:
  volumeHierarchyNode->HideFromEditorsOn();
  std::string hnodeName = std::string(node->GetName()) + std::string(" Hierarchy ");
  volumeHierarchyNode->SetName(this->GetMRMLScene()->GetUniqueNameByString(hnodeName.c_str()));
  this->GetMRMLScene()->AddNode(volumeHierarchyNode);
  
  // make it the child of the active report node
  if (!this->GetActiveReportHierarchyID())
    {
    vtkWarningMacro("No active report, please select one!");
    }
  else
    {
    vtkDebugMacro("Set volume hierarchy parent to active report id " << this->GetActiveReportHierarchyID());
    }
  volumeHierarchyNode->SetParentNodeID(this->GetActiveReportHierarchyID());
  
  // set the displayable node id to point to this volume node
  node->SetDisableModifiedEvent(1);
  volumeHierarchyNode->SetDisplayableNodeID(node->GetID());
  node->SetDisableModifiedEvent(0);

  /// add an annotations hierarchy if it doesn't exist
  std::string ahnodeName = std::string("Markup ") + std::string(node->GetName());
  vtkMRMLNode *mrmlNode = this->GetMRMLScene()->GetFirstNodeByName(ahnodeName.c_str());
  char *ahnodeID = NULL;
  if (!mrmlNode)
    {
    vtkMRMLAnnotationHierarchyNode *ahnode = vtkMRMLAnnotationHierarchyNode::New();
    ahnode->HideFromEditorsOff();
    ahnode->SetName(ahnodeName.c_str());
    this->GetMRMLScene()->AddNode(ahnode);
    ahnodeID = ahnode->GetID();
    // make it a child of the volume
    ahnode->SetParentNodeID(volumeHierarchyNode->GetID());
    ahnode->Delete();
    }
  else
    {
    ahnodeID = mrmlNode->GetID();
    }
  /// make the annotation hierarchy active so new ones will get added to it
  this->SetActiveMarkupHierarchyID(ahnodeID);
  vtkDebugMacro("Set the active markup hierarchy id from node id = " << (ahnodeID ? ahnodeID : "null"));
  
  /// clean up
  volumeHierarchyNode->Delete();
}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::SetActiveMarkupHierarchyIDFromNode(vtkMRMLNode *node)
{
  if (!node || !node->GetName())
    {
    vtkDebugMacro("SetActiveMarkupHierarchyIDFromNode: node is " << (node? "not null" : "null") << ", name is " << (node->GetName() ? node->GetName() : "null") << ", settting active id to null");
    this->SetActiveMarkupHierarchyID(NULL);
    return;
    }

  // look for a markup node associated with this node
  std::string ahnodeName = std::string("Markup ") + std::string(node->GetName());
  vtkMRMLNode *mrmlNode = this->GetMRMLScene()->GetFirstNodeByName(ahnodeName.c_str());
                                                                   
  if (!mrmlNode)
    {
    vtkWarningMacro("SetActiveMarkupHierarchyIDFromNode: didn't find markup node by name " << ahnodeName.c_str() << ", setting active hierarchy to null");
    this->SetActiveMarkupHierarchyID(NULL);
    return;
    }
  vtkDebugMacro("SetActiveMarkupHierarchyIDFromNode: Setting active markup hierarchy to " << mrmlNode->GetID());
  this->SetActiveMarkupHierarchyID(mrmlNode->GetID());
}

//---------------------------------------------------------------------------
void vtkSlicerReportingModuleLogic::SetActiveMarkupHierarchyIDToNull()
{
  if (this->ActiveMarkupHierarchyID)
    {
    delete [] this->ActiveMarkupHierarchyID;
    }
  this->ActiveMarkupHierarchyID = NULL;
}
