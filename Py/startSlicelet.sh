#!/usr/bin/env bash
SLICER="/Applications/Slicer.app/Contents/MacOS/Slicer"

$SLICER --python-code "from QuantitativeReporting import QuantitativeReportingSlicelet; slicelet=QuantitativeReportingSlicelet();" --no-splash --no-main-window