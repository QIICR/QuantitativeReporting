#-----------------------------------------------------------------------------
set(MODULE_NAME SEG2NRRD)

#-----------------------------------------------------------------------------
set(MODULE_INCLUDE_DIRECTORIES
  )

set(MODULE_SRCS
  SEG2NRRD.cxx
  framesorter.h
  )

set(MODULE_TARGET_LIBRARIES
  ${ITK_LIBRARIES}
  )

#-----------------------------------------------------------------------------
SEMMacroBuildCLI(
  NAME ${MODULE_NAME}
  TARGET_LIBRARIES ${MODULE_TARGET_LIBRARIES}
  INCLUDE_DIRECTORIES ${MODULE_INCLUDE_DIRECTORIES}
  ADDITIONAL_SRCS ${MODULE_SRCS}
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)
  #add_subdirectory(Testing)
endif()
