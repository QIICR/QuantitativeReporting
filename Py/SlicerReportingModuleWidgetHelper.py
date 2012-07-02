# slicer imports
from __main__ import vtk, slicer, tcl

# python includes
import sys
import time

class SlicerReportingModuleWidgetHelper( object ):
  '''
  classdocs
  '''

  @staticmethod
  def Info( message ):
    '''
    
    '''

    #print "[ChangeTrackerPy " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "]: " + str( message )
    #sys.stdout.flush()

  @staticmethod
  def Warning( message ):
    '''
    
    '''

    #print "[ChangeTrackerPy " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "]: WARNING: " + str( message )
    #sys.stdout.flush()

  @staticmethod
  def Error( message ):
    '''
    
    '''

    print "[ChangeTrackerPy " + time.strftime( "%m/%d/%Y %H:%M:%S" ) + "]: ERROR: " + str( message )
    sys.stdout.flush()


  @staticmethod
  def Debug( message ):
    '''
    
    '''

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
  def GetNthStepId( n ):
    '''
    '''
    steps = [None, # 0
             'SelectScans', # 1
             'DefineROI', # 2
             'SegmentROI', # 3
             'AnalyzeROI', # 4
             'ReportROI', # 5
             ]                        

    if n < 0 or n > len( steps ):
      n = 0

    return steps[n]

  @staticmethod
  def SetBgFgVolumes(bg, fg):
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveVolumeID(bg)
    selectionNode.SetReferenceSecondaryVolumeID(fg)
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
  def SetLabelVolume(lb):
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveLabelVolumeID(lb)
    appLogic.PropagateVolumeSelection()

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
  Figure out the slice viewer with the scan direction images
  '''
  @staticmethod
  def GetScanOrderSliceName(vol):
    if vol == None:
      return ""
    print "GetScanOrderSlice: volume =",vol.GetName()
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
      print "Unable to detect orientation from IJK to RAS matrix of volume"
    else:
      print "Orientation of volume is ",orientation,". Please place mark ups in the ",orientation," slice viewer."
    # return orientation

    # get the Z/K to RAS column vector from the volumes IJK to RAS matrix
    kToRAS = [0,0,0]
    vol.GetKToRASDirection(kToRAS)
    kToRASVector = [kToRAS[0],kToRAS[1],kToRAS[2],1]

    # iterate over slice widgets to get slice nodes
    lm = slicer.app.layoutManager()
    logics = lm.mrmlSliceLogics()

    import numpy

    mat = vtk.vtkMatrix4x4()
    sliceViewerName = "not found"
    for s in range(logics.GetNumberOfItems()):
      l = logics.GetItemAsObject(s)
      mat = l.GetSliceNode().GetSliceToRAS()
      zToRAS = [0,0,0,1]
      zToRAS[0] = mat.GetElement(2,0)
      zToRAS[1] = mat.GetElement(2,1)
      zToRAS[2] = mat.GetElement(2,2)
      dotprod = numpy.dot(kToRASVector,zToRAS)
      print s,": dot product =",dotprod    
      if dotprod < 0.001:
        sliceViewerName = l.GetSliceNode().GetName()
        print "Found a slice viewer aligned to volume, name = ",sliceViewerName

    if sliceViewerName == "not found":
      print "No slice viewer slice to RAS vectors line up, using volume compute scan order of ", orientation
      return orientation
    else:
      return sliceViewerName

