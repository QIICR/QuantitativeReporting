cmake_minimum_required(VERSION 3.5.0)

project(QuantitativeReporting)

#-----------------------------------------------------------------------------
set(EXTENSION_HOMEPAGE "http://wiki.slicer.org/slicerWiki/index.php/Documentation/Nightly/Modules/QuantitativeReporting")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Andrey Fedorov (SPL), Christian Herz (SPL), Csaba Pinter (Queen's), Andras Lasso (Queen's), Steve Pieper (SPL)")
set(EXTENSION_DESCRIPTION "Support of quantitative image reporting with DICOM")
set(EXTENSION_ICONURL "https://www.slicer.org/w/images/3/30/QuantitativeReportingLogo.png")
set(EXTENSION_SCREENSHOTURLS "https://www.slicer.org/w/images/f/fe/QuantitativeReporting-screenshot.jpg")
set(EXTENSION_STATUS "Work in progress")
set(EXTENSION_DEPENDS SlicerDevelopmentToolbox DCMQI PETDICOMExtension)

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
set(MODULE_NAME QuantitativeReporting)
set(MODULE_TITLE ${MODULE_NAME})

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  )

slicerMacroBuildScriptedModule(
  NAME  ${MODULE_NAME}
  SCRIPTS  ${MODULE_NAME}.py
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )

string(TOUPPER ${MODULE_NAME} MODULE_NAME_UPPER)

#-----------------------------------------------------------------------------

add_subdirectory(DICOMPlugins)

#-----------------------------------------------------------------------------

if(BUILD_TESTING)
  add_subdirectory(Testing)
endif()

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
