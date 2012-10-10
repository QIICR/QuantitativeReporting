# Andrey Fedorov, BWH
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
