/*=auto=========================================================================

Portions (c) Copyright 2005 Brigham and Women\"s Hospital (BWH) All Rights Reserved.

See COPYRIGHT.txt
or http://www.slicer.org/copyright/copyright.txt for details.

Program:   3D Slicer
Module:    $RCSfile: vtkMRMLReportingAnnotationRANONode.cxx,v $
Date:      $Date: 2006/03/17 15:10:10 $
Version:   $Revision: 1.2 $

=========================================================================auto=*/

// VTK includes
#include <vtkCommand.h>
#include <vtkObjectFactory.h>
#include <vtkDoubleArray.h>

// MRML includes
#include "vtkMRMLVolumeNode.h"

// CropModuleMRML includes
#include "vtkMRMLReportingAnnotationRANONode.h"

// STD includes

//----------------------------------------------------------------------------
vtkMRMLNodeNewMacro(vtkMRMLReportingAnnotationRANONode);

//----------------------------------------------------------------------------
vtkMRMLReportingAnnotationRANONode::vtkMRMLReportingAnnotationRANONode()
{
}

//----------------------------------------------------------------------------
vtkMRMLReportingAnnotationRANONode::~vtkMRMLReportingAnnotationRANONode()
{
}

//----------------------------------------------------------------------------
void vtkMRMLReportingAnnotationRANONode::ReadXMLAttributes(const char** atts)
{
  Superclass::ReadXMLAttributes(atts);
  this->WriteXML(std::cout,1);
}

//----------------------------------------------------------------------------
void vtkMRMLReportingAnnotationRANONode::WriteXML(ostream& of, int nIndent)
{
  Superclass::WriteXML(of, nIndent);
}

//----------------------------------------------------------------------------
// Copy the node\"s attributes to this object.
// Does NOT copy: ID, FilePrefix, Name, SliceID
void vtkMRMLReportingAnnotationRANONode::Copy(vtkMRMLNode *anode)
{
  Superclass::Copy(anode);
}

//----------------------------------------------------------------------------
void vtkMRMLReportingAnnotationRANONode::PrintSelf(ostream& os, vtkIndent indent)
{
  Superclass::PrintSelf(os,indent);
}
