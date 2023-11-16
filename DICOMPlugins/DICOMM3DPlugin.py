from __future__ import absolute_import
import glob
import os
import json
import vtk
import io
import shutil
import vtkSegmentationCorePython as vtkSegmentationCore
import logging
import pydicom

from base.DICOMPluginBase import DICOMPluginBase

import slicer
from DICOMLib import DICOMLoadable

from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS
from six.moves import range


#
# This is the plugin to handle translation of DICOM M3D objects
# M3D stands for Model for 3D Manufacturing.
# DICOM M3D objects can be for example .STL files encoded into DICOM M3D.
#
class DICOMM3DPluginClass(DICOMPluginBase):

  def __init__(self):
    super(DICOMM3DPluginClass,self).__init__()
    self.loadType = "DICOMM3D"

  def examineFiles(self,files):
    """ Returns a list of DICOMLoadable instances
    corresponding to ways of interpreting the
    files parameter.
    """
    loadables = []

    for candidateFile in files:

      uid = slicer.dicomDatabase.fileValue(candidateFile, self.tags['instanceUID'])
      if uid == '':
        return []

      desc = slicer.dicomDatabase.fileValue(candidateFile, self.tags['seriesDescription'])
      if desc == '':
        desc = "Unknown"

      #read EncapsulatedDocument for candidateFile
      docFile = self.getEncapsulatedDocument(candidateFile)

      #read EncapsulatedDocumentLength for candidateFile
      docLengthFile = self.getEncapsulatedDocumentLength(candidateFile)

      #read modality type to flag M3D object.
      isDicomM3D = (slicer.dicomDatabase.fileValue(candidateFile, self.tags['modality']) == 'M3D')

      if isDicomM3D:
        loadable = DICOMLoadable()
        loadable.files = [candidateFile]
        loadable.name = desc
        loadable.tooltip = loadable.name + ' - as a DICOM M3D object'
        loadable.selected = True
        loadable.confidence = 0.95
        loadable.uid = uid
        loadable.doc = docFile
        loadable.docLength = docLengthFile
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

  def getEncapsulatedDocument(self, candidateFile):
    dcm = pydicom.read_file(candidateFile)
    if hasattr(dcm, "EncapsulatedDocument"):
      return dcm.EncapsulatedDocument
    else:
      return b''
    
  def getEncapsulatedDocumentLength(self, candidateFile):
    dcm = pydicom.read_file(candidateFile)
    if hasattr(dcm, "EncapsulatedDocumentLength"):
      return dcm.EncapsulatedDocumentLength
    else:
      return 0

  def load(self,loadable):
    """ Load the DICOM M3D object
    """
    logging.debug('DICOM M3D load()')
    try:
      uid = loadable.uid
      logging.debug('in load(): uid = '+uid)
    except AttributeError:
      return False

    self.tempDir = slicer.util.tempDirectory()
    print(self.tempDir)
    try:
        os.makedirs(self.tempDir)
    except OSError:
      pass
    
    stlFileName = slicer.dicomDatabase.fileForInstance(uid)
    if stlFileName is None:
      logging.error('Failed to get the filename from the DICOM database for ' + uid)
      self.cleanup()
      return False
    
    read_buffer = io.BytesIO(loadable.doc)
    buffer_view = read_buffer.getbuffer()
    if (int(loadable.docLength) % 2) != 0:
      buffer_view = buffer_view[0:(read_buffer.getbuffer().nbytes -1)]
    
    stlFilePath = os.path.join(self.tempDir, "temp.STL")
    
    with open(stlFilePath, 'wb') as file: 
      shutil.copyfileobj(read_buffer, file)
    assert os.path.exists(stlFilePath)
    file.close()

    self._createModelNode(loadable, stlFilePath)
    
    self.cleanup()
    
    return True

  def _createModelNode(self, loadable, stlFilePath):
    modelNode = slicer.util.loadModel(stlFilePath)
    modelNode.SetName(loadable.name)
   
    modelDisplayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode")
    modelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
    self.addSeriesInSubjectHierarchy(loadable, modelNode)

class DICOMM3DPlugin:
  """
  This class is the 'hook' for slicer to detect and recognize the plugin
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "DICOM M3D Object Import Plugin"
    parent.categories = ["Developer Tools.DICOM Plugins"]
    parent.contributors = ["Cosmin Ciausu, BWH"]
    parent.helpText = """
    Plugin to the DICOM Module to parse and load DICOM M3D modality.
    No module interface here, only in the DICOM module
    """
    parent.dependencies = ['DICOM', 'Colors', 'SlicerDevelopmentToolbox']
    parent.acknowledgementText = """
    This DICOM Plugin was developed by
    Cosmin Ciausu, BWH.
    """

    # Add this extension to the DICOM module's list for discovery when the module
    # is created.  Since this module may be discovered before DICOM itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.dicomPlugins
    except AttributeError:
      slicer.modules.dicomPlugins = {}
    slicer.modules.dicomPlugins['DICOMM3DPlugin'] = DICOMM3DPluginClass
