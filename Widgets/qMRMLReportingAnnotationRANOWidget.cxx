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
#include <vtkMRMLReportingAnnotationRANONode.h>

// qMRML includes
#include "qMRMLReportingAnnotationRANOWidget.h"

// CTK includes
#include <ctkComboBox.h>

// Qt includes
#include <QFormLayout>
#include <QLabel>
#include <QString>

class qMRMLReportingAnnotationRANOWidgetPrivate
{
  Q_DECLARE_PUBLIC(qMRMLReportingAnnotationRANOWidget);
protected:
  qMRMLReportingAnnotationRANOWidget* const q_ptr;
  void setMRMLReportingAnnotationNode(vtkMRMLReportingAnnotationRANONode* newAnnotationNode);

public:
  qMRMLReportingAnnotationRANOWidgetPrivate(qMRMLReportingAnnotationRANOWidget& object);

  vtkMRMLReportingAnnotationRANONode *annotationNode;

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

void qMRMLReportingAnnotationRANOWidgetPrivate::setMRMLReportingAnnotationNode(vtkMRMLReportingAnnotationRANONode *newNode)
{
  Q_Q(qMRMLReportingAnnotationRANOWidget);

  q->qvtkReconnect(this->annotationNode, newNode, vtkCommand::ModifiedEvent,
                   q, SLOT(updateWidgetFromMRML()));
  this->annotationNode = newNode;

  if(this->annotationNode)
  {
    if(!q->layout())
    {
      std::cout << "Before init()" << std::endl;
      q->init();
    }
    q->updateWidgetFromMRML();
  }
}

//------------------------------------------------------------------------------
// qMRMLReportingAnnotationRANOWidget methods

// --------------------------------------------------------------------------
qMRMLReportingAnnotationRANOWidget::qMRMLReportingAnnotationRANOWidget(QWidget* newParent)
  : Superclass(newParent)
  , d_ptr(new qMRMLReportingAnnotationRANOWidgetPrivate(*this))
{
}

void qMRMLReportingAnnotationRANOWidget::init()
{
  Q_D(qMRMLReportingAnnotationRANOWidget);

  if(!d->annotationNode){
    std::cout << "Annotation node not set!" << std::endl;
    return;
  }

  QFormLayout *layout = new QFormLayout();
  this->setLayout(layout);

  vtkMRMLReportingAnnotationRANONode *an = d->annotationNode;

  if(an->componentDescriptionList.size() != an->componentCodeList.size())
  {
    std::cout << "Component size mismatch" << std::endl;
    return;
  }

  int nComponents = an->componentDescriptionList.size();
  for(int i=0;i<nComponents;i++)
  {
    vtkMRMLReportingAnnotationRANONode::StringPairType cdPair;
    cdPair = an->componentDescriptionList[i];
    QLabel *label = new QLabel(cdPair.first);
    ctkComboBox *combo = new ctkComboBox();
    label->setToolTip(cdPair.second);
    combo->setToolTip(cdPair.second);
    combo->setDefaultText("---");

    int nCodes = an->componentCodeList[i].size();

    for(int j=0;j<nCodes;j++)
    {
      QString meaning = "";
      meaning = an->codeToMeaningMap[an->componentCodeList[i].at(j)];
      combo->addItem(meaning);
    }
    combo->setCurrentIndex(-1);
    layout->addRow(label, combo);
  }
}

// --------------------------------------------------------------------------
qMRMLReportingAnnotationRANOWidget::~qMRMLReportingAnnotationRANOWidget()
{
}

//------------------------------------------------------------------------------
void qMRMLReportingAnnotationRANOWidget::setMRMLAnnotationNode(vtkMRMLNode* newAnnotationNode)
{
  Q_D(qMRMLReportingAnnotationRANOWidget);
  std::cout << "Setting annotation node!" << std::endl;
  d->setMRMLReportingAnnotationNode(vtkMRMLReportingAnnotationRANONode::SafeDownCast(newAnnotationNode));
}

//------------------------------------------------------------------------------
vtkMRMLScene* qMRMLReportingAnnotationRANOWidget::mrmlScene() const
{
//  Q_D(const qMRMLReportingAnnotationRANOWidget);
    vtkMRMLScene *scene = NULL;
    return scene;
}

// AF NB: we do not need to handle individual events per element!

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

void qMRMLReportingAnnotationRANOWidget::updateWidgetFromMRML()
{
  Q_D(qMRMLReportingAnnotationRANOWidget);
  Q_ASSERT(d->annotationNode);
}
