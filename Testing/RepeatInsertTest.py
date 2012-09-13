import string

def RepeatInsertTest():

  volNumber = slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLScalarVolumeNode')
  if volNumber<2:
    print('Need two volume nodes')
    return

  v1=slicer.mrmlScene.GetNthNodeByClass(0,'vtkMRMLScalarVolumeNode')
  v2=slicer.mrmlScene.GetNthNodeByClass(1,'vtkMRMLScalarVolumeNode')

  if not v1.GetAttribute('DICOM.instanceUIDs') or not v2.GetAttribute('DICOM.instanceUIDs'):
    print('Volumes must be loaded from DICOM')
    return

  db = slicer.dicomDatabase

  v1uids = string.split(v1.GetAttribute('DICOM.instanceUIDs'),' ')
  v2uids = string.split(v2.GetAttribute('DICOM.instanceUIDs'),' ')

  reportingLogic = slicer.modules.reporting.logic()
  if not reportingLogic:
    print('Need Reporting module')
    return

  volumesLogic = slicer.modules.volumes.logic()

  v1label = volumesLogic.CreateLabelVolume(v1,'v1label')
  v2label = volumesLogic.CreateLabelVolume(v2,'v2label')

  tmpDir = slicer.app.settings().value('Modules/TemporaryDirectory')

  print('v1 header loading')
  #slicer.dicomDatabase.loadInstanceHeader(v1uids[0])
  #bd1=db.headerValue('0010,0030')
  #bt1=db.headerValue('0010,0032')

  coll1 = vtk.vtkCollection()
  coll1.AddItem(v1label)

  ds1=reportingLogic.DicomSegWrite(coll1, tmpDir)

  db.insert(ds1,0)
  print('done with v1')

  #slicer.dicomDatabase.loadInstanceHeader(v2uids[0])
  #bd2=db.headerValue('0010,0030')
  #bt2=db.headerValue('0010,0032')

  coll2 = vtk.vtkCollection()
  coll2.AddItem(v2label)

  ds2=reportingLogic.DicomSegWrite(coll1, tmpDir)

  db.insert(ds2,0)

  print('done with v2')
