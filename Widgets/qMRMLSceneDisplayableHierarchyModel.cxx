/*==============================================================================

  Program: 3D Slicer

  Copyright (c) Kitware Inc.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

  This file was originally developed by Julien Finet, Kitware Inc.
  and was partially funded by NIH grant 3P41RR013218-12S1

==============================================================================*/

// Qt includes

// qMRML includes
#include "qMRMLSceneDisplayableHierarchyModel.h"
#include "qMRMLSceneDisplayableModel_p.h"

// MRMLLogic includes
#include <vtkMRMLDisplayableNode.h>
#include <vtkMRMLDisplayNode.h>
#include <vtkMRMLDisplayableHierarchyLogic.h>
#include <vtkMRMLDisplayableHierarchyNode.h>

// MRML includes
#include <vtkMRMLAnnotationNode.h>

// VTK includes
#include <vtkCollection.h>

//------------------------------------------------------------------------------
class qMRMLSceneDisplayableHierarchyModelPrivate: public qMRMLSceneDisplayableModelPrivate
{
protected:
  Q_DECLARE_PUBLIC(qMRMLSceneDisplayableHierarchyModel);
public:
  typedef qMRMLSceneDisplayableModelPrivate Superclass;
  qMRMLSceneDisplayableHierarchyModelPrivate(qMRMLSceneDisplayableHierarchyModel& object);

  virtual vtkMRMLHierarchyNode* CreateHierarchyNode()const;
  virtual void init();

};

//------------------------------------------------------------------------------
qMRMLSceneDisplayableHierarchyModelPrivate
::qMRMLSceneDisplayableHierarchyModelPrivate(qMRMLSceneDisplayableHierarchyModel& object)
  : Superclass(object)
{
}

//------------------------------------------------------------------------------
void qMRMLSceneDisplayableHierarchyModelPrivate::init()
{
    Q_Q(qMRMLSceneDisplayableHierarchyModel);
    q->setVisibilityColumn(0);
    
}

//------------------------------------------------------------------------------
vtkMRMLHierarchyNode* qMRMLSceneDisplayableHierarchyModelPrivate::CreateHierarchyNode()const
{
  return vtkMRMLDisplayableHierarchyNode::New();
}

//----------------------------------------------------------------------------

//------------------------------------------------------------------------------
qMRMLSceneDisplayableHierarchyModel::qMRMLSceneDisplayableHierarchyModel(QObject *vparent)
  :Superclass(new qMRMLSceneDisplayableHierarchyModelPrivate(*this), vparent)
{
  Q_D(qMRMLSceneDisplayableHierarchyModel);
  d->init();
}

//------------------------------------------------------------------------------
qMRMLSceneDisplayableHierarchyModel::~qMRMLSceneDisplayableHierarchyModel()
{
}

//------------------------------------------------------------------------------
int qMRMLSceneDisplayableHierarchyModel::nodeIndex(vtkMRMLNode* node)const
{
  Q_D(const qMRMLSceneDisplayableHierarchyModel);
  if (!d->MRMLScene)
    {
    return -1;
    }
  const char* nodeId = node ? node->GetID() : 0;
  if (nodeId == 0)
    {
    return -1;
    }

  // is there a hierarchy node associated with this node?
  vtkMRMLHierarchyNode *assocHierarchyNode = vtkMRMLHierarchyNode::GetAssociatedHierarchyNode(d->MRMLScene, node->GetID());
  if (assocHierarchyNode)
    {
    int assocHierarchyNodeIndex = this->nodeIndex(assocHierarchyNode);
    return assocHierarchyNodeIndex + 1;
    }

  const char* nId = 0;
  vtkMRMLNode* parent = this->parentNode(node);
  int index = 0;
  // if it's part of a hierarchy, use the GetIndexInParent call
  if (parent)
    {
    vtkMRMLHierarchyNode *hnode = vtkMRMLHierarchyNode::SafeDownCast(node);
    if (hnode)
      {
      vtkMRMLHierarchyNode* parentHierarchy = vtkMRMLHierarchyNode::SafeDownCast(parent);
      if (!parentHierarchy)
        {
//        std::cout << "DisplayableHierarchyModel::nodeIndex: parent is not a hierarchy for node " << node->GetName() << ": " << node->GetID() << std::endl;
        // could be the case where we have a hidden hierarchy node and the
        // parent has been returned as the associated node. So, get the
        // hierarchy node for the parent node
        vtkMRMLDisplayableNode *parentDisplayableNode = vtkMRMLDisplayableNode::SafeDownCast(parent);
        if (parentDisplayableNode)
          {
          parentHierarchy = vtkMRMLHierarchyNode::GetAssociatedHierarchyNode(parentDisplayableNode->GetScene(), parentDisplayableNode->GetID());
          if (parentHierarchy)
            {
//            std::cout << "\tfound hierarchy node for parent node: " << parentHierarchy->GetName() << ": " << parentHierarchy->GetID() << std::endl;
            }
          }
        }
      if (parentHierarchy)
        {
        const int childrenCount =  parentHierarchy->GetNumberOfChildrenNodes();
        for ( int i = 0; i < childrenCount ; ++i)
          {
          vtkMRMLHierarchyNode* child = parentHierarchy->GetNthChildNode(i);
          if (child == hnode)
            {
            return index;
            }
          ++index;
          // the associated node of a hierarchynode is displayed after the hierarchynode
          if (child->GetAssociatedNode())
            {
            ++index;
            }
          }
        }
      
      }
    }

  // otherwise, iterate through the scene
    vtkCollection* nodes = d->MRMLScene->GetNodes();
  vtkMRMLNode* n = 0;
  vtkCollectionSimpleIterator it;

  for (nodes->InitTraversal(it);
       (n = (vtkMRMLNode*)nodes->GetNextItemAsObject(it)) ;)
    {
    // note: parent can be NULL, it means that the scene is the parent
    if (parent == this->parentNode(n))
      {
      nId = n->GetID();
      if (nId && !strcmp(nodeId, nId))
        {
//      std::cout << "nodeIndex:  no parent for node " << node->GetID() << " index = " << index << std::endl;
        return index;
       }
      if (!vtkMRMLHierarchyNode::GetAssociatedHierarchyNode(d->MRMLScene, n->GetID()))
        {
        ++index;
        }
      vtkMRMLHierarchyNode* hierarchy = vtkMRMLHierarchyNode::SafeDownCast(n);
      if (hierarchy && hierarchy->GetAssociatedNode())
        {
        // if the current node is a hierarchynode associated with the node,
        // then it should have been caught at the beginning of the function
        Q_ASSERT(strcmp(nodeId, hierarchy->GetAssociatedNodeID()));
        ++index;
        }
      }
    }
  return -1;

}

