project(vtkSlicer${MODULE_NAME}ModuleLogic)

set(KIT ${PROJECT_NAME})

set(${KIT}_EXPORT_DIRECTIVE "VTK_SLICER_${MODULE_NAME_UPPER}_MODULE_LOGIC_EXPORT")

set(${KIT}_INCLUDE_DIRECTORIES
  ${DCMTK_INCLUDE}
  ${CMAKE_BINARY_DIR}
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

