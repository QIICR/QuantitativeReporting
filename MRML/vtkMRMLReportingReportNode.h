/*=auto=========================================================================

  Portions (c) Copyright 2005 Brigham and Women's Hospital (BWH) All Rights Reserved.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Program:   3D Slicer
  Module:    $RCSfile: vtkMRMLVolumeRenderingParametersNode.h,v $
  Date:      $Date: 2006/03/19 17:12:29 $
  Version:   $Revision: 1.3 $

=========================================================================auto=*/
// .NAME vtkMRMLReportingReportNode 
// This node keeps pointers to the two elements of the report: annotation
// and markup.
//
// Annotation element will (eventually) contain the report template and the
// user-initialized fields of the template.
//
// Markup element will point to the hierarchy of the markup elements.
//
// On export/import, this node will be used by the IO logic to determine how
// to code the formatted report.
// .SECTION Description
// This node keeps pointers to the two elements of the report: annotation
// and markup.
//

#ifndef __vtkMRMLReportingReportNode_h
#define __vtkMRMLReportingReportNode_h

// MRML includes
#include "vtkDoubleArray.h"
#include "vtkMRML.h"
#include "vtkMRMLNode.h"
#include "vtkMRMLScene.h"
#include <vtkSlicerReportingModuleMRMLExport.h>


/// \ingroup Slicer_QtModules_ReportingReportNode
class VTK_SLICER_REPORTING_MODULE_MRML_EXPORT vtkMRMLReportingReportNode : public vtkMRMLNode
{
  public:   

  static vtkMRMLReportingReportNode *New();
  vtkTypeMacro(vtkMRMLReportingReportNode,vtkMRMLNode);
  void PrintSelf(ostream& os, vtkIndent indent);

  virtual vtkMRMLNode* CreateNodeInstance();

  /// Set node attributes
  virtual void ReadXMLAttributes( const char** atts);

  /// Write this node's information to a MRML file in XML format.
  virtual void WriteXML(ostream& of, int indent);

  /// Copy the node's attributes to this object
  virtual void Copy(vtkMRMLNode *node);

  /// Get node XML tag name (like Volume, Model)
  virtual const char* GetNodeTagName() {return "Report";};

  std::string GetVolumeNodeID();
  void SetVolumeNodeID(std::string);
  
  vtkGetMacro(FindingLabel, int);
  vtkSetMacro(FindingLabel, int);

  std::string GetColorNodeID();
  void SetColorNodeID(std::string);
  
  std::string GetAIMFileName();
  void SetAIMFileName(std::string);

  std::string GetDICOMDatabaseFileName();
  void SetDICOMDatabaseFileName(std::string);

  vtkBooleanMacro(AllowOutOfPlaneMarkups, int);
  vtkGetMacro(AllowOutOfPlaneMarkups, int);
  vtkSetMacro(AllowOutOfPlaneMarkups, int);
  
protected:
  vtkMRMLReportingReportNode();
  ~vtkMRMLReportingReportNode();
  vtkMRMLReportingReportNode(const vtkMRMLReportingReportNode&);
  void operator=(const vtkMRMLReportingReportNode&);

  /// volume being annotated
  std::string VolumeNodeID;
  /// label assigned to the structure being annotated
  int   FindingLabel;
  /// color node used to associate the label with the terminology
  std::string ColorNodeID;
  /// XML file that will be used for serialization in AIM format
  std::string AIMFileName; 

  std::string DICOMDatabaseFileName;

  /// Default 0, don't allow users to place annotations out of or spanning
  /// scan acquisition planes. If 1, warn the user, if 0, delete the
  /// annotation when error is detected
  int AllowOutOfPlaneMarkups;
};

#endif

