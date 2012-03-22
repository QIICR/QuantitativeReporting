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

// ExtensionTemplate Logic includes
#include <vtkSlicerReportingModuleLogic.h>

// ExtensionTemplate includes
#include "qSlicerReportingModule.h"
#include "qSlicerReportingModuleWidget.h"

// SlicerQT includes
#include <qSlicerModuleManager.h>
#include <qSlicerScriptedLoadableModuleWidget.h>
#include <qSlicerUtils.h>
#include <vtkSlicerConfigure.h>

//-----------------------------------------------------------------------------
Q_EXPORT_PLUGIN2(qSlicerReportingModule, qSlicerReportingModule);

//-----------------------------------------------------------------------------
/// \ingroup Slicer_QtModules_ExtensionTemplate
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
  return "Reporting module provides support for structured markup and annotation, and "
    "some support of AIM import/export. This is work in progress, see details "
    "<a href=\"http://wiki.na-mic.org/Wiki/index.php/Projects:QIN:3D_Slicer_Annotation_Image_Markup\">"
    "QIN:3D Slicer Annotation Image Markup</a>.";
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
