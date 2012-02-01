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

// MRML includes
#include <vtkMRMLReportingAnnotationNode.h>

// qMRML includes
#include "qMRMLReportingAnnotationWidget.h"

class qMRMLReportingAnnotationWidgetPrivate: public QWidget // Ui_qMRMLReportingAnnotationWidget
{
  Q_DECLARE_PUBLIC(qMRMLReportingAnnotationWidget);
protected:
  qMRMLReportingAnnotationWidget* const q_ptr;

public:
  qMRMLReportingAnnotationWidgetPrivate(qMRMLReportingAnnotationWidget& object);
  void init();
  
};

qMRMLReportingAnnotationWidgetPrivate::qMRMLReportingAnnotationWidgetPrivate(qMRMLReportingAnnotationWidget& object) : q_ptr(&object)
{
}

void qMRMLReportingAnnotationWidgetPrivate::init()
{
  Q_Q(qMRMLReportingAnnotationWidget);
  //this->setupUi(q);
}

//------------------------------------------------------------------------------
// qMRMLReportingAnnotationWidget methods

// --------------------------------------------------------------------------
qMRMLReportingAnnotationWidget::qMRMLReportingAnnotationWidget(QWidget* widget)
  : Superclass(widget)
  , d_ptr(new qMRMLReportingAnnotationWidgetPrivate(*this))
{
  Q_D(qMRMLReportingAnnotationWidget);
  d->init();
}

// --------------------------------------------------------------------------
qMRMLReportingAnnotationWidget::~qMRMLReportingAnnotationWidget()
{
}

//------------------------------------------------------------------------------
void qMRMLReportingAnnotationWidget::setMRMLScene(vtkMRMLScene* scene)
{
//  Q_D(qMRMLReportingAnnotationWidget);
}

//------------------------------------------------------------------------------
vtkMRMLScene* qMRMLReportingAnnotationWidget::mrmlScene()const
{
//  Q_D(const qMRMLReportingAnnotationWidget);
    vtkMRMLScene *scene = NULL;
    return scene;
}
