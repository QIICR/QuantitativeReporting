/*=auto=========================================================================

  Portions (c) Copyright 2005 Brigham and Women's Hospital (BWH) All Rights Reserved.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Program:   3D Slicer
  Module:    $RCSfile: vtkMRMLVolumeRenderingParametersNode.h,v $
  Date:      $Date: 2006/03/19 17:12:29 $
  Version:   $Revision: 1.3 $

=========================================================================auto=*/
// .NAME vtkMRMLReportingAnnotationNode Node to keep the conent and possibly describe the structure of a structured report 
// .SECTION Description
// This node stores the content and possible structure of the report
//
//

#ifndef __vtkMRMLReportingAnnotationNode_h
#define __vtkMRMLReportingAnnotationNode_h

// MRML includes
#include "vtkDoubleArray.h"
#include "vtkMRML.h"
#include "vtkMRMLNode.h"
#include "vtkMRMLScene.h"
#include <vtkSlicerReportingModuleMRMLExport.h>


/// \ingroup Slicer_QtModules_ReportingAnnotationNode
class VTK_SLICER_REPORTING_MODULE_MRML_EXPORT vtkMRMLReportingAnnotationNode : public vtkMRMLNode
{
  public:   

  static vtkMRMLReportingAnnotationNode *New();
  vtkTypeMacro(vtkMRMLReportingAnnotationNode,vtkMRMLNode);
  void PrintSelf(ostream& os, vtkIndent indent);

  virtual vtkMRMLNode* CreateNodeInstance();

  /// Set node attributes
  virtual void ReadXMLAttributes( const char** atts);

  /// Write this node's information to a MRML file in XML format.
  virtual void WriteXML(ostream& of, int indent);

  /// Copy the node's attributes to this object
  virtual void Copy(vtkMRMLNode *node);

  /// Get node XML tag name (like Volume, Model)
  virtual const char* GetNodeTagName() {return "MRMLReportingAnnotation";};

  /// Update the stored reference to another node in the scene
  //virtual void UpdateReferenceID(const char *oldID, const char *newID);

  /// Updates this node if it depends on other nodes
  /// when the node is deleted in the scene
  //virtual void UpdateReferences();

  // Description:
  //virtual void UpdateScene(vtkMRMLScene *scene);

  //virtual void ProcessMRMLEvents ( vtkObject *caller, unsigned long event, void *callData);

protected:
  vtkMRMLReportingAnnotationNode();
  ~vtkMRMLReportingAnnotationNode();
  vtkMRMLReportingAnnotationNode(const vtkMRMLReportingAnnotationNode&);
  void operator=(const vtkMRMLReportingAnnotationNode&);
};

#endif

