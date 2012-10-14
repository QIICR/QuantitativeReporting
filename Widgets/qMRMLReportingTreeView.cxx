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
#include <QDebug>
#include <QHeaderView>
#include <QInputDialog>
#include <QMenu>
#include <QMouseEvent>
#include <QScrollBar>

// qMRML includes
#include "qMRMLItemDelegate.h"
#include "qMRMLSceneDisplayableModel.h"
#include "qMRMLSceneDisplayableHierarchyModel.h"
#include "qMRMLSceneModelHierarchyModel.h"
#include "qMRMLSceneTransformModel.h"
#include "qMRMLSortFilterHierarchyProxyModel.h"
#include "qMRMLSortFilterDisplayableHierarchyProxyModel.h"
#include "qMRMLReportingTreeView_p.h"

// MRML includes
#include <vtkMRMLAnnotationNode.h>
#include <vtkMRMLAnnotationControlPointsNode.h>
#include <vtkMRMLDisplayNode.h>
#include <vtkMRMLDisplayableHierarchyNode.h>
#include <vtkMRMLDisplayableNode.h>
#include <vtkMRMLModelNode.h>
#include <vtkMRMLModelHierarchyLogic.h>
#include <vtkMRMLModelHierarchyNode.h>
#include <vtkMRMLScene.h>
#include <vtkMRMLSliceNode.h>

