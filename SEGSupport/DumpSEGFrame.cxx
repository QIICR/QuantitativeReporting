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

#include "dcmtk/dcmdata/dcrledrg.h"

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


//#include "framesorter.h"
#include "SegmentAttributes.h"

// CLP inclides
#include "DumpSEGFrameCLP.h"

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

  DcmRLEDecoderRegistration::registerCodecs();

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

  // Region size
  int frameRows, frameColumns;
  {
    OFString str;
    if(segDataset->findAndGetOFString(DCM_Rows, str).good()){
      frameRows = atoi(str.c_str());
    }
    if(segDataset->findAndGetOFString(DCM_Columns, str).good()){
      frameColumns = atoi(str.c_str());
    }
  }

  // Iterate over frames, find the matching slice for each of the frames based on
  // ImagePositionPatient, set non-zero pixels to the segment number. Notify
  // about pixels that are initialized more than once.

  DcmIODTypes::Frame *unpackedFrame = NULL;

  std::map<int,int> frameCntWithinSegment;

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

    if(frameCntWithinSegment.find(segmentId) == frameCntWithinSegment.end()){
      frameCntWithinSegment[segmentId] = 1;
    } else {
      frameCntWithinSegment[segmentId]++;
    }

    if(segmentIdToShow != -1 and frameNumberToShow != frameCntWithinSegment[segmentId]-1)
      // skip this segment
      continue;

    // WARNING: this is needed only for David's example, which numbers
    // (incorrectly!) segments starting from 0, should start from 1
    if(segmentId == 0){
      std::cerr << "Segment numbers should start from 1!" << std::endl;
      abort();
    }

    if(segdoc->getSegmentationType() == DcmSegTypes::ST_BINARY){
      unpackedFrame = DcmSegUtils::unpackBinaryFrame(frame, frameRows, frameColumns);
    } else
      unpackedFrame = new DcmIODTypes::Frame(*frame);

    // initialize slice with the frame content
    for(int row=0;row<frameRows;row++){
      for(int col=0;col<frameColumns;col++){
        unsigned bitCnt = row*frameColumns+col;
        if(unpackedFrame->pixData[bitCnt])
          std::cout << "X";
        else
          std::cout << ".";
      }
      std::cout << std::endl;
    }

    std::cout << std::endl << " ---- " << std::endl;

    if(unpackedFrame != NULL)
      delete unpackedFrame;
  }

  return 0;
}
