slicerMacroBuildScriptedModule(
  NAME DICOMSegmentationPlugin
  SCRIPTS DICOMPluginBase.py,DICOMSegmentationPlugin.py
  )

slicerMacroBuildScriptedModule(
  NAME DICOMParametricMapPlugin
  SCRIPTS DICOMPluginBase.py,DICOMParametricMapPlugin.py
  )

slicerMacroBuildScriptedModule(
  NAME DICOMTID1500Plugin
  SCRIPTS DICOMPluginBase.py,DICOMTID1500Plugin.py
  )

slicerMacroBuildScriptedModule(
  NAME SEGExporterSelfTest
  SCRIPTS SEGExporterSelfTest.py
  )

slicerMacroBuildScriptedModule(
  NAME QuantitativeReporting
  SCRIPTS QuantitativeReporting.py
  )
