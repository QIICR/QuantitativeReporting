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

// Qt includes
#include <QString>
#include <QStringList>

//----------------------------------------------------------------------------
vtkMRMLNodeNewMacro(vtkMRMLReportingAnnotationRANONode);

//----------------------------------------------------------------------------
vtkMRMLReportingAnnotationRANONode::vtkMRMLReportingAnnotationRANONode()
{
  //this->measurableDiseaseCode = "";
  //this->nonmeasurableDiseaseCode = "";
  //this->flairCode = "";

  // initiate helpers
  this->componentDescriptionList.push_back(StringPairType(QString("1 - Measurable Disease"),QString("Presence or Absence of Measurable Lesions")));
  this->componentDescriptionList.push_back(StringPairType(QString("2 - Non-measurable Disease"),QString("Evaluation of Non-measurable Disease")));
  this->componentDescriptionList.push_back(StringPairType(QString("3 - FLAIR"),QString("Tumor Evaluation on FLAIR")));

  this->codeToMeaningMap[QString("RANO0")] = QString("Baseline");
  this->codeToMeaningMap[QString("RANO1")] = QString("Stable Disease");
  this->codeToMeaningMap[QString("RANO4")] = QString("Progressive Disease");
  this->codeToMeaningMap[QString("RANO5")] = QString("Not Present");
  this->codeToMeaningMap[QString("RANO6")] = QString("Non-evaluable");
  this->codeToMeaningMap[QString("RANO7")] = QString("Yes");
  this->codeToMeaningMap[QString("RANO8")] = QString("No");

  this->componentCodeList.push_back(QStringList() << "RANO7" << "RANO8" << "RANO6");
  this->componentCodeList.push_back(QStringList() << "RANO1" << "RANO4" << "RANO0" << "RANO5" << "RANO6");
  this->componentCodeList.push_back(QStringList() << "RANO1" << "RANO4" << "RANO0" << "RANO5" << "RANO6");

  this->selectedCodeList.push_back(QString());
  this->selectedCodeList.push_back(QString());
  this->selectedCodeList.push_back(QString());
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
/*
QString vtkMRMLReportingAnnotationRANONode::ConvertCodeToMeaning(QString code)
{
  return code2meaningDict[code];
}

QString vtkMRMLReportingAnnotationRANONode::GetMeasurableDiseaseCode() const
{
  return this->measurableDiseaseCode;
}

QString vtkMRMLReportingAnnotationRANONode::GetNonmeasurableDiseaseCode() const
{
  return this->nonmeasurableDiseaseCode;
}

QString vtkMRMLReportingAnnotationRANONode::GetFlairCode() const
{
  return this->flairCode;
}

void vtkMRMLReportingAnnotationRANONode::SetMeasurableDiseaseCode(QString code)
{
  this->measurableDiseaseCode = code;
}

void vtkMRMLReportingAnnotationRANONode::SetNonmeasurableDiseaseCode(QString code)
{
  this->nonmeasurableDiseaseCode = code;
}

void vtkMRMLReportingAnnotationRANONode::SetFlairCode(QString code)
{
  this->flairCode = code;
}
*/
