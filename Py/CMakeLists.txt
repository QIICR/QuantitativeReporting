set(MODULE_PYTHON_SCRIPTS
  base/__init__.py
  base/DICOMPluginBase.py
)

slicerMacroBuildScriptedModule(
  NAME DICOMSegmentationPlugin
  SCRIPTS ${MODULE_PYTHON_SCRIPTS} DICOMSegmentationPlugin.py
  )

slicerMacroBuildScriptedModule(
  NAME DICOMParametricMapPlugin
  SCRIPTS ${MODULE_PYTHON_SCRIPTS} DICOMParametricMapPlugin.py
  )

slicerMacroBuildScriptedModule(
  NAME DICOMTID1500Plugin
  SCRIPTS ${MODULE_PYTHON_SCRIPTS} DICOMTID1500Plugin.py
  )

slicerMacroBuildScriptedModule(
  NAME SEGExporterSelfTest
  SCRIPTS SEGExporterSelfTest.py
  )

slicerMacroBuildScriptedModule(
  NAME QuantitativeReporting
  SCRIPTS QuantitativeReporting.py
  )
