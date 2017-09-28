slicer_add_python_unittest(SCRIPT ${MODULE_NAME}Tests.py)

ctkMacroCompilePythonScript(
  TARGET_NAME ApplicationSelfTests
  SCRIPTS "${MODULE_NAME}Tests.py"
  DESTINATION_DIR ${Slicer_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
  INSTALL_DIR ${Slicer_INSTALL_QTSCRIPTEDMODULES_LIB_DIR}
  NO_INSTALL_SUBDIR
)