#include "dcmtk/config/osconfig.h"   // make sure OS specific configuration is included first
#include "dcmtk/ofstd/ofstream.h"
#include "dcmtk/oflog/oflog.h"
#include "dcmtk/ofstd/ofconapp.h"
#include "dcmtk/dcmseg/segdoc.h"
#include "dcmtk/dcmseg/segment.h"
#include "dcmtk/dcmseg/segutils.h"
#include "dcmtk/dcmfg/fginterface.h"
#include "dcmtk/dcmiod/iodutil.h"
#include "dcmtk/dcmiod/modmultiframedimension.h"
#include "dcmtk/dcmdata/dcsequen.h"

#include "dcmtk/dcmfg/fgderimg.h"
#include "dcmtk/dcmfg/fgplanor.h"
#include "dcmtk/dcmfg/fgpixmsr.h"
#include "dcmtk/dcmfg/fgfracon.h"
#include "dcmtk/dcmfg/fgplanpo.h"
#include "dcmtk/dcmfg/fgseg.h"

#include "dcmtk/oflog/loglevel.h"

#include "vnl/vnl_cross.h"

#define INCLUDE_CSTDLIB
#define INCLUDE_CSTRING
#include "dcmtk/ofstd/ofstdinc.h"

#include <sstream>
#include <map>
#include <vector>

#ifdef WITH_ZLIB
#include <zlib.h>                     /* for zlibVersion() */
#endif

// ITK includes
#include <itkImageFileWriter.h>
#include <itkLabelImageToLabelMapFilter.h>
#include <itkImageRegionConstIterator.h>
#include <itkChangeInformationImageFilter.h>
#include <itkImageDuplicator.h>


#include "framesorter.h"
#include "SegmentAttributes.h"

// CLP inclides
#include "SEG2NRRDCLP.h"

static OFLogger dcemfinfLogger = OFLog::getLogger("qiicr.apps.iowa1");

#define CHECK_COND(condition) \
    do { \
        if (condition.bad()) { \
            OFLOG_FATAL(dcemfinfLogger, condition.text() << " in " __FILE__ << ":" << __LINE__ ); \
            throw -1; \
        } \
    } while (0)

typedef unsigned short PixelType;
typedef itk::Image<PixelType,3> ImageType;

double distanceBwPoints(vnl_vector<double> from, vnl_vector<double> to){
  return sqrt((from[0]-to[0])*(from[0]-to[0])+(from[1]-to[1])*(from[1]-to[1])+(from[2]-to[2])*(from[2]-to[2]));
}

int getImageDirections(FGInterface &fgInterface, ImageType::DirectionType &dir);
int getDeclaredImageSpacing(FGInterface &fgInterface, ImageType::SpacingType &spacing);
int computeVolumeExtent(FGInterface &fgInterface, vnl_vector<double> &sliceDirection, ImageType::PointType &imageOrigin, double &sliceSpacing, double &sliceExtent);

