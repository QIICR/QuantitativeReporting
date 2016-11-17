cmake_minimum_required(VERSION 3.5.0)

project(Reporting)

#-----------------------------------------------------------------------------
set(EXTENSION_HOMEPAGE "http://wiki.slicer.org/slicerWiki/index.php/Documentation/Nightly/Modules/Reporting")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Andrey Fedorov (SPL), Christian Herz (SPL), Nicole Aucoin (SPL), Steve Pieper (SPL)")
set(EXTENSION_DESCRIPTION "Support of quantitative image reporting with DICOM")
set(EXTENSION_ICONURL "http://wiki.slicer.org/slicerWiki/images/3/31/ReportingLogo.png")
set(EXTENSION_SCREENSHOTURLS "http://wiki.slicer.org/slicerWiki/images/d/d6/Reporting-Prostate.png")
set(EXTENSION_STATUS "Work in progress")
set(EXTENSION_DEPENDS "SlicerProstate DCMQI")

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

#-----------------------------------------------------------------------------
if(BUILD_TESTING)
#  add_subdirectory(Testing)
endif()

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
