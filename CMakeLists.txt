cmake_minimum_required(VERSION 3.5.0)

#-----------------------------------------------------------------------------
set(EXTENSION_NAME QuantitativeReporting)
set(EXTENSION_HOMEPAGE "https://qiicr.gitbooks.io/quantitativereporting-guide")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Andrey Fedorov (SPL), Christian Herz (SPL), Csaba Pinter (Queen's), Andras Lasso (Queen's), Steve Pieper (SPL)")
set(EXTENSION_DESCRIPTION "Support of quantitative image reporting with DICOM")
set(EXTENSION_ICONURL "https://www.slicer.org/w/images/3/30/QuantitativeReportingLogo.png")
set(EXTENSION_SCREENSHOTURLS "https://www.slicer.org/w/images/f/fe/QuantitativeReporting-screenshot.jpg")
set(EXTENSION_STATUS "Work in progress")
set(EXTENSION_DEPENDS SlicerDevelopmentToolbox DCMQI PETDICOMExtension)

#-----------------------------------------------------------------------------

set(MODULE_NAME QuantitativeReporting)

find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

add_subdirectory(DICOMPlugins)
add_subdirectory(QuantitativeReporting)

#-----------------------------------------------------------------------------

if(BUILD_TESTING)
  add_subdirectory(Testing)
endif()

#-----------------------------------------------------------------------------

include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
