project(qSlicer${MODULE_NAME}ModuleWidgets)

set(KIT ${PROJECT_NAME})

set(${KIT}_EXPORT_DIRECTIVE "Q_SLICER_${MODULE_NAME_UPPER}_MODULE_WIDGETS_EXPORT")

# Additional directories to include
set(${KIT}_INCLUDE_DIRECTORIES
  ${CMAKE_CURRENT_SOURCE_DIR}/../MRML
  ${CMAKE_CURRENT_BINARY_DIR}/../MRML
  )
  
# Source files
set(${KIT}_SRCS
  qMRMLReportingTreeView.cxx
  qMRMLReportingTreeView.h
  qMRMLReportingTreeView_p.h
  qMRMLSceneDisplayableHierarchyModel.cxx
  qMRMLSceneDisplayableHierarchyModel.h
  qMRMLSortFilterDisplayableHierarchyProxyModel.cxx
  qMRMLSortFilterDisplayableHierarchyProxyModel.h
 )

# Headers that should run through moc
set(${KIT}_MOC_SRCS
  qMRMLReportingTreeView.h
  qMRMLSceneDisplayableHierarchyModel.h
  qMRMLSortFilterDisplayableHierarchyProxyModel.h
  )

# UI files
set(${KIT}_UI_SRCS
  )

# Resources
set(${KIT}_RESOURCES
  )

# Additional Target libraries
set(${KIT}_TARGET_LIBRARIES
  vtkSlicerReportingModuleMRML
  vtkSlicerAnnotationsModuleMRML
  )

SlicerMacroBuildModuleWidgets(
  NAME ${KIT}
  EXPORT_DIRECTIVE ${${KIT}_EXPORT_DIRECTIVE}
  INCLUDE_DIRECTORIES ${${KIT}_INCLUDE_DIRECTORIES}
  SRCS ${${KIT}_SRCS}
  MOC_SRCS ${${KIT}_MOC_SRCS}
  UI_SRCS ${${KIT}_UI_SRCS}
  TARGET_LIBRARIES ${${KIT}_TARGET_LIBRARIES}
  RESOURCES ${${KIT}_RESOURCES}
  WRAP_PYTHONQT
  )
