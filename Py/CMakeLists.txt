
SET(KIT_PYTHON_SCRIPTS
  SlicerReportingModuleWidgetHelper.py
  qSlicerReportingModuleWidget.py
  )

SET(KIT_PYTHON_RESOURCES
  )

ctkMacroCompilePythonScript(
  TARGET_NAME qSlicerReportingModuleWidget
  SCRIPTS "${KIT_PYTHON_SCRIPTS}"
  RESOURCES "${KIT_PYTHON_RESOURCES}"
  DESTINATION_DIR ${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_PYTHON_LIB_DIR}
  INSTALL_DIR ${Slicer_INSTALL_QTLOADABLEMODULES_PYTHON_LIB_DIR}
  NO_INSTALL_SUBDIR
  )

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
