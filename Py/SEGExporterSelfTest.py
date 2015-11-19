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
      headMR = slicer.util.getNode('2: SAG*')
      volumesLogic = slicer.modules.volumes.logic()
      headLabel = volumesLogic.CreateAndAddLabelVolume( slicer.mrmlScene, headMR, headMR.GetName() + '-label' )
      headLabel.GetDisplayNode().SetAndObserveColorNodeID('vtkMRMLColorTableNodeFileGenericAnatomyColors.txt')
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActiveVolumeID( headMR.GetID() )
      selectionNode.SetReferenceActiveLabelVolumeID( headLabel.GetID() )
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

      # export the volumes into a SEG
      tempSEGDirectory = slicer.app.temporaryPath + '/tempDICOMSEG'
      qt.QDir().mkpath(tempSEGDirectory)
      segFilePath = os.path.join(tempSEGDirectory, "test.SEG.dcm")

      # TODO: this should move to EditorLib/HelperBox.py
      self.editorExportAsDICOMSEG(headMR.GetName(), segFilePath)

      # close scene re-load the input data and SEG
      slicer.mrmlScene.Clear(0)
      indexer.addDirectory(slicer.dicomDatabase, tempSEGDirectory, None)
      indexer.waitForImportFinished()

      mrHeadStudyUID = "2.16.840.1.113662.4.4168496325.1025305873.7118351817185979330"
      dicomWidget.detailsPopup.offerLoadables(mrHeadStudyUID, 'Study')
      dicomWidget.detailsPopup.examineForLoading()
      self.delayDisplay('Loading Selection')
      dicomWidget.detailsPopup.loadCheckedLoadables()

      # confirm that segmentations are available again as per-structure volumes

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

  def editorExportAsDICOMSEG(self,masterName,segFilePath):

    self.delayDisplay('exporting...', 200)

    # split the label map to per-structure volumes
    # - to be done in the helper directly
    slicer.util.findChildren(text='Split Merge Volume')[0].clicked()

    masterNode = slicer.util.getNode(masterName)
    instanceUIDs = masterNode.GetAttribute("DICOM.instanceUIDs").split()
    if instanceUIDs == "":
      raise Exception("Editor master node does not have DICOM information")

    # get the list of source DICOM files
    inputDICOMImageFileNames = ""
    for instanceUID in instanceUIDs:
      inputDICOMImageFileNames += slicer.dicomDatabase.fileForInstance(instanceUID) + ","
    inputDICOMImageFileNames = inputDICOMImageFileNames[:-1] # strip last comma

    # save the per-structure volumes in the temp directory
    inputSegmentationsFileNames = ""
    import random
    import vtkITK
    writer = vtkITK.vtkITKImageWriter()
    rasToIJKMatrix = vtk.vtkMatrix4x4()
    perStructureNodes = slicer.util.getNodes(masterName+"-*-label")
    for nodeName in perStructureNodes.keys():
      node = perStructureNodes[nodeName]
      structureName = nodeName[len(masterName)+1:-1*len('-label')]
      structureFileName = structureName + str(random.randint(0,vtk.VTK_INT_MAX)) + ".nrrd"
      filePath = os.path.join(slicer.app.temporaryPath, structureFileName)
      writer.SetFileName(filePath)
      writer.SetInputDataObject(node.GetImageData())
      node.GetRASToIJKMatrix(rasToIJKMatrix)
      writer.SetRasToIJKMatrix(rasToIJKMatrix)
      print("Saving to %s..." % filePath)
      writer.Write()
      inputSegmentationsFileNames += filePath + ","
    inputSegmentationsFileNames = inputSegmentationsFileNames[:-1] # strip last comma

    # save the per-structure volumes label attributes
    mergeNode = slicer.util.getNode(masterName+"-label")
    colorNode = mergeNode.GetDisplayNode().GetColorNode()
    terminologyName = colorNode.GetAttribute("TerminologyName")
    colorLogic = slicer.modules.colors.logic()
    if not terminologyName or not colorLogic:
      raise Exception("No terminology or color logic - cannot export")
    inputLabelAttributesFileNames = ""
    perStructureNodes = slicer.util.getNodes(masterName+"-*-label")
    for nodeName in perStructureNodes.keys():
      node = perStructureNodes[nodeName]
      structureName = nodeName[len(masterName)+1:-1*len('-label')]
      labelIndex = colorNode.GetColorIndexByName( structureName )

      rgbColor = [0,]*4
      colorNode.GetColor(labelIndex, rgbColor)
      rgbColor = map(lambda e: e*255., rgbColor)

      # get the attributes and conver to format CodeValue,CodeMeaning,CodingSchemeDesignator
      # or empty strings if not defined
      propertyCategoryWithColons = colorLogic.GetSegmentedPropertyCategory(labelIndex, terminologyName)
      if propertyCategoryWithColons == '':
        print ('ERROR: no segmented property category found for label ',str(labelIndex))
        # Try setting a default as this section is required
        propertyCategory = "C94970,NCIt,Reference Region"
      else:
        propertyCategory = propertyCategoryWithColons.replace(':',',')

      propertyTypeWithColons = colorLogic.GetSegmentedPropertyType(labelIndex, terminologyName)
      propertyType = propertyTypeWithColons.replace(':',',')

      propertyTypeModifierWithColons = colorLogic.GetSegmentedPropertyTypeModifier(labelIndex, terminologyName)
      propertyTypeModifier = propertyTypeModifierWithColons.replace(':',',')

      anatomicRegionWithColons = colorLogic.GetAnatomicRegion(labelIndex, terminologyName)
      anatomicRegion = anatomicRegionWithColons.replace(':',',')

      anatomicRegionModifierWithColons = colorLogic.GetAnatomicRegionModifier(labelIndex, terminologyName)
      anatomicRegionModifier = anatomicRegionModifierWithColons.replace(':',',')

      structureFileName = structureName + str(random.randint(0,vtk.VTK_INT_MAX)) + ".info"
      filePath = os.path.join(slicer.app.temporaryPath, structureFileName)

      # EncodeSEG is expecting a file of format:
      # labelNum;SegmentedPropertyCategory:codeValue,codeScheme,codeMeaning;SegmentedPropertyType:v,m,s etc
      attributes = "%d" % labelIndex
      attributes += ";SegmentedPropertyCategory:"+propertyCategory
      if propertyType != "":
        attributes += ";SegmentedPropertyType:" + propertyType
      if propertyTypeModifier != "":
        attributes += ";SegmentedPropertyTypeModifier:" + propertyTypeModifier
      if anatomicRegion != "":
        attriutes += ";AnatomicRegion:" + anatomicRegion
      if anatomicRegionModifier != "":
        attributes += ";AnatomicRegionModifer:" + anatomicRegionModifier
      attributes += ";SegmentAlgorithmType:AUTOMATIC"
      attributes += ";SegmentAlgorithmName:SlicerSelfTest"
      attributes += ";RecommendedDisplayRGBValue:%g,%g,%g" % tuple(rgbColor[:-1])
      fp = open(filePath, "w")
      fp.write(attributes)
      fp.close()
      print(filePath, "Attributes", attributes)
      inputLabelAttributesFileNames += filePath + ","
    inputLabelAttributesFileNames = inputLabelAttributesFileNames[:-1] # strip last comma

    parameters = {
        "inputDICOMImageFileNames": inputDICOMImageFileNames,
        "inputSegmentationsFileNames": inputSegmentationsFileNames,
        "inputLabelAttributesFileNames": inputLabelAttributesFileNames,
        "readerId": "pieper",
        "sessionId": "1",
        "timepointId": "1",
        "seriesDescription": "SlicerEditorSEGExport",
        "seriesNumber": "100",
        "instanceNumber": "1",
        "bodyPart": "HEAD",
        "algorithmDescriptionFileName": "Editor",
        "outputSEGFileName": segFilePath,
        "skipEmptySlices": False,
        "compress": False,
        }

    encodeSEG = slicer.modules.encodeseg
    self.cliNode = None
    self.cliNode = slicer.cli.run(encodeSEG, self.cliNode, parameters, delete_temporary_files=False)
    waitCount = 0
    while self.cliNode.IsBusy() and waitCount < 20:
      self.delayDisplay( "Running SEG Encoding... %d" % waitCount, 1000 )
      waitCount += 1

    if self.cliNode.GetStatusString() != 'Completed':
      raise Exception("encodeSEG CLI did not complete cleanly")

    self.delayDisplay("Finished!")
