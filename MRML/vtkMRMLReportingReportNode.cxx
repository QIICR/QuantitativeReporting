/*=auto=========================================================================

Portions (c) Copyright 2005 Brigham and Women\"s Hospital (BWH) All Rights Reserved.

See COPYRIGHT.txt
or http://www.slicer.org/copyright/copyright.txt for details.

Program:   3D Slicer
Module:    $RCSfile: vtkMRMLReprtingReportNode.cxx,v $
Date:      $Date: 2006/03/17 15:10:10 $
Version:   $Revision: 1.2 $

=========================================================================auto=*/

// VTK includes
#include <vtkCommand.h>
#include <vtkObjectFactory.h>
#include <vtkDoubleArray.h>

// MRML includes
#include "vtkMRMLReportingReportNode.h"

// STD includes

//----------------------------------------------------------------------------
vtkMRMLNodeNewMacro(vtkMRMLReportingReportNode);

//----------------------------------------------------------------------------
vtkMRMLReportingReportNode::vtkMRMLReportingReportNode()
{
  this->HideFromEditors = 0;
}

//----------------------------------------------------------------------------
vtkMRMLReportingReportNode::~vtkMRMLReportingReportNode()
{
}

//----------------------------------------------------------------------------
void vtkMRMLReportingReportNode::ReadXMLAttributes(const char** atts)
{
  Superclass::ReadXMLAttributes(atts);
  this->WriteXML(std::cout,1);
}

//----------------------------------------------------------------------------
void vtkMRMLReportingReportNode::WriteXML(ostream& of, int nIndent)
{
  Superclass::WriteXML(of, nIndent);
}

//----------------------------------------------------------------------------
// Copy the node\"s attributes to this object.
// Does NOT copy: ID, FilePrefix, Name, SliceID
void vtkMRMLReportingReportNode::Copy(vtkMRMLNode *anode)
{
  Superclass::Copy(anode);
}

//----------------------------------------------------------------------------
void vtkMRMLReportingReportNode::PrintSelf(ostream& os, vtkIndent indent)
{
  Superclass::PrintSelf(os,indent);
}
