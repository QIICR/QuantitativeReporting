
SET(KIT_PYTHON_SCRIPTS
  SlicerReportingModuleWidgetHelper.py
  qSlicerReportingModuleWidget.py
  )

SET(KIT_PYTHON_RESOURCES
  )

slicerMacroBuildScriptedModule(
  NAME qSlicerReportingModuleWidget
  SCRIPTS "${KIT_PYTHON_SCRIPTS}"
  RESOURCES "${KIT_PYTHON_RESOURCES}"
  )

SET(KIT_PYTHON_SCRIPTS
  DICOMSegmentationPlugin.py
  )

slicerMacroBuildScriptedModule(
  NAME DICOMSegmentationPlugin
  SCRIPTS "${KIT_PYTHON_SCRIPTS}"
  RESOURCES "${KIT_PYTHON_RESOURCES}"
  )
