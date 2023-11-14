from __future__ import absolute_import
import glob
import os
import json
import vtk
import io
import shutil
import vtkSegmentationCorePython as vtkSegmentationCore
import logging

from base.DICOMM3DPluginBase import DICOMM3DPluginBase

import slicer
from DICOMLib import DICOMLoadable

from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS
from six.moves import range


#
# This is the plugin to handle translation of DICOM SEG objects
#
class DICOMM3DPluginClass(DICOMM3DPluginBase):

  def __init__(self):
    super(DICOMM3DPluginClass,self).__init__()
    self.loadType = "DICOMM3D"

  def examineFiles(self,files):
    """ Returns a list of DICOMLoadable instances
    corresponding to ways of interpreting the
    files parameter.
    """
    loadables = []

    # just read the modality type; need to go to reporting logic, since DCMTK
    #   is not wrapped ...

    for cFile in files:

      uid = slicer.dicomDatabase.fileValue(cFile, self.tags['instanceUID'])
      if uid == '':
        return []

      desc = slicer.dicomDatabase.fileValue(cFile, self.tags['seriesDescription'])
      if desc == '':
        desc = "Unknown"
      
      # EncapsulatedDocument = slicer.dicomDatabase.fileValue(cFile, self.tags['EncapsulatedDocument'])
      # EncapsulatedDocumentLength = slicer.dicomDatabase.fileValue(cFile, self.tags['EncapsulatedDocumentLength'])

      isDicomM3D = (slicer.dicomDatabase.fileValue(cFile, self.tags['modality']) == 'M3D')

      # print(isDicomM3D)
      # print(desc)
      # print(self.tags['modality'])
      # print(cFile)
      # print(uid)
      if isDicomM3D:
        loadable = DICOMLoadable()
        loadable.files = [cFile]
        loadable.name = desc
        loadable.tooltip = loadable.name + ' - as a DICOM M3D object'
        loadable.selected = True
        loadable.confidence = 0.95
        loadable.uid = uid
        # loadable.EncapsulatedDocument = EncapsulatedDocument
        # loadable.EncapsulatedDocumentLength = EncapsulatedDocumentLength 
        self.addReferences(loadable)
        loadables.append(loadable)

        logging.debug('DICOM M3D modality found')

    return loadables

  def referencedSeriesName(self,loadable):
    """Returns the default series name for the given loadable"""
    referencedName = "Unnamed Reference"
    if hasattr(loadable, "referencedSeriesUID"):
      referencedName = self.defaultSeriesNodeName(loadable.referencedSeriesUID)
    return referencedName

  def GetEncapsulatedDocument(self, loadable):
    return loadable.EncapsulatedDocument
  
  def GetEncapsulatedDocumentLength(self, loadable):
    return loadable.EncapsulatedDocumentLength


  def load(self,loadable):
    """ Load the DICOM M3D object
    """
    logging.debug('DICOM M3D load()')
    try:
      uid = loadable.uid
      logging.debug('in load(): uid = '+uid)
    except AttributeError:
      return False

    self.tempDir = os.path.join(slicer.app.temporaryPath, 
                                "QIICR", "M3D",
                                  self.currentDateTime, loadable.uid)
    print(self.tempDir)
    try:
        os.makedirs(self.tempDir)
    except OSError:
      pass
    
    # produces output label map files, one per segment, and information files with
    # the terminology information for each segment
    STLFileName = slicer.dicomDatabase.fileForInstance(uid)
    if STLFileName is None:
      logging.error('Failed to get the filename from the DICOM database for ' + uid)
      self.cleanup()
      return False
    
    read_buffer = io.BytesIO(self.GetEncapsulatedDocument(loadable))#bytes(loadable.EncapsulatedDocument))
    buffer_view = read_buffer.getbuffer()
    if (int(self.GetEncapsulatedDocumentLength(loadable)) % 2) != 0:
      buffer_view = buffer_view[0:(read_buffer.getbuffer().nbytes -1)]
    else:
      pass
    
    STLFilePath = os.path.join(self.tempDir, "temp.STL")
    
    with open(STLFilePath, 'wb') as file: 
      shutil.copyfileobj(read_buffer, file)
    assert os.path.exists(STLFilePath)
    file.close()
    #validity checks !!!!!
    ####
    self._createModelNode(loadable, STLFilePath)
    
    self.cleanup()
    
    return True

  def _createModelNode(self, loadable, STLFilePath):
    ModelNode = slicer.util.loadModel(STLFilePath)#slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode").AddModel(STLFileName)
    ModelNode.SetName(loadable.name)
   
    ModelDisplayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode")
    ModelNode.SetAndObserveDisplayNodeID(ModelDisplayNode.GetID())
    self.addSeriesInSubjectHierarchy(loadable, ModelNode)
    # return ModelNode
  
class DICOMM3DPlugin:
  """
  This class is the 'hook' for slicer to detect and recognize the plugin
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "DICOM M3D Object Import Plugin"
    parent.categories = ["Developer Tools.DICOM Plugins"]
    parent.contributors = ["Andrey Fedorov, BWH"]
    parent.helpText = """
    Plugin to the DICOM Module to parse and load DICOM M3D modality.
    No module interface here, only in the DICOM module
    """
    parent.dependencies = ['DICOM', 'Colors', 'SlicerDevelopmentToolbox']
    parent.acknowledgementText = """
    This DICOM Plugin was developed by
    Andrey Fedorov, BWH.
    """

    # Add this extension to the DICOM module's list for discovery when the module
    # is created.  Since this module may be discovered before DICOM itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.dicomPlugins
    except AttributeError:
      slicer.modules.dicomPlugins = {}
    slicer.modules.dicomPlugins['DICOMM3DPlugin'] = DICOMM3DPluginClass
