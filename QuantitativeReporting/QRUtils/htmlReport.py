from __future__ import absolute_import
from __future__ import print_function
import os

import ctk
import slicer
import vtk
from QRCustomizations.CustomSegmentEditor import CustomSegmentEditorLogic
from DICOMSegmentationPlugin import DICOMSegmentationExporter

from SlicerDevelopmentToolboxUtils.buttons import CrosshairButton
from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin

import vtkSegmentationCorePython as vtkSegmentationCore
from six.moves import range


class ScreenShotHelper(ModuleWidgetMixin):

  @staticmethod
  def addRuler(widget, color=None):
    color = color if color else [0.25, 0.25, 0.75]

    controller = widget.sliceController()
    sliceView = widget.sliceView()

    controller.setRulerType(2)

    collection = vtk.vtkCollection()
    sliceView.getDisplayableManagers(collection)
    manager = None
    for i in range(collection.GetNumberOfItems()):
      if type(collection.GetItemAsObject(i)) is slicer.vtkMRMLRulerDisplayableManager:
        manager = collection.GetItemAsObject(i)
        break

    renderers = manager.GetRenderer().GetRenderWindow().GetRenderers()
    axisActor = None
    textActor = None
    for i in range(renderers.GetNumberOfItems()):
      actors2D = renderers.GetItemAsObject(i).GetActors2D()
      for j in range(actors2D.GetNumberOfItems()):
        if type(actors2D.GetItemAsObject(j)) is vtk.vtkTextActor:
          textActor = actors2D.GetItemAsObject(j)
        elif type(actors2D.GetItemAsObject(j)) is vtk.vtkAxisActor2D:
          axisActor = actors2D.GetItemAsObject(j)
      if axisActor and textActor:
        axisActor.GetProperty().SetColor(color)
        textActor.GetProperty().SetColor(color)
        sliceView.update()
        break

  @staticmethod
  def hideRuler(widget):
    controller = widget.sliceController()
    controller.setRulerType(0)

  @staticmethod
  def findLargest2DRegion(segmentationNode):
    qrLogic = CustomSegmentEditorLogic
    segmentationsLogic = slicer.modules.segmentations.logic()

    largestLM = None
    largestSize = 0
    for segment in qrLogic.getAllSegments(segmentationNode):
      imageData = vtkSegmentationCore.vtkOrientedImageData()
      segmentID = segmentationNode.GetSegmentation().GetSegmentIdBySegment(segment)
      segmentationsLogic.GetSegmentBinaryLabelmapRepresentation(segmentationNode, segmentID, imageData)
      extent = imageData.GetExtent()

      if extent[1] != -1 and extent[3] != -1 and extent[5] != -1:
        tempLabel = slicer.vtkMRMLLabelMapVolumeNode()
        tempLabel.SetName(segment.GetName() + "CentroidHelper")
        segmentationsLogic.CreateLabelmapVolumeFromOrientedImageData(imageData, tempLabel)

        dims = tempLabel.GetImageData().GetDimensions()
        size = dims[0]*dims[1]
        if size > largestSize:
          largestSize = size
          largestLM = tempLabel

    return largestLM

  @staticmethod
  def jumpToSegmentAndCreateScreenShot(segmentationNode, segment, widgets, center=False, crosshair=False):
    segmentID = segmentationNode.GetSegmentation().GetSegmentIdBySegment(segment)
    centroid = segmentationNode.GetSegmentCenterRAS(segmentID)

    if centroid:

      annotationNodes = []

      crosshairButton = None
      if crosshair:
        crosshairButton = CrosshairButton()
        crosshairButton.setSliceIntersectionEnabled(True)
        crosshairButton.checked = True

      for widget in widgets:
        sliceLogic = widget.sliceLogic()
        sliceNode = sliceLogic.GetSliceNode()

        if not center:
          sliceNode.JumpSliceByOffsetting(centroid[0], centroid[1], centroid[2])
        else:
          markupsLogic = slicer.modules.markups.logic()
          markupsLogic.JumpSlicesToLocation(centroid[0], centroid[1], centroid[2], True)

        dNodeProperties = ScreenShotHelper.saveSegmentDisplayProperties(segmentationNode, segment)
        segmentationNode.GetDisplayNode().SetAllSegmentsVisibility(False)
        ScreenShotHelper.setDisplayNodeProperties(segmentationNode, segment,
                                                  properties={'fill': True, 'outline': True, 'visible': True})

        if crosshairButton:
          crosshairButton.crosshairNode.SetCrosshairRAS(centroid)

        slicer.util.forceRenderAllViews()

        annotationNode = ScreenShotHelper.takeScreenShot("{}_Screenshot_{}_{}".format(segment.GetName(),
                                                                                      sliceNode.GetName(),
                                                                                      sliceNode.GetOrientation()),
                                                         "", widget)
        segmentationNode.GetDisplayNode().SetAllSegmentsVisibility(True)
        ScreenShotHelper.setDisplayNodeProperties(segmentationNode, segment, dNodeProperties)
        annotationNodes.append(annotationNode)
        if crosshairButton:
          crosshairButton.checked = False

      return annotationNodes[0] if len(annotationNodes) == 1 else annotationNodes

  @staticmethod
  def saveSegmentDisplayProperties(segmentationNode, segment):
    dNode = segmentationNode.GetDisplayNode()
    sName = segment.GetName()
    properties = {
      'fill': dNode.GetSegmentVisibility2DFill(sName),
      'outline': dNode.GetSegmentVisibility2DOutline(sName),
      'visible': dNode.GetSegmentVisibility(sName)
    }
    return properties

  @staticmethod
  def setDisplayNodeProperties(segmentationNode, segment, properties):
    dNode = segmentationNode.GetDisplayNode()
    sName = segment.GetName()
    dNode.SetSegmentVisibility2DFill(sName, properties['fill'])
    dNode.SetSegmentVisibility2DOutline(sName, properties['outline'])
    dNode.SetSegmentVisibility(sName, properties['visible'])

  @staticmethod
  def takeScreenShot(name, description, widget=None, screenShotType=-1):
    lm = slicer.app.layoutManager()
    if not widget:
      if screenShotType == slicer.qMRMLScreenShotDialog.FullLayout:
        widget = lm.viewport()
      elif screenShotType == slicer.qMRMLScreenShotDialog.ThreeD:
        widget = lm.threeDWidget(0).threeDView()
      elif screenShotType == slicer.qMRMLScreenShotDialog.Red:
        widget = lm.sliceWidget("Red")
      elif screenShotType == slicer.qMRMLScreenShotDialog.Yellow:
        widget = lm.sliceWidget("Yellow")
      elif screenShotType == slicer.qMRMLScreenShotDialog.Green:
        widget = lm.sliceWidget("Green")
      else:
        widget = slicer.util.mainWindow()
        screenShotType = slicer.qMRMLScreenShotDialog.FullLayout

    qImage = ctk.ctkWidgetsUtils.grabWidget(widget)
    imageData = vtk.vtkImageData()
    slicer.qMRMLUtils().qImageToVtkImageData(qImage, imageData)

    annotationLogic = slicer.modules.annotations.logic()
    annotationLogic.CreateSnapShot(name, description, screenShotType, 1.0, imageData)
    return slicer.util.getNodesByClass('vtkMRMLAnnotationSnapshotNode')[-1]


