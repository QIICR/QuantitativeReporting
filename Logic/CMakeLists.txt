project(vtkSlicer${MODULE_NAME}ModuleLogic)

set(KIT ${PROJECT_NAME})

set(${KIT}_EXPORT_DIRECTIVE "VTK_SLICER_${MODULE_NAME_UPPER}_MODULE_LOGIC_EXPORT")

set(${KIT}_INCLUDE_DIRECTORIES
  ${DCMTK_INCLUDE}
  ${CMAKE_BINARY_DIR}
  ${MODULE_BINARY_DIR}
  )

set(${KIT}_SRCS
  vtkSlicerReportingModuleLogic.cxx
  vtkSlicerReportingModuleLogic.h
  )

set(${KIT}_TARGET_LIBRARIES
  vtkSlicerAnnotationsModuleMRML
  vtkSlicerReportingModuleMRML
  ${DCMTK_LIBRARIES}
  )

#-----------------------------------------------------------------------------
SlicerMacroBuildModuleLogic(
  NAME ${KIT}
  EXPORT_DIRECTIVE ${${KIT}_EXPORT_DIRECTIVE}
  INCLUDE_DIRECTORIES ${${KIT}_INCLUDE_DIRECTORIES}
  SRCS ${${KIT}_SRCS}
  TARGET_LIBRARIES ${${KIT}_TARGET_LIBRARIES}
  )

file(GLOB TMFILES RELATIVE ${CMAKE_CURRENT_SOURCE_DIR}../Resources "StandardTerminology/*csv")

foreach(TMFILE ${TMFILES})
  configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/../Resources/${TMFILE}
    ${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_SHARE_DIR}/${MODULE_NAME}/${TMFILE}
    COPYONLY)
  install(
    FILES ${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_SHARE_DIR}/${MODULE_NAME}/${TMFILE}
    DESTINATION ${Slicer_INSTALL_QTLOADABLEMODULES_SHARE_DIR}/${MODULE_NAME} COMPONENT Runtime)
endforeach()
