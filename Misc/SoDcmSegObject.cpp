/*
 *  COPYRIGHT NOTICE.  Copyright (C) 2007 Siemens Corporate Research, 
 *  Inc. ("caBIG(tm) Participant"). The eXtensible Imaging Platform
 *  (XIP) was created with NCI funding and is part of the caBIG(tm) 
 *  initiative. The software subject to this notice and license 
 *  includes both human readable source code form and machine 
 *  readable, binary, object code form (the "caBIG(tm) Software").
 *  
 *  This caBIG(tm) Software License (the "License") is between 
 *  caBIG(tm) Participant and You.  "You (or "Your") shall mean a 
 *  person or an entity, and all other entities that control, are 
 *  controlled by, or are under common control with the entity.  
 *  "Control" for purposes of this definition means (i) the direct or 
 *  indirect power to cause the direction or management of such 
 *  entity, whether by contract or otherwise, or (ii) ownership of 
 *  fifty percent (50%) or more of the outstanding shares, or (iii) 
 *  beneficial ownership of such entity.
 *  
 *  LICENSE.  Provided that You agree to the conditions described 
 *  below, caBIG(tm) Participant grants You a non-exclusive, 
 *  worldwide, perpetual, fully-paid-up, no-charge, irrevocable, 
 *  transferable and royalty-free right and license in its rights in 
 *  the caBIG(tm) Software, including any copyright or patent rights 
 *  therein that may be infringed by the making, using, selling, 
 *  offering for sale, or importing of caBIG(tm) Software, to (i) 
 *  use, install, access, operate, execute, reproduce, copy, modify, 
 *  translate, market, publicly display, publicly perform, and 
 *  prepare derivative works of the caBIG(tm) Software; (ii) make, 
 *  have made, use, practice, sell, and offer for sale, and/or 
 *  otherwise dispose of caBIG(tm) Software (or portions thereof); 
 *  (iii) distribute and have distributed to and by third parties the 
 *  caBIG(tm) Software and any modifications and derivative works 
 *  thereof; and (iv) sublicense the foregoing rights set out in (i), 
 *  (ii) and (iii) to third parties, including the right to license 
 *  such rights to further third parties.  For sake of clarity, and 
 *  not by way of limitation, caBIG(tm) Participant shall have no 
 *  right of accounting or right of payment from You or Your 
 *  sublicensees for the rights granted under this License.  This 
 *  License is granted at no charge to You.  Your downloading, 
 *  copying, modifying, displaying, distributing or use of caBIG(tm) 
 *  Software constitutes acceptance of all of the terms and 
 *  conditions of this Agreement.  If you do not agree to such terms 
 *  and conditions, you have no right to download, copy, modify, 
 *  display, distribute or use the caBIG(tm) Software.
 *  
 *  1.	Your redistributions of the source code for the caBIG(tm) 
 *      Software must retain the above copyright notice, this list 
 *      of conditions and the disclaimer and limitation of 
 *      liability of Article 6 below.  Your redistributions in 
 *      object code form must reproduce the above copyright notice, 
 *      this list of conditions and the disclaimer of Article 6 in 
 *      the documentation and/or other materials provided with the 
 *      distribution, if any.
 *  2.	Your end-user documentation included with the 
 *      redistribution, if any, must include the following 
 *      acknowledgment: "This product includes software developed 
 *      by Siemens Corporate Research Inc."  If You do not include 
 *      such end-user documentation, You shall include this 
 *      acknowledgment in the caBIG(tm) Software itself, wherever 
 *      such third-party acknowledgments normally appear.
 *  3.	You may not use the names "Siemens Corporate Research, 
 *      Inc.", "The National Cancer Institute", "NCI", "Cancer 
 *      Bioinformatics Grid" or "caBIG(tm)" to endorse or promote 
 *      products derived from this caBIG(tm) Software.  This 
 *      License does not authorize You to use any trademarks, 
 *  	service marks, trade names, logos or product names of 
 *      either caBIG(tm) Participant, NCI or caBIG(tm), except as 
 *      required to comply with the terms of this License.
 *  4.	For sake of clarity, and not by way of limitation, You may 
 *      incorporate this caBIG(tm) Software into Your proprietary 
 *      programs and into any third party proprietary programs.  
 *      However, if You incorporate the caBIG(tm) Software into 
 *      third party proprietary programs, You agree that You are 
 *      solely responsible for obtaining any permission from such 
 *      third parties required to incorporate the caBIG(tm) 
 *      Software into such third party proprietary programs and for 
 *      informing Your sublicensees, including without limitation 
 *      Your end-users, of their obligation to secure any required 
 *      permissions from such third parties before incorporating 
 *      the caBIG(tm) Software into such third party proprietary 
 *      software programs.  In the event that You fail to obtain 
 *      such permissions, You agree to indemnify caBIG(tm) 
 *      Participant for any claims against caBIG(tm) Participant by 
 *      such third parties, except to the extent prohibited by law, 
 *      resulting from Your failure to obtain such permissions.
 *  5.	For sake of clarity, and not by way of limitation, You may 
 *      add Your own copyright statement to Your modifications and 
 *      to the derivative works, and You may provide additional or 
 *      different license terms and conditions in Your sublicenses 
 *      of modifications of the caBIG(tm) Software, or any 
 *      derivative works of the caBIG(tm) Software as a whole, 
 *      provided Your use, reproduction, and distribution of the 
 *      Work otherwise complies with the conditions stated in this 
 *      License.
 *  6.	THIS caBIG(tm) SOFTWARE IS PROVIDED "AS IS" AND ANY 
 *      EXPRESSED OR IMPLIED WARRANTIES (INCLUDING, BUT NOT LIMITED 
 *      TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY, NON-
 *      INFRINGEMENT AND FITNESS FOR A PARTICULAR PURPOSE) ARE 
 *      DISCLAIMED.  IN NO EVENT SHALL SIEMENS CORPORATE RESEARCH 
 *      INC. OR ITS AFFILIATES BE LIABLE FOR ANY DIRECT, INDIRECT, 
 *      INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
 *      (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE 
 *      GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR 
 *      BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
 *      LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
 *      (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT 
 *      OF THE USE OF THIS caBIG(tm) SOFTWARE, EVEN IF ADVISED OF 
 *      THE POSSIBILITY OF SUCH DAMAGE.
 *  
 */

