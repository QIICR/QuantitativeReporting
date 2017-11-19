import vtk
from DICOMLib import DICOMDetailsWidget
from SlicerDevelopmentToolboxUtils.mixins import ParameterNodeObservationMixin


class CustomDICOMDetailsWidget(DICOMDetailsWidget, ParameterNodeObservationMixin):

  FinishedLoadingEvent = vtk.vtkCommand.UserEvent + 101

  def __init__(self, dicomBrowser=None, parent=None):
    DICOMDetailsWidget.__init__(self, dicomBrowser, parent)
    self.browserPersistentButton.visible = True
    self.browserPersistentButton.checked = False

  def onLoadingFinished(self):
    DICOMDetailsWidget.onLoadingFinished(self)
    if not self.browserPersistent:
      self.invokeEvent(self.FinishedLoadingEvent)