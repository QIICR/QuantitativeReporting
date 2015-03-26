
#
# Install test data
#
message("Module source dir is ${${MODULE_NAME}_SOURCE_DIR}")
set(REPORTING_TEST_DATA_DIR "${${MODULE_NAME}_SOURCE_DIR}/Prototype/TestData")
set(SOURCE_DICOM_DIR ${REPORTING_TEST_DATA_DIR}/DICOM.CT)
set(TEMP_DIR "${CMAKE_BINARY_DIR}/Testing/Temporary")
set(TEMP_DICOM "${TEMP_DIR}/DICOM.CT")
MESSAGE(STATUS "Reporting: copying files from ${SOURCE_DICOM_DIR} to ${TEMP_DICOM}")
configure_file(
  ${SOURCE_DICOM_DIR}/instance_487.dcm
  ${TEMP_DICOM}/instance_487.dcm
  COPYONLY)
configure_file(
  ${SOURCE_DICOM_DIR}/instance_488.dcm
  ${TEMP_DICOM}/instance_488.dcm
  COPYONLY)
configure_file(
  ${SOURCE_DICOM_DIR}/instance_489.dcm
  ${TEMP_DICOM}/instance_489.dcm
  COPYONLY)


slicer_add_python_unittest(
  SCRIPT ReportingRoundTripTest.py
  SLICER_ARGS --disable-cli-modules
              --additional-module-path "${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR}"
  )

slicer_add_python_unittest(
  SCRIPT ReportingSelfTest.py
  SLICER_ARGS --disable-cli-modules
              --additional-module-path "${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR}"
  )

slicerMacroBuildScriptedModule(
  NAME ReportingSelfTest
  SCRIPTS "ReportingSelfTest.py"
  RESOURCES ""
  )

# test the converter script with this DICOM as well as label map volumes
# made from the DICOM volume
set(REPORTING_OUTPUT_SEG_DIR "${TEMP_DIR}/OutputSeg")
message("Using output segmentation dir of ${REPORTING_OUTPUT_SEG_DIR}")
file(MAKE_DIRECTORY ${REPORTING_OUTPUT_SEG_DIR})
message("Copying label volumes from ${REPORTING_TEST_DATA_DIR} to ${TEMP_DIR}")
configure_file(
  ${REPORTING_TEST_DATA_DIR}/labelToSEG.nrrd
  ${TEMP_DIR}/labelToSEG.nrrd
  COPYONLY)
configure_file(
  ${REPORTING_TEST_DATA_DIR}/labelToSEGTransformed.nrrd
  ${TEMP_DIR}/labelToSEGTransformed.nrrd
  COPYONLY)

add_test(
  NAME "py_LabelToDICOMSEGConverterScript_TestLabelVolume"
  COMMAND ${Slicer_LAUNCHER_EXECUTABLE}  --no-main-window
  --additional-module-path ${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR}
  --python-script ${${MODULE_NAME}_SOURCE_DIR}/Util/LabelToDICOMSEGConverterScript.py
  ${TEMP_DICOM} ${TEMP_DIR}/labelToSEG.nrrd ${REPORTING_OUTPUT_SEG_DIR}
  )
# add a test that triggers the resampling of the input label map
# Note: without the --force argument, this test is expected to fail
add_test(
  NAME "py_LabelToDICOMSEGConverterScript_TestTransformedLabelVolume"
  COMMAND ${Slicer_LAUNCHER_EXECUTABLE}  --no-main-window
  --additional-module-path ${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR}
  --python-script ${${MODULE_NAME}_SOURCE_DIR}/Util/LabelToDICOMSEGConverterScript.py
  --force ${TEMP_DICOM} ${TEMP_DIR}/labelToSEGTransformed.nrrd ${REPORTING_OUTPUT_SEG_DIR}
  )