/* author Jie Zheng */

// SoDcmSegObject.cpp: implementation of the SoDcmSegObject class.
//
//////////////////////////////////////////////////////////////////////

#include "SoDcmSegObject.h"
#include <Inventor/errors/SoMemoryError.h>
#include <string>
#include <io.h>

const float pi = 3.1415726;
const float epsilon = 0.000001f;

using namespace std ;

#define UID_SegmentationSOPClass          "1.2.840.10008.5.1.4.1.1.66.4"

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////
SO_ENGINE_SOURCE( SoDcmSegObject );

SoDcmSegObject::SoDcmSegObject()
{
	SO_ENGINE_CONSTRUCTOR( SoDcmSegObject );

	//Initialize the input parameter
	SO_ENGINE_ADD_INPUT( file, (SbString()) );

	SO_ENGINE_ADD_INPUT( refInput, (0) );
	refInput.setNum(0);

	SO_ENGINE_ADD_INPUT( ann_name, (SbString()) );
	SO_ENGINE_ADD_INPUT( ann_date, (SbString()) );
	SO_ENGINE_ADD_INPUT( tumor_ID, (SbString()) );
	SO_ENGINE_ADD_INPUT( tumor_Confidence, (SbString()) );
	SO_ENGINE_ADD_INPUT( tumor_Comments, (SbString()) );

	SO_ENGINE_ADD_INPUT( origin, (0) );
	SO_ENGINE_ADD_INPUT( input0, (NULL) );

	SO_ENGINE_ADD_INPUT( process, () );

	// Outputs
	SO_ENGINE_ADD_OUTPUT( status, SoSFBool );	

	mXipImage = NULL;
}

void SoDcmSegObject::initClass()
{
	SO_ENGINE_INIT_CLASS( SoDcmSegObject, SoEngine, "SoEngine" );
}

