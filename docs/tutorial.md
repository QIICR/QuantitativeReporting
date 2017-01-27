# Tutorial

This section of the manual describes in detail how to create a segmentation for a given DICOM sample dataset and save it in combination with automatically created volumetric measurements into the DICOM file format. The resulting data will be stored in the Slicer DICOM database and is therefore centrally accessible for later reading.

### Prerequisites

Make sure that you followed the instructions given in [Installation and upgrade](install.md)

## Create a DICOM Structured Report

In this section you will learn how to create a DICOM Structured Report which will include a DICOM Segmentation and volumetric measurements.

### Load DICOM sample dataset

First of all you will need to download a DICOM sample dataset. With using the button shown below this task will be performed for you.

![](screenshots/testarea.png)

This button will do the following for you: 

1. **download** the DICOM sample dataset, 
2. **unpacking** and **importing** it into 3D Slicer 
3. initiating the **creation of a new measurement** table which references the downloaded DICOM sample dataset finally 
4. **displays** it within your preferred slice view layout

**add screenshot here**

### Create segmentation

Here you will get introduce to creating a segmentation with our module.

#### Add segment

Once the DICOM sample dataset has been loaded into Quantitative Reporting you can go ahead and create a first segment. 

**add screenshot here** of a new segment

**Note**: Initially every segment is assigned to the terminology category and type **"Tissue"**.

#### Select terminology

In order to make a segmentation more specific you can select another terminology by double clicking onto the color icon of the segment.

**add screenshot here** of terminology selection

#### Segment by using SegmentEditor effects

reference SegmentEditor and tutorials for that if exists

**add screenshot here** of effects and segmentation result

### Save report
Once you are done with creating a segmentation and you want to save the measurements result as DICOM, you can push one of the following buttons:
![](screenshots/reportButtons.png)

**"Save Report"**: Will create the **partially completed** DICOM Structured Report which could be continued at a later time (work in progress)

**"Complete Report"**: Will create the **completed** DICOM Structured Report representing the final version which usually wouldn't be modified afterwards.

## Load a DICOM Structured Report

This section will show you how to load a DICOM Structured Report from the Slicer DICOM database and how to load and display the results with Quantitative Reporting.