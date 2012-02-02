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
#include "qMRMLReportingAnnotationRANOWidget.h"

// CTK includes
#include <ctkComboBox.h>

// Qt includes
#include <QFormLayout>
#include <QLabel>

class qMRMLReportingAnnotationRANOWidgetPrivate
{
  Q_DECLARE_PUBLIC(qMRMLReportingAnnotationRANOWidget);
protected:
  qMRMLReportingAnnotationRANOWidget* const q_ptr;
  void setMRMLReportingAnnotationNode(vtkMRMLReportingAnnotationNode* newAnnotationNode);

public:
  qMRMLReportingAnnotationRANOWidgetPrivate(qMRMLReportingAnnotationRANOWidget& object);
  void init();

  vtkMRMLReportingAnnotationNode *annotationNode;

  // widgets
  ctkComboBox *measurableDiseaseSelector;
  ctkComboBox *nonmeasurableDiseaseSelector;
  ctkComboBox *flairSelector;

  // variables
  int measurableDiseaseIndex;
  int nonmeasurableDiseaseIndex;
  int flairIndex;
};

CTK_GET_CPP(qMRMLReportingAnnotationRANOWidget, int, measurableDiseaseIndex, measurableDiseaseIndex)
void qMRMLReportingAnnotationRANOWidget::setMeasurableDiseaseIndex(int index)
{
  Q_D(qMRMLReportingAnnotationRANOWidget);
  if(index != d->measurableDiseaseIndex)
  {
    d->measurableDiseaseIndex = index;
    // this->updateWidgetFromMRML(); // AF ASK: why would I do this? Who updates the MRML?
  }
}

CTK_GET_CPP(qMRMLReportingAnnotationRANOWidget, int, nonmeasurableDiseaseIndex, nonmeasurableDiseaseIndex)
void qMRMLReportingAnnotationRANOWidget::setNonmeasurableDiseaseIndex(int index)
{
  Q_D(qMRMLReportingAnnotationRANOWidget);
  if(index != d->nonmeasurableDiseaseIndex)
  {
    d->nonmeasurableDiseaseIndex = index;
    // this->updateWidgetFromMRML(); // AF ASK: why would I do this? Who updates the MRML?
  }
}

CTK_GET_CPP(qMRMLReportingAnnotationRANOWidget, int, flairIndex, flairIndex)
void qMRMLReportingAnnotationRANOWidget::setFlairIndex(int index)
{
  Q_D(qMRMLReportingAnnotationRANOWidget);
  if(index != d->flairIndex)
  {
    d->flairIndex = index;
    // this->updateWidgetFromMRML(); // AF ASK: why would I do this? Who updates the MRML?
  }
}

qMRMLReportingAnnotationRANOWidgetPrivate::qMRMLReportingAnnotationRANOWidgetPrivate(qMRMLReportingAnnotationRANOWidget& object)
  : q_ptr(&object)
{
  this->annotationNode = 0;

  this->measurableDiseaseSelector = 0;
  this->nonmeasurableDiseaseSelector = 0;
  this->flairSelector = 0;

  this->measurableDiseaseIndex = -1;
  this->nonmeasurableDiseaseIndex = -1;
  this->flairIndex = -1;
}

void qMRMLReportingAnnotationRANOWidgetPrivate::setMRMLReportingAnnotationNode(vtkMRMLReportingAnnotationNode *newNode)
{
  Q_Q(qMRMLReportingAnnotationRANOWidget);
  this->annotationNode = newNode;
  // TODO: update the widget here
  /*

  */
}

//------------------------------------------------------------------------------
// qMRMLReportingAnnotationRANOWidget methods

