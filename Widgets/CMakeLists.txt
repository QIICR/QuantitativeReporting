project(qSlicer${qt_module_name}ModuleWidgets)

# from Modules/Annotations/Widgets

#
# See CMake/SlicerMacroBuildModuleWidgets.cmake for details
#

set(module_widgets_name ${PROJECT_NAME})

# The header '${module_widgets_name}Export.h' will be automatically configured.
MESSAGE(STATUS "Relying on auto creation of file ${module_widgets_name}Export.h")
set(module_widgets_export_directive "Q_SLICER_MODULE_REPORTING_WIDGETS_EXPORT")

# Additional directories to include
set(module_widgets_include_directories
  ${CMAKE_CURRENT_SOURCE_DIR}/../MRML
  ${CMAKE_CURRENT_BINARY_DIR}/../MRML
  )
  
# Source files
set(module_widgets_SRCS
  qMRMLAnnotationReportingWidget.cxx
  qMRMLAnnotationReportingWidget.h
 )

# Headers that should run through moc
set(module_widgets_MOC_SRCS
  qMRMLAnnotationReportingWidget.h
  )

# UI files
set(module_widgets_UI_SRCS
  )

# Resources
set(module_widgets_resources
  )

# Additional Target libraries
set(module_widgets_target_libraries
  vtkSlicerReportingModuleMRML
  )

SlicerMacroBuildModuleWidgets(
  NAME ${module_widgets_name}
  EXPORT_DIRECTIVE ${module_widgets_export_directive}
  INCLUDE_DIRECTORIES ${module_widgets_include_directories}
  SRCS ${module_widgets_SRCS}
  MOC_SRCS ${module_widgets_MOC_SRCS}
  UI_SRCS ${module_widgets_UI_SRCS}
  TARGET_LIBRARIES ${module_widgets_target_libraries}
  RESOURCES ${module_widgets_resources}
  WRAP_PYTHONQT
  )

# Qt Designer Plugins
# add_subdirectory(DesignerPlugins)
