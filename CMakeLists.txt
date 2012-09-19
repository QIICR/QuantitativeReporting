cmake_minimum_required(VERSION 2.8.7)

#-----------------------------------------------------------------------------
set(MODULE_NAME Reporting)
set(MODULE_TITLE ${MODULE_NAME})

string(TOUPPER ${MODULE_NAME} MODULE_NAME_UPPER)

#-----------------------------------------------------------------------------
if(NOT Slicer_SOURCE_DIR)
  set(EXTENSION_NAME Reporting)
  set(EXTENSION_HOMEPAGE "http://wiki.slicer.org/slicerWiki/index.php/Documentation/4.1/Modules/Reporting")
  set(EXTENSION_CATEGORY "Informatics")
  set(EXTENSION_CONTRIBUTORS "Andrey Fedorov (SPL), Nicole Aucoin (SPL), Steve Pieper (SPL)")
  set(EXTENSION_DESCRIPTION "The purpose of the Reporting module is to provide Slicer interface for creating image annotations/markup that are stored in a structured form, and can be exported into Annotation Image Markup (AIM) XML-based format. The documentation is available at this location: http://wiki.slicer.org/slicerWiki/index.php/Documentation/4.1/Extensions/Reporting")
  set(EXTENSION_ICONURL "https://github.com/fedorov/Reporting/raw/master/Resources/Icons/ReportingLogo128px.png")
  set(EXTENSION_SCREENSHOTURLS "https://github.com/fedorov/Reporting/raw/master/Resources/Screenshots/ReportingGUI-prostate.png https://github.com/fedorov/Reporting/raw/master/Resources/Screenshots/ReportingGUI-LUT.png https://github.com/fedorov/Reporting/raw/master/Resources/Screenshots/ReportingGUI-TreeWidgetMenu.png")
  set(EXTENSION_STATUS "Work in progress")
  find_package(Slicer REQUIRED)
  include(${Slicer_USE_FILE})

  set(MODULE_NAME ${EXTENSION_NAME})
endif()

set(CMAKE_MODULE_PATH
  ${CMAKE_CURRENT_SOURCE_DIR}/CMake
  ${CMAKE_MODULE_PATH}
)

include(SlicerMacroExtractRepositoryInfo)
set(MODULE_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR})
set(MODULE_BINARY_DIR ${CMAKE_CURRENT_BINARY_DIR})

message("Module source dir in main cmake is ${MODULE_SOURCE_DIR}")


SlicerMacroExtractRepositoryInfo(VAR_PREFIX Reporting)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/CMake/vtkReportingVersionConfigure.h.in
  ${CMAKE_CURRENT_BINARY_DIR}/vtkReportingVersionConfigure.h)

#-----------------------------------------------------------------------------
add_subdirectory(MRML)
add_subdirectory(Widgets)
add_subdirectory(Logic)
add_subdirectory(Py)

set(MODULE_EXPORT_DIRECTIVE "Q_SLICER_QTMODULE_${MODULE_NAME_UPPER}_EXPORT")

#-----------------------------------------------------------------------------
set(MODULE_EXPORT_DIRECTIVE "Q_SLICER_QTMODULES_${MODULE_NAME_UPPER}_EXPORT")

set(MODULE_INCLUDE_DIRECTORIES
  ${CMAKE_CURRENT_SOURCE_DIR}/Logic
  ${CMAKE_CURRENT_BINARY_DIR}/Logic
  ${CMAKE_CURRENT_SOURCE_DIR}/MRML
  ${CMAKE_CURRENT_BINARY_DIR}/MRML
  ${CMAKE_CURRENT_SOURCE_DIR}/Widgets
  ${CMAKE_CURRENT_BINARY_DIR}/Widgets
  )

set(MODULE_SRCS
  qSlicerReportingIO.cxx
  qSlicerReportingIO.h
  qSlicerReportingModule.cxx
  qSlicerReportingModule.h
  )

set(MODULE_MOC_SRCS
  qSlicerReportingIO.h
  qSlicerReportingModule.h
  )

set(MODULE_UI_SRCS
  )

set(MODULE_TARGET_LIBRARIES
  vtkSlicerReportingModuleLogic
  )

set(MODULE_RESOURCES
  Resources/qSlicerReportingModule.qrc
  )


#-----------------------------------------------------------------------------
slicerMacroBuildQtModule(
  NAME ${MODULE_NAME}
  EXPORT_DIRECTIVE ${MODULE_EXPORT_DIRECTIVE}
  INCLUDE_DIRECTORIES ${MODULE_INCLUDE_DIRECTORIES}
  SRCS ${MODULE_SRCS}
  MOC_SRCS ${MODULE_MOC_SRCS}
  UI_SRCS ${MODULE_UI_SRCS}
  TARGET_LIBRARIES ${MODULE_TARGET_LIBRARIES}
  RESOURCES ${MODULE_RESOURCES}
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)
  add_subdirectory(Testing)
endif()

# add_subdirectory(Prototype)

#-----------------------------------------------------------------------------
if(NOT Slicer_SOURCE_DIR)
  include(${Slicer_EXTENSION_CPACK})
endif()

