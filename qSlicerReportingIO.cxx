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
#include <QFileInfo>

// PythonQt includes
#include <PythonQt.h>

// SlicerQt includes
#include "qSlicerApplication.h"
#include "qSlicerPythonManager.h"
#include "qSlicerReportingIO.h"

//#include "qSlicerReportingIOOptionsWidget.h"

// Logic includes
#include <vtkSlicerApplicationLogic.h>
#include "vtkSlicerReportingModuleLogic.h"

// MRML includes
#include <vtkMRMLNode.h>
#include <vtkMRMLColorNode.h>
#include <vtkMRMLReportingReportNode.h>
#include <vtkMRMLScriptedModuleNode.h>

// VTK includes
#include <vtkNew.h>
#include <vtkSmartPointer.h>

//-----------------------------------------------------------------------------
class qSlicerReportingIOPrivate
{
  public:
  vtkSmartPointer<vtkSlicerReportingModuleLogic> ReportingLogic;
};


//-----------------------------------------------------------------------------
/// \ingroup Slicer_QtModules_Reporting
//-----------------------------------------------------------------------------
qSlicerReportingIO::qSlicerReportingIO(QObject* _parent)
  : Superclass(_parent)
  , d_ptr(new qSlicerReportingIOPrivate)
{
}

qSlicerReportingIO::qSlicerReportingIO(vtkSlicerReportingModuleLogic* logic, QObject* _parent)
  : Superclass(_parent)
  , d_ptr(new qSlicerReportingIOPrivate)
{
  this->setReportingLogic(logic);
}

//-----------------------------------------------------------------------------
qSlicerReportingIO::~qSlicerReportingIO()
{
}

//-----------------------------------------------------------------------------
void qSlicerReportingIO::setReportingLogic(vtkSlicerReportingModuleLogic* logic)
{
  Q_D(qSlicerReportingIO);
  d->ReportingLogic = logic;
}

//-----------------------------------------------------------------------------
vtkSlicerReportingModuleLogic* qSlicerReportingIO::reportingLogic()const
{
  Q_D(const qSlicerReportingIO);
  return d->ReportingLogic.GetPointer();
}

//-----------------------------------------------------------------------------
QString qSlicerReportingIO::description()const
{
  return "Reporting";
}

//-----------------------------------------------------------------------------
qSlicerIO::IOFileType qSlicerReportingIO::fileType()const
{
    return QString("AIMXML");
}

//-----------------------------------------------------------------------------
QStringList qSlicerReportingIO::extensions()const
{
  return QStringList()
    << "Reporting (*.xml)";
}

//-----------------------------------------------------------------------------
qSlicerIOOptions* qSlicerReportingIO::options()const
{
  return 0;
}

//-----------------------------------------------------------------------------
bool qSlicerReportingIO::load(const IOProperties& properties)
{
  Q_D(qSlicerReportingIO);
  Q_ASSERT(properties.contains("fileName"));
  QString fileName = properties["fileName"].toString();

  QString name = QFileInfo(fileName).baseName();
  if (properties.contains("name"))
    {
    name = properties["name"].toString();
    }

  if (d->ReportingLogic.GetPointer() == 0)
    {
    return false;
    }

  // make a new report node
  vtkMRMLReportingReportNode *reportNode = vtkMRMLReportingReportNode::New();
  // get the default colour node id
  const char * colorNodeID =  d->ReportingLogic->GetDefaultColorNode()->GetID();
  reportNode->SetColorNodeID(colorNodeID);
  this->mrmlScene()->AddNode(reportNode);

  
  qSlicerPythonManager* pythonManager = qSlicerApplication::application()->pythonManager();
  // first go to the Reporting module
  QVariant retvar = pythonManager->executeString(QString("slicer.util.mainWindow().moduleSelector().selectModule('Reporting')"));

  // set the active report
  vtkMRMLNode *scriptedModuleNode = this->mrmlScene()->GetNodeByID("vtkMRMLScriptedModuleNodeReporting");
  if (scriptedModuleNode && vtkMRMLScriptedModuleNode::SafeDownCast(scriptedModuleNode))
    {
    vtkMRMLScriptedModuleNode::SafeDownCast(scriptedModuleNode)->SetParameter("reportID", reportNode->GetID());
    qDebug() << "Set reportID parameter to " + QString(reportNode->GetID());
    }
  
  // load the helper class
  retvar = pythonManager->executeString(QString("from SlicerReportingModuleWidgetHelper import SlicerReportingModuleWidgetHelper as ReportingHelper"));

  // set up the file load command
  QString loadFileString = QString("ReportingHelper().LoadAIMFile(\"") + QString(reportNode->GetID()) + QString("\",\"") + QString(fileName) + QString("\")");
  qDebug() << loadFileString;

  // run the file load command
  retvar = pythonManager->executeString(loadFileString);

  char * nodeID = reportNode->GetID();
  
  if (!nodeID)
    {
    this->setLoadedNodes(QStringList());
    return false;
    }
  this->setLoadedNodes( QStringList(QString(nodeID)) );
  if (properties.contains("name"))
    {
    std::string uname = this->mrmlScene()->GetUniqueNameByString(
      properties["name"].toString().toLatin1());
    this->mrmlScene()->GetNodeByID(nodeID)->SetName(uname.c_str());
    }
  return true;
}
