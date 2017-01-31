# User Interface Description

## 3D Slicer Interface Overview

The screenshot below shown gives you a basic overview of the 3D Slicer UI components. For further information see [Slicer Documentation](https://www.slicer.org/wiki/Documentation/Nightly/SlicerApplication/MainApplicationGUI)

![Alt Text](screenshots/user_interface.png)

## QuantitativeReporting Interface Overview

The following section describes all QuantitativeReporting user interface components from top to bottom.

### Tabs

![](screenshots/tabs.png)

**QR**: The actually **workspace** which will be used in 90% of your workflow

**DICOM**: The Slicer **DICOM Browser** to make it easier accessible within the QuantitativeReporting extension \(especially for the [Slicelet version](slicelet.md))

### Information Display

![](screenshots/watchbox.png)

This UI component is used for displaying general information about the currently selected master volume, which is used for creating segmentations and measurements. Furthermore the reader name is displayed.

### View Settings Area

![](screenshots/viewSettings.png)

We added all currently supported Slicer viewer layouts and in addition to that a button for enabling/disabling the crosshair \(which can be very helpful when a segment is selected from the tables and you, the user needs to locate it within the viewers\)

### Test Area

![](screenshots/testarea.png)

Currently only with one button for downloading and displaying a DICOM sample dataset that can be used for trying the module

### Selector Area

![](screenshots/inputSelectors.png)

   **Measurement report**: Create/select a new table for holding all the measurements created with this extension
   
   **Image volume to annotate**: Represents the master volume which will be used for creation of segmentations/volumetric measurements

### Segmentations Area

![](screenshots/segmentationsArea.png)

This area is supposed to help you creating segmentations. The here integrated widget is the Slicer SegmentEditor. It adds capabilities for:
   * Add/remove segments:  
   * Add terminology for each segment  
   * Create surface from segmentations  
   * Use a variety of tools \(so called effects\) that help you creating a segmentation \(i.e. thresholding, scissors\)  

   For further information also see [Slicer Segment Editor](https://www.slicer.org/wiki/Documentation/Nightly/Modules/SegmentEditor)

###  Measurements Area and Calculation Controls

![](screenshots/measurementsArea.png)

Once you start creating segmentations by using the SegmentEditor, you will notice default measurements that will be displayed as the result of the SegmentStatistics module for each created segment within this table. You can either click onto a segment in the SegmentEditor table or the measurements table which will cause all viewers to jump to the centroid of the selected segment \(as long as there is pixel data of the segment available\)

   You decide if you manually want to trigger the computation of the previously mentioned measurements or if it should be triggered automatically whenever a segment changes \(pixel data, name, terminology\)

###  Report Buttons 

![](screenshots/reportButtons.png)

You can either save a report and continue later \(needs to be implemented\) or complete the current report. Either way a DICOM Structured Report with a referenced DICOM Segmentation will be created and pushed into the Slicer DICOM database.
