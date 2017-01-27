# Tutorial

This section of the manual describes in detail how to create a segmentation for a given DICOM sample dataset and save it in combination with automatically created volumetric measurements into the DICOM file format. The resulting data will be stored in the Slicer DICOM database and is therefore centrally accessible for later reading.

### Prerequisites

Make sure that you followed the instructions given in [Installation and upgrade](install.md)

## Create a DICOM Structured Report

In this section you will learn how to create a DICOM Structured Report which will include a DICOM Segmentation and volumetric measurements.

### Load DICOM sample dataset

First of all you will need to download a DICOM sample dataset. With using the button shown below this task will be performed for you.

![](screenshots/testarea.png)

The task includes **a)** download of the DICOM sample dataset, **b)** unpacking and importing it into 3D Slicer **c)** initiating the creation of a new measurement table which references the downloaded DICOM sample dataset finally **d)** displays it within your preferred slice view layout

**add screenshot here**





### Create segmentation

#### Add segment

#### Select terminology

#### Segment by using SegmentEditor effects

### Save report
Once you are done with creating a segmentation and you want to save the measurements result as DICOM, you can push one of the following buttons:
![](screenshots/reportButtons.png)

**"Save Report"**: Will create the **partially completed** DICOM Structured Report which could be continued at a later time (work in progress)

**"Complete Report"**: Will create the **completed** DICOM Structured Report representing the final version which usually wouldn't be modified afterwards.


## Load a DICOM Structured Report

This section will show you how to load a DICOM Structured Report from the Slicer DICOM database and how to load and display the results with Quantitative Reporting.