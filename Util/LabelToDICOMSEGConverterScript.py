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

def DoIt(inputDir, labelFile, outputDir, forceLabel):

  dbDir1 = slicer.app.temporaryPath+'/LabelConverter'
  reportingLogic = slicer.modules.reporting.logic()

  print('Temporary directory location: '+dbDir1)
  qt.QDir().mkpath(dbDir1)

  dbDir0 = None
  if slicer.dicomDatabase:
    dbDir0 = os.path.split(slicer.dicomDatabase.databaseFilename)[0]

  try:
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
      exit()
  
    inputVolume = scalarVolumePlugin.load(loadables[0])
    slicer.mrmlScene.AddNode(inputVolume)
    print('Input volume loaded!')

    # read the label volume
    labelVolume = slicer.vtkMRMLScalarVolumeNode()
    sNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
    sNode.SetFileName(labelFile)
    sNode.ReadData(labelVolume)
    labelVolume.LabelMapOn()

    if forceLabel>0:
      print('Forcing label to '+str(forceLabel))
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

    volumesLogic = slicer.modules.volumes.logic()
    geometryCheckString = volumesLogic.CheckForLabelVolumeValidity(inputVolume, labelVolume)
    if geometryCheckString != "":
      print('Label volume geometry mismatch, resampling:\n%s' % geometryCheckString)

      # resample label to the input volume raster
      resampledLabel = slicer.vtkMRMLScalarVolumeNode()
      slicer.mrmlScene.AddNode(resampledLabel)
      eye = slicer.vtkMRMLLinearTransformNode()
      slicer.mrmlScene.AddNode(eye)
      parameters = {}
      parameters['inputVolume'] = labelVolume.GetID()
      parameters['referenceVolume'] = inputVolume.GetID()
      parameters['outputVolume'] = resampledLabel.GetID()
      parameters['warpTransform'] = eye.GetID()
      parameters['interpolationMode'] = 'NearestNeighbor'
      parameters['pixelType'] = 'ushort'
      cliNode = None
      cliNode = slicer.cli.run(slicer.modules.brainsresample, None, parameters, 1)
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
  except:
    print('Error occurred!')

  dicomWidget.onDatabaseDirectoryChanged(dbDir0)

  exit()

if len(sys.argv)<4:
  print 'Input parameters missing!'
  print 'Usage: ',sys.argv[0],' <input directory with DICOM data> <input label> <output dir> <optional: label to assign>'
  exit()
else:
  inputDICOMDir = sys.argv[1]
  inputLabelName = sys.argv[2]
  outputDICOMDir = sys.argv[3]
  forceLabel = 0
  if len(sys.argv)>4:
    forceLabel = sys.argv[4]
  DoIt(inputDICOMDir, inputLabelName, outputDICOMDir, forceLabel) 
