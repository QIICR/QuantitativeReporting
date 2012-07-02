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

#ifndef __qMRMLSortFilterDisplayableHierarchyProxyModel_h
#define __qMRMLSortFilterDisplayableHierarchyProxyModel_h

// qMRML includes


#include "qMRMLSortFilterProxyModel.h"

#include "qSlicerReportingModuleWidgetsExport.h"

class qMRMLSortFilterDisplayableHierarchyProxyModelPrivate;

class Q_SLICER_REPORTING_MODULE_WIDGETS_EXPORT qMRMLSortFilterDisplayableHierarchyProxyModel
  : public qMRMLSortFilterProxyModel
{
  Q_OBJECT
public:
  typedef qMRMLSortFilterProxyModel Superclass;
  qMRMLSortFilterDisplayableHierarchyProxyModel(QObject *parent=0);
  virtual ~qMRMLSortFilterDisplayableHierarchyProxyModel();

protected:
  // Show vtkMRMLHierarchyNode if they are tied to a vtkMRMLModelNode
  virtual bool filterAcceptsRow(int source_row, const QModelIndex &source_parent)const;
  
protected:
  QScopedPointer<qMRMLSortFilterDisplayableHierarchyProxyModelPrivate> d_ptr;

private:
  Q_DECLARE_PRIVATE(qMRMLSortFilterDisplayableHierarchyProxyModel);
  Q_DISABLE_COPY(qMRMLSortFilterDisplayableHierarchyProxyModel);
};

#endif
