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
class QString;
class QStringList;

class ctkDICOMDatabase;

class DcmDataset;
class DcmTag;

/// \ingroup Slicer_QtModules_ExtensionTemplate
class VTK_SLICER_REPORTING_MODULE_LOGIC_EXPORT vtkSlicerReportingModuleLogic :
  public vtkSlicerModuleLogic
{
public:

  struct StandardTerm
    {
    std::string CodeValue;
    std::string CodeMeaning;
    std::string CodingSchemeDesignator;

    StandardTerm(){
      CodeValue = "";
      CodeMeaning = "";
      CodingSchemeDesignator = "";
    }

    void PrintSelf(ostream &os){
      os << "Code value: " << CodeValue << " Code meaning: " << CodeMeaning << " Code scheme designator: " << CodingSchemeDesignator << std::endl;
    }
    };

  struct ColorLabelCategorization
    {
    unsigned LabelValue;
    StandardTerm SegmentedPropertyCategory;
    StandardTerm SegmentedPropertyType;
    StandardTerm SegmentedPropertyTypeModifier;

    void PrintSelf(ostream &os){
      os << "Label: " << LabelValue << std::endl <<
        "   Segmented property category: ";
      SegmentedPropertyCategory.PrintSelf(os);
        os << "   Segmented property type: ";
      SegmentedPropertyType.PrintSelf(os);
        os << "   Segmented property type modifier: ";
      SegmentedPropertyTypeModifier.PrintSelf(os);
      os << std::endl;
    };
    };

  static vtkSlicerReportingModuleLogic *New();
  vtkTypeMacro(vtkSlicerReportingModuleLogic, vtkSlicerModuleLogic);
  void PrintSelf(ostream& os, vtkIndent indent);

  /// Convert the RAS of a mark up element (vtkMRMLAnnotation*Node) that's
  /// associated with a volume node to the UID of the slice it's on. Returns
  /// the UID, or the string NONE if there's no associated node, all control
  /// points aren't on the same slice
  std::string GetSliceUIDFromMarkUp(vtkMRMLAnnotationNode *node);

  /// Set up the report to include the newly selected volume node
  void AddVolumeToReport(vtkMRMLVolumeNode *node);

  /// Return the active volume ID for the given report, returns NULL on error
  std::string GetVolumeIDForReportNode(vtkMRMLReportingReportNode *node);

  /// return true if the node has an attribute ReportingReportNodeID that
  /// matches the active report, and an associatedNodeID attribute that
  /// matches the active volume in the active report
  bool IsInReport(vtkMRMLNode *node);
  
  /// Hide reporting annotations that aren't under this report node
  void HideAnnotationsForOtherReports(vtkMRMLReportingReportNode *node);

  /// Save report to AIM file, returns 1 on success, 0 on failure
  int SaveReportToAIM(vtkMRMLReportingReportNode *reportNode);

  bool InitializeDICOMDatabase(std::string dbLocation);
  bool InitializeTerminologyMapping();
  bool InitializeTerminologyMappingFromFile(std::string mapFile);
  bool LookupCategorizationFromLabel(int label, ColorLabelCategorization&);
  bool LookupLabelFromCategorization(ColorLabelCategorization&, int&);
  bool PrintCategorizationFromLabel(int label);

  // set/get the currently active parameter node
  vtkGetMacro(ActiveParameterNodeID, std::string);
  vtkSetMacro(ActiveParameterNodeID, std::string);

  /// set/get the GUI hidden flag
  vtkGetMacro(GUIHidden, int);
  vtkSetMacro(GUIHidden, int);
  vtkBooleanMacro(GUIHidden, int);
    
  bool IsDicomSeg(const std::string fname);
  // TODO: consider taking report as as a parameter here?
  std::string DicomSegWrite(vtkCollection* labelNodes, const std::string dirname, bool saveReferencedDcm = false);
  bool DicomSegRead(vtkCollection*, const std::string fname, vtkMRMLColorNode* colorNode = NULL);

  /// set/get the error string
  vtkGetMacro(ErrorMessage, std::string);
  vtkSetMacro(ErrorMessage, std::string);
  
  std::string GetFileNameFromUID(std::string uid);

  vtkMRMLColorNode* GetDefaultColorNode();

  void AddNodeToReport(vtkMRMLNode*);

  void PropagateFindingUpdateToMarkup();

  /// logic events
  enum
    {
      ErrorEvent = 0x0000,
      AnnotationAdded,
    };

  /// Add the calculated values of annotations to the document as a CalculationData
  /// keeping this public for testing/verification
  int AddCalculationCollectionElement(QDomDocument &doc, QDomElement &parent, QString &codeMeaning, QString &codeValue, QString &description, QString &unitOfMeasure, QString &value, QString &shapeIdentifier, QString &UID);
  
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

  /// get the currently active report node id, from the parameter
  /// node. Returns an empty string on failure.
  std::string GetActiveReportID();
  
  int AddSpatialCoordinateCollectionElement(QDomDocument&, QDomElement&, QStringList&, QString&);
//  int AddCalculationCollectionElement(QDomDocument &doc, QDomElement &parent, QString &rulerLength, QString &sliceUID);

private:

  vtkSlicerReportingModuleLogic(const vtkSlicerReportingModuleLogic&); // Not implemented
  void operator=(const vtkSlicerReportingModuleLogic&);               // Not implemented

  std::string RemoveLeadAndTrailSpaces(std::string);
  bool ParseTerm(std::string, StandardTerm&);

  // copy the content of Dcm tag from one dataset to another, or set to ""
  //  if not available
  void copyDcmElement(const DcmTag&, DcmDataset*, DcmDataset*);
  // get string representation of a Dcm tag, return "" if not available
  std::string getDcmElementAsString(const DcmTag& tag, DcmDataset* dcmIn);

  QStringList GetMarkupPointCoordinatesStr(vtkMRMLAnnotationNode *ann);
  vtkMRMLScalarVolumeNode* GetMarkupVolumeNode(vtkMRMLAnnotationNode *ann);

  /// the currently active parameter node, contains the active report
  /// node
  std::string ActiveParameterNodeID;

  /// is the GUI hidden? When it's hidden/true, don't grab fiducials (but do grab
  /// label volumes if they're associated with the current volume being
  /// annotated
  int GUIHidden;

  ctkDICOMDatabase *DICOMDatabase;

  typedef std::map<int,ColorLabelCategorization> ColorCategorizationMapType;

  std::map<std::string, ColorCategorizationMapType> colorCategorizationMaps;

  /// save an error string to pass to the gui, reset when test passes
  std::string ErrorMessage;
};

#endif