class HTMLReportCreator(ScreenShotHelper):

  style = '''
    body {
      font-family: Helvetica, Arial;
    }

    h2 {
      color: #2e6c80;
    }
    @media print {
      @page { size: auto;  margin: 7mm; }
      .print-friendly {
          page-break-inside: avoid;
      }
    }
  '''

  infoRow = '''
      <tr>
        <td class='heading'><b>{0}</b></td>
        <td>{1}</td>
      </tr>
    '''

  patientInfoTemplate = '''
    <table border=0 cellPadding=3 cellSpacing=0 width='100%' class="print-friendly">
      <tr><td><b>Patient Name:</b></td><td>{0}</td></tr>
      <tr><td><b>Patient ID:</b></td><td>{1}</td></tr>
      <tr><td><b>Date of Birth:</b></td><td>{2}</td></tr>
    </table>
  '''

  template = '''
      <html>
        <head>
        <meta name=\"Author\" content=\"...\">
        <title> QIICR Report </title>
        <style type=\"text/css\">{0}</style>
        <body>
          {1}
        </body>
       </html>
    '''

  def __init__(self, segmentationNode, statisticsTable):
    self.segmentationNode = segmentationNode
    self.statistics = statisticsTable
    self.createSliceWidgetClassMembers("Red")
    self.createSliceWidgetClassMembers("Green")
    self.patientInfo = None

  def generateReport(self):

    def currentDateTime():
      from datetime import datetime
      return  datetime.now().strftime('%Y-%m-%d_%H%M%S')

    html = self.template.format(self.style, self.getData())

    outputPath = os.path.join(slicer.app.temporaryPath, "QIICR", "QR")
    if not os.path.exists(outputPath):
      ModuleLogicMixin.createDirectory(outputPath)
    outputHTML = os.path.join(outputPath, currentDateTime()+"_testReport.html")
    print(outputHTML)
    f = open(outputHTML, 'w')
    f.write(html)
    f.close()

    # Open the html report in the default web browser
    import qt
    qt.QDesktopServices.openUrl(qt.QUrl.fromLocalFile(outputHTML));

  def getPatientInformation(self):
    if not self.patientInfo:
      masterVolume = ModuleLogicMixin.getReferencedVolumeFromSegmentationNode(self.segmentationNode)
      self.patientInfo =  self.patientInfoTemplate.format(ModuleLogicMixin.getDICOMValue(masterVolume,
                                                                                         DICOMTAGS.PATIENT_NAME),
                                                          ModuleLogicMixin.getDICOMValue(masterVolume,
                                                                                         DICOMTAGS.PATIENT_ID),
                                                           ModuleLogicMixin.getDICOMValue(masterVolume,
                                                                                          DICOMTAGS.PATIENT_BIRTH_DATE))
    return self.patientInfo

  def getData(self):
    annotationLogic = slicer.modules.annotations.logic()
    qrLogic = CustomSegmentEditorLogic

    data = ""

    def find_2nd(string, substring):
      return string.find(substring, string.find(substring) + 1)

    widget = self.redWidget

    for w in [self.redWidget, self.greenWidget]:
      ScreenShotHelper.addRuler(w)

    self.setFOV2Largest2DRegion(widget)

    self.greenWidget.sliceLogic().FitSliceToAll()
    fov = self.greenSliceNode.GetFieldOfView()
    masterVolume = ModuleLogicMixin.getReferencedVolumeFromSegmentationNode(self.segmentationNode)
    xNumSlices = masterVolume.GetImageData().GetDimensions() [0]
    xSpacing = masterVolume.GetSpacing()[0]
    size = xNumSlices * xSpacing
    self.greenSliceNode.SetFieldOfView(size, fov[1] * size/fov[0], fov[2])

    tableHelper = vtkMRMLTableNodeHTMLHelper(self.statistics)

    for idx, segment in enumerate(qrLogic.getAllSegments(self.segmentationNode)):
      redAnnotationNode = self.jumpToSegmentAndCreateScreenShot(self.segmentationNode, segment,
                                                                [widget], center=True)
      redSS = annotationLogic.GetHTMLRepresentation(redAnnotationNode, 0)
      redSS = redSS[find_2nd(redSS, "<img src="):redSS.find(">", find_2nd(redSS, "<img src=")) + 1]
      redSS = redSS.replace("width='400'", "width=100%")

      greenAnnotationNode = self.jumpToSegmentAndCreateScreenShot(self.segmentationNode, segment,
                                                                  [self.greenWidget], center=False, crosshair=True)
      greenSS = annotationLogic.GetHTMLRepresentation(greenAnnotationNode, 0)
      greenSS = greenSS[find_2nd(greenSS, "<img src="):greenSS.find(">", find_2nd(greenSS, "<img src=")) + 1]
      greenSS = greenSS.replace("width='400'", "width=100%")

      data += '''
        <div class="print-friendly">
          <h2>{0}</h2>
          <table border=1 width='100%' cellPadding=3 cellSpacing=0>
            <thead>
              <tr>
                <th><b>Terminology</b></th>
                <th><b>Patient Info</b></th>
              </tr>
            </thead>
            <tr>
              <td valign='top' width='50%'>{1}</td>
              <td valign='top' width='50%'>{2}</td>
            </tr>
          </table>
          <br>
          <table border=1 width='100%' cellPadding=3 cellSpacing=0>
            <thead border=1>
              <tr>
                <th colspan="2"><b>Screenshots</b></th>
              </tr>
              <tr>
                <th><b>Axial</b></th>
                <th><b>Coronal</b></th>
              </tr>
            </thead>
            <tr>
              <td>{3}</td>
              <td>{4}</td>
            </tr>
          </table>
          <br>
          <table border=1 width='100%' cellPadding=3 cellSpacing=0>
            <thead border=1>
              <tr>
                <th><b>Measurements</b></th>
              </tr>
            </thead>
            <tr>
              <td valign='top' width='100%'>{5}</td>
            </tr>
          </table>
        </div>
        '''.format(tableHelper.getNthSegmentName(idx),
                   self.getTerminologyInformation(segment), self.getPatientInformation(),
                   redSS, greenSS,
                   tableHelper.getHeaderAndNthRow(idx))

    for w in [self.redWidget, self.greenWidget]:
      ScreenShotHelper.hideRuler(w)
    # ModuleWidgetMixin.setFOV(sliceLogic, savedFOV)
    return data

  def setFOV2Largest2DRegion(self, widget, largestLabel=None, factor=1.5):
    if not largestLabel:
      largestLabel = self.findLargest2DRegion(self.segmentationNode)
    slicer.mrmlScene.AddNode(largestLabel)
    sliceLogic = widget.sliceLogic()
    sliceNode = sliceLogic.GetSliceNode()
    compositeNode = widget.mrmlSliceCompositeNode()
    savedVolumeID = compositeNode.GetBackgroundVolumeID()
    savedFOV = sliceNode.GetFieldOfView()
    compositeNode.SetBackgroundVolumeID(largestLabel.GetID())
    sliceLogic.FitSliceToAll()
    compositeNode.SetBackgroundVolumeID(savedVolumeID)
    FOV = sliceNode.GetFieldOfView()
    ModuleWidgetMixin.setFOV(sliceLogic, [FOV[0] * factor, FOV[1] * factor, FOV[2]])
    slicer.mrmlScene.RemoveNode(largestLabel)
    return largestLabel

  def getTerminologyInformation(self, segment):
    terminologyEntry = DICOMSegmentationExporter.getDeserializedTerminologyEntry(segment)
    catModifier = terminologyEntry.GetTypeModifierObject ().GetCodeMeaning()
    anatomicRegion = terminologyEntry.GetAnatomicRegionObject().GetCodeMeaning()
    anatomicRegionModifier = terminologyEntry.GetAnatomicRegionModifierObject ().GetCodeMeaning()
    html = '''
      <table border=0 width='100%' cellPadding=3 cellSpacing=0>
        {}{}{}{}{}
      </table>
    '''.format(self.infoRow.format("Category:", terminologyEntry.GetCategoryObject().GetCodeMeaning()),
               self.infoRow.format("Category Type:", terminologyEntry.GetTypeObject().GetCodeMeaning()),
               self.infoRow.format("Category Type Modifier:", catModifier) if catModifier else "",
               self.infoRow.format("Anatomic Region:", anatomicRegion) if anatomicRegion else "",
               self.infoRow.format("Anatomic Region Modifier:", anatomicRegionModifier) if anatomicRegionModifier else "")
    return html


class vtkMRMLTableNodeHTMLHelper(ModuleLogicMixin):

  tableTemplate = '''
    <table border=1 width='100%' cellPadding=3 cellSpacing=0>
      {0}
    </table>
  '''

  def __init__(self, tableNode):
    self.table = tableNode

  def getNthSegmentName(self, row):
    return self.table.GetCellText(row, 0)

  def getHeaderAndNthRow(self, row, skipSegmentName=True):
    html = ""
    for col in range(self.table.GetNumberOfColumns()):
      if skipSegmentName and col == 0:
        continue
      html += '''
        <tr>
          <td><b>{0}</b></td>
          <td>{1}</td>
        </tr>
      '''.format(self.table.GetColumnName(col), self.table.GetCellText(row, col))
    return self.tableTemplate.format(html)