SoDcmSegObject::~SoDcmSegObject()
{
	if( mXipImage )
	{
		mXipImage->unref();
		mXipImage = 0;
	}
}

void SoDcmSegObject::inputChanged(SoField *whichInput)
{
	if (whichInput == &process || whichInput == &file)
		processResult();
}

void SoDcmSegObject::evaluate()
{
	SO_ENGINE_OUTPUT( status, SoSFBool, setValue(true) );	
}

void SoDcmSegObject::processResult()
{
	if (!loadDicomStrings())
		return;

	SbString filename = file.getValue();

	SoXipDataImage *pXipData = input0.getValue();
	if( !pXipData)
		return;

	char uid[128];
	SbString strSOPUID = dcmGenerateUniqueIdentifier(uid, SITE_INSTANCE_UID_ROOT);

	saveSegObject(filename.getString(), strSOPUID.getString());
}

BOOL SoDcmSegObject::saveSegObject(const char *filename, const char *maskUID)
{
	DcmFileFormat fileformat; 
	DcmDataset *dataset = fileformat.getDataset(); 

	//get segmentation information
	SoXipDataImage *inputXipImage = input0.getValue();
	if( !inputXipImage )
		return false;

    SbXipImage* inputImage = inputXipImage->get();
	SbXipImageDimensions dimensions = inputImage->getDimStored();

	int nDimension[ 3 ];
	nDimension[0] = dimensions[0];
	nDimension[1] = dimensions[1];
	nDimension[2] = dimensions[2];

	//create DICOM segment header
	writeSegHeader(dataset, maskUID, nDimension);

	SbMatrix volModelMatrix = inputImage->getModelMatrix();

	//decompose the model matrix
	SbVec3f colVector, rowVector, norVector, volPosition;

	colVector[0] = volModelMatrix[0][0];
	colVector[1] = volModelMatrix[0][1];
	colVector[2] = volModelMatrix[0][2];

	rowVector[0] = volModelMatrix[1][0];
	rowVector[1] = volModelMatrix[1][1];
	rowVector[2] = volModelMatrix[1][2];

	norVector[0] = volModelMatrix[2][0];
	norVector[1] = volModelMatrix[2][1];
	norVector[2] = volModelMatrix[2][2];

	volPosition[0] = volModelMatrix[3][0];
	volPosition[1] = volModelMatrix[3][1];
	volPosition[2] = volModelMatrix[3][2];

	float fVolumePosition[3];
	fVolumePosition[0] = volPosition[0];
	fVolumePosition[1] = volPosition[1];
	fVolumePosition[2] = volPosition[2];

	float fVolumeSpacing[3];
	fVolumeSpacing[0] = colVector.length() / float(nDimension[0]);
	fVolumeSpacing[1] = rowVector.length() / float(nDimension[1]);
	fVolumeSpacing[2] = norVector.length() / float(nDimension[2]);

	//create DICOM segment frames
	writeSegFrames(dataset, colVector, rowVector, volPosition, fVolumeSpacing, nDimension);

	//write the mask
	unsigned char* radData = (unsigned char*)inputImage->refBufferPtr();
	writeSegPixel(dataset, radData, nDimension);

	//save as DICOM segmenta object
	OFCondition status = fileformat.saveFile(filename, EXS_LittleEndianExplicit);

	if (status.good())
		return true;
	else
		return false;
}

