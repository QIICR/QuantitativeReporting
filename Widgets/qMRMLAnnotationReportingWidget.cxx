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
#include <vtkMRMLAnnotationReportingNode.h>

// qMRML includes
#include "qMRMLAnnotationReportingWidget.h"

class qMRMLAnnotationReportingWidgetPrivate: public QWidget // Ui_qMRMLAnnotationReportingWidget
{
  Q_DECLARE_PUBLIC(qMRMLAnnotationReportingWidget);
protected:
  qMRMLAnnotationReportingWidget* const q_ptr;

public:
  qMRMLAnnotationReportingWidgetPrivate(qMRMLAnnotationReportingWidget& object);
  void init();
  
};

qMRMLAnnotationReportingWidgetPrivate::qMRMLAnnotationReportingWidgetPrivate(qMRMLAnnotationReportingWidget& object) : q_ptr(&object)
{
}

void qMRMLAnnotationReportingWidgetPrivate::init()
{
//  Q_Q(qMRMLAnnotationReportingWidget);
  //this->setupUi(q);
}

//------------------------------------------------------------------------------
// qMRMLAnnotationReportingWidget methods

// --------------------------------------------------------------------------
qMRMLAnnotationReportingWidget::qMRMLAnnotationReportingWidget(QWidget* widget)
  : Superclass(widget)
  , d_ptr(new qMRMLAnnotationReportingWidgetPrivate(*this))
{
  Q_D(qMRMLAnnotationReportingWidget);
  d->init();
}

// --------------------------------------------------------------------------
qMRMLAnnotationReportingWidget::~qMRMLAnnotationReportingWidget()
{
}

//------------------------------------------------------------------------------
void qMRMLAnnotationReportingWidget::setMRMLScene(vtkMRMLScene* scene)
{
//  Q_D(qMRMLAnnotationReportingWidget);
}

//------------------------------------------------------------------------------
vtkMRMLScene* qMRMLAnnotationReportingWidget::mrmlScene()const
{
//  Q_D(const qMRMLAnnotationReportingWidget);
    vtkMRMLScene *scene = NULL;
    return scene;
}
