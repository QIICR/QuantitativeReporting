project(qMRMLReportingWidgets)

set(MRMLWidgets_SRCS
  qMRMLAnnotationReportingWidget.cxx
  qMRMLAnnotationReportingWidget.h
  )

#set(MRMLWidgets_MOC_SRCS
#  qMRMLAnnotationReportingWidget.cxx
#  qMRMLAnnotationReportingWidget.h
#  )

QT4_WRAP_CPP(MRMLWidgets_MOC_CXX ${MRMLWidgets_MOC_SRCS})
QT4_WRAP_UI(MRMLWidgets_UI_CXX ${MRMLWidgets_UI_SRCS})
QT4_ADD_RESOURCES(MRMLWidgets_QRC_CXX ${MRMLWidgets_QRC_SRCS})

source_group("Resources" FILES
  )

source_group("Generated" FILES
  ${MRMLWidgets_MOC_CXX}
  ${MRMLWidgets_UI_CXX}
  ${MRMLWidgets_QRC_CXX}
  )

# --------------------------------------------------------------------------
# Include dirs
# --------------------------------------------------------------------------
set(include_dirs
  ${CMAKE_CURRENT_SOURCE_DIR}
  ${CMAKE_CURRENT_BINARY_DIR}
  ${MRMLCore_INCLUDE_DIRS}
  ${MRMLLogic_INCLUDE_DIRS}
  ${MRMLDisplayableManager_INCLUDE_DIRS}
  # FIXME: this will cause problems for an extension!
  ${Slicer_SOURCE_DIR}/Libs/MRML/Widgets
  ${Slicer_BINARY_DIR}/Libs/MRML/Widgets
  )
include_directories(${include_dirs})

# --------------------------------------------------------------------------
# Install headers
# --------------------------------------------------------------------------
if(NOT DEFINED ${PROJECT_NAME}_INSTALL_NO_DEVELOPMENT)
  set(${PROJECT_NAME}_INSTALL_NO_DEVELOPMENT ON)
endif()
if(NOT ${PROJECT_NAME}_INSTALL_NO_DEVELOPMENT)
  file(GLOB headers "${CMAKE_CURRENT_SOURCE_DIR}/*.h")
  install(
    FILES ${headers}
    DESTINATION include/${PROJECT_NAME} COMPONENT Development)
endif()

# --------------------------------------------------------------------------
# Build library
# --------------------------------------------------------------------------
set(lib_name ${PROJECT_NAME})
set(targets_to_export ${lib_name})

add_library(${lib_name}
  ${MRMLWidgets_SRCS}
  ${MRMLWidgets_MOC_CXX}
  ${MRMLWidgets_UI_CXX}
  ${MRMLWidgets_QRC_CXX}
  )

set(MRMLWidgets_LIBRARIES
  ${QT_LIBRARIES}
  ${CTK_LIBRARIES}
  ${CTK_EXTERNAL_LIBRARIES}
  MRMLLogic
  )

target_link_libraries(${lib_name} ${MRMLWidgets_LIBRARIES})

# Apply user-defined properties to the library target.
if(Slicer_LIBRARY_PROPERTIES)
  set_target_properties(${lib_name} PROPERTIES ${Slicer_LIBRARY_PROPERTIES})
endif()


# --------------------------------------------------------------------------
# PythonQt wrapping
# --------------------------------------------------------------------------
if(MRMLWidgets_WRAP_PYTHON)
  ctkMacroBuildLibWrapper(
    NAMESPACE "org.slicer.libs"
    TARGET ${lib_name}
    SRCS "${MRMLWidgets_SRCS}"
    INSTALL_BIN_DIR ${Slicer_INSTALL_BIN_DIR}
    INSTALL_LIB_DIR ${Slicer_INSTALL_LIB_DIR}
    )
endif()

# --------------------------------------------------------------------------
# Export target
# --------------------------------------------------------------------------
if(NOT DEFINED ${PROJECT_NAME}_EXPORT_FILE)
  set(${PROJECT_NAME}_EXPORT_FILE ${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}Targets.cmake)
endif()
export(TARGETS ${targets_to_export} APPEND FILE ${${PROJECT_NAME}_EXPORT_FILE})

# --------------------------------------------------------------------------
# Install library
# --------------------------------------------------------------------------
if(NOT DEFINED ${PROJECT_NAME}_INSTALL_BIN_DIR)
  set(${PROJECT_NAME}_INSTALL_BIN_DIR bin)
endif()
if(NOT DEFINED ${PROJECT_NAME}_INSTALL_LIB_DIR)
  set(${PROJECT_NAME}_INSTALL_LIB_DIR lib/${PROJECT_NAME})
endif()

install(TARGETS ${lib_name}
  RUNTIME DESTINATION ${${PROJECT_NAME}_INSTALL_BIN_DIR} COMPONENT RuntimeLibraries
  LIBRARY DESTINATION ${${PROJECT_NAME}_INSTALL_LIB_DIR} COMPONENT RuntimeLibraries
  ARCHIVE DESTINATION ${${PROJECT_NAME}_INSTALL_LIB_DIR} COMPONENT Development
  )

# --------------------------------------------------------------------------
# Testing
# --------------------------------------------------------------------------
#if(BUILD_TESTING)
#  add_subdirectory(Testing)
#endif()

# --------------------------------------------------------------------------
# Qt Designer Plugins
# --------------------------------------------------------------------------
# add_subdirectory(DesignerPlugins)

# --------------------------------------------------------------------------
# Set INCLUDE_DIRS variable
# --------------------------------------------------------------------------
set(${PROJECT_NAME}_INCLUDE_DIRS ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR}
  CACHE INTERNAL "${PROJECT_NAME} include dirs" FORCE)