int main(int argc, char *argv[])
{
  PARSE_ARGS;

  dcemfinfLogger.setLogLevel(dcmtk::log4cplus::OFF_LOG_LEVEL);

  DcmFileFormat segFF;
  DcmDataset *segDataset = NULL;
  if(segFF.loadFile(inputSEGFileName.c_str()).good()){
    segDataset = segFF.getDataset();
  } else {
    std::cerr << "Failed to read input " << std::endl;
    return -1;
  }

  OFCondition cond;
  DcmSegmentation *segdoc = NULL;
  cond = DcmSegmentation::loadFile(inputSEGFileName.c_str(), segdoc);
  if(!segdoc){
    std::cerr << "Failed to load seg! " << cond.text() << std::endl;
    return -1;
  }

  DcmSegment *segment = segdoc->getSegment(1);
  FGInterface &fgInterface = segdoc->getFunctionalGroups();

  ImageType::PointType imageOrigin;
  ImageType::RegionType imageRegion;
  ImageType::SizeType imageSize;
  ImageType::SpacingType imageSpacing;
  ImageType::Pointer segImage = ImageType::New();

  // Directions
  ImageType::DirectionType dir;
  if(getImageDirections(fgInterface, dir)){
    std::cerr << "Failed to get image directions" << std::endl;
    return -1;
  }

  // Spacing and origin
  double computedSliceSpacing, computedVolumeExtent;
  vnl_vector<double> sliceDirection(3);
  sliceDirection[0] = dir[0][2];
  sliceDirection[1] = dir[1][2];
  sliceDirection[2] = dir[2][2];
  if(computeVolumeExtent(fgInterface, sliceDirection, imageOrigin, computedSliceSpacing, computedVolumeExtent)){
    std::cerr << "Failed to compute origin and/or slice spacing!" << std::endl;
    return -1;
  }

  imageSpacing.Fill(0);
  if(getDeclaredImageSpacing(fgInterface, imageSpacing)){
    std::cerr << "Failed to get image spacing from DICOM!" << std::endl;
    return -1;
  }


  if(!imageSpacing[2]){
    imageSpacing[2] = computedSliceSpacing;
  }
  else if(fabs(imageSpacing[2]-computedSliceSpacing)>0.00001){
    std::cerr << "WARNING: Declared slice spacing is significantly different from the one declared in DICOM!" <<
                 " Declared = " << imageSpacing[2] << " Computed = " << computedSliceSpacing << std::endl;
  }

  // Region size
  {
    OFString str;
    if(segDataset->findAndGetOFString(DCM_Rows, str).good()){
      imageSize[0] = atoi(str.c_str());
    }
    if(segDataset->findAndGetOFString(DCM_Columns, str).good()){
      imageSize[1] = atoi(str.c_str());
    }
  }
  // number of slices should be computed, since segmentation may have empty frames
  imageSize[2] = computedVolumeExtent/imageSpacing[2]+2;

  // Initialize the image
  imageRegion.SetSize(imageSize);
  segImage->SetRegions(imageRegion);
  segImage->SetOrigin(imageOrigin);
  segImage->SetSpacing(imageSpacing);
  segImage->SetDirection(dir);
  segImage->Allocate();
  segImage->FillBuffer(0);

  // ITK images corresponding to the individual segments
  std::map<unsigned,ImageType::Pointer> segment2image;
  // list of strings that
  std::map<unsigned,std::vector<std::string> > segment2meta;

  // Iterate over frames, find the matching slice for each of the frames based on
  // ImagePositionPatient, set non-zero pixels to the segment number. Notify
  // about pixels that are initialized more than once.

  DcmIODTypes::Frame *unpackedFrame = NULL;

  for(int frameId=0;frameId<fgInterface.getNumberOfFrames();frameId++){
    const DcmIODTypes::Frame *frame = segdoc->getFrame(frameId);
    bool isPerFrame;

    FGPlanePosPatient *planposfg =
        OFstatic_cast(FGPlanePosPatient*,fgInterface.get(frameId, DcmFGTypes::EFG_PLANEPOSPATIENT, isPerFrame));
    assert(planposfg);

    FGFrameContent *fracon =
        OFstatic_cast(FGFrameContent*,fgInterface.get(frameId, DcmFGTypes::EFG_FRAMECONTENT, isPerFrame));
    assert(fracon);

    FGSegmentation *fgseg =
        OFstatic_cast(FGSegmentation*,fgInterface.get(frameId, DcmFGTypes::EFG_SEGMENTATION, isPerFrame));
    assert(fgseg);

    Uint16 segmentId = -1;
    if(fgseg->getReferencedSegmentNumber(segmentId).bad()){
      std::cerr << "Failed to get seg number!";
      abort();
    }


    // WARNING: this is needed only for David's example, which numbers
    // (incorrectly!) segments starting from 0, should start from 1
    if(segmentId == 0){
      std::cerr << "Segment numbers should start from 1!" << std::endl;
      abort();
    }

    if(segment2image.find(segmentId) == segment2image.end()){
      typedef itk::ImageDuplicator<ImageType> DuplicatorType;
      DuplicatorType::Pointer dup = DuplicatorType::New();
      dup->SetInputImage(segImage);
      dup->Update();
      ImageType::Pointer newSegmentImage = dup->GetOutput();
      newSegmentImage->FillBuffer(0);
      segment2image[segmentId] = newSegmentImage;
    }

    // populate meta information needed for Slicer ScalarVolumeNode initialization
    //  (for example)
    {
      segment = segdoc->getSegment(segmentId);
      std::cout << "Parsing relevant meta info for segment " << segmentId << std::endl;
      // get CIELab color for the segment
      Uint16 ciedcm[3];
      unsigned cielabScaled[3];
      float cielab[3], ciexyz[3];
      unsigned rgb[3];
      if(segment->getRecommendedDisplayCIELabValue(
        ciedcm[0], ciedcm[1], ciedcm[2]
      ).bad()) {
        std::cerr << "Failed to get CIELab values" << std::endl;
        return -1;
      }
      std::cout << "DCMTK CIELab values:" << ciedcm[0] << "," << ciedcm[1] << "," << ciedcm[2] << std::endl;
      cielabScaled[0] = unsigned(ciedcm[0]);
      cielabScaled[1] = unsigned(ciedcm[1]);
      cielabScaled[2] = unsigned(ciedcm[2]);

      getCIELabFromIntegerScaledCIELab(&cielabScaled[0],&cielab[0]);

      std::cout << "CIELab: ";
      for(int i=0;i<3;i++)
        std::cout << cielab[i] << " ";
      std::cout << std::endl;

      getCIEXYZFromCIELab(&cielab[0],&ciexyz[0]);
      std::cout << "CIEXYZ: ";
      for(int i=0;i<3;i++)
        std::cout << ciexyz[i] << " ";
      std::cout << std::endl;

      getRGBFromCIEXYZ(&ciexyz[0],&rgb[0]);
      std::cout << "RGB: ";
      for(int i=0;i<3;i++)
        std::cout << rgb[i] << " ";
      std::cout << std::endl;

      {
        std::ostringstream strs;
        std::string metastr;
        strs << rgb[0] << "," << rgb[1] << "," << rgb[2] << std::endl;
        metastr = std::string("RGBColor:")+strs.str();
      }

      // get anatomy codes
      GeneralAnatomyMacro &anatomyMacro = segment->getGeneralAnatomyCode();
      OFString anatomicRegionMeaning, anatomicRegionModifierMeaning;
      anatomyMacro.getAnatomicRegion().getCodeMeaning(anatomicRegionMeaning);
      std::cout << "Anatomic region meaning: " << anatomicRegionMeaning << std::endl;
      if(anatomyMacro.getAnatomicRegionModifier().size()>0){
        anatomyMacro.getAnatomicRegionModifier()[0]->getCodeMeaning(anatomicRegionModifierMeaning);
        std::cout << "  Modifier: " << anatomicRegionModifierMeaning << std::endl;
      }

      OFString categoryMeaning;
      segment->getSegmentedPropertyCategoryCode().getCodeMeaning(categoryMeaning);
      std::cout << "Category meaning: " << categoryMeaning << std::endl;

      OFString typeMeaning, typeModifierMeaning;
      segment->getSegmentedPropertyTypeCode().getCodeMeaning(typeMeaning);
      std::cout << "Type meaning: " << anatomicRegionMeaning << std::endl;
      if(segment->getSegmentedPropertyTypeModifierCode().size()>0){
        segment->getSegmentedPropertyTypeModifierCode()[0]->getCodeMeaning(typeModifierMeaning);
        std::cout << "  Modifier: " << typeModifierMeaning << std::endl;
      }

    }

    // get string representation of the frame origin
    ImageType::PointType frameOriginPoint;
    ImageType::IndexType frameOriginIndex;
    for(int j=0;j<3;j++){
      OFString planposStr;
      if(planposfg->getImagePositionPatient(planposStr, j).good()){
        frameOriginPoint[j] = atof(planposStr.c_str());
      }
    }

    if(!segment2image[segmentId]->TransformPhysicalPointToIndex(frameOriginPoint, frameOriginIndex)){
      std::cerr << "ERROR: Frame " << frameId << " origin " << frameOriginPoint <<
                   " is outside image geometry!" << frameOriginIndex << std::endl;
      std::cerr << "Image size: " << segment2image[segmentId]->GetBufferedRegion().GetSize() << std::endl;
      return -1;
    }

    unsigned slice = frameOriginIndex[2];

    if(segdoc->getSegmentationType() == DcmSegTypes::ST_BINARY)
      unpackedFrame = DcmSegUtils::unpackBinaryFrame(frame, imageSize[0], imageSize[1]);
    else
      unpackedFrame = new DcmIODTypes::Frame(*frame);

    // initialize slice with the frame content
    for(int row=0;row<imageSize[1];row++){
      for(int col=0;col<imageSize[0];col++){
        ImageType::PixelType pixel;
        unsigned bitCnt = row*imageSize[0]+col;
        pixel = unpackedFrame->pixData[bitCnt];

        if(pixel!=0){
          ImageType::IndexType index;
          index[0] = col;
          index[1] = row;
          index[2] = slice;
          segment2image[segmentId]->SetPixel(index, 1);
        }
      }
    }

    if(unpackedFrame != NULL)
      delete unpackedFrame;
  }

  for(std::map<unsigned,ImageType::Pointer>::const_iterator sI=segment2image.begin();sI!=segment2image.end();++sI){
    typedef itk::ImageFileWriter<ImageType> WriterType;
    std::stringstream fileNameSStream;
    // is this safe?
    fileNameSStream << outputDirName << "/" << sI->first << ".nrrd";
    WriterType::Pointer writer = WriterType::New();
    writer->SetFileName(fileNameSStream.str());
    writer->SetInput(sI->second);
    writer->SetUseCompression(1);
    writer->Update();
  }

  return 0;
}

