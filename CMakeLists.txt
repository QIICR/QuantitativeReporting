cmake_minimum_required(VERSION 3.5.0)

#-----------------------------------------------------------------------------
set(EXTENSION_NAME QuantitativeReporting)
set(EXTENSION_HOMEPAGE "https://qiicr.gitbooks.io/quantitativereporting-guide")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Christian Herz (SPL), Andrey Fedorov (SPL, BWH), Csaba Pinter (Queen`s), Andras Lasso (Queen`s), Steve Pieper (Isomics)")
set(EXTENSION_DESCRIPTION "Segmentation-based measurements with DICOM-based import and export of the results.")
set(EXTENSION_ICONURL "https://github.com/QIICR/QuantitativeReporting/raw/master/QuantitativeReporting/Resources/Icons/ReportingLogo128px.png")
set(EXTENSION_SCREENSHOTURLS "https://github.com/QIICR/QuantitativeReporting/raw/master/QuantitativeReporting/Resources/Screenshots/QuantitativeReporting-screenshot.jpg")
set(EXTENSION_STATUS "Work in progress")
set(EXTENSION_DEPENDS SlicerDevelopmentToolbox DCMQI PETDICOMExtension)

#-----------------------------------------------------------------------------

set(MODULE_NAME QuantitativeReporting)

find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

set(DEPENDENCIES_ADDITIONAL_MODULE_PATHS)

if(NOT Slicer_SOURCE_DIR)
  find_package(SlicerDevelopmentToolbox REQUIRED)
  find_package(DCMQI REQUIRED)
  find_package(PETDICOMExtension REQUIRED)

  list(APPEND DEPENDENCIES_ADDITIONAL_MODULE_PATHS
    ${SlicerDevelopmentToolbox_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
    ${SlicerDevelopmentToolbox_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR}
    ${SlicerDevelopmentToolbox_DIR}/${Slicer_CLIMODULES_LIB_DIR}
    ${PETDICOMExtension_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
    ${PETDICOMExtension_DIR}/${Slicer_CLIMODULES_LIB_DIR}
    ${DCMQI_DIR}/bin
    )
endif()

add_subdirectory(DICOMPlugins)
add_subdirectory(QuantitativeReporting)

#-----------------------------------------------------------------------------

if(BUILD_TESTING)
  add_subdirectory(Testing)
endif()

#-----------------------------------------------------------------------------

include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
