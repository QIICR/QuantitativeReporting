#
# This module was developed by Andrey Fedorov, BWH 
#    with the support of Slicer Community
#
# This work was supported in part by NIH NCI U01CA151261 grant (Quantitative
# Imaging Network), PI Fiona Fennessy.
#
# This script performs conversion of the segmentation saved as a
# Slicer-readable volume into DICOM SEG format.
# 
# == Usage ==
#
# This script takes on input three arguments:
#  1) directory that contains reference DICOM series
#  2) input label (geometry is expected to match the one of the volume read
#  from DICOM, if not it will be resampled)
#  3) directory to store the output DICOM SEG series. 
#  4) (optional) the label to be assigned, this label will be used to match
#     SegmentedPropertyCategory and SegmentedPropertyType for the output
#     object
#
# To run the script install Slicer4 and the latest version of the Reporting
# extension, then from command line run:
# > Slicer --python-script LabelToDICOMSEGConverterScript.py <input_dicom_dir> <input_label> <output_dicom_dir>
#
# == Limitations ==
#
# Note that currently DICOM SEG support is limited to a single label! If you
# have more than one distinctive labels in your segmentation, they will all be
# assigned the same label ID!
#
# It is recommended to pick a label value that corresponds to the segmented
# structure, as this information will be encoded in the DICOM SEG object. See
# the list of available labels in the Reporting extension wiki documentation
# page here:
#  http://wiki.slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/Reporting
#
# == Support ==
#
# fedorov@bwh.harvard.edu
#   and 
# http://slicer.org user list
# 

from __main__ import slicer, vtk, ctk
import sys, glob, shutil, qt

from DICOMLib import DICOMPlugin
from DICOMLib import DICOMLoadable

