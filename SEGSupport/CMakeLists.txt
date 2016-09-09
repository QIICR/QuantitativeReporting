#-----------------------------------------------------------------------------
# Not used
set(MODULE_NAME SEGSupport)

#-----------------------------------------------------------------------------
set(MODULE_INCLUDE_DIRECTORIES
  ${CMAKE_CURRENT_BINARY_DIR}/..
  )

#-----------------------------------------------------------------------------
set(MODULE_TARGET_LIBRARIES
  ${DCMTK_LIBRARIES}
  ${ITK_LIBRARIES}
)

#-----------------------------------------------------------------------------
SEMMacroBuildCLI(
  NAME EncodeSEG
  INCLUDE_DIRECTORIES ${MODULE_INCLUDE_DIRECTORIES}
  TARGET_LIBRARIES ${MODULE_TARGET_LIBRARIES}
)

#-----------------------------------------------------------------------------
SEMMacroBuildCLI(
  NAME SEG2NRRD
  INCLUDE_DIRECTORIES ${MODULE_INCLUDE_DIRECTORIES}
  TARGET_LIBRARIES ${MODULE_TARGET_LIBRARIES}
)

#-----------------------------------------------------------------------------
#SEMMacroBuildCLI(
#  NAME DumpSEGFrame
#  INCLUDE_DIRECTORIES ${MODULE_INCLUDE_DIRECTORIES}
#  TARGET_LIBRARIES ${MODULE_TARGET_LIBRARIES}
#)
