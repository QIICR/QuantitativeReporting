import os
import string
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

#
# This is the plugin to perform a test of dicom segmentation object export
#

class SEGExporterSelfTest(ScriptedLoadableModule):
  """
  This class is the 'hook' for slicer to detect and recognize the test
  as a loadable scripted module
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SEGExporterSelfTest" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Testing", "TestCases"]
    self.parent.dependencies = []
    self.parent.contributors = ["Steve Piepper (Isomics, Inc.)"]
    self.parent.helpText = """
        A module to perform a test of dicom segmentation object export.
    """
    self.parent.acknowledgementText = """
    This file was developed by Steve Pieper, Isomics, Inc.
    and was partially funded by NAC, NIH grant 3P41RR013218-12S1 and
    QIICR, NIH National Cancer Institute, award U24 CA180918.
""" # replace with organization, grant and thanks.

class SEGExporterSelfTestWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

class SEGExporterSelfTestLogic(ScriptedLoadableModuleLogic):

    pass

class SEGExporterSelfTestTest(ScriptedLoadableModuleTest):
  """
  This is the test case for the scripted module.
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SEGExporterSelfTest1()

  def test_SEGExporterSelfTest1(self):
    """ Test DICOM import, segmentation, export
    """
    self.messageDelay = 50

    import os
    self.delayDisplay("Starting the DICOM SEG Export test")

    #
    # first, get the data - a zip file of dicom data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download/item/220834/PieperMRHead.zip', 'PieperMRHead.zip'),
    )
    self.delayDisplay("Downloading")
    for url,name in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        self.delayDisplay('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
    self.delayDisplay('Finished with download\n')

    self.delayDisplay("Unzipping")
    dicomFilesDirectory = slicer.app.temporaryPath + '/dicomFiles'
    qt.QDir().mkpath(dicomFilesDirectory)
    slicer.app.applicationLogic().Unzip(filePath, dicomFilesDirectory)

    try:
      self.delayDisplay("Switching to temp database directory")
      tempDatabaseDirectory = slicer.app.temporaryPath + '/tempDICOMDatabase'
      import shutil
      shutil.rmtree(tempDatabaseDirectory)
      qt.QDir().mkpath(tempDatabaseDirectory)
      if slicer.dicomDatabase:
        originalDatabaseDirectory = os.path.split(slicer.dicomDatabase.databaseFilename)[0]
      else:
        originalDatabaseDirectory = None
        settings = qt.QSettings()
        settings.setValue('DatabaseDirectory', tempDatabaseDirectory)
      dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
      dicomWidget.onDatabaseDirectoryChanged(tempDatabaseDirectory)

      self.delayDisplay('Importing DICOM')
      mainWindow = slicer.util.mainWindow()
      mainWindow.moduleSelector().selectModule('DICOM')

      indexer = ctk.ctkDICOMIndexer()
      indexer.addDirectory(slicer.dicomDatabase, dicomFilesDirectory, None)
      indexer.waitForImportFinished()

      dicomWidget.detailsPopup.open()

      # load the data by series UID
      mrHeadSeriesUID = "2.16.840.1.113662.4.4168496325.1025306170.548651188813145058"
      dicomWidget.detailsPopup.offerLoadables(mrHeadSeriesUID, 'Series')
      dicomWidget.detailsPopup.examineForLoading()
      self.delayDisplay('Loading Selection')
      dicomWidget.detailsPopup.loadCheckedLoadables()

      #
      # create a label map and set it for editing
      #
      masterNode = slicer.util.getNode('2: SAG*')
      volumesLogic = slicer.modules.volumes.logic()
      mergeNode = volumesLogic.CreateAndAddLabelVolume( slicer.mrmlScene, masterNode, masterNode.GetName() + '-label' )
      mergeNode.GetDisplayNode().SetAndObserveColorNodeID('vtkMRMLColorTableNodeFileGenericAnatomyColors.txt')
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActiveVolumeID( masterNode.GetID() )
      selectionNode.SetReferenceActiveLabelVolumeID( mergeNode.GetID() )
      slicer.app.applicationLogic().PropagateVolumeSelection(0)

      #
      # go to the editor and do some drawing
      #
      slicer.util.selectModule('Editor')

      import EditorLib
      from EditorLib.EditUtil import EditUtil
      parameterNode = EditUtil.getParameterNode()
      parameterNode.SetParameter("LabelEffect,paintThreshold", "1")
      parameterNode.SetParameter("LabelEffect,paintThresholdMin", "70.0")
      parameterNode.SetParameter("LabelEffect,paintThresholdMax", "279.75")
      parameterNode.SetParameter("PaintEffect,radius", "40")
      parameterNode.SetParameter("PaintEffect,sphere", "1")
      
      self.delayDisplay("Paint some things")
      parameterNode = EditUtil.getParameterNode()
      lm = slicer.app.layoutManager()
      paintEffect = EditorLib.PaintEffectOptions()
      paintEffect.setMRMLDefaults()
      paintEffect.__del__()
      sliceWidget = lm.sliceWidget('Red')
      paintTool = EditorLib.PaintEffectTool(sliceWidget)
      EditUtil.setLabel(1)
      paintTool.paintAddPoint(100,100)
      paintTool.paintApply()
      EditUtil.setLabel(2)
      paintTool.paintAddPoint(200,200)
      paintTool.paintApply()
      paintTool.cleanup()
      paintTool = None

      # save these to compare with the one we read back
      originalSegmentationArray = slicer.util.array(mergeNode.GetID())
      originalSegmentationNodeCopy = slicer.vtkMRMLLabelMapVolumeNode()
      originalSegmentationNodeCopy.CopyOrientation(mergeNode)

      # export the volumes into a SEG
      tempSEGDirectory = slicer.app.temporaryPath + '/tempDICOMSEG'
      qt.QDir().mkpath(tempSEGDirectory)
      segFilePath = os.path.join(tempSEGDirectory, "test.SEG.dcm")


      self.delayDisplay('spliting...', 200)
      EditUtil.splitPerStructureVolumes(masterNode, mergeNode)

      self.delayDisplay('exporting...', 200)
      EditUtil.exportAsDICOMSEG(masterNode)

      # close scene re-load the input data and SEG
      slicer.mrmlScene.Clear(0)
      indexer.addDirectory(slicer.dicomDatabase, tempSEGDirectory, None)
      indexer.waitForImportFinished()

      mrHeadStudyUID = "2.16.840.1.113662.4.4168496325.1025305873.7118351817185979330"
      dicomWidget.detailsPopup.offerLoadables(mrHeadStudyUID, 'Study')
      dicomWidget.detailsPopup.examineForLoading()
      self.delayDisplay('Loading Selection')
      dicomWidget.detailsPopup.loadCheckedLoadables()

      # confirm that segmentations are correctly reloaded
      headLabelName = '2: SAG/RF-FAST/VOL/FLIP 30-label'
      reloadedLabel = slicer.util.getNode(headLabelName)
      reloadedSegmentationArray = slicer.util.array(reloadedLabel.GetID())

      import numpy
      self.assertTrue(numpy.alltrue(originalSegmentationArray == reloadedSegmentationArray))
      geometryWarnings = volumesLogic.CompareVolumeGeometry(mergeNode, reloadedLabel)
      print(geometryWarnings)
      self.assertTrue(geometryWarnings == '')

      # re-export

      # close scene re-load the input data and SEG

      # confirm that segmentations are available again as per-structure volumes


      self.delayDisplay('Test passed!')
    except Exception, e:
      import traceback
      traceback.print_exc()
      self.delayDisplay('Test caused exception!\n' + str(e))

    self.delayDisplay("Restoring original database directory")
    if originalDatabaseDirectory:
      dicomWidget.onDatabaseDirectoryChanged(originalDatabaseDirectory)

    self.delayDisplay("Finished!")
