/*=auto=========================================================================

  Portions (c) Copyright 2005 Brigham and Women's Hospital (BWH) All Rights Reserved.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Program:   3D Slicer
  Module:    $RCSfile: vtkMRMLVolumeRenderingParametersNode.h,v $
  Date:      $Date: 2006/03/19 17:12:29 $
  Version:   $Revision: 1.3 $

=========================================================================auto=*/
// .NAME vtkMRMLReportingAnnotationRANONode Node to keep the conent of RANO
// annotation
// .SECTION Description
//
//

#ifndef __vtkMRMLReportingAnnotationRANONode_h
#define __vtkMRMLReportingAnnotationRANONode_h

// MRML includes
#include "vtkDoubleArray.h"
#include "vtkMRML.h"
#include "vtkMRMLNode.h"
#include "vtkMRMLScene.h"
#include <vtkSlicerReportingModuleMRMLExport.h>

class qMRMLReportingAnnotationRANOWidget;

/// \ingroup Slicer_QtModules_ReportingAnnotationRANONode
class VTK_SLICER_REPORTING_MODULE_MRML_EXPORT vtkMRMLReportingAnnotationRANONode : public vtkMRMLNode
{
public:

  static vtkMRMLReportingAnnotationRANONode *New();
  vtkTypeMacro(vtkMRMLReportingAnnotationRANONode,vtkMRMLNode);
  void PrintSelf(ostream& os, vtkIndent indent);

  virtual vtkMRMLNode* CreateNodeInstance();

  /// Set node attributes
  virtual void ReadXMLAttributes( const char** atts);

  /// Write this node's information to a MRML file in XML format.
  virtual void WriteXML(ostream& of, int indent);

  /// Copy the node's attributes to this object
  virtual void Copy(vtkMRMLNode *node);

  /// Get node XML tag name (like Volume, Model)
  virtual const char* GetNodeTagName() {return "MRMLReportingAnnotationRANO";};

  /// Update the stored reference to another node in the scene
  //virtual void UpdateReferenceID(const char *oldID, const char *newID);

  /// Updates this node if it depends on other nodes
  /// when the node is deleted in the scene
  //virtual void UpdateReferences();

  // Description:
  //virtual void UpdateScene(vtkMRMLScene *scene);

  //virtual void ProcessMRMLEvents ( vtkObject *caller, unsigned long event, void *callData);

  typedef std::pair<std::string,std::string> StringPairType;

  friend class qMRMLReportingAnnotationRANOWidget;

protected:
  vtkMRMLReportingAnnotationRANONode();
  ~vtkMRMLReportingAnnotationRANONode();
  vtkMRMLReportingAnnotationRANONode(const vtkMRMLReportingAnnotationRANONode&);
  void operator=(const vtkMRMLReportingAnnotationRANONode&);

  // Structure
  // -- pairs <component,description> to initialize the GUI
  std::vector<StringPairType> componentDescriptionList;
  // -- map code ID -> code meaning
  std::map<std::string,std::string> codeToMeaningMap;
  // -- list codes that will be used to initialize each component (same order as components)
  std::vector<std::vector<std::string> > componentCodeList;

  // -- list of components selected (same order as components)
  std::vector<std::string> selectedCodeList;

private:
  std::vector<std::string> splitString(std::string, char);
};

#endif

