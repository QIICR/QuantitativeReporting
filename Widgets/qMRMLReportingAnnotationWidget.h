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

==============================================================================*/

#ifndef __qMRMLReportingAnnotationWidget_h
#define __qMRMLReportingAnnotationWidget_h

// Qt includes
#include <QWidget>

// CTK includes
#include "ctkVTKObject.h"

// qMRML includes
#include "qSlicerReportingModuleWidgetsExport.h"

// MRML includes

class vtkMRMLReportingAnnotationNode;
class qMRMLReportingAnnotationWidgetPrivate;
class vtkMRMLScene;

class Q_SLICER_MODULE_REPORTING_WIDGETS_EXPORT qMRMLReportingAnnotationWidget : public QWidget
{
  Q_OBJECT
  QVTK_OBJECT
public:
  /// Superclass typedef
  typedef QWidget Superclass;

  /// Constructors
  explicit qMRMLReportingAnnotationWidget(QWidget* parent=0);
  virtual ~qMRMLReportingAnnotationWidget();

  /// Utility function that returns the mrml scene of the layout manager
  vtkMRMLScene* mrmlScene()const;

public slots:
  /// Set the MRML scene
  void setMRMLScene(vtkMRMLScene* scene);

protected:
  QScopedPointer<qMRMLReportingAnnotationWidgetPrivate> d_ptr;

private:
  Q_DECLARE_PRIVATE(qMRMLReportingAnnotationWidget);
  Q_DISABLE_COPY(qMRMLReportingAnnotationWidget);

  vtkMRMLReportingAnnotationNode* annotationNode;
};

#endif
