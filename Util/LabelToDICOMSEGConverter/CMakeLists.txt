#-----------------------------------------------------------------------------
set(MODULE_NAME LabelToDICOMSEGConverter)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  LabelToDICOMSEGConverter.py
  )

set(MODULE_PYTHON_RESOURCES
  )

#-----------------------------------------------------------------------------
ctkMacroCompilePythonScript(
  TARGET_NAME LabelToDICOMSEGConverter
  SCRIPTS "${MODULE_PYTHON_SCRIPTS}"
  RESOURCES "${MODULE_PYTHON_RESOURCES}"
  DESTINATION_DIR ${CMAKE_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
  INSTALL_DIR ${Slicer_INSTALL_QTSCRIPTEDMODULES_LIB_DIR}
  NO_INSTALL_SUBDIR
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # this will regiester the unittest subclass in the main script
  # as a ctest (note that it is also usable as a runtime test).
  # slicer_add_python_unittest(SCRIPT LabelToDICOMSEGConverter.py)

  # additional build-time testing goes in here
  add_subdirectory(Testing)
endif()