//------------------------------------------------------------------------------
qMRMLReportingTreeViewPrivate::qMRMLReportingTreeViewPrivate(qMRMLReportingTreeView& object)
  : q_ptr(&object)
{
  this->SceneModel = 0;
  this->SortFilterModel = 0;
  this->FitSizeToVisibleIndexes = true;
  this->TreeViewSizeHint = QSize();
  this->NodeMenu = 0;
  this->EditAction = 0;
  this->SceneMenu = 0;

  this->JumpToAnnotationAction = 0;
}
//------------------------------------------------------------------------------
qMRMLReportingTreeViewPrivate::~qMRMLReportingTreeViewPrivate()
{
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeViewPrivate::init()
{
  Q_Q(qMRMLReportingTreeView);

  q->setItemDelegate(new qMRMLItemDelegate(q));
  q->setAutoScrollMargin(32); // scroll hot area sensitivity

  this->updateTreeViewModel();
  
  //ctkModelTester * tester = new ctkModelTester(p);
  //tester->setModel(this->SortFilterModel);
  //QObject::connect(q, SIGNAL(activated(QModelIndex)),
  //                 q, SLOT(onActivated(QModelIndex)));
  //QObject::connect(q, SIGNAL(clicked(QModelIndex)),
  //                 q, SLOT(onActivated(QModelIndex)));

  q->setUniformRowHeights(true);
  
  QObject::connect(q, SIGNAL(collapsed(QModelIndex)),
                   q, SLOT(onNumberOfVisibleIndexChanged()));
  QObject::connect(q, SIGNAL(expanded(QModelIndex)),
                   q, SLOT(onNumberOfVisibleIndexChanged()));
//QObject::connect(q->header(), SIGNAL(sectionResized(int,int,int)),
  //                  q, SLOT(onSectionResized()));
  q->horizontalScrollBar()->installEventFilter(q);
  
  this->NodeMenu = new QMenu(q);

  // rename node
  QAction* renameAction =
    new QAction(qMRMLReportingTreeView::tr("Rename"),this->NodeMenu);
  this->NodeMenu->addAction(renameAction);
  QObject::connect(renameAction, SIGNAL(triggered()),
                   q, SLOT(renameCurrentNode()));

  // delete node
  QAction* deleteAction =
    new QAction(qMRMLReportingTreeView::tr("Delete"),this->NodeMenu);
  this->NodeMenu->addAction(deleteAction);
  QObject::connect(deleteAction, SIGNAL(triggered()),
                   q, SLOT(deleteCurrentNode()));
  // EditAction is hidden by default
  this->EditAction =
    new QAction(qMRMLReportingTreeView::tr("Edit properties..."), this->NodeMenu);
  QObject::connect(this->EditAction, SIGNAL(triggered()),
                   q, SLOT(editCurrentNode()));

  QObject::connect(q, SIGNAL(clicked(QModelIndex)),
                   q, SLOT(onClicked(QModelIndex)));

  // jump to slice
  this->JumpToAnnotationAction = new QAction(QAction::tr("Jump to Annotation"), q);
  QObject::connect(this->JumpToAnnotationAction, SIGNAL(triggered()),
          q, SLOT(jumpToAnnotation()));
  
  this->SceneMenu = new QMenu(q);
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeViewPrivate::updateTreeViewModel()
{
  Q_Q(qMRMLReportingTreeView); 

  this->setSortFilterProxyModel(new qMRMLSortFilterDisplayableHierarchyProxyModel(q));
  q->setSceneModelType(QString("DisplayableHierarchy"));

  // we only want to show nodeTypes = ['vtkMRMLDisplayableHierarchyNode', 'vtkMRMLAnnotationHierarchyNode', 'vtkMRMLAnnotationNode', 'vtkMRMLVolumeNode', 'vtkMRMLReportingReportNode']
  QStringList nodeTypes = QStringList();
  nodeTypes.append("vtkMRMLAnnotationNode");
  nodeTypes.append("vtkMRMLAnnotationHierarchyNode");
  nodeTypes.append("vtkMRMLVolumeNode");
  nodeTypes.append("vtkMRMLReportingReportNode");
  nodeTypes.append("vtkMRMLDisplayableHierarchyNode");

  q->setNodeTypes(nodeTypes);

  // hide the visibility column for now
  //q->sceneModel()->setVisibilityColumn(-1);
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeViewPrivate::setSceneModel(qMRMLSceneModel* newModel)
{
  Q_Q(qMRMLReportingTreeView);
  if (!newModel)
    {
    return;
    }

  newModel->setMRMLScene(q->mrmlScene());

  this->SceneModel = newModel;
  this->SortFilterModel->setSourceModel(this->SceneModel);
  //q->expandToDepth(2);
  q->expandAll();
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeViewPrivate::setSortFilterProxyModel(qMRMLSortFilterProxyModel* newSortModel)
{
  Q_Q(qMRMLReportingTreeView);
  if (newSortModel == this->SortFilterModel)
    {
    return;
    }
  
  // delete the previous filter
  delete this->SortFilterModel;
  this->SortFilterModel = newSortModel;
  // Set the input of the view
  // if no filter is given then let's show the scene model directly
  q->QTreeView::setModel(this->SortFilterModel
    ? static_cast<QAbstractItemModel*>(this->SortFilterModel)
    : static_cast<QAbstractItemModel*>(this->SceneModel));
  // Setting a new model to the view resets the selection model
  QObject::connect(q->selectionModel(), SIGNAL(currentRowChanged(QModelIndex,QModelIndex)),
                   q, SLOT(onCurrentRowChanged(QModelIndex)));
  if (!this->SortFilterModel)
    {
    return;
    }
  this->SortFilterModel->setParent(q);
  // Set the input of the filter
  this->SortFilterModel->setSourceModel(this->SceneModel);

  // resize the view if new rows are added/removed
  QObject::connect(this->SortFilterModel, SIGNAL(rowsAboutToBeRemoved(QModelIndex,int,int)),
                   q, SLOT(onNumberOfVisibleIndexChanged()));
  QObject::connect(this->SortFilterModel, SIGNAL(rowsInserted(QModelIndex,int,int)),
                   q, SLOT(onNumberOfVisibleIndexChanged()));

//  q->expandToDepth(2);
  q->expandAll();
  q->onNumberOfVisibleIndexChanged();
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeViewPrivate::recomputeSizeHint(bool force)
{
  Q_Q(qMRMLReportingTreeView);
  this->TreeViewSizeHint = QSize();
  if ((this->FitSizeToVisibleIndexes || force) && q->isVisible())
    {
    // TODO: if the number of items changes often, don't update geometry,
    // it might be too expensive, maybe use a timer
    q->updateGeometry();
    }
}

//------------------------------------------------------------------------------
QSize qMRMLReportingTreeViewPrivate::sizeHint()const
{
  Q_Q(const qMRMLReportingTreeView);
  if (!this->FitSizeToVisibleIndexes)
    {
    return q->QTreeView::sizeHint();
    }
  if (this->TreeViewSizeHint.isValid())
    {
    return this->TreeViewSizeHint;
    }
  int visibleIndexCount = 0;
  for(QModelIndex index = this->SortFilterModel->mrmlSceneIndex();
      index.isValid();
      index = q->indexBelow(index))
    {
    ++visibleIndexCount;
    }

  this->TreeViewSizeHint = q->QTreeView::sizeHint();
  this->TreeViewSizeHint.setHeight(
    q->frameWidth()
    + (q->isHeaderHidden() ? 0 : q->header()->sizeHint().height())
    + visibleIndexCount * q->sizeHintForRow(0)
    + (q->horizontalScrollBar()->isVisibleTo(const_cast<qMRMLReportingTreeView*>(q)) ? q->horizontalScrollBar()->height() : 0)
    + q->frameWidth());
  // Add half a line to give some space under the tree
  this->TreeViewSizeHint.rheight() += q->sizeHintForRow(0) / 2;
  return this->TreeViewSizeHint;
}

//------------------------------------------------------------------------------
// qMRMLReportingTreeView
//------------------------------------------------------------------------------
qMRMLReportingTreeView::qMRMLReportingTreeView(QWidget *_parent)
  :QTreeView(_parent)
  , d_ptr(new qMRMLReportingTreeViewPrivate(*this))
{
  Q_D(qMRMLReportingTreeView);
  d->init();
}

//------------------------------------------------------------------------------
qMRMLReportingTreeView::~qMRMLReportingTreeView()
{
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::setMRMLScene(vtkMRMLScene* scene)
{
  Q_D(qMRMLReportingTreeView);
  Q_ASSERT(d->SortFilterModel);
  // only qMRMLSceneModel needs the scene, the other proxies don't care.
  d->SceneModel->setMRMLScene(scene);

  // listen for import end events
  qvtkReconnect(this->mrmlScene(), scene,
                vtkMRMLScene::EndImportEvent,
                this, SLOT(onEndImportEvent()));
  
  this->expandAll();
//  this->expandToDepth(2);  
}

//------------------------------------------------------------------------------
QString qMRMLReportingTreeView::sceneModelType()const
{
  Q_D(const qMRMLReportingTreeView);
  return d->SceneModelType;
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::setSceneModelType(const QString& modelName)
{
  Q_D(qMRMLReportingTreeView);

  qMRMLSceneModel* newModel = 0;
  qMRMLSortFilterProxyModel* newFilterModel = d->SortFilterModel;
  // switch on the incoming model name
  if (modelName == QString("Transform"))
    {
    newModel = new qMRMLSceneTransformModel(this);
    }
  else if (modelName == QString("Displayable"))
    {
    newModel = new qMRMLSceneDisplayableModel(this);
    }
  else if (modelName == QString("ModelHierarchy"))
    {
    newModel = new qMRMLSceneModelHierarchyModel(this);
    newFilterModel = new qMRMLSortFilterHierarchyProxyModel(this);
    }
  else if (modelName == QString("DisplayableHierarchy"))
    {
    newModel = new qMRMLSceneDisplayableHierarchyModel(this);
    newFilterModel = new qMRMLSortFilterDisplayableHierarchyProxyModel(this);
    }
  else if (modelName == QString(""))
    {
    newModel = new qMRMLSceneModel(this);
    }
  else
    {
    std::cout << "Unknown model name: " << modelName.toAscii().data() << std::endl;
    }
  if (newModel)
    {
    d->SceneModelType = modelName;
    newModel->setListenNodeModifiedEvent(this->listenNodeModifiedEvent());
    }
  if (newFilterModel)
    {
    newFilterModel->setNodeTypes(this->nodeTypes());
    newFilterModel->setShowHidden(this->showHidden());
    }
  d->setSceneModel(newModel);
  // typically a no op except for ModelHierarchy
  d->setSortFilterProxyModel(newFilterModel);
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::setSceneModel(qMRMLSceneModel* newSceneModel, const QString& modelType)
{
  Q_D(qMRMLReportingTreeView);

  if (!newSceneModel) 
    {
    return;
    }
  d->SceneModelType = modelType;
  d->setSceneModel(newSceneModel);
}

//------------------------------------------------------------------------------
vtkMRMLScene* qMRMLReportingTreeView::mrmlScene()const
{
  Q_D(const qMRMLReportingTreeView);
  return d->SceneModel ? d->SceneModel->mrmlScene() : 0;
}

//------------------------------------------------------------------------------
vtkMRMLNode* qMRMLReportingTreeView::currentNode()const
{
  Q_D(const qMRMLReportingTreeView);
  return d->SortFilterModel->mrmlNodeFromIndex(this->selectionModel()->currentIndex());
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::onCurrentRowChanged(const QModelIndex& index)
{
  Q_D(qMRMLReportingTreeView);
  Q_ASSERT(d->SortFilterModel);
  Q_ASSERT(this->currentNode() == d->SortFilterModel->mrmlNodeFromIndex(index));
  emit currentNodeChanged(d->SortFilterModel->mrmlNodeFromIndex(index));
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::setListenNodeModifiedEvent(bool listen)
{
  Q_D(qMRMLReportingTreeView);
  Q_ASSERT(d->SceneModel);
  d->SceneModel->setListenNodeModifiedEvent(listen);
}

//------------------------------------------------------------------------------
bool qMRMLReportingTreeView::listenNodeModifiedEvent()const
{
  Q_D(const qMRMLReportingTreeView);
  return d->SceneModel ? d->SceneModel->listenNodeModifiedEvent() : true;
}

// --------------------------------------------------------------------------
QStringList qMRMLReportingTreeView::nodeTypes()const
{
  return this->sortFilterProxyModel()->nodeTypes();
}

// --------------------------------------------------------------------------
void qMRMLReportingTreeView::setNodeTypes(const QStringList& _nodeTypes)
{
  this->sortFilterProxyModel()->setNodeTypes(_nodeTypes);
}

//--------------------------------------------------------------------------
bool qMRMLReportingTreeView::isEditMenuActionVisible()const
{
  Q_D(const qMRMLReportingTreeView);
  return d->NodeMenu->actions().contains(d->EditAction);
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::setEditMenuActionVisible(bool show)
{
  Q_D(qMRMLReportingTreeView);
  if (show)
    {
    // Prepend the action in the menu
    this->prependNodeMenuAction(d->EditAction);
    }
  else
    {
    d->NodeMenu->removeAction(d->EditAction);
    }
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::prependNodeMenuAction(QAction* action)
{
  Q_D(qMRMLReportingTreeView);
  // Prepend the action in the menu
  d->NodeMenu->insertAction(d->NodeMenu->actions()[0], action);
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::prependSceneMenuAction(QAction* action)
{
  Q_D(qMRMLReportingTreeView);
  // Prepend the action in the menu
  QAction* beforeAction =
    d->SceneMenu->actions().size() ? d->SceneMenu->actions()[0] : 0;
  d->SceneMenu->insertAction(beforeAction, action);
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::removeNodeMenuAction(QAction* action)
{
  Q_D(qMRMLReportingTreeView);
  d->NodeMenu->removeAction(action);
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::editCurrentNode()
{
  if (!this->currentNode())
    {
    // not sure if it's a request to have a valid node.
    Q_ASSERT(this->currentNode());
    return;
    }
  emit editNodeRequested(this->currentNode());
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::setRootNode(vtkMRMLNode* rootNode)
{
  qvtkReconnect(this->rootNode(), rootNode, vtkCommand::ModifiedEvent,
                this, SLOT(updateRootNode(vtkObject*)));
  this->setRootIndex(this->sortFilterProxyModel()->indexFromMRMLNode(rootNode));
}

//--------------------------------------------------------------------------
vtkMRMLNode* qMRMLReportingTreeView::rootNode()const
{
  return this->sortFilterProxyModel()->mrmlNodeFromIndex(this->rootIndex());
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::updateRootNode(vtkObject* node)
{
  // Maybe the node has changed of QModelIndex, need to resync
  this->setRootNode(vtkMRMLNode::SafeDownCast(node));
}

//--------------------------------------------------------------------------
qMRMLSortFilterProxyModel* qMRMLReportingTreeView::sortFilterProxyModel()const
{
  Q_D(const qMRMLReportingTreeView);
  Q_ASSERT(d->SortFilterModel);
  return d->SortFilterModel;
}

//--------------------------------------------------------------------------
qMRMLSceneModel* qMRMLReportingTreeView::sceneModel()const
{
  Q_D(const qMRMLReportingTreeView);
  Q_ASSERT(d->SceneModel);
  return d->SceneModel;
}

//--------------------------------------------------------------------------
QSize qMRMLReportingTreeView::minimumSizeHint()const
{
  Q_D(const qMRMLReportingTreeView);
  return d->sizeHint();
}

//--------------------------------------------------------------------------
QSize qMRMLReportingTreeView::sizeHint()const
{
  Q_D(const qMRMLReportingTreeView);
  return d->sizeHint();
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::updateGeometries()
{
  // don't update the geometries if it's not visible on screen
  // UpdateGeometries is for tree child widgets geometry
  if (!this->isVisible())
    {
    return;
    }
  this->QTreeView::updateGeometries();
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::onNumberOfVisibleIndexChanged()
{
  Q_D(qMRMLReportingTreeView);
  d->recomputeSizeHint();
}

//--------------------------------------------------------------------------
void qMRMLReportingTreeView::setFitSizeToVisibleIndexes(bool enable)
{
  Q_D(qMRMLReportingTreeView);
  d->FitSizeToVisibleIndexes = enable;
  d->recomputeSizeHint(true);
}

//--------------------------------------------------------------------------
bool qMRMLReportingTreeView::fitSizeToVisibleIndexes()const
{
  Q_D(const qMRMLReportingTreeView);
  return d->FitSizeToVisibleIndexes;
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::mousePressEvent(QMouseEvent* e)
{
  Q_D(qMRMLReportingTreeView);
  this->QTreeView::mousePressEvent(e);
  
  if (e->button() != Qt::RightButton)
    {
    return;
    }
  // get the index of the current column
  QModelIndex index = this->indexAt(e->pos());
  
  vtkMRMLNode* node = this->sortFilterProxyModel()->mrmlNodeFromIndex(index);
  
  if (node)
    {
    d->NodeMenu->exec(e->globalPos());
    }
  else if (index == this->sortFilterProxyModel()->mrmlSceneIndex())
    {
    d->SceneMenu->exec(e->globalPos());
    }
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::mouseReleaseEvent(QMouseEvent* e)
{
  if (e->button() == Qt::LeftButton)
    {
    // get the index of the current column
    QModelIndex index = this->indexAt(e->pos());
    QStyleOptionViewItemV4 opt = this->viewOptions();
    opt.rect = this->visualRect(index);
    qobject_cast<qMRMLItemDelegate*>(this->itemDelegate())->initStyleOption(&opt,index);
    QRect decorationElement =
      this->style()->subElementRect(QStyle::SE_ItemViewItemDecoration, &opt, this);
    //decorationElement.translate(this->visualRect(index).topLeft());
    if (decorationElement.contains(e->pos()))  
      {
      if (this->onDecorationClicked(index))
        {
        return;
        }
      }
    }

  this->QTreeView::mouseReleaseEvent(e);
}

//------------------------------------------------------------------------------
bool qMRMLReportingTreeView::onDecorationClicked(const QModelIndex& index)
{
  QModelIndex sourceIndex = this->sortFilterProxyModel()->mapToSource(index);
  if (!(sourceIndex.flags() & Qt::ItemIsEnabled))
    {
    return false;
    }
  if (sourceIndex.column() == this->sceneModel()->visibilityColumn())
    {
    this->toggleVisibility(index);
    return true;
    }
  return false;
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::onClicked(const QModelIndex& index)
{

  Q_D(qMRMLReportingTreeView);

  vtkMRMLNode *mrmlNode = d->SortFilterModel->mrmlNodeFromIndex(index);
  if (!mrmlNode)
    {
    return;
    }
    // if the user clicked on an annotation node, insert an action
  if(mrmlNode->IsA("vtkMRMLAnnotationNode"))
    {
    this->prependNodeMenuAction(d->JumpToAnnotationAction);
    }
  else
    {
    this->removeNodeMenuAction(d->JumpToAnnotationAction);
    }

  // check if user clicked on icon, this can happen even after we marked a
  // hierarchy as active
  /*
  if (index.column() == this->sceneModel()->visibilityColumn())
    {
    // user wants to toggle the visibility of the annotation
    this->onVisibilityColumnClicked(mrmlNode);
    }
  */
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::toggleVisibility(const QModelIndex& index)
{
  vtkMRMLNode* node = this->sortFilterProxyModel()->mrmlNodeFromIndex(index);
  
  vtkMRMLAnnotationNode *annotationNode = vtkMRMLAnnotationNode::SafeDownCast(node);
  vtkMRMLDisplayNode* displayNode =
    vtkMRMLDisplayNode::SafeDownCast(node);
  vtkMRMLDisplayableNode* displayableNode =
    vtkMRMLDisplayableNode::SafeDownCast(node);
  vtkMRMLDisplayableHierarchyNode* displayableHierarchyNode =
      vtkMRMLDisplayableHierarchyNode::SafeDownCast(node);
  int visibility = -1;
  if (displayableHierarchyNode)
    {
    vtkMRMLDisplayNode *hierDisplayNode = displayableHierarchyNode->GetDisplayNode();
    if (hierDisplayNode)
      {
      visibility = (hierDisplayNode->GetVisibility() ? 0 : 1);
      }
    this->mrmlScene()->StartState(vtkMRMLScene::BatchProcessState);
    vtkMRMLModelHierarchyLogic::SetChildrenVisibility(displayableHierarchyNode,visibility);
    this->mrmlScene()->EndState(vtkMRMLScene::BatchProcessState);
    }
  else if (annotationNode)
    {
    //visibility = !annotationNode->GetVisible();
    //annotationNode->SetVisible(visibility);
    }
  else if (displayNode)
    {
    visibility = displayNode->GetVisibility() ? 0 : 1;
    displayNode->SetVisibility(visibility);
    }
  else if (displayableNode)
    {
    visibility = displayableNode->GetDisplayVisibility() ? 0 : 1;
    displayableNode->SetDisplayVisibility(visibility);
    }
 
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::renameCurrentNode()
{
  if (!this->currentNode())
    {
    Q_ASSERT(this->currentNode());
    return;
    }
  // pop up an entry box for the new name, with the old name as default
  QString oldName = this->currentNode()->GetName();

  bool ok = false;
  QString newName = QInputDialog::getText(
    this, "Rename " + oldName, "New name:",
    QLineEdit::Normal, oldName, &ok);
  if (!ok)
    {
    return;
    }
  this->currentNode()->SetName(newName.toLatin1());

}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::deleteCurrentNode()
{
//  Q_D(qMRMLReportingTreeView);

  if (!this->currentNode())
    {
    Q_ASSERT(this->currentNode());
    return;
    }
  this->mrmlScene()->RemoveNode(this->currentNode());
}

//------------------------------------------------------------------------------
bool qMRMLReportingTreeView::isAncestor(const QModelIndex& index, const QModelIndex& potentialAncestor)
{
  QModelIndex ancestor = index.parent();
  while(ancestor.isValid())
    {
    if (ancestor == potentialAncestor)
      {
      return true;
      }
    ancestor = ancestor.parent();
    }
  return false;
}

//------------------------------------------------------------------------------
QModelIndex qMRMLReportingTreeView::findAncestor(const QModelIndex& index, const QModelIndexList& potentialAncestors)
{
  foreach(const QModelIndex& potentialAncestor, potentialAncestors)
    {
    if (qMRMLReportingTreeView::isAncestor(index, potentialAncestor))
      {
      return potentialAncestor;
      }
    }
  return QModelIndex();
}

//------------------------------------------------------------------------------
QModelIndexList qMRMLReportingTreeView::removeChildren(const QModelIndexList& indexes)
{
  QModelIndexList noAncestorIndexList;
  foreach(QModelIndex index, indexes)
    {
    if (!qMRMLReportingTreeView::findAncestor(index, indexes).isValid())
      {
      noAncestorIndexList << index;
      }
    }
  return noAncestorIndexList;
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::showEvent(QShowEvent* event)
{
  Q_D(qMRMLReportingTreeView);
  this->Superclass::showEvent(event);
  if (d->FitSizeToVisibleIndexes &&
      !d->TreeViewSizeHint.isValid())
    {
    this->updateGeometry();
    }
}

//------------------------------------------------------------------------------
bool qMRMLReportingTreeView::eventFilter(QObject* object, QEvent* e)
{
  Q_D(qMRMLReportingTreeView);
  bool res = this->QTreeView::eventFilter(object, e);
  // When the horizontal scroll bar is shown/hidden, the sizehint should be
  // updated ?
  if (d->FitSizeToVisibleIndexes &&
      object == this->horizontalScrollBar() &&
      (e->type() == QEvent::Show ||
       e->type() == QEvent::Hide))
    {
    d->recomputeSizeHint();
    }
  return res;
}

//-----------------------------------------------------------------------------
void qMRMLReportingTreeView::onEndImportEvent()
{
  Q_D(qMRMLReportingTreeView);
  qDebug() << "onEndImportEvent";

  d->updateTreeViewModel();

//  qDebug() << "onEndImportEvent: after updating tree view model";
}

//------------------------------------------------------------------------------
void qMRMLReportingTreeView::jumpToAnnotation()
{
//  Q_Q(qMRMLReportingTreeView);
  qDebug() << "jumpToAnnotation";
  if (!this->mrmlScene())
    {
    qDebug() << "No Scene";
    return;
    }
  // get the currently selected node
  const char *id = this->firstSelectedNode();
  if (!id)
    {
    qDebug() << "No id for first selected node";
    return;
    }
  vtkMRMLNode* node = this->mrmlScene()->GetNodeByID(id);
  if (!node ||
      !node->IsA("vtkMRMLAnnotationNode"))
    {
    qDebug() << "Not an annotation node with id " << id;
    return;
    }

  vtkMRMLAnnotationNode* annotationNode = vtkMRMLAnnotationNode::SafeDownCast(node);
  
  if (!annotationNode)
    {
    return;
    }

  vtkMRMLAnnotationControlPointsNode* controlpointsNode = vtkMRMLAnnotationControlPointsNode::SafeDownCast(annotationNode);
  
  if (!controlpointsNode)
    {
    // we don't have a controlpointsNode so we can not jump the slices
    qDebug() << "Not a control points node with id " << id;
    return;
    }

  // get the slice node so can jump slices
  vtkMRMLNode *mrmlSliceNode = this->mrmlScene()->GetNthNodeByClass(0,"vtkMRMLSliceNode");
  if (!mrmlSliceNode)
    {
    qDebug() << "No slice node found";
    return;
    }
  vtkMRMLSliceNode *sliceNode = vtkMRMLSliceNode::SafeDownCast(mrmlSliceNode);
  if (!sliceNode)
    {
    qDebug() << "Can't cast to a vtkMRMLSliceNode";
    return;
    }

  // jump to slices, only consider the first control point
  double *rasCoordinates = controlpointsNode->GetControlPointCoordinates(0);
  double r = rasCoordinates[0];
  double a = rasCoordinates[1];
  double s = rasCoordinates[2];
  
  sliceNode->JumpAllSlices(r,a,s);
  // JumpAllSlices jumps all the other slices, not self, so JumpSlice on
  // this node as well
  sliceNode->JumpSlice(r,a,s);
}

//------------------------------------------------------------------------------
const char * qMRMLReportingTreeView::firstSelectedNode()
{
  Q_D(qMRMLReportingTreeView);
  QModelIndexList selected = this->selectedIndexes();

  // first, check if we selected anything
  if (selected.isEmpty())
    {
    return 0;
    }

  // now get the first selected item
  QModelIndex index = selected.first();

  // check if it is a valid node
  if (!d->SortFilterModel->mrmlNodeFromIndex(index))
    {
    return 0;
    }

  return d->SortFilterModel->mrmlNodeFromIndex(index)->GetID();
}

//-----------------------------------------------------------------------------
void qMRMLReportingTreeView::updateTreeView()
{
  Q_D(qMRMLReportingTreeView);

  d->updateTreeViewModel();
}
