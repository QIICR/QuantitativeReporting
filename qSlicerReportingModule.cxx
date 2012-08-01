/*==============================================================================

  Program: 3D Slicer

  Portions (c) Copyright Brigham and Women's Hospital (BWH) All Rights Reserved.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

==============================================================================*/

// Qt includes
#include <QFileInfo>
#include <QScopedPointer>
#include <QtPlugin>
#include <QtPlugin>

// Reporting Logic includes
#include <vtkSlicerReportingModuleLogic.h>

// Reporting includes
#include "qSlicerReportingModule.h"

// SlicerQT includes
#include <qSlicerModuleManager.h>
#include <qSlicerScriptedLoadableModuleWidget.h>
#include <qSlicerUtils.h>
#include <vtkSlicerConfigure.h>

//-----------------------------------------------------------------------------
Q_EXPORT_PLUGIN2(qSlicerReportingModule, qSlicerReportingModule);

//-----------------------------------------------------------------------------
/// \ingroup Slicer_QtModules_Reporting
class qSlicerReportingModulePrivate
{
public:
  qSlicerReportingModulePrivate();
};

//-----------------------------------------------------------------------------
// qSlicerReportingModulePrivate methods

//-----------------------------------------------------------------------------
qSlicerReportingModulePrivate::qSlicerReportingModulePrivate()
{
}

//-----------------------------------------------------------------------------
// qSlicerReportingModule methods

//-----------------------------------------------------------------------------
qSlicerReportingModule::qSlicerReportingModule(QObject* _parent)
  : Superclass(_parent)
  , d_ptr(new qSlicerReportingModulePrivate)
{
}

//-----------------------------------------------------------------------------
qSlicerReportingModule::~qSlicerReportingModule()
{
}

//-----------------------------------------------------------------------------
QString qSlicerReportingModule::helpText()const
{
  return "The Reporting module provides support for structured markup and annotation, and "
    "some support of AIM import/export.<br>"
    "Select a markup and right click to jump slice viewers to that location.<br>"
    "This is a work in progress. "
    "<a href=\"http://wiki.slicer.org/slicerWiki/index.php/Documentation/4.1/Extensions/Reporting\">"
    "Usage instructions</a>.";
}

//-----------------------------------------------------------------------------
QString qSlicerReportingModule::acknowledgementText()const
{
  return "This work was supported by a supplement to NIH grant U01CA151261 (PI Fiona Fennessy).";
}

//-----------------------------------------------------------------------------
QIcon qSlicerReportingModule::icon()const
{
  return QIcon(":/Icons/ReportingModule.png");
}

//-----------------------------------------------------------------------------
QStringList qSlicerReportingModule::categories() const
{
  return QStringList() << "Work in Progress.Informatics";
}

//-----------------------------------------------------------------------------
QStringList qSlicerReportingModule::dependencies() const
{
  return QStringList() << "Annotations" << "Volumes" << "DICOM";
}

//-----------------------------------------------------------------------------
QStringList qSlicerReportingModule::contributors() const
{
  QStringList contributors;
  contributors << "Andrey Fedorov (SPL, BWH)";
  contributors << "Nicole Aucoin (SPL, BWH)";
  contributors << "Steve Pieper (Isomics)";

  return contributors;
}


//-----------------------------------------------------------------------------
void qSlicerReportingModule::setup()
{
  this->Superclass::setup();
}

//-----------------------------------------------------------------------------
qSlicerAbstractModuleRepresentation * qSlicerReportingModule::createWidgetRepresentation()
{
  QString pythonPath = qSlicerUtils::pathWithoutIntDir(
              QFileInfo(this->path()).path(), Slicer_QTLOADABLEMODULES_LIB_DIR);

  QScopedPointer<qSlicerScriptedLoadableModuleWidget> widget(new qSlicerScriptedLoadableModuleWidget);
  QString classNameToLoad = "qSlicerReportingModuleWidget";
  bool ret = widget->setPythonSource(
        pythonPath + "/Python/" + classNameToLoad + ".py", classNameToLoad);
  if (!ret)
    {
    return 0;
    }
  return widget.take();
}

//-----------------------------------------------------------------------------
vtkMRMLAbstractLogic* qSlicerReportingModule::createLogic()
{
  return vtkSlicerReportingModuleLogic::New();
}
