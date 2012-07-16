set(KIT Reporting)

add_executable(WriteDICOMSEG WriteDICOMSEG.cxx)
target_link_libraries(WriteDICOMSEG ${lib_name})

add_executable(ReadDICOMSEG ReadDICOMSEG.cxx)
target_link_libraries(ReadDICOMSEG ${lib_name})
