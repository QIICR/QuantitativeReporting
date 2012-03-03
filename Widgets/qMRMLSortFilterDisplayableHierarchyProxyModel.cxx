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
#include "qMRMLSceneModel.h"
#include "qMRMLSortFilterDisplayableHierarchyProxyModel.h"

// VTK includes
#include <vtkMRMLHierarchyNode.h>

// -----------------------------------------------------------------------------
// qMRMLSortFilterDisplayableHierarchyProxyModelPrivate

// -----------------------------------------------------------------------------
class qMRMLSortFilterDisplayableHierarchyProxyModelPrivate
{
public:
  qMRMLSortFilterDisplayableHierarchyProxyModelPrivate();
};

// -----------------------------------------------------------------------------
qMRMLSortFilterDisplayableHierarchyProxyModelPrivate::qMRMLSortFilterDisplayableHierarchyProxyModelPrivate()
{
}

// -----------------------------------------------------------------------------
// qMRMLSortFilterDisplayableHierarchyProxyModel

//------------------------------------------------------------------------------
qMRMLSortFilterDisplayableHierarchyProxyModel::qMRMLSortFilterDisplayableHierarchyProxyModel(QObject *vparent)
  : qMRMLSortFilterProxyModel(vparent)
  , d_ptr(new qMRMLSortFilterDisplayableHierarchyProxyModelPrivate)
{
}

//------------------------------------------------------------------------------
qMRMLSortFilterDisplayableHierarchyProxyModel::~qMRMLSortFilterDisplayableHierarchyProxyModel()
{
}

//------------------------------------------------------------------------------
bool qMRMLSortFilterDisplayableHierarchyProxyModel
::filterAcceptsRow(int source_row, const QModelIndex &source_parent)const
{
  //Q_D(const qMRMLSortFilterDisplayableHierarchyProxyModel);
  bool res = this->Superclass::filterAcceptsRow(source_row, source_parent);
  // the superclass will return true in all the cases we want to accept
  if (res)
    {
    return res;
    }
  // but we want to over ride some false cases to return true
  //std::cout << "qMRMLSortFilterDisplayableHierarchyProxyModel::filterAcceptsRow: superclass returned false for source_row " << source_row << std::endl;

  // this might fail if Superclass::filterAcceptsRow returned false 
  QStandardItem* parentItem = this->sourceItem(source_parent);
  if (!parentItem)
    {
    return res;
    }
  QStandardItem* item = 0;
  // Sometimes the row is not complete, search for a non null item
  for (int childIndex = 0; childIndex < parentItem->columnCount(); ++childIndex)
    {
    item = parentItem->child(source_row, childIndex);
    if (item)
      {
      break;
      }
    }
  Q_ASSERT(item);
  qMRMLSceneModel* sceneModel = qobject_cast<qMRMLSceneModel*>(
    this->sourceModel());
  vtkMRMLNode* node = sceneModel->mrmlNodeFromItem(item);
  vtkMRMLHierarchyNode* hNode = vtkMRMLHierarchyNode::SafeDownCast(node);
  if (!hNode)
    {
    return res;
    }
//  std::cout << "qMRMLSortFilterDisplayableHierarchyProxyModel::filterAcceptsRow: have a hierarchy node " << hNode->GetName() << ": " << hNode->GetID() << ", hide from editors is " << hNode->GetHideFromEditors() << ", res is currently " << (res ? "true" : "false") << std::endl;
  // Show vtkMRMLHierarchyNode if they are tied to a vtkMRMLDisplayableNode
  if (hNode->GetAssociatedNode())
    {
    /// does it have children as well?
    if (hNode->GetNumberOfChildrenNodes())
      {
      return true;
      }
    else
      {
//      std::cout << "qMRMLSortFilterDisplayableHierarchyProxyModel::filterAcceptsRow: have a hierarchy node with just an associated node: " << hNode->GetName() << ": " << hNode->GetID() << ", returning false" << std::endl;
      return false;
      }
    }
  return res;
}
