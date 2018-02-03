slicer_add_python_unittest(
  SCRIPT ${MODULE_NAME}Tests.py
  SLICER_ARGS --additional-module-paths
    ${CMAKE_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
    ${DEPENDENCIES_ADDITIONAL_MODULE_PATHS}
  )