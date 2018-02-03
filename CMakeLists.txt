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

#find_package(SlicerDevelopmentToolbox REQUIRED)
#find_package(DCMQI REQUIRED)
#find_package(PETDICOMExtension REQUIRED)

set(DEPENDENCY_BUILD_DIRS
  ${SlicerDevelopmentToolbox_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR}
  ${SlicerDevelopmentToolbox_DIR}/${Slicer_CLIMODULES_LIB_DIR}
  ${PETDICOMExtension_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR}
  ${PETDICOMExtension_DIR}/${Slicer_CLIMODULES_LIB_DIR}
  ${DCMQI_DIR}/dcmqi-build/bin
  )

message("DEPENDENCY_BUILD_DIRS: ${DEPENDENCY_BUILD_DIRS}")

set(DEPENDENCIES_ADDITIONAL_MODULE_PATHS
  ${DEPENDENCY_BUILD_DIRS}
  ${SlicerDevelopmentToolbox_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
)

add_subdirectory(DICOMPlugins)
add_subdirectory(QuantitativeReporting)

#-----------------------------------------------------------------------------

if(BUILD_TESTING)
  add_subdirectory(Testing)
endif()

#-----------------------------------------------------------------------------

include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
