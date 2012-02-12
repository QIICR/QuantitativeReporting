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
#include <string>


//----------------------------------------------------------------------------
vtkMRMLNodeNewMacro(vtkMRMLReportingAnnotationRANONode);

//----------------------------------------------------------------------------
vtkMRMLReportingAnnotationRANONode::vtkMRMLReportingAnnotationRANONode()
{
  // initiate helpers
  this->componentDescriptionList.push_back(StringPairType(std::string("1 - Measurable Disease"),std::string("Presence or Absence of Measurable Lesions")));
  this->componentDescriptionList.push_back(StringPairType(std::string("2 - Non-measurable Disease"),std::string("Evaluation of Non-measurable Disease")));
  this->componentDescriptionList.push_back(StringPairType(std::string("3 - FLAIR"),std::string("Tumor Evaluation on FLAIR")));

  this->codeToMeaningMap[std::string("RANO0")] = std::string("Baseline");
  this->codeToMeaningMap[std::string("RANO1")] = std::string("Stable Disease");
  this->codeToMeaningMap[std::string("RANO4")] = std::string("Progressive Disease");
  this->codeToMeaningMap[std::string("RANO5")] = std::string("Not Present");
  this->codeToMeaningMap[std::string("RANO6")] = std::string("Non-evaluable");
  this->codeToMeaningMap[std::string("RANO7")] = std::string("Yes");
  this->codeToMeaningMap[std::string("RANO8")] = std::string("No");

  std::vector<std::string> componentVector;
  componentVector.push_back(std::string("RANO7"));
  componentVector.push_back(std::string("RANO8"));
  componentVector.push_back(std::string("RANO6"));
  this->componentCodeList.push_back(componentVector);
  componentVector.clear();
  componentVector.push_back(std::string("RANO1"));
  componentVector.push_back(std::string("RANO4"));
  componentVector.push_back(std::string("RANO0"));
  componentVector.push_back(std::string("RANO5"));
  componentVector.push_back(std::string("RANO6"));
  this->componentCodeList.push_back(componentVector);
  this->componentCodeList.push_back(componentVector);

  this->selectedCodeList.push_back(std::string("---"));
  this->selectedCodeList.push_back(std::string("---"));
  this->selectedCodeList.push_back(std::string("---"));
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

  os << indent << "Components and descriptions:" << std::endl;
  int nComponents = this->componentDescriptionList.size();
  for(int i=0;i<nComponents;i++)
  {
    os << indent << " " << this->componentDescriptionList[i].first << ": " << this->componentDescriptionList[i].second << std::endl;
    os << indent << " Allowed codes: ";
    int nCodes = this->componentCodeList[i].size();
    for(int j=0;j<nCodes;j++)
      os << this->componentCodeList[i][j] << " ";
    os << std::endl;
    os << indent << " Selected code: ";
    os << this->selectedCodeList[i] << " ";
    os << std::endl;
  }

  os << indent << "Code descriptions: " << std::endl;
  int nCodes = this->codeToMeaningMap.size();
  for(std::map<std::string,std::string>::iterator mIt=this->codeToMeaningMap.begin();
      mIt!=this->codeToMeaningMap.end();++mIt)
    os << indent << mIt->first << ": " << mIt->second << std::endl;
}
