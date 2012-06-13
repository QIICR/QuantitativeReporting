set(KIT Reporting)

add_executable(DICOMReadWriteTest DICOMReadWriteTest.cxx)
target_link_libraries(DICOMReadWriteTest ${lib_name})

add_executable(AddDICOMSEGToSceneTest AddDICOMSEGToSceneTest.cxx)
target_link_libraries(AddDICOMSEGToSceneTest ${lib_name})
