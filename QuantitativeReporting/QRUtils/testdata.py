from __future__ import absolute_import
import ctk
import os
import slicer
import qt
import logging
from urllib.request import urlretrieve
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
import six



class TestDataLogic(ScriptedLoadableModuleLogic):

  collections = {
    'MRHead': {
      'volume': ('http://slicer.kitware.com/midas3/download/item/220834/PieperMRHead.zip', 'PieperMRHead.zip')
    },
    'CTLiver': {
      'volume': ('https://github.com/QIICR/QuantitativeReporting/releases/download/test-data/CTLiver.zip', 'CTLiver.zip'),
      'sr': ('https://github.com/QIICR/QuantitativeReporting/releases/download/test-data/SR.zip', 'SR.zip'),
      'seg_dcm': ('https://github.com/QIICR/QuantitativeReporting/releases/download/test-data/Segmentations_DCM.zip',
                  'Liver_Segmentation_DCM.zip'),
      'seg_nrrd': ('https://github.com/QIICR/QuantitativeReporting/releases/download/test-data/Segmentations_NRRD.zip',
                   'Segmentations_NRRD.zip')
    }
  }

  DOWNLOAD_DIRECTORY = os.path.join(slicer.app.temporaryPath, 'QR', 'downloads')

  @staticmethod
  def importIntoDICOMDatabase(dicomFilesDirectory):
    indexer = ctk.ctkDICOMIndexer()
    indexer.addDirectory(slicer.dicomDatabase, dicomFilesDirectory, None)
    indexer.waitForImportFinished()

  @staticmethod
  def unzipSampleData(filePath, collection, kind):
    destinationDirectory = TestDataLogic.getUnzippedDirectoryPath(collection, kind)
    qt.QDir().mkpath(destinationDirectory)
    success = slicer.app.applicationLogic().Unzip(filePath, destinationDirectory)
    if not success:
      logging.error("Archive %s was NOT unzipped successfully." %  filePath)
    return destinationDirectory

  @staticmethod
  def getUnzippedDirectoryPath(collection, kind):
    return os.path.join(TestDataLogic.DOWNLOAD_DIRECTORY, collection, kind)

  @staticmethod
  def downloadAndUnzipSampleData(collection='MRHead'):
    slicer.util.delayDisplay("Downloading", 1000)

    downloaded = {}
    for kind, (url, filename) in six.iteritems(TestDataLogic.collections[collection]):
      filePath = os.path.join(TestDataLogic.DOWNLOAD_DIRECTORY, collection, filename)
      if not os.path.exists(os.path.dirname(filePath)):
        os.makedirs(os.path.dirname(filePath))
      logging.debug('Saving download %s to %s ' % (filename, filePath))
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        slicer.util.delayDisplay('Requesting download %s from %s...\n' % (filename, url), 1000)
        urlretrieve(url, filePath)
      expectedOutput = TestDataLogic.getUnzippedDirectoryPath(collection, kind)
      if not os.path.exists(expectedOutput) or not len(os.listdir(expectedOutput)):
        logging.debug('Unzipping data into %s' % expectedOutput)
        downloaded[kind] = TestDataLogic.unzipSampleData(filePath, collection, kind)
      else:
        downloaded[kind] = expectedOutput

    return downloaded