int getImageDirections(FGInterface &fgInterface, ImageType::DirectionType &dir){
  // For directions, we can only handle segments that have patient orientation
  //  identical for all frames, so either find it in shared FG, or fail
  // TODO: handle the situation when FoR is not initialized
  OFBool isPerFrame;
  vnl_vector<double> rowDirection(3), colDirection(3);

  FGPlaneOrientationPatient *planorfg = OFstatic_cast(FGPlaneOrientationPatient*,
                                                      fgInterface.get(0, DcmFGTypes::EFG_PLANEORIENTPATIENT, isPerFrame));
  if(!planorfg){
    std::cerr << "Plane Orientation (Patient) is missing, cannot parse input " << std::endl;
    return -1;
  }
  OFString orientStr;
  for(int i=0;i<3;i++){
    if(planorfg->getImageOrientationPatient(orientStr, i).good()){
      rowDirection[i] = atof(orientStr.c_str());
    } else {
      std::cerr << "Failed to get orientation " << i << std::endl;
      return -1;
    }
  }
  for(int i=3;i<6;i++){
    if(planorfg->getImageOrientationPatient(orientStr, i).good()){
      colDirection[i-3] = atof(orientStr.c_str());
    } else {
      std::cerr << "Failed to get orientation " << i << std::endl;
      return -1;
    }
  }
  vnl_vector<double> sliceDirection = vnl_cross_3d(rowDirection, colDirection);
  sliceDirection.normalize();

  for(int i=0;i<3;i++){
    dir[i][0] = rowDirection[i];
    dir[i][1] = colDirection[i];
    dir[i][2] = sliceDirection[i];
  }

  std::cout << "Direction: " << std::endl << dir << std::endl;

  return 0;
}

