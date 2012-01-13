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
#include <QtPlugin>

// ExtensionTemplate Logic includes
#include <vtkSlicerReportingModuleLogic.h>

// ExtensionTemplate includes
#include "qSlicerReportingModuleModule.h"
#include "qSlicerReportingModuleModuleWidget.h"

//-----------------------------------------------------------------------------
Q_EXPORT_PLUGIN2(qSlicerReportingModuleModule, qSlicerReportingModuleModule);

//-----------------------------------------------------------------------------
/// \ingroup Slicer_QtModules_ExtensionTemplate
class qSlicerReportingModuleModulePrivate
{
public:
  qSlicerReportingModuleModulePrivate();
};

//-----------------------------------------------------------------------------
// qSlicerReportingModuleModulePrivate methods

//-----------------------------------------------------------------------------
qSlicerReportingModuleModulePrivate::qSlicerReportingModuleModulePrivate()
{
}

//-----------------------------------------------------------------------------
// qSlicerReportingModuleModule methods

//-----------------------------------------------------------------------------
qSlicerReportingModuleModule::qSlicerReportingModuleModule(QObject* _parent)
  : Superclass(_parent)
  , d_ptr(new qSlicerReportingModuleModulePrivate)
{
}

//-----------------------------------------------------------------------------
qSlicerReportingModuleModule::~qSlicerReportingModuleModule()
{
}

//-----------------------------------------------------------------------------
QString qSlicerReportingModuleModule::helpText()const
{
  return "This ReportingModule module illustrates how a loadable module should "
      "be implemented.";
}

//-----------------------------------------------------------------------------
QString qSlicerReportingModuleModule::acknowledgementText()const
{
  return "This work was supported by ...";
}

//-----------------------------------------------------------------------------
QIcon qSlicerReportingModuleModule::icon()const
{
  return QIcon(":/Icons/ReportingModule.png");
}

//-----------------------------------------------------------------------------
void qSlicerReportingModuleModule::setup()
{
  this->Superclass::setup();
}

//-----------------------------------------------------------------------------
qSlicerAbstractModuleRepresentation * qSlicerReportingModuleModule::createWidgetRepresentation()
{
  return new qSlicerReportingModuleModuleWidget;
}

//-----------------------------------------------------------------------------
vtkMRMLAbstractLogic* qSlicerReportingModuleModule::createLogic()
{
  return vtkSlicerReportingModuleLogic::New();
}
