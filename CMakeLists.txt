#-----------------------------------------------------------------------------
cmake_minimum_required(VERSION 2.8.8)
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# See http://cmake.org/cmake/help/cmake-2-8-docs.html#section_Policies for details
#-----------------------------------------------------------------------------
if(POLICY CMP0017)
  cmake_policy(SET CMP0017 OLD)
endif()

#-----------------------------------------------------------------------------
# Module name
#   - Usually identique to the directory name)
#   - You shouldn't call 'project(...)'. See SlicerConfig.cmake for more details.
#-----------------------------------------------------------------------------
set(MODULE_NAME Reporting)
set(MODULE_TITLE ${MODULE_NAME})

string(TOUPPER ${MODULE_NAME} MODULE_NAME_UPPER)

#-----------------------------------------------------------------------------
#set(MODULE_HOMEPAGE "http://www.slicer.org/slicerWiki/index.php/Documentation/4.1/Extensions/Reporting")
#set(MODULE_CATEGORY "Informatics")
#set(MODULE_CONTRIBUTORS "Andrey Fedorov (SPL)")
#set(MODULE_DESCRIPTION "This is an example of extension bundling a CLI, a loadable and a scripted module")
#set(MODULE_ICONURL "http://viewvc.slicer.org/viewvc.cgi/Slicer4/trunk/Extensions/Testing/LoadableExtensionTemplate/Resources/Icons/LoadableExtensionTemplate.png?revision=19437&view=co")

#-----------------------------------------------------------------------------
# Prerequisites
#-----------------------------------------------------------------------------
if(NOT Slicer_SOURCE_DIR)
  set(MODULE_HOMEPAGE "http://www.slicer.org/slicerWiki/index.php/Slicer4:Developers:Projects:QtSlicer/Tutorials/ExtensionWriting")
  set(MODULE_CATEGORY "Informatics")
  set(MODULE_CONTRIBUTORS "Andrey Fedorov")
  set(MODULE_DESCRIPTION "Reporting Module")
  #  set(MODULE_DEPENDS NA) # Specified as a space separated list or 'NA' if any
  set(MODULE_ICONURL "http://viewvc.slicer.org/viewvc.cgi/Slicer4/trunk/Extensions/Testing/LoadableExtensionTemplate/Resources/Icons/LoadableExtensionTemplate.png?revision=19437&view=co")

  set(MODULE_SCREENSHOTURLS "http://google.com")
  set(MODULE_STATUS "work in progress")
  
  find_package(Slicer REQUIRED)
  include(${Slicer_USE_FILE})

endif()

# Include SQL not included by default
include(SlicerBlockFindQtAndCheckVersion)

# Add subdirectories
add_subdirectory(MRML)
add_subdirectory(Widgets)
add_subdirectory(Logic)
add_subdirectory(Py)

set(MODULE_EXPORT_DIRECTIVE "Q_SLICER_QTMODULE_${MODULE_NAME_UPPER}_EXPORT")

#-----------------------------------------------------------------------------
# Sources
#-----------------------------------------------------------------------------
set(qt_module_export_directive "Q_SLICER_QTMODULES_REPORTING_EXPORT")

# Additional includes - Current_{source,binary} and Slicer_{Libs,Base} already included
set(qt_module_include_directories
  ${CMAKE_CURRENT_SOURCE_DIR}/Logic
  ${CMAKE_CURRENT_BINARY_DIR}/Logic
  ${CMAKE_CURRENT_SOURCE_DIR}/MRML
  ${CMAKE_CURRENT_BINARY_DIR}/MRML
  ${CMAKE_CURRENT_SOURCE_DIR}/Widgets
  ${CMAKE_CURRENT_BINARY_DIR}/Widgets
  )

# Source files
set(qt_module_SRCS
  qSlicerReportingModule.cxx
  qSlicerReportingModule.h
  qSlicerReportingModuleWidget.cxx
  qSlicerReportingModuleWidget.h
  )

# Headers that should run through moc
set(qt_module_MOC_SRCS
  qSlicerReportingModule.h
  qSlicerReportingModuleWidget.h
  )

# UI files
set(qt_module_UI_SRCS
  Resources/UI/qSlicerReportingModule.ui
)

# Additional Target libraries
set(qt_module_target_libraries
  vtkSlicerReportingModuleLogic
  )

# Resources
set(qt_module_resources
  Resources/qSlicerReportingModule.qrc
)


#-----------------------------------------------------------------------------
# Build
#-----------------------------------------------------------------------------
slicerMacroBuildQtModule(
  NAME ${EXTENSION_NAME}
  EXPORT_DIRECTIVE ${MODULE_EXPORT_DIRECTIVE}
  INCLUDE_DIRECTORIES ${qt_module_include_directories}
  SRCS ${qt_module_SRCS}
  MOC_SRCS ${qt_module_MOC_SRCS}
  UI_SRCS ${qt_module_UI_SRCS}
  TARGET_LIBRARIES ${qt_module_target_libraries}
  RESOURCES ${qt_module_resources}
  )

#-----------------------------------------------------------------------------
# Testing
#-----------------------------------------------------------------------------
if(BUILD_TESTING)
  add_subdirectory(Testing)
endif()

#-----------------------------------------------------------------------------
# Packaging
#-----------------------------------------------------------------------------
if(NOT Slicer_SOURCE_DIR)
  include(${Slicer_EXTENSION_CPACK})
endif()