void SoDcmSegObject::writeSegHeader(DcmDataset *dataset, const char *maskUID, int iSegDimension[3])
{
	assert(dataset != NULL);

	SbString strName = dicom_name;
	SbString strGender = dicom_gender;
	SbString strAge = dicom_age;
	SbString strPatID = dicom_patientID;
	SbString strStudyID = dicom_studyID;
	SbString strStudyUID = dicom_studyUID;
	SbString strSeriesNumber = dicom_seriesNumber;

	SbString strAnnDate = ann_date.getValue();

	dataset->putAndInsertString(DCM_StudyDate,strAnnDate.getString());
	dataset->putAndInsertString(DCM_PatientsName,strName.getString());
	dataset->putAndInsertString(DCM_PatientsSex,strGender.getString());
	dataset->putAndInsertString(DCM_PatientsAge,strAge.getString());
	dataset->putAndInsertString(DCM_PatientID,strPatID.getString());
	dataset->putAndInsertString(DCM_StudyID,strStudyID.getString());
	dataset->putAndInsertString(DCM_StudyInstanceUID,strStudyUID.getString());
	dataset->putAndInsertString(DCM_AccessionNumber,"1");

	dataset->putAndInsertString(DCM_StudyDate, dicom_studyDate.getString());
	dataset->putAndInsertString(DCM_StudyTime, dicom_studyTime.getString());

	dataset->putAndInsertUint16(DCM_FileMetaInformationVersion,0x0001);
	dataset->putAndInsertString(DCM_SOPClassUID, UID_SegmentationSOPClass);
	dataset->putAndInsertString(DCM_SOPInstanceUID, maskUID);
	dataset->putAndInsertString(DCM_Modality,"SEG");
	dataset->putAndInsertString(DCM_ImageType,"DERIVED\\PRIMARY");
	dataset->putAndInsertString(DCM_SeriesNumber,"1");
	dataset->putAndInsertString(DCM_InstanceNumber,"1");

	char uid[128];
	SbString strSeriesUID = dcmGenerateUniqueIdentifier(uid, SITE_SERIES_UID_ROOT);
	dataset->putAndInsertString(DCM_SeriesInstanceUID,strSeriesUID.getString());
	dataset->putAndInsertString(DCM_InstanceCreatorUID,OFFIS_UID_ROOT);

	strSeriesUID = dicom_seriesUID;
	dataset->putAndInsertString(DCM_FrameOfReferenceUID,strSeriesUID.getString());

	char buf[16] = {0};
	sprintf(buf,"%d", iSegDimension[0]);
	dataset->putAndInsertString(DCM_Columns,buf);

	sprintf(buf,"%d", iSegDimension[1]);
	dataset->putAndInsertString(DCM_Rows,buf);

	sprintf(buf,"%d", iSegDimension[2]);
	dataset->putAndInsertString(DCM_NumberOfFrames,buf);

	dataset->putAndInsertString(DCM_SamplesPerPixel,"1");
	dataset->putAndInsertString(DCM_PhotometricInterpretation,"MONOCHROME2");
	
	dataset->putAndInsertString(DCM_BitsAllocated,"8");
	dataset->putAndInsertString(DCM_BitsStored,"8");
	dataset->putAndInsertString(DCM_HighBit,"7");
	dataset->putAndInsertString(DCM_PixelRepresentation,"0");
	dataset->putAndInsertString(DCM_LossyImageCompression,"00");

}


