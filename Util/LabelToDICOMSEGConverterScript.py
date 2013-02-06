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
# This script takes on input two arguments:
#  1) directory that contains reference DICOM series
#  2) input label (geometry is expected to match the one of the volume read
#  from DICOM)
#  3) directory to store the output DICOM SEG series. i
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
# import args

from DICOMLib import DICOMPlugin
from DICOMLib import DICOMLoadable

def DoIt(inputDir, labelFile, outputDir):

  dbDir1 = slicer.app.temporaryPath+'/LabelConverter'

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
    print('Input volume loaded!')

    # read the label volume
    labelVolume = slicer.vtkMRMLScalarVolumeNode()
    sNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
    sNode.SetFileName(labelFile)
    sNode.ReadData(labelVolume)
    labelVolume.LabelMapOn()


    '''
    sNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
    sNode.ResetFileNameList()
    for f in rgbRenamedList:
      sNode.AddFileName(f)
    sNode.SetFileName(rgbRenamedList[0])
    sNode.SetSingleFile(0)
    inputRGBVolume = slicer.vtkMRMLVectorVolumeNode()
    sNode.ReadData(inputRGBVolume)
    '''

    reportingLogic = slicer.modules.reporting.logic()

    displayNode = slicer.vtkMRMLLabelMapVolumeDisplayNode()
    displayNode.SetAndObserveColorNodeID(reportingLogic.GetDefaultColorNode().GetID())
    slicer.mrmlScene.AddNode(displayNode)
    slicer.mrmlScene.AddNode(labelVolume)
    labelVolume.SetAndObserveDisplayNodeID(displayNode.GetID())
    print('Display node set up, ID = '+str(displayNode.GetID()))
  
    # save as DICOM SEG
    labelCollection = vtk.vtkCollection()
    labelCollection.AddItem(labelVolume)

    slicer.mrmlScene.AddNode(inputVolume)
    labelVolume.SetAttribute('AssociatedNodeID',inputVolume.GetID())

    # initialize the DICOM DB for Reporting logic

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
  print 'Usage: ',sys.argv[0],' <input directory with DICOM data> <input label> <output dir>'
  exit()
else:
  inputDICOMDir = sys.argv[1]
  inputLabelName = sys.argv[2]
  outputDICOMDir = sys.argv[3]
  DoIt(inputDICOMDir, inputLabelName, outputDICOMDir) 