//------------------------------------------------------------------------------
vtkMRMLNode* qMRMLSceneDisplayableHierarchyModel::parentNode(vtkMRMLNode* node)const
{
  vtkMRMLDisplayableHierarchyNode *dhnode = vtkMRMLDisplayableHierarchyNode::SafeDownCast(
    this->Superclass::parentNode(node));
  // if the returned parent node is hidden from editors but has an associated
  // node, return that instead.
  if (dhnode && dhnode->GetHideFromEditors() &&
      dhnode->GetDisplayableNode())
    {
//    std::cout << "DisplayableHierarchyModel::parentNode: for node " << node->GetID() << ", have a node with a hidden parent: " << dhnode->GetID() << " which has a displayable node: " << dhnode->GetDisplayableNodeID() << std::endl;
    return vtkMRMLDisplayableNode::SafeDownCast(dhnode->GetDisplayableNode());
    }
  else
    {
    return dhnode;
    }
}

//------------------------------------------------------------------------------
bool qMRMLSceneDisplayableHierarchyModel::canBeAChild(vtkMRMLNode* node)const
{
  if (!node)
    {
    return false;
    }
  return node->IsA("vtkMRMLDisplayableHierarchyNode") || node->IsA("vtkMRMLDisplayableNode");
}

//------------------------------------------------------------------------------
bool qMRMLSceneDisplayableHierarchyModel::canBeAParent(vtkMRMLNode* node)const
{
  vtkMRMLDisplayableHierarchyNode* hnode = vtkMRMLDisplayableHierarchyNode::SafeDownCast(node);
//  if (hnode && hnode->GetDisplayableNodeID() == 0)
//    {
//    return true;
//    }
  if (hnode)
    {
    return true;
    }
  //std::cout << "DisplayableHierarchyModel::canBeAParent: returning false because a hierarchy node is null " << std::endl;
  // probably need to tweak here to say can be a parent if there's an
  // associated node
  return false;
}

//------------------------------------------------------------------------------
void qMRMLSceneDisplayableHierarchyModel::updateItemDataFromNode(QStandardItem* item, vtkMRMLNode* node, int column)
{
//  Q_D(qMRMLSceneDisplayableHierarchyModel);

  this->Superclass::updateItemDataFromNode(item, node, column);

  if (!node)
    {
    return;
    }
  // the superclass update call won't work on annotation nodes as they've
  // got a different call to get the visibility flag
  if (!node->IsA("vtkMRMLAnnotationNode"))
    {
    return;
    }
  if (column == this->visibilityColumn())
    {
    vtkMRMLAnnotationNode *annotationNode = vtkMRMLAnnotationNode::SafeDownCast(node);
    if (annotationNode)
      {
      // update the icon
      if (annotationNode->GetDisplayVisibility())
        {
        item->setIcon(QIcon(":Icons/VisibleOn.png"));
        }
      else
        {
        item->setIcon(QIcon(":Icons/VisibleOff.png"));
        }
      }
    }
}
