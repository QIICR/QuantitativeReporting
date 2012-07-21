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
class vtkMRMLColorNode;
class vtkMRMLVolumeNode;
class vtkMRMLReportingReportNode;
class vtkMRMLScalarVolumeNode;

class QDomDocument;
class QDomElement;
class QStringList;

class ctkDICOMDatabase;

class DcmDataset;
class DcmTag;

/// \ingroup Slicer_QtModules_ExtensionTemplate
class VTK_SLICER_REPORTING_MODULE_LOGIC_EXPORT vtkSlicerReportingModuleLogic :
  public vtkSlicerModuleLogic
{
public:

  static vtkSlicerReportingModuleLogic *New();
  vtkTypeMacro(vtkSlicerReportingModuleLogic, vtkSlicerModuleLogic);
  void PrintSelf(ostream& os, vtkIndent indent);

  /// Convert the RAS of a mark up element (vtkMRMLAnnotation*Node) that's
  /// associated with a volume node to the UID of the slice it's on. Returns
  /// the UID, or the string NONE if there's no associated node, all control
  /// points aren't on the same slice
  std::string GetSliceUIDFromMarkUp(vtkMRMLAnnotationNode *node);

  /// Return the id of the top level reporting module hierarchy node, creating
  /// one if not found, NULL on error
  char *GetTopLevelHierarchyNodeID();
  
  /// Set up the hierarchy for the newly selected report node
  void InitializeHierarchyForReport(vtkMRMLReportingReportNode *node);
  
  /// Set up the hierarchy for the newly selected volume node
  void InitializeHierarchyForVolume(vtkMRMLVolumeNode *node);

  /// Set the active hierarchy from a node by looking for hierarchies
  void SetActiveMarkupHierarchyIDFromNode(vtkMRMLNode *node);

  /// Return the active volume ID for the given report, returns NULL on error
  char *GetVolumeIDForReportNode(vtkMRMLReportingReportNode *node);

  /// Return the annotation node id for the given report, returns NULL on
  /// error
  char *GetAnnotationIDForReportNode(vtkMRMLReportingReportNode *node);
  
  /// Hide reporting annotations that aren't under this report node
  void HideAnnotationsForOtherReports(vtkMRMLReportingReportNode *node);

  /// Save report to AIM file, returns 1 on success, 0 on failure
  int SaveReportToAIM(vtkMRMLReportingReportNode *reportNode);

  bool InitializeDICOMDatabase();

  // set/get the currently active parameter node
  vtkGetStringMacro(ActiveParameterNodeID);
  vtkSetStringMacro(ActiveParameterNodeID);

  /// set/get the currently active markup hierarchy
  vtkGetStringMacro(ActiveMarkupHierarchyID);
  vtkSetStringMacro(ActiveMarkupHierarchyID);

  /// set/get the GUI hidden flag
  vtkGetMacro(GUIHidden, int);
  vtkSetMacro(GUIHidden, int);
  vtkBooleanMacro(GUIHidden, int);
  
  /// utility methods to call from python
  void SetActiveMarkupHierarchyIDToNull();
  
  bool IsDicomSeg(const std::string fname);
  // TODO: consider taking report as as a parameter here?
  std::string DicomSegWrite(vtkCollection* labelNodes, const std::string dirname);
  bool DicomSegRead(vtkCollection*, const std::string fname, vtkMRMLColorNode* colorNode = NULL);

  /// set/get the error string
  vtkGetStringMacro(ErrorMessage);
  vtkSetStringMacro(ErrorMessage);
  
  std::string GetFileNameFromUID(std::string uid);

  vtkMRMLColorNode* GetDefaultColorNode();

  void AddNodeToReport(vtkMRMLNode*);

protected:
  vtkSlicerReportingModuleLogic();
  virtual ~vtkSlicerReportingModuleLogic();

  // set up listening to scene events
  virtual void SetMRMLSceneInternal(vtkMRMLScene* newScene);

  /// Register MRML Node classes to Scene. Gets called automatically when the MRMLScene is attached to this logic class.
  virtual void RegisterNodes();
  virtual void UpdateFromMRMLScene();
  /// Respond to events on the mrml scene
  virtual void ProcessMRMLNodesEvents(vtkObject *caller,
                                      unsigned long event,
                                      void *callData );
  virtual void OnMRMLSceneNodeAdded(vtkMRMLNode* node);
  virtual void OnMRMLSceneNodeRemoved(vtkMRMLNode* node);
 
  /// get the currently active report hierarchy from the parameter node
  const char *GetActiveReportHierarchyID();
  
  int AddSpatialCoordinateCollectionElement(QDomDocument&, QDomElement&, QStringList&, QStringList&);

private:

  vtkSlicerReportingModuleLogic(const vtkSlicerReportingModuleLogic&); // Not implemented
  void operator=(const vtkSlicerReportingModuleLogic&);               // Not implemented

  // copy the content of Dcm tag from one dataset to another, or set to ""
  //  if not available
  void copyDcmElement(const DcmTag&, DcmDataset*, DcmDataset*);
  // get string representation of a Dcm tag, return "" if not available
  std::string getDcmElementAsString(const DcmTag& tag, DcmDataset* dcmIn);

  QStringList GetMarkupPointCoordinatesStr(vtkMRMLAnnotationNode *ann);
  vtkMRMLScalarVolumeNode* GetMarkupVolumeNode(vtkMRMLAnnotationNode *ann);

  /// the currently active parameter node, contains the active report
  /// hierarchy node
  char *ActiveParameterNodeID;
  /// the currently active markup hierarchy
  char *ActiveMarkupHierarchyID;

  /// is the GUI hidden? When it's hidden/true, don't grab fiducials (but do grab
  /// label volumes if they're associated with the current volume being
  /// annotated
  int GUIHidden;

/*
  struct VocabularyItem 
    {
    unsigned LabelValue;
    std::string CodeValue;
    std::string CodeMeaning;
    std::string CodingSchemeDesignator;
    }
*/

  ctkDICOMDatabase *DICOMDatabase;

  /// save an error string to pass to the gui, reset when test passes
  char *ErrorMessage;
};

#endif