int computeVolumeExtent(FGInterface &fgInterface, vnl_vector<double> &sliceDirection, ImageType::PointType &imageOrigin, double &sliceSpacing, double &sliceExtent){
  // Size
  // Rows/Columns can be read directly from the respective attributes
  // For number of slices, consider that all segments must have the same number of frames.
  //   If we have FoR UID initialized, this means every segment should also have Plane
  //   Position (Patient) initialized. So we can get the number of slices by looking
  //   how many per-frame functional groups a segment has.

  std::vector<double> originDistances;
  std::map<OFString, double> originStr2distance;
  std::map<OFString, unsigned> frame2overlap;
  double minDistance;

  unsigned numFrames = fgInterface.getNumberOfFrames();

  FrameSorterIPP fsIPP;
  FrameSorterIPP::Results sortResults;
  fsIPP.setSorterInput(&fgInterface);
  fsIPP.sort(sortResults);

  // Determine ordering of the frames, keep mapping from ImagePositionPatient string
  //   to the distance, and keep track (just out of curiousity) how many frames overlap
  vnl_vector<double> refOrigin(3);
  {
    OFBool isPerFrame;
    FGPlanePosPatient *planposfg =
        OFstatic_cast(FGPlanePosPatient*,fgInterface.get(0, DcmFGTypes::EFG_PLANEPOSPATIENT, isPerFrame));
    for(int j=0;j<3;j++){
      OFString planposStr;
      if(planposfg->getImagePositionPatient(planposStr, j).good()){
          refOrigin[j] = atof(planposStr.c_str());
      } else {
        std::cerr << "Failed to read patient position" << std::endl;
      }
    }
  }

  for(int frameId=0;frameId<numFrames;frameId++){
    OFBool isPerFrame;
    FGPlanePosPatient *planposfg =
        OFstatic_cast(FGPlanePosPatient*,fgInterface.get(frameId, DcmFGTypes::EFG_PLANEPOSPATIENT, isPerFrame));

    if(!planposfg){
      std::cerr << "PlanePositionPatient is missing" << std::endl;
      return -1;
    }

    if(!isPerFrame){
      std::cerr << "PlanePositionPatient is required for each frame!" << std::endl;
      return -1;
    }

    vnl_vector<double> sOrigin;
    OFString sOriginStr = "";
    sOrigin.set_size(3);
    for(int j=0;j<3;j++){
      OFString planposStr;
      if(planposfg->getImagePositionPatient(planposStr, j).good()){
          sOrigin[j] = atof(planposStr.c_str());
          sOriginStr += planposStr;
          if(j<2)
            sOriginStr+='/';
      } else {
        std::cerr << "Failed to read patient position" << std::endl;
        return -1;
      }
    }

    // check if this frame has already been encountered
    if(originStr2distance.find(sOriginStr) == originStr2distance.end()){
      vnl_vector<double> difference;
      difference.set_size(3);
      difference[0] = sOrigin[0]-refOrigin[0];
      difference[1] = sOrigin[1]-refOrigin[1];
      difference[2] = sOrigin[2]-refOrigin[2];
      double dist = dot_product(difference,sliceDirection);
      frame2overlap[sOriginStr] = 1;
      originStr2distance[sOriginStr] = dist;
      assert(originStr2distance.find(sOriginStr) != originStr2distance.end());
      originDistances.push_back(dist);

      if(frameId==0){
        minDistance = dist;
        imageOrigin[0] = sOrigin[0];
        imageOrigin[1] = sOrigin[1];
        imageOrigin[2] = sOrigin[2];
      }
      else
        if(dist<minDistance){
          imageOrigin[0] = sOrigin[0];
          imageOrigin[1] = sOrigin[1];
          imageOrigin[2] = sOrigin[2];
          minDistance = dist;
        }
    } else {
      frame2overlap[sOriginStr]++;
    }
  }

  // sort all unique distances, this will be used to check consistency of
  //  slice spacing, and also to locate the slice position from ImagePositionPatient
  //  later when we read the segments
  sort(originDistances.begin(), originDistances.end());

  sliceSpacing = fabs(originDistances[0]-originDistances[1]);

  for(int i=1;i<originDistances.size();i++){
    float dist1 = fabs(originDistances[i-1]-originDistances[i]);
    float delta = sliceSpacing-dist1;
    if(delta > 0.001){
      std::cerr << "WARNING: Inter-slice distance " << originDistances[i] << " difference exceeded threshold: " << delta << std::endl;
    }
  }

  sliceExtent = fabs(originDistances[0]-originDistances[originDistances.size()-1]);
  unsigned overlappingFramesCnt = 0;
  for(std::map<OFString, unsigned>::const_iterator it=frame2overlap.begin();
      it!=frame2overlap.end();++it){
    if(it->second>1)
      overlappingFramesCnt++;
  }

  std::cout << "Total frames: " << numFrames << std::endl;
  std::cout << "Total frames with unique IPP: " << originDistances.size() << std::endl;
  std::cout << "Total overlapping frames: " << overlappingFramesCnt << std::endl;
  std::cout << "Origin: " << imageOrigin << std::endl;

  return 0;
}

int getDeclaredImageSpacing(FGInterface &fgInterface, ImageType::SpacingType &spacing){
  OFBool isPerFrame;
  FGPixelMeasures *pixm = OFstatic_cast(FGPixelMeasures*,
                                                      fgInterface.get(0, DcmFGTypes::EFG_PIXELMEASURES, isPerFrame));
  if(!pixm){
    std::cerr << "Pixel measures FG is missing!" << std::endl;
    return -1;
  }

  pixm->getPixelSpacing(spacing[0], 0);
  pixm->getPixelSpacing(spacing[1], 1);

  Float64 spacingFloat;
  if(pixm->getSpacingBetweenSlices(spacingFloat,0).good() && spacingFloat != 0){
    spacing[2] = spacingFloat;
  } else if(pixm->getSliceThickness(spacingFloat,0).good() && spacingFloat != 0){
    // SliceThickness can be carried forward from the source images, and may not be what we need
    // As an example, this ePAD example has 1.25 carried from CT, but true computed thickness is 1!
    std::cerr << "WARNING: SliceThickness is present and is " << spacingFloat << ". NOT using it!" << std::endl;
  }

  return 0;
}
