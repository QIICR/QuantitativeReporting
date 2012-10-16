#
# This module was developed by Andrey Fedorov, BWH 
#    with the support of Slicer Community
#
# This work was supported in part by NIH NCI U01CA151261 grant (Quantitative
# Imaging Network), PI Fiona Fennessy.
#
# This script performs conversion of the segmentation saved as a stack of RGB
# slices into NRRD and DICOM SEG formats.
# 
# == Usage ==
#
# This script takes on input two arguments:
#  1) directory that contains reference DICOM series
#  2) directory that contains segmentation slices for the reference DICOM
#  series. This directory should contain one RGB slice per each DICOM slice,
#  and the name of that slice should include the name for the corresponding
#  DICOM slice. For example, if DICOM slice name is "F0-1234.dcm", the name
#  for the corresponding RGB slice can be "F0-1234-label.bmp".
#
# To run the script install Slicer4 and the latest version of the Reporting
# extension, then from command line run:
# > Slicer --python-script RGBStackLabelConverter.py <input_dicom_dir> <input_rgb_dir>
#
# As a result, the following files will be created in the directory from which
# the script was run:
# 1) input_volume.nrrd: reconstructed DICOM series in NRRD format
# 2) output_label.nrrd: reconstructed segmentation volume
# 3) <UID>.dcm: DICOM SEG object containing the segmentation
#
# In order to load the resulting NRRD files, use Slicer "Add data" menu
# option
# 
# In order to load the DICOM SEG object, use the DICOM Module "Import"
# functionality to first import the directory containing the SEG object into
# the DICOM database. After that (considering you have Reporting module
# installed) you will be able to select the segmentation object from DICOM
# module and load into Slicer.
#
# == Limitations ==
#
# Note that currently DICOM SEG support is limited to a single label! If you
# have more than one distinctive labels in your segmentation, they will all be
# assigned the same label ID!
#
# == Support ==
#
# fedorov@bwh.harvard.edu
#   and 
# http://slicer.org user list
# 

from __main__ import slicer, vtk, ctk
import sys, glob, shutil
# import args

from DICOMLib import DICOMPlugin
from DICOMLib import DICOMLoadable

