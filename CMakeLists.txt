cmake_minimum_required(VERSION 2.8.9)

project(Reporting)

#-----------------------------------------------------------------------------
set(EXTENSION_HOMEPAGE "http://wiki.slicer.org/slicerWiki/index.php/Documentation/4.2/Modules/Reporting")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Andrey Fedorov (SPL), Nicole Aucoin (SPL), Steve Pieper (SPL)")
set(EXTENSION_DESCRIPTION "The purpose of the Reporting module is to provide Slicer interface for creating image annotations/markup that are stored in a structured form, and can be exported into Annotation Image Markup (AIM) XML-based format. The documentation is available at this location: http://wiki.slicer.org/slicerWiki/index.php/Documentation/4.2/Extensions/Reporting")
set(EXTENSION_ICONURL "http://wiki.slicer.org/slicerWiki/images/3/31/ReportingLogo.png")
set(EXTENSION_SCREENSHOTURLS "http://wiki.slicer.org/slicerWiki/images/d/d6/Reporting-Prostate.png")
set(EXTENSION_STATUS "Work in progress")

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
set(MODULE_NAME Reporting)
set(MODULE_TITLE ${MODULE_NAME})

string(TOUPPER ${MODULE_NAME} MODULE_NAME_UPPER)

#-----------------------------------------------------------------------------
SlicerMacroExtractRepositoryInfo(VAR_PREFIX ${MODULE_NAME})
configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/CMake/vtk${MODULE_NAME}VersionConfigure.h.in
  ${CMAKE_CURRENT_BINARY_DIR}/vtk${MODULE_NAME}VersionConfigure.h
  )

#-----------------------------------------------------------------------------
add_subdirectory(MRML)
add_subdirectory(Logic)
add_subdirectory(Py)
add_subdirectory(SEGSupport)

#-----------------------------------------------------------------------------
set(MODULE_EXPORT_DIRECTIVE "Q_SLICER_QTMODULES_${MODULE_NAME_UPPER}_EXPORT")

set(MODULE_INCLUDE_DIRECTORIES
  ${CMAKE_CURRENT_SOURCE_DIR}/Logic
  ${CMAKE_CURRENT_BINARY_DIR}/Logic
  ${CMAKE_CURRENT_SOURCE_DIR}/MRML
  ${CMAKE_CURRENT_BINARY_DIR}/MRML
  )

set(MODULE_SRCS
  qSlicer${MODULE_NAME}IO.cxx
  qSlicer${MODULE_NAME}IO.h
  qSlicer${MODULE_NAME}Module.cxx
  qSlicer${MODULE_NAME}Module.h
  )

set(MODULE_MOC_SRCS
  qSlicer${MODULE_NAME}IO.h
  qSlicer${MODULE_NAME}Module.h
  )

set(MODULE_UI_SRCS
  )

set(MODULE_TARGET_LIBRARIES
  vtkSlicer${MODULE_NAME}ModuleLogic
  )

set(MODULE_RESOURCES
  Resources/qSlicer${MODULE_NAME}Module.qrc
  )

#-----------------------------------------------------------------------------
slicerMacroBuildLoadableModule(
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
add_subdirectory(Util/LabelToDICOMSEGConverter)

#-----------------------------------------------------------------------------
# Configure terminology dictionaries
file(GLOB TMFILES RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} "Resources/StandardTerminology/*csv")
message("Globbed files: ${TMFILES}")

foreach(TMFILE ${TMFILES})
  configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/${TMFILE}
    ${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_SHARE_DIR}/${MODULE_NAME}/${TMFILE}
    COPYONLY)
  install(
    FILES ${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_SHARE_DIR}/${MODULE_NAME}/${TMFILE}
    DESTINATION ${Slicer_INSTALL_QTLOADABLEMODULES_SHARE_DIR}/${MODULE_NAME}/Resources/StandardTerminology COMPONENT Runtime)
endforeach()

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