// --------------------------------------------------------------------------
qMRMLReportingAnnotationRANOWidget::qMRMLReportingAnnotationRANOWidget(QWidget* newParent)
  : Superclass(newParent)
  , d_ptr(new qMRMLReportingAnnotationRANOWidgetPrivate(*this))
{
  Q_D(qMRMLReportingAnnotationRANOWidget);
  QFormLayout *layout = new QFormLayout();
  this->setLayout(layout);
  QLabel *label = new QLabel("1 - Measurable Disease");
  d->measurableDiseaseSelector = new ctkComboBox();
  d->measurableDiseaseSelector->setDefaultText("---");
  d->measurableDiseaseSelector->addItem("Yes");
  d->measurableDiseaseSelector->addItem("No");
  d->measurableDiseaseSelector->addItem("Not Evaluable");
  d->measurableDiseaseSelector->setCurrentIndex(-1);
  layout->addRow(label, d->measurableDiseaseSelector);

  label = new QLabel("2 - Non-measurable Disease");
  d->nonmeasurableDiseaseSelector = new ctkComboBox();
  d->nonmeasurableDiseaseSelector->setDefaultText("---");
  d->nonmeasurableDiseaseSelector->addItem("Stable Disease");
  d->nonmeasurableDiseaseSelector->addItem("Progressive Disease");
  d->nonmeasurableDiseaseSelector->addItem("Baseline");
  d->nonmeasurableDiseaseSelector->addItem("Not Present");
  d->nonmeasurableDiseaseSelector->addItem("Not Evaluable");
  d->nonmeasurableDiseaseSelector->setCurrentIndex(-1);
  layout->addRow(label, d->nonmeasurableDiseaseSelector);

  label = new QLabel("3 - FLAIR");
  d->flairSelector = new ctkComboBox();
  d->flairSelector->setDefaultText("---");
  d->flairSelector->addItem("Stable Disease");
  d->flairSelector->addItem("Progressive Disease");
  d->flairSelector->addItem("Baseline");
  d->flairSelector->addItem("Not Present");
  d->flairSelector->addItem("Not Evaluable");
  d->flairSelector->setCurrentIndex(-1);
  layout->addRow(label, d->flairSelector);

  // connect widgets to the variables
  this->connect(d->measurableDiseaseSelector, SIGNAL(currentIndexChanged(int)),
                this, SLOT(onMeasurableDiseaseChanged(int)));
  this->connect(d->nonmeasurableDiseaseSelector, SIGNAL(currentIndexChanged(int)),
                this, SLOT(onNonmeasurableDiseaseChanged(int)));
  this->connect(d->flairSelector, SIGNAL(currentIndexChanged(int)),
                this, SLOT(onFlairChanged(int)));
}

// --------------------------------------------------------------------------
qMRMLReportingAnnotationRANOWidget::~qMRMLReportingAnnotationRANOWidget()
{
}

//------------------------------------------------------------------------------
void qMRMLReportingAnnotationRANOWidget::setMRMLAnnotationNode(vtkMRMLNode* newAnnotationNode)
{
  Q_D(qMRMLReportingAnnotationRANOWidget);
  d->setMRMLReportingAnnotationNode(vtkMRMLReportingAnnotationNode::SafeDownCast(newAnnotationNode));
}

//------------------------------------------------------------------------------
vtkMRMLScene* qMRMLReportingAnnotationRANOWidget::mrmlScene() const
{
//  Q_D(const qMRMLReportingAnnotationRANOWidget);
    vtkMRMLScene *scene = NULL;
    return scene;
}

//------------------------------------------------------------------------------
void qMRMLReportingAnnotationRANOWidget::onNonmeasurableDiseaseChanged(int index)
{
  Q_D(qMRMLReportingAnnotationRANOWidget);

  d->nonmeasurableDiseaseIndex = index;
}

//------------------------------------------------------------------------------
void qMRMLReportingAnnotationRANOWidget::onMeasurableDiseaseChanged(int index)
{
  Q_D(qMRMLReportingAnnotationRANOWidget);

  d->measurableDiseaseIndex = index;
}

//------------------------------------------------------------------------------
void qMRMLReportingAnnotationRANOWidget::onFlairChanged(int index)
{
  Q_D(qMRMLReportingAnnotationRANOWidget);

  d->flairIndex = index;
}
