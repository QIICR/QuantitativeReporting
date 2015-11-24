SET(KIT_PYTHON_SCRIPTS
  DICOMSegmentationPlugin.py
  )

slicerMacroBuildScriptedModule(
  NAME DICOMSegmentationPlugin
  SCRIPTS "${KIT_PYTHON_SCRIPTS}"
  RESOURCES "${KIT_PYTHON_RESOURCES}"
  )

slicerMacroBuildScriptedModule(
  NAME SEGExporterSelfTest
  SCRIPTS SEGExporterSelfTest.py
  )
