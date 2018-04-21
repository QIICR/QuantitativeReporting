#-----------------------------------------------------------------------------

set(MODULE_PYTHON_SCRIPTS
  QRCustomizations/__init__.py
  QRCustomizations/CustomDICOMDetailsWidget.py
  QRCustomizations/CustomSegmentEditor.py
  QRCustomizations/CustomSegmentStatistics.py
  QRCustomizations/SegmentEditorAlgorithmTracker.py
  QRUtils/__init__.py
  QRUtils/htmlReport.py
  QRUtils/testdata.py
  ${MODULE_NAME}.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/QuantitativeReporting.png
  Resources/Icons/ReportingLogo128px.png
  Resources/Validation/general_content_schema.json
)

slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
)

#-----------------------------------------------------------------------------
