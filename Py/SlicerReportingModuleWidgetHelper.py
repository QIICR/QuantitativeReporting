# slicer imports
from __main__ import vtk, slicer, tcl

# python includes
import sys
import time

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
  def Warning( message ):
    print("[Reporting " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "]: WARNING: " + str( message ))
    sys.stdout.flush()

  @staticmethod
  def Error( message ):
    print("[Reporting " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "]: ERROR: " + str( message ))
    sys.stdout.flush()

  @staticmethod
  def Debug( message ):
    showDebugOutput = 0
    from time import strftime
    if showDebugOutput:
        print "[ChangeTrackerPy " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "] DEBUG: " + str( message )
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
  Figure out the slice viewer with the scan direction images
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

   
    sliceViewerName = "not found"
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
        sliceViewerName = l.GetSliceNode().GetName()
        SlicerReportingModuleWidgetHelper.Info("Found a slice viewer aligned to volume, name = "+sliceViewerName)

    if sliceViewerName == "not found":
      SlicerReportingModuleWidgetHelper.Error("No slice viewer slice to RAS vectors line up, using volume compute scan order of "+orientation)
      return orientation
    else:
      return sliceViewerName

