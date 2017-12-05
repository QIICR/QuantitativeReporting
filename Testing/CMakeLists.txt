slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}Tests
  SCRIPTS ${MODULE_NAME}Tests
)

slicer_add_python_unittest(SCRIPT ${MODULE_NAME}Tests.py)