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

// .NAME vtkSlicerReportingModuleLogic - slicer logic class for volumes manipulation
// .SECTION Description
// This class manages the logic associated with reading, saving,
// and changing propertied of the volumes


#ifndef __vtkSlicerReportingModuleLogic_h
#define __vtkSlicerReportingModuleLogic_h

// Slicer includes
#include "vtkSlicerModuleLogic.h"

// MRML includes

// STD includes
#include <cstdlib>

#include "vtkSlicerReportingModuleLogicExport.h"

class vtkMRMLAnnotationNode;
/// \ingroup Slicer_QtModules_ExtensionTemplate
class VTK_SLICER_REPORTINGMODULE_MODULE_LOGIC_EXPORT vtkSlicerReportingModuleLogic :
  public vtkSlicerModuleLogic
{
public:

  static vtkSlicerReportingModuleLogic *New();
  vtkTypeMacro(vtkSlicerReportingModuleLogic, vtkSlicerModuleLogic);
  void PrintSelf(ostream& os, vtkIndent indent);

  /// Initialize listening to MRML events
  void InitializeEventListeners();

  /// Convert the RAS of a mark up element (vtkMRMLAnnotation*Node) that's
  /// associated with a volume node to the UID of the slice it's on. Returns
  /// the UID, or the string NONE if there's no associated node, all control
  /// points aren't on the same slice
  const char *GetSliceUIDFromMarkUp(vtkMRMLAnnotationNode *node);

protected:
  vtkSlicerReportingModuleLogic();
  virtual ~vtkSlicerReportingModuleLogic();

  /// Register MRML Node classes to Scene. Gets called automatically when the MRMLScene is attached to this logic class.
  virtual void RegisterNodes();
  virtual void UpdateFromMRMLScene();
  virtual void OnMRMLSceneNodeAdded(vtkMRMLNode* node);
  virtual void OnMRMLSceneNodeRemoved(vtkMRMLNode* node);
private:

  vtkSlicerReportingModuleLogic(const vtkSlicerReportingModuleLogic&); // Not implemented
  void operator=(const vtkSlicerReportingModuleLogic&);               // Not implemented
};

#endif