def DoIt(inputDir, labelFile, outputDir, forceLabel, forceResample):

  dbDir1 = slicer.app.temporaryPath+'/LabelConverter'

  if not hasattr(slicer.modules, 'reporting'):
    print 'The Reporting module has not been loaded into Slicer, script cannot run!\n\tTry setting the --additional-module-path parameter.'
    sys.exit(1)

  reportingLogic = slicer.modules.reporting.logic()

  print('Temporary directory location: '+dbDir1)
  qt.QDir().mkpath(dbDir1)

  dbDir0 = None
  if slicer.dicomDatabase:
    dbDir0 = os.path.split(slicer.dicomDatabase.databaseFilename)[0]

  dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
  dicomWidget.onDatabaseDirectoryChanged(dbDir1)

  # import DICOM study
  indexer = ctk.ctkDICOMIndexer()
  indexer.addDirectory(slicer.dicomDatabase, inputDir, None)
  indexer.waitForImportFinished()

  print('DICOM import finished!')

  #
  # Read the input DICOM series as a volume
  #
  dcmList = []
  for dcm in os.listdir(inputDir):
    if len(dcm)-dcm.rfind('.dcm') == 4:
      dcmList.append(inputDir+'/'+dcm)

  scalarVolumePlugin = slicer.modules.dicomPlugins['DICOMScalarVolumePlugin']()

  loadables = scalarVolumePlugin.examine([dcmList])

  if len(loadables) == 0:
    print 'Could not parse the DICOM Study!'
    sys.exit(1)

  inputVolume = scalarVolumePlugin.load(loadables[0])
  print 'Input volume loaded! ID = ', inputVolume.GetID()

  # read the label volume
  labelVolume = slicer.vtkMRMLScalarVolumeNode()
  sNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
  sNode.SetFileName(labelFile)
  sNode.ReadData(labelVolume)
  labelVolume.LabelMapOn()

  if forceLabel>0:
    # print('Forcing label to '+str(forceLabel))
    labelImage = labelVolume.GetImageData()
    thresh = vtk.vtkImageThreshold()
    if vtk.vtkVersion().GetVTKMajorVersion() < 6:
      thresh.SetInput(labelImage)
    else:
      thresh.SetInputData(labelImage)
      thresh.ThresholdBetween(1, labelImage.GetScalarRange()[1])
      thresh.SetInValue(int(forceLabel))
      thresh.SetOutValue(0)
      thresh.ReplaceInOn()
      thresh.ReplaceOutOn()
      thresh.Update()
      labelImage = thresh.GetOutput()
      labelVolume.SetAndObserveImageData(labelImage)

  slicer.mrmlScene.AddNode(labelVolume)
  print 'Label volume added, id = ', labelVolume.GetID()

  # ensure that the label volume scalar type is unsigned short
  if labelVolume.GetImageData() != None:
    scalarType = labelVolume.GetImageData().GetScalarType()
    if scalarType != vtk.VTK_UNSIGNED_SHORT:
      print 'Label volume has pixel type of ',vtk.vtkImageScalarTypeNameMacro(scalarType),', casting to unsigned short'
      cast = vtk.vtkImageCast()
      cast.SetOutputScalarTypeToUnsignedShort()
      if vtk.vtkVersion().GetVTKMajorVersion() < 6:
        cast.SetInput(labelVolume.GetImageData())
        cast.Update()
        labelVolume.SetAndObserveImageData(cast.GetOutput())
      else:
        cast.SetInputConnection(labelVolume.GetImageDataConnection())
        cast.Update()
        labelVolume.SetImageDataConnection(cast.GetOutputPort())
      if labelVolume.GetImageData().GetScalarType() != vtk.VTK_UNSIGNED_SHORT:
        print 'Failed to cast label volume to unsigned short, type is ',  vtk.vtkImageScalarTypeNameMacro(labelVolume.GetImageData().GetScalarType())
        sys.exit(1)

  volumesLogic = slicer.modules.volumes.logic()
  geometryCheckString = volumesLogic.CheckForLabelVolumeValidity(inputVolume, labelVolume)
  if geometryCheckString != "":
    # has the user specified that forced resampling is okay?
    if forceResample == 0:
      print 'Label volume mismatch with input volume:\n',geometryCheckString,'\nForced resample not specified, aborting. Re-run with -F option to ignore geometric inconsistencies'
      sys.exit(1)
    # resample label to the input volume raster
    resampledLabel = slicer.vtkMRMLScalarVolumeNode()
    slicer.mrmlScene.AddNode(resampledLabel)
    print 'Resampled label added, id = ', resampledLabel.GetID()
    resampledLabel = volumesLogic.ResampleVolumeToReferenceVolume(labelVolume, inputVolume)
    labelVolume = resampledLabel

  displayNode = slicer.vtkMRMLLabelMapVolumeDisplayNode()
  displayNode.SetAndObserveColorNodeID(reportingLogic.GetDefaultColorNode().GetID())
  slicer.mrmlScene.AddNode(displayNode)

  labelVolume.SetAttribute('AssociatedNodeID',inputVolume.GetID())
  labelVolume.LabelMapOn()
  labelVolume.SetAndObserveDisplayNodeID(displayNode.GetID())

  # initialize the DICOM DB for Reporting logic, save as DICOM SEG
  labelCollection = vtk.vtkCollection()
  labelCollection.AddItem(labelVolume)

  print('About to write DICOM SEG!')
  dbFileName = slicer.dicomDatabase.databaseFilename
  reportingLogic.InitializeDICOMDatabase(dbFileName)
  reportingLogic.DicomSegWrite(labelCollection, outputDir)

  dicomWidget.onDatabaseDirectoryChanged(dbDir0)

  exit()

if len(sys.argv)<4:
  print 'Input parameters missing!'
  print 'Usage: ',sys.argv[0],' <input directory with DICOM data> <input label> <output dir> <optional: label to assign> <optional: -F>'
  print '\t-F to force ignoring geometry inconsistencies (auto resample is done)'
  sys.exit(1)
else:
  inputDICOMDir = sys.argv[1]
  inputLabelName = sys.argv[2]
  outputDICOMDir = sys.argv[3]
  forceLabel = 0
  forceResample = 0
  if len(sys.argv)>4:
    if sys.argv[4].isdigit():
      forceLabel = sys.argv[4]
    else:
      if sys.argv[4].startswith("-F"):
        forceResample = 1
  if len(sys.argv) > 5:
    if sys.argv[4].startswith("-F"):
      forceResample = 1

  print 'Force resample = ',forceResample
  DoIt(inputDICOMDir, inputLabelName, outputDICOMDir, forceLabel, forceResample)
