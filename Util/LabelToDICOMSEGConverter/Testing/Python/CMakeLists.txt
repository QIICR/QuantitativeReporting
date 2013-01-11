
#-----------------------------------------------------------------------------
set(KIT_UNITTEST_SCRIPTS)
SlicerMacroConfigureGenericPythonModuleTests("${EXTENSION_NAME}" KIT_UNITTEST_SCRIPTS)

#-----------------------------------------------------------------------------
#foreach(script_name ${KIT_UNITTEST_SCRIPTS})
#  slicer_add_python_unittest(
#    SCRIPT ${script_name}
#    SLICER_ARGS --no-main-window --disable-cli-modules --disable-loadable-modules
#                --additional-module-path ${CMAKE_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
#    TESTNAME_PREFIX nomainwindow_
#    )
#endforeach()

slicer_add_python_unittest(
  SCRIPT LabelToDICOMSEGConverterSelfTest.py
  SLICER_ARGS
    --additional-module-paths ${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR} ${CMAKE_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
  )


ctkMacroCompilePythonScript(
  TARGET_NAME LabelToDICOMSEGConverterSelfTest
  SCRIPTS "LabelToDICOMSEGConverterSelfTest.py"
  RESOURCES ""
  DESTINATION_DIR ${CMAKE_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
  INSTALL_DIR ${Slicer_INSTALL_QTSCRIPTEDMODULES_LIB_DIR}
  NO_INSTALL_SUBDIR
  )

