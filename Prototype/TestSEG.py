volume = slicer.mrmlScene.GetNodeByID('vtkMRMLScalarVolumeNode1')
label = slicer.mrmlScene.GetNodeByID('vtkMRMLScalarVolumeNode2')
logic = slicer.modules.reporting.logic()
logic.WriteLabelAsSegObject(volume, label, '/Users/fedorov/Temp/seg_test.dcm')
