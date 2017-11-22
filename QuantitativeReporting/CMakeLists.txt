#-----------------------------------------------------------------------------

set(MODULE_PYTHON_SCRIPTS
  __init__.py
  QRCustomizations/__init__.py
  QRCustomizations/CustomDICOMDetailsWidget.py
  QRCustomizations/CustomSegmentEditor.py
  QRCustomizations/CustomSegmentStatistics.py
  QRUtils/__init__.py
  QRUtils/htmlReport.py
  QRUtils/testdata.py
  ${MODULE_NAME}.py
  )

file(GLOB_RECURSE MODULE_PYTHON_RESOURCES RELATIVE ${CMAKE_CURRENT_SOURCE_DIR}
  ${PROJECT_SOURCE_DIR}/${MODULE_NAME}/Resources/*
)

slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
)

#-----------------------------------------------------------------------------