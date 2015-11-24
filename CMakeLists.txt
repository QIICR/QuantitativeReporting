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
add_subdirectory(Py)
add_subdirectory(SEGSupport)

#-----------------------------------------------------------------------------
if(BUILD_TESTING)
#  add_subdirectory(Testing)
endif()

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