def DoIt(inputDir, rgbDir):


  #
  # Read the input DICOM series as a volume
  # 
  dcmList = []
  for dcm in os.listdir(inputDir):
    if len(dcm)-dcm.rfind('.dcm') == 4:
      dcmList.append(inputDir+'/'+dcm)

  scalarVolumePlugin = slicer.modules.dicomPlugins['DICOMScalarVolumePlugin']()

  print 'Will examine: ',dcmList


  indexer = ctk.ctkDICOMIndexer()
  indexer.addDirectory(slicer.dicomDatabase, inputDir, None)
  indexer.waitForImportFinished()

  loadables = scalarVolumePlugin.examine([dcmList])

  if len(loadables) == 0:
    print 'Could not parse the DICOM Study!'
    exit()
  
  inputVolume = scalarVolumePlugin.load(loadables[0])

  sNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
  '''
  sNode.ResetFileNameList()
  for f in loadables[0].files:
    sNode.AddFileName(f)
  sNode.SetFileName(loadables[0].files[0])
  sNode.SetSingleFile(0)
  inputVolume = slicer.vtkMRMLScalarVolumeNode()
  sNode.ReadData(inputVolume)
  '''

  sNode.SetWriteFileFormat('nrrd')
  sNode.SetFileName('input_volume.nrrd')
  sNode.WriteData(inputVolume)

  # 
  # Order the input RGBs and rename in a temp directory
  #
  rgbList = []
  for rgb in os.listdir(rgbDir):
    rgbList.append(rgb)

  tmpDir = slicer.app.settings().value('Modules/TemporaryDirectory')
  tmpDir = tmpDir+'/PNGStackLabelConverter'
  if not os.path.exists(tmpDir):
    os.mkdir(tmpDir)

  oldFiles = os.listdir(tmpDir)
  # just in case there is anything in that directory
  for f in oldFiles:
    os.unlink(tmpDir+'/'+f)

  rgbOrdered = [None] * len(loadables[0].files)
  rgbCnt = 0
  rgbExt = rgbList[0][rgbList[0].rfind('.')+1:len(rgbList[0])]
  print 'Extension for RGBs: ',rgbExt

  dcmFileList = loadables[0].files
  rgbRenamedList = []

  print 'Number of dcm files: ',len(dcmFileList), ' and rgb files: ',len(rgbOrdered)

  dcmIdx = 0
  for dcm in dcmFileList:
    rgbIdx = 0
    
    for rgb in rgbList:

      dcmPrefix = dcm[dcm.rfind('/')+1:dcm.rfind('.')]

      if rgb.find(dcmPrefix) != -1:
        name = string.zfill(str(dcmIdx),5)
        rgbCnt = rgbCnt+1
        src = rgbDir+'/'+rgb
        dest = tmpDir+'/'+name+'.'+rgbExt
        rgbRenamedList.append(dest)
        shutil.copy(src,dest)
      
        break
      rgbIdx = rgbIdx+1

    # remove the matched DICOM file from the list
    del rgbList[rgbIdx]
    dcmIdx = dcmIdx+1

  if len(rgbRenamedList) == 0:
    print 'Could not parse the DICOM Study!'
    return

  sNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
  sNode.ResetFileNameList()
  for f in rgbRenamedList:
    sNode.AddFileName(f)
  sNode.SetFileName(rgbRenamedList[0])
  sNode.SetSingleFile(0)
  inputRGBVolume = slicer.vtkMRMLVectorVolumeNode()
  sNode.ReadData(inputRGBVolume)


  # run the filter
  # - extract the RGB portions 
  extract = vtk.vtkImageExtractComponents()
  extract.SetComponents(0,1,2)
  extract.SetInput(inputRGBVolume.GetImageData())
  
  luminance = vtk.vtkImageLuminance()
  luminance.SetInput(extract.GetOutput())
  cast = vtk.vtkImageCast()
  cast.SetInput(luminance.GetOutput())
  cast.SetOutputScalarTypeToShort()
  cast.GetOutput().Update()

  ijkToRAS = vtk.vtkMatrix4x4()
  inputVolume.GetIJKToRASMatrix(ijkToRAS)
  
  outputLabel = slicer.vtkMRMLScalarVolumeNode()
  outputLabel.SetIJKToRASMatrix(ijkToRAS)
  outputLabel.SetAndObserveImageData(cast.GetOutput())
  
  reportingLogic = slicer.modules.reporting.logic()

  displayNode = slicer.vtkMRMLLabelMapVolumeDisplayNode()
  displayNode.SetAndObserveColorNodeID(reportingLogic.GetDefaultColorNode().GetID())
  slicer.mrmlScene.AddNode(displayNode)
  outputLabel.SetAndObserveDisplayNodeID(displayNode.GetID())
  
  sNode.SetWriteFileFormat('nrrd')
  sNode.SetFileName('label_output.nrrd')
  sNode.WriteData(outputLabel)
  
  # save as DICOM SEG
  labelCollection = vtk.vtkCollection()
  labelCollection.AddItem(outputLabel)

  slicer.mrmlScene.AddNode(inputVolume)
  outputLabel.LabelMapOn()
  outputLabel.SetAttribute('AssociatedNodeID',inputVolume.GetID())
  slicer.mrmlScene.AddNode(outputLabel)

  # initialize the DICOM DB for Reporting logic
  settings = qt.QSettings()
  dbFileName = settings.value('DatabaseDirectory','')
  if dbFileName =='':
    print('ERROR: database must be initialized')
  else:
    dbFileName = dbFileName +'/ctkDICOM.sql'
    reportingLogic.InitializeDICOMDatabase(dbFileName)

    reportingLogic.DicomSegWrite(labelCollection, '.')

#
if len(sys.argv)<3:
  print 'Input parameters missing!'
  print 'Usage: ',sys.argv[0],' <input directory with DICOM data> <input directory with RGB segmentation slices>'
  exit()
else:
  inputDir = sys.argv[1]
  rgbDir = sys.argv[2]
  DoIt(inputDir, rgbDir) 
