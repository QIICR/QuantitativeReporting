# slicer imports
from __main__ import vtk, slicer, tcl, qt

# python includes
import sys
import time

import xml.dom.minidom
import DICOMLib # for loading a volume on AIM import
from DICOMLib import DICOMPlugin
from DICOMLib import DICOMLoadable

class SlicerReportingModuleWidgetHelper( object ):
  '''
  classdocs
  '''

  # TODO: add a capability to control the level of messages
  @staticmethod
  def Info( message ):
    print("[Reporting " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "]: INFO: " + str( message ))
    sys.stdout.flush()

  @staticmethod
  def InfoPopup(message):
    messageBox = qt.QMessageBox()
    messageBox.information(None, '', message)

  @staticmethod
  def Warning( message ):
    print("[Reporting " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "]: WARNING: " + str( message ))
    sys.stdout.flush()
  
  @staticmethod
  def WarningPopup(message):
    messageBox = qt.QMessageBox()
    messageBox.warning(None, '', message)

  @staticmethod
  def Error( message ):
    print("[Reporting " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "]: ERROR: " + str( message ))
    sys.stdout.flush()
  
  @staticmethod
  def ErrorPopup(message):
    messageBox = qt.QMessageBox()
    messageBox.critical(None, '', message)

  @staticmethod
  def Debug( message ):
    print "[Reporting " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "] DEBUG: " + str( message )
    sys.stdout.flush()

  @staticmethod
  def CreateSpace( n ):
    '''
    '''
    spacer = ""
    for s in range( n ):
      spacer += " "

    return spacer

  @staticmethod
  def SetBgFgVolumes(bg, fg):
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveVolumeID(bg)
    selectionNode.SetReferenceSecondaryVolumeID(fg)
    appLogic.PropagateVolumeSelection()

  @staticmethod
  def SetLabelVolume(label):
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveLabelVolumeID(label)
    appLogic.PropagateVolumeSelection()

  @staticmethod
  def RotateToVolumePlanes():
    # AF TODO: check with Steve if this has any undesired consequences
    # Volumes slicenode has a method for this, no need for tcl
    tcl('EffectSWidget::RotateToVolumePlanes')
    # snap to IJK to try and avoid rounding errors
    sliceLogics = slicer.app.layoutManager().mrmlSliceLogics()
    numLogics = sliceLogics.GetNumberOfItems()
    for n in range(numLogics):
      l = sliceLogics.GetItemAsObject(n)
      l.SnapSliceOffsetToIJK() 

  @staticmethod
  def findChildren(widget=None,name="",text=""):
    """ return a list of child widgets that match the passed name """
    # TODO: figure out why the native QWidget.findChildren method
    # does not seem to work from PythonQt
    if not widget:
      widget = mainWindow()
    children = []
    parents = [widget]
    while parents != []:
      p = parents.pop()
      parents += p.children()
      if name and p.name.find(name)>=0:
        children.append(p)
      elif text: 
        try:
          p.text
          if p.text.find(text)>=0:
            children.append(p)
        except AttributeError:
          pass
    return children

  @staticmethod
  def getNodeByID(id):
    return slicer.mrmlScene.GetNodeByID(id)

  @staticmethod
  def readFileAsString(fname):
    s = ''
    with open(fname, 'r') as f:
      s = f.read()
    return s

  '''
  Create and return a unit length vector from v[3]
  '''
  @staticmethod
  def GetUnitVector(v):
    import math
    vectorLength = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
    # print 'vectorLength = ',vectorLength
    v2 = [0,0,0]
    if vectorLength != 0:
      v2[0] = v[0] / vectorLength
      v2[1] = v[1] / vectorLength
      v2[2] = v[2] / vectorLength
      # print 'Input vector =",v,", unit vector = ',v2
    else:
      SlicerReportingModuleWidgetHelper.Error('Vector was of length 0, cannot make it a unit vector')
    return v2

  '''
  Figure out the slice viewer(s) with the scan direction images, return as a list
  '''
  @staticmethod
  def GetScanOrderSliceName(vol):
    if vol == None:
      return ""
    SlicerReportingModuleWidgetHelper.Info("GetScanOrderSlice: volume = "+vol.GetName())
    # figure out scan order
    mat = vtk.vtkMatrix4x4()
    vol.GetIJKToRASMatrix(mat)
    scanOrder = ""
    scanOrder = vol.ComputeScanOrderFromIJKToRAS(mat)
    orientation = "Unknown"
    if scanOrder == "LR" or scanOrder == "RL":
      orientation = "Sagittal"
    elif scanOrder == "PA" or scanOrder == "AP":
      orientation = "Coronal"
    elif scanOrder == "IS" or scanOrder == "SI":
      orientation = "Axial"
    if orientation == "Unknown":
      SlicerReportingModuleWidgetHelper.Error("Unable to detect orientation from IJK to RAS matrix of volume")
    else:
      SlicerReportingModuleWidgetHelper.Info("Orientation of volume is "+orientation+".")
    # return orientation

    # get the Z/K to RAS column vector from the volumes IJK to RAS matrix
    kToRAS = [0,0,0]
    vol.GetKToRASDirection(kToRAS)
    kToRASVector = [kToRAS[0],kToRAS[1],kToRAS[2]]
    kToRASVectorUnit = SlicerReportingModuleWidgetHelper.GetUnitVector(kToRASVector)

    # iterate over slice widgets to get slice nodes
    lm = slicer.app.layoutManager()
    logics = lm.mrmlSliceLogics()

    import numpy

    sliceViewers = []
    for s in range(logics.GetNumberOfItems()):
      l = logics.GetItemAsObject(s)
      mat = vtk.vtkMatrix4x4()
      mat = l.GetSliceNode().GetSliceToRAS()
      # print s,": matrix = \n",mat
      zToRAS = [0,0,0]
      zToRAS[0] = mat.GetElement(0,2)
      zToRAS[1] = mat.GetElement(1,2)
      zToRAS[2] = mat.GetElement(2,2)
      zToRASUnit = SlicerReportingModuleWidgetHelper.GetUnitVector(zToRAS)

      dotprod = numpy.dot(kToRASVectorUnit,zToRASUnit)
      # print s,":",l.GetSliceNode().GetName()," kToRAS = ",kToRASVectorUnit,", slice node zToRAS = ",zToRASUnit,", dot product =",dotprod
      # to find the vectors that line up in the same direction want a dot product of 1 or -1
      diff = numpy.abs(dotprod) - 1.0
      diff = numpy.abs(diff)
      # print  "dot product diff from 1 = ",diff
      if diff < 0.001:
        sliceViewers.append(l.GetSliceNode().GetName())
        SlicerReportingModuleWidgetHelper.Info("Finding slice viewers aligned to volume, name = " + l.GetSliceNode().GetName())

    if len(sliceViewers) == 0:
      SlicerReportingModuleWidgetHelper.Error("No slice viewer slice to RAS vectors line up, using volume compute scan order of "+orientation)
      return orientation
    else:
      return sliceViewers

  '''
  Parse and load an aim file
  '''
  @staticmethod
  def LoadAIMFile(newReportID, fileName):
    dom = xml.dom.minidom.parse(fileName)

    SlicerReportingModuleWidgetHelper.Debug('Parsed AIM report:')
    SlicerReportingModuleWidgetHelper.Debug(dom.toxml())

    volumeList = []

    ddb = slicer.dicomDatabase
    volId = 1
    volume = None
  
    # get the annotation element and retrieve its name
    annotations = dom.getElementsByTagName('ImageAnnotation')
    if len(annotations) == 0:
      SlicerReportingModuleWidgetHelper.ErrorPopup('AIM file does not contain any annotations!')
      return
    ann = annotations[0]
    desc = ann.getAttribute('name')

    # get the anatomic entity element and initialize the report node based on
    # it
    anatomics = dom.getElementsByTagName('AnatomicEntity')
    if len(anatomics) != 1:
      SlicerReportingModuleWidgetHelper.ErrorPopup('AIM file does not contain any anatomic entities or contains more than one! This is not supported.')
      return
    anatomy = anatomics[0]

    labelValue = anatomy.getAttribute('codeValue')
    labelName = anatomy.getAttribute('codeMeaning')
    codingSchemeDesignator = anatomy.getAttribute('codingSchemeDesignator')
    if codingSchemeDesignator != '3DSlicer':
      SlicerReportingModuleWidgetHelper.WarningPopup('Code scheme designator '+codingSchemeDesignator+' is not supported. Default will be used instead.')
      labelValue = "1"

    newReport = slicer.mrmlScene.GetNodeByID(newReportID)
    newReport.SetFindingLabel(int(labelValue))


    # pull all the volumes that are referenced into the scene
    for node in dom.getElementsByTagName('ImageSeries'):
      instanceUID = node.getAttribute('instanceUID')
      filelist = ddb.filesForSeries(instanceUID)

      scalarVolumePlugin = slicer.modules.dicomPlugins['DICOMScalarVolumePlugin']()
      scalarVolumeLoadables = scalarVolumePlugin.examine([filelist])
      if len(scalarVolumeLoadables) == 0:
        SlicerReportingModuleWidgetHelper.ErrorPopup('Error loading AIM: Failed to load the volume node reference in the file')
     
      volumeName = scalarVolumeLoadables[0].name
      newReport.SetName('Report for Volume '+volumeName)

      volume = scalarVolumePlugin.load(scalarVolumeLoadables[0])
      volume.SetName(volumeName)

      if volume == None:
        SlicerReportingModuleWidgetHelper.Error('Failed to read series!')
        return

      if len(volumeList) != 0:
        SlicerReportingModuleWidgetHelper.ErrorPopup('Error importing AIM report: Report references more than one volume, which is not allowed!')
        return

      volumeList.append(volume)
      SlicerReportingModuleWidgetHelper.Debug('Volume read from AIM report:')

      slicer.modules.reporting.logic().InitializeHierarchyForVolume(volume)
      newReport.SetVolumeNodeID(volume.GetID())

    if len(volumeList) > 1:
      SlicerReportingModuleWidgetHelper.ErrorPopup('AIM does not allow to have more than one volume per file!')
      return

    if len(volumeList) == 0:
      SlicerReportingModuleWidgetHelper.ErrorPopup('AIM file you requested to load does not reference any volumes, cannot process it!')
      return

    #if volume != None:
    #  self.__volumeSelector.setCurrentNode(volume)

    instanceUIDs = volume.GetAttribute('DICOM.instanceUIDs')
    instanceUIDList = instanceUIDs.split()

    # AF: GeometricShape is inside geometricShapeCollection, but
    # there's no need to parse at that level, I think 
    # 
    # geometricShapeCollection
    #  |
    #  +-spatialCoordinateCollection
    #     |
    #     +-SpatialCoordinate
    #

    for node in dom.getElementsByTagName('GeometricShape'):

      ijCoordList = []
      rasPointList = []
      uidList = []
      elementType = node.getAttribute('xsi:type')
 
      for child in node.childNodes:
        if child.nodeName == 'spatialCoordinateCollection':
          for coord in child.childNodes:
            if coord.nodeName == 'SpatialCoordinate':
              ijCoordList.append(float(coord.getAttribute('x')))
              ijCoordList.append(float(coord.getAttribute('y')))
              uid = coord.getAttribute('imageReferenceUID')
              uidList.append(uid)
   
      SlicerReportingModuleWidgetHelper.Debug('Coordinate list: '+str(ijCoordList))

      ijk2ras = vtk.vtkMatrix4x4()
      volume.GetIJKToRASMatrix(ijk2ras)


      # convert each point from IJ to RAS
      for ij in range(len(uidList)):
        pointUID = uidList[ij]
        # locate the UID in the list assigned to the volume
        totalSlices = len(instanceUIDList)
        for k in range(len(instanceUIDList)):
          if pointUID == instanceUIDList[k]:
            break

        # print "k = ",k,", totalSlices = ",totalSlices 
        pointIJK = [ijCoordList[ij*2], ijCoordList[ij*2+1], k, 1.]
        pointRAS = ijk2ras.MultiplyPoint(pointIJK)
        SlicerReportingModuleWidgetHelper.Debug('Input point: '+str(pointIJK))
        SlicerReportingModuleWidgetHelper.Debug('Converted point: '+str(pointRAS))
        rasPointList.append(pointRAS[0:3])

      # instantiate the markup elements
      if elementType == 'Point':
        SlicerReportingModuleWidgetHelper.Debug("Importing a fiducial!")
        if len(ijCoordList) != 2:
          SlicerReportingModuleWidgetHelper.Error('Number of coordinates not good for a fiducial')
          return

        fiducial = slicer.mrmlScene.CreateNodeByClass('vtkMRMLAnnotationFiducialNode')
        fiducial.SetReferenceCount(fiducial.GetReferenceCount()-1)
        # associate it with the report
        fiducial.SetAttribute('ReportingReportNodeID', newReport.GetID())
        # associate it with the volume
        fiducial.SetAttribute('AssociatedNodeID', volume.GetID())
        # ??? Why the API is so inconsistent -- there's no SetPosition1() ???
        fiducial.SetFiducialCoordinates(rasPointList[0])
        fiducial.Initialize(slicer.mrmlScene)
        # adding to hierarchy is handled by the Reporting logic

      if elementType == 'MultiPoint':
        SlicerReportingModuleWidgetHelper.Debug("Importing a ruler!")
        if len(ijCoordList) != 4:
          SlicerReportingModuleWidgetHelper.Error('Number of coordinates not good for a ruler')
          return

        ruler = slicer.mrmlScene.CreateNodeByClass('vtkMRMLAnnotationRulerNode')
        ruler.SetReferenceCount(ruler.GetReferenceCount()-1)
        # associate it with the report
        ruler.SetAttribute('ReportingReportNodeID', newReport.GetID())
        # associate it with the volume
        ruler.SetAttribute('AssociatedNodeID', volume.GetID())
        SlicerReportingModuleWidgetHelper.Debug('Initializing with points '+str(rasPointList[0])+' and '+str(rasPointList[1]))
        ruler.SetPosition1(rasPointList[0])
        ruler.SetPosition2(rasPointList[1])
        ruler.Initialize(slicer.mrmlScene)
        # AF: Initialize() adds to the scene ...

    for node in dom.getElementsByTagName('Segmentation'):
      # read all labels that are available in the SEG object
      # check if the referenced volume is already in the scene
      #   if not, load it
      # initialize AssociatedNodeID for the label node to point to the
      # reference
      SlicerReportingModuleWidgetHelper.Debug('Importing a segmentation')
      labelNodes = vtk.vtkCollection()
      referenceNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLScalarVolumeNode')
      referenceNode.SetReferenceCount(referenceNode.GetReferenceCount()-1)

      uid = node.getAttribute('sopInstanceUID')

      res = False
      colorNode = slicer.mrmlScene.GetNodeByID(newReport.GetColorNodeID())
      res = slicer.modules.reporting.logic().DicomSegRead(labelNodes, uid, colorNode)
      SlicerReportingModuleWidgetHelper.Debug('Read this many labels from the seg object:'+str(labelNodes.GetNumberOfItems()))

      if labelNodes.GetNumberOfItems() == 0:
        print("Error loading segmentation object, have 0 labels")
      else:
        # read the reference node
        label0 = labelNodes.GetItemAsObject(0)

        referenceUIDs = label0.GetAttribute('DICOM.referenceInstanceUIDs')
        SlicerReportingModuleWidgetHelper.Debug('Seg object reference uids: '+referenceUIDs)

      for i in range(labelNodes.GetNumberOfItems()):
        displayNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLLabelMapVolumeDisplayNode')
        displayNode.SetReferenceCount(displayNode.GetReferenceCount()-1)
        displayNode.SetAndObserveColorNodeID(newReport.GetColorNodeID())
        slicer.mrmlScene.AddNode(displayNode)
        labelNode = labelNodes.GetItemAsObject(i)
        labelNode.SetAttribute('ReportingReportNodeID', newReport.GetID())
        labelNode.SetAttribute('AssociatedNodeID', volumeList[0].GetID())
        labelNode.SetAndObserveDisplayNodeID(displayNode.GetID())
        slicer.mrmlScene.AddNode(labelNode)

      # AF: this shuould not be necessary with the "proper" AIM input, since
      # only one volume should be present in the report, and only one item in
      # that volume should be annotated
      if 0:
      # if referenceUIDs != None:

        reader = slicer.vtkMRMLVolumeArchetypeStorageNode()
        reader.ResetFileNameList()

        for uid in string.split(referenceUIDs, ' '):

          fname = slicer.modules.reporting.logic().GetFileNameFromUID(uid)
          reader.AddFileName(fname)

        reader.SetFileName(string.split(referenceUIDs, ' ')[0])
        reader.SetSingleFile(0)
        
        referenceVolume = slicer.mrmlScene.CreateNodeByClass('vtkMRMLScalarVolumeNode')
        referenceVolumeUIDs = referenceVolume.GetAttribute('DICOM.instanceUIDs')
        reader.ReadData(referenceVolume)

        nodeToAdd = referenceVolume

        allVolumeNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLScalarVolumeNode')
        allVolumeNodes.SetReferenceCount(allVolumeNodes.GetReferenceCount()-1)
        for i in range(allVolumeNodes.GetNumberOfItems()):
          v = allVolumeNodes.GetItemAsObject(i)
          uids = v.GetAttribute('DICOM.instanceUIDs')
          if uids == referenceNodeUIDs:
            print('Referenced node is already in the scene!')
            nodeToAdd = None
            referenceNode = v
            break

        if nodeToAdd != None:
          slicer.mrmlScene.AddNode(nodeToAdd)

        slicer.modules.reporting.logic().InitializeHierarchyForVolume(referenceNode)

        for i in range(labelNodes.GetNumberOfItems()):
          displayNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLScalarVolumeDisplayNode')
          displayNode.SetReferenceCount(displayNode.GetReferenceCount()-1)
          displayNode.SetAndObserveColorNodeID(newReport.GetColorNodeID())
          slicer.mrmlScene.AddNode(displayNode)
          labelNode = labelNodes.GetItemAsObject(i)
          labelNode.SetAttribute('ReportingReportNodeID', newReport.GetID())
          labelNode.SetAttribute('AssociatedNodeID', referenceNode.GetID())
          labelNode.SetAndObserveDisplayNodeID(displayNode.GetID())
          slicer.mrmlScene.AddNode(labelNodes.GetItemAsObject(i))

  '''
  Check if the geometries of the two volumes match
  '''
  @staticmethod
  def GeometriesMatch(vol1, vol2):
    # for now, just match the extents of the image data
    image1 = vol1.GetImageData()
    image2 = vol2.GetImageData()

    dim1 = image1.GetDimensions()
    dim2 = image2.GetDimensions()

    print dim1,' ',dim2

    if dim1[0] == dim2[0] and dim1[1] == dim2[1] and dim1[2] == dim2[2]:
      return True

    return False

  @staticmethod
  def getEditorParameterNode():
    """Get the Editor parameter node - a singleton in the scene"""
    node = None
    size =  slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLScriptedModuleNode")
    for i in xrange(size):
      n  = slicer.mrmlScene.GetNthNodeByClass( i, "vtkMRMLScriptedModuleNode" )
      if n.GetModuleName() == "Editor":
        node = n

    if not node:
      node = slicer.vtkMRMLScriptedModuleNode()
      node.SetSingletonTag( "Editor" )
      node.SetModuleName( "Editor" )
      node.SetParameter( "label", "1" )
      slicer.mrmlScene.AddNode(node)
    return node

  @staticmethod
  def initializeNewLabel(newLabel, sourceVolume):    
    displayNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLLabelMapVolumeDisplayNode())

    threshold = vtk.vtkImageThreshold()
    threshold.ReplaceInOn()
    threshold.ReplaceOutOn()
    threshold.SetInValue(0)
    threshold.SetOutValue(0)
    threshold.SetOutputScalarTypeToUnsignedShort()
    threshold.SetInput(sourceVolume.GetImageData())
    threshold.Update()

    labelImage = vtk.vtkImageData()
    labelImage.DeepCopy(threshold.GetOutput())
    
    newLabel.SetAndObserveStorageNodeID(None)
    newLabel.SetLabelMap(1)
    newLabel.CopyOrientation(sourceVolume)
    ras2ijk = vtk.vtkMatrix4x4()
    sourceVolume.GetRASToIJKMatrix(ras2ijk)
    newLabel.SetRASToIJKMatrix(ras2ijk)

    newLabel.SetAttribute('ReportingReportNodeID', sourceVolume.GetAttribute('ReportingReportNodeID'))
    newLabel.SetAttribute('AssociatedNodeID', sourceVolume.GetID())
    
    newLabel.SetAndObserveDisplayNodeID(displayNode.GetID())
    newLabel.SetAndObserveImageData(labelImage)
