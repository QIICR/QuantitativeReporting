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
  this->VolumeNodeID = "";
  this->ColorNodeID = "";
  this->FindingLabel = 1;
  this->AIMFileName = "";
}

//----------------------------------------------------------------------------
vtkMRMLReportingReportNode::~vtkMRMLReportingReportNode()
{
  this->VolumeNodeID = "";
  this->ColorNodeID = "";
  this->AIMFileName = "";
}

//----------------------------------------------------------------------------
void vtkMRMLReportingReportNode::ReadXMLAttributes(const char** atts)
{
  int disabledModify = this->StartModify();

  Superclass::ReadXMLAttributes(atts);

  const char * attName;
  const char * attValue;
  while(*atts != NULL)
    {
    attName = *(atts++);
    attValue = *(atts++);

    if(strcmp(attName, "VolumeNodeID"))
      {
      this->SetVolumeNodeID(attValue);
      }
    if(strcmp(attName, "FindingLabel"))
      {      
      this->SetFindingLabel(atoi(attValue));
      }
    if(strcmp(attName, "ColorNodeID"))
      {
      this->SetColorNodeID(attValue);
      }
    if(strcmp(attName, "AIMFileName"))
      {
      this->SetAIMFileName(attValue);
      }
    }

    this->EndModify(disabledModify);
}

//----------------------------------------------------------------------------
void vtkMRMLReportingReportNode::WriteXML(ostream& of, int nIndent)
{
  Superclass::WriteXML(of, nIndent);

  vtkIndent indent(nIndent);
  of << indent << " VolumeNodeID=\"" << this->VolumeNodeID << "\"";
  of << indent << " FindingLabel=\"" << this->FindingLabel << "\"";
  of << indent << " ColorNodeID=\"" << this->ColorNodeID << "\"";
  of << indent << " AIMFileName=\"" << this->AIMFileName << "\"";
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

  os << indent << "VolumeNodeID: " << this->VolumeNodeID << "\n";
  os << indent << "FindingLabel: " << this->FindingLabel << "\n";
  os << indent << "ColorNodeID: " << this->ColorNodeID << "\n";
  os << indent << "AIMFileName: " << this->AIMFileName << "\n";
}

//----------------------------------------------------------------------------
void vtkMRMLReportingReportNode::SetVolumeNodeID(std::string id)
{
  this->VolumeNodeID = id;
}

//----------------------------------------------------------------------------
std::string vtkMRMLReportingReportNode::GetVolumeNodeID()
{
  return this->VolumeNodeID;
}

//----------------------------------------------------------------------------
void vtkMRMLReportingReportNode::SetColorNodeID(std::string id)
{
  this->ColorNodeID = id;
}

//----------------------------------------------------------------------------
std::string vtkMRMLReportingReportNode::GetColorNodeID()
{
  return this->ColorNodeID;
}

//----------------------------------------------------------------------------
void vtkMRMLReportingReportNode::SetAIMFileName(std::string fname)
{
  this->AIMFileName = fname;
}

//----------------------------------------------------------------------------
std::string vtkMRMLReportingReportNode::GetAIMFileName()
{
  return this->AIMFileName;
}