void SoDcmSegObject::writeSegFrames(DcmDataset *dataset, SbVec3f &colVector, SbVec3f &rowVector, SbVec3f &volPosition, float fVolumeSpacing[3], int iSegDimension[3])
{
	char buf[64];

	SbVec3f colDir = colVector;
	colDir.normalize();

	SbVec3f rowDir = rowVector;
	rowDir.normalize();

	sprintf(buf, "%f\\%f\\%f\\%f\\%f\\%f", colDir[0], colDir[1], colDir[2], rowDir[0], rowDir[1], rowDir[2]);
	SbString strPatOrientation = buf;
	dataset->putAndInsertString(DCM_ImageOrientationPatient,strPatOrientation.getString());

	sprintf(buf, "%f\\%f\\%f", volPosition[0], volPosition[1], volPosition[2]);
	SbString  strPatPosition = buf;
	dataset->putAndInsertString(DCM_ImagePositionPatient,strPatPosition.getString());

	sprintf(buf, "%f", fVolumeSpacing[2]);
    dataset->putAndInsertString(DCM_SliceThickness, buf);

	sprintf(buf, "%f\\%f", fVolumeSpacing[0], fVolumeSpacing[1]);
	dataset->putAndInsertString(DCM_PixelSpacing, buf);

 	DcmItem *Item = NULL;
 	DcmItem *subItem = NULL;
	dataset->putAndInsertString(DCM_SegmentationType,"BINARY");

	SbString strTumorID = tumor_ID.getValue();
	dataset->putAndInsertString(DCM_ContentLabel,strTumorID.getString());

	SbString strTumorComment = tumor_Comments.getValue();
	dataset->putAndInsertString(DCM_ContentDescription,strTumorComment.getString());

	SbString strAnnName = ann_name.getValue();
	dataset->putAndInsertString(DCM_ContentCreatorsName,strAnnName.getString());

	//segment sequence [0x00620,0x0002]
	dataset->findOrCreateSequenceItem(DCM_SegmentSequence,Item);
	
  	Item->putAndInsertString(DCM_SegmentNumber,"1");
	Item->putAndInsertString(DCM_SegmentLabel,"Segmentation");
	Item->putAndInsertString(DCM_SegmentAlgorithmType,"SEMIAUTOMATIC");
	Item->putAndInsertString(DCM_SegmentAlgorithmName,"FastMarching");

	//segmentation properties - category
    Item->findOrCreateSequenceItem(DCM_SegmentedPropertyCategoryCodeSequence, subItem);
	subItem->putAndInsertString(DCM_CodeValue,"T-D0050");
	subItem->putAndInsertString(DCM_CodingSchemeDesignator,"SRT");
	subItem->putAndInsertString(DCM_CodeMeaning,"Tissue");

	//segmentation properties - type
    Item->findOrCreateSequenceItem(DCM_SegmentedPropertyTypeCodeSequence, subItem);
	subItem->putAndInsertString(DCM_CodeValue,"M-03010");
	subItem->putAndInsertString(DCM_CodingSchemeDesignator,"SRT");
	subItem->putAndInsertString(DCM_CodeMeaning,"Nodule");

	//Shared functional groups sequence
	dataset->findOrCreateSequenceItem(DCM_SharedFunctionalGroupsSequence, Item);

	//segmentation macro - attributes
    Item->findOrCreateSequenceItem(DCM_SegmentIdentificationSequence, subItem);
	subItem->putAndInsertString(DCM_ReferencedSegmentNumber,"1");

	//segmentation functional group macros
	sprintf(buf, "%f", fVolumeSpacing[2]);
    Item->putAndInsertString(DCM_SliceThickness, buf);

	sprintf(buf, "%f\\%f", fVolumeSpacing[0], fVolumeSpacing[1]);
	Item->putAndInsertString(DCM_PixelSpacing, buf);

	const unsigned long itemNum = iSegDimension[2]-1;

	//Derivation Image functional group
    Item->findOrCreateSequenceItem(DCM_DerivationImageSequence, subItem, itemNum);

	for (int i = 0; i < itemNum+1; i++)
	{
		SbString strSopUID;
		if (loadImageInstanceUID(i+origin[2], strSopUID))
		{
			Item->findAndGetSequenceItem(DCM_DerivationImageSequence,subItem,i);

			subItem->putAndInsertString(DCM_SOPClassUID,dicom_sopClassUID.getString());
			subItem->putAndInsertString(DCM_SOPInstanceUID,strSopUID.getString());
		}
	}

	//per-frame functional groups
    dataset->findOrCreateSequenceItem(DCM_PerFrameFunctionalGroupsSequence, Item, itemNum);
	
	for (int i=0;i<itemNum+1;i++)
	{
		dataset->findAndGetSequenceItem(DCM_PerFrameFunctionalGroupsSequence,Item,i);

		Item->findOrCreateSequenceItem(DCM_FrameContentSequence, subItem);
		subItem->putAndInsertString(DCM_StackID,"1"); 
		
		sprintf(buf, "%d", i+1);
		subItem->putAndInsertString(DCM_InStackPositionNumber,buf);

		DcmItem *seqItem = NULL;

		sprintf(buf, "%f\\%f\\%f", volPosition[0], volPosition[1], volPosition[2]+i*fVolumeSpacing[2]);
		SbString  strPosition = buf;
		subItem->findOrCreateSequenceItem(DCM_PlanePositionSequence, seqItem);
		seqItem->putAndInsertString(DCM_ImagePositionPatient,strPosition.getString());

		sprintf(buf, "%f\\%f\\%f\\%f\\%f\\%f", colDir[0], colDir[1], colDir[2], rowDir[0], rowDir[1], rowDir[2]);
		SbString strOrientation = buf;
		subItem->findOrCreateSequenceItem(DCM_PlaneOrientationSequence, seqItem);
		seqItem->putAndInsertString(DCM_ImageOrientationPatient,strOrientation.getString());
	}//Per-Frame Functional Groups Sequence information

}

