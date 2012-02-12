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
  bool disableMRMLUpdates;

public:
  qMRMLReportingAnnotationRANOWidgetPrivate(qMRMLReportingAnnotationRANOWidget& object);

  vtkMRMLReportingAnnotationRANONode *annotationNode;

  std::vector<ctkComboBox*> comboBoxList;
};

qMRMLReportingAnnotationRANOWidgetPrivate::qMRMLReportingAnnotationRANOWidgetPrivate(qMRMLReportingAnnotationRANOWidget& object)
  : q_ptr(&object)
{
  this->annotationNode = 0;
  this->disableMRMLUpdates = false;
}

void qMRMLReportingAnnotationRANOWidgetPrivate::setMRMLReportingAnnotationNode(vtkMRMLReportingAnnotationRANONode *newNode)
{
  Q_Q(qMRMLReportingAnnotationRANOWidget);

  // do not update MRML based on the widget content during switchover to another annotation node
  this->disableMRMLUpdates = true;

  q->qvtkReconnect(this->annotationNode, newNode, vtkCommand::ModifiedEvent,
                   q, SLOT(updateWidgetFromMRML()));
  this->annotationNode = newNode;

  if(this->annotationNode)
  {
    if(!q->layout())
      q->init();
    q->updateWidgetFromMRML();
  }

  this->disableMRMLUpdates = false;
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
    QLabel *label = new QLabel(cdPair.first.c_str());
    ctkComboBox *combo = new ctkComboBox();
    label->setToolTip(cdPair.second.c_str());
    combo->setToolTip(cdPair.second.c_str());
    combo->setDefaultText("---");

    int nCodes = an->componentCodeList[i].size();
    //std::vector<std::string> componentCode = an->codeToMeaningMap[an->componentCodeList[i]];
    for(int j=0;j<nCodes;j++)
    {
      QString meaning = "";
      meaning = QString(an->codeToMeaningMap[an->componentCodeList[i].at(j)].c_str());
      combo->addItem(meaning);
    }

    combo->setCurrentIndex(-1);
    layout->addRow(label, combo);
    d->comboBoxList.push_back(combo);
    this->connect(combo, SIGNAL(currentIndexChanged(int)), this,
                  SLOT(updateMRMLFromWidget()));
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

void qMRMLReportingAnnotationRANOWidget::updateWidgetFromMRML()
{
  Q_D(qMRMLReportingAnnotationRANOWidget);

  if(!d->annotationNode)
    return;

  std::cout << "Current annotation node: ";
  vtkIndent indent;
  d->annotationNode->PrintSelf(std::cout, indent);
  vtkMRMLReportingAnnotationRANONode* an = d->annotationNode;

  int nComponents = an->componentDescriptionList.size();
  for(int i=0;i<nComponents;i++)
  {
    int idx = -1;
    std::string code = an->selectedCodeList[i];
    std::cout << "Selected code: " << code << std::endl;
    std::vector<std::string> codeList = an->componentCodeList[i];
    std::vector<std::string>::iterator codeIt = std::find(codeList.begin(), codeList.end(), code);
    if(codeIt != codeList.end())
      idx = codeIt-codeList.begin();
    std::cout << "Setting index to " << idx << std::endl;
    d->comboBoxList[i]->setCurrentIndex(idx);
  }
}

void qMRMLReportingAnnotationRANOWidget::updateMRMLFromWidget()
{
  Q_D(qMRMLReportingAnnotationRANOWidget);

  if(!d->annotationNode || d->disableMRMLUpdates)
    return;

  vtkMRMLReportingAnnotationRANONode* an = d->annotationNode;
  int nComponents = an->componentDescriptionList.size();
  int nWidgets = d->comboBoxList.size();
  Q_ASSERT(nComponents==nWidgets);

  for(int i=0;i<nWidgets;i++)
  {
    int idx = d->comboBoxList[i]->currentIndex();
    if(idx==-1)
    {
      an->selectedCodeList[i] = "";
    }
    else
    {
      Q_ASSERT(idx<an->componentCodeList[i].size());
      an->selectedCodeList[i] = an->componentCodeList[i][idx];
    }
  }
}
