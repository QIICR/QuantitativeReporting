#-----------------------------------------------------------------------------

file(GLOB_RECURSE MODULE_PYTHON_SCRIPTS RELATIVE ${CMAKE_CURRENT_SOURCE_DIR}
  *.py
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