void SoDcmSegObject::writeSegPixel(DcmDataset *dataset, unsigned char *pData, int iSegDimension[3])
{
	assert(dataset != NULL);
	assert(pData != NULL);

	int iSize = iSegDimension[0]*iSegDimension[1]*iSegDimension[2];

	BYTE *pMask = new BYTE[iSize];
	memcpy(pMask, pData, iSize);

	dataset->putAndInsertUint8Array(DCM_PixelData,reinterpret_cast<const Uint8*>(pMask), iSize);//write pixels

	delete [] pMask;
	pMask = NULL;

}

bool SoDcmSegObject::loadImageInstanceUID(int index, SbString &strUID)
{
	if (refInput.getNum() <= index)
		return false;

	SoXipDataDicom *dicom = refInput[index];

	if (dicom)
	{
		if (!dicom->getDataset().isNull())
		{
			SbXipDicomItem dataset(dicom->getDataset());

			//SOP Instance UID
			dataset.findAndGet(SbXipDicomTagKey(0x08, 0x18), strUID, true);

			return true;
		}
	}

	return false;
}

bool SoDcmSegObject::loadDicomStrings()
{
	if (refInput.getNum() <= 0)
		return false;

	SoXipDataDicom *dicom = refInput[0];

	if (dicom)
	{
		if (!dicom->getDataset().isNull())
		{
			SbXipDicomItem dataset(dicom->getDataset());

			//patient name
			dataset.findAndGet(SbXipDicomTagKey(0x10, 0x10), dicom_name, true);

			//patient ID
			dataset.findAndGet(SbXipDicomTagKey(0x10, 0x20), dicom_patientID, true);

			//patient gender
			dataset.findAndGet(SbXipDicomTagKey(0x10, 0x40), dicom_gender, true);

			//patient age
			dataset.findAndGet(SbXipDicomTagKey(0x10, 0x1010), dicom_age, true);

			//study ID
			dataset.findAndGet(SbXipDicomTagKey(0x20, 0x10), dicom_studyID, true);

			//study date
			dataset.findAndGet(SbXipDicomTagKey(0x08, 0x20), dicom_studyDate, true);

			//study time
			dataset.findAndGet(SbXipDicomTagKey(0x08, 0x30), dicom_studyTime, true);

			//study InstanceUID
			dataset.findAndGet(SbXipDicomTagKey(0x20, 0x0d), dicom_studyUID, true);

			//series number
			dataset.findAndGet(SbXipDicomTagKey(0x20, 0x11), dicom_seriesNumber, true);

			//series InstanceUID
			dataset.findAndGet(SbXipDicomTagKey(0x20, 0x0e), dicom_seriesUID, true);

			//volume orientation
			dataset.findAndGet(SbXipDicomTagKey(0x20, 0x37), dicom_imageOrientation, true);

			//volume positon
			dataset.findAndGet(SbXipDicomTagKey(0x20, 0x32), dicom_imagePosition, true);

			//slice thickness
			dataset.findAndGet(SbXipDicomTagKey(0x18, 0x50), dicom_sliceThickness, true);

			//pixel spacing
			dataset.findAndGet(SbXipDicomTagKey(0x28, 0x30), dicom_pixelSpacing, true);

			//sop class UID
			dataset.findAndGet(SbXipDicomTagKey(0x08, 0x16), dicom_sopClassUID, true);

			SbString strBuf;
			
			//image col
			dataset.findAndGet(SbXipDicomTagKey(0x0028, 0x0011), dicom_imageCols, true);

			//image row
			dataset.findAndGet(SbXipDicomTagKey(0x0028, 0x0010), dicom_imageRows, true);

			return true;
		}
	}

	return false;

}
