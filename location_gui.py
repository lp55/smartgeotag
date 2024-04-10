from PySide6 import QtCore, QtWidgets, QtGui, QtWebEngineWidgets
from __feature__ import snake_case, true_property
from textwrap import shorten
from pathlib import Path
from nominatim_suggest import NominatimLineEdit
from map import set_map
from geo import Coordinates


class LocationWindow(QtWidgets.QDialog):
    def __init__(
        self,
        folder: str,
        files: list[str] | None = None,
        parent: QtWidgets.QWidget | None = None,
        f: QtCore.Qt.WindowType = QtCore.Qt.WindowType.Dialog,
    ) -> None:
        super().__init__(parent, f)

        self.folder = folder
        self.files = files

        layout = QtWidgets.QVBoxLayout()

        self.lbl_info = QtWidgets.QLabel()

        if not files:
            self.window_title = "Smart Geo Tag - Folder Location"
            self.lbl_info.text = f"Set location for images in folder {folder}"
        else:
            imgs = ",".join([Path(img).name for img in files])
            self.window_title = "Smart Geo Tag - Files Location"
            self.lbl_info.text = shorten(
                f"Set location for the images {imgs}",
                width=self.width,
                placeholder="...",
            )
            self.lbl_info.tool_tip = f"{imgs}"

        layout.add_widget(self.lbl_info, 0)

        self.ldt_location = NominatimLineEdit()
        self.ldt_location.location_selected.connect(self.show_location_on_map)
        layout.add_widget(self.ldt_location, 1)

        self.web_view = QtWebEngineWidgets.QWebEngineView()
        self.web_view.set_html("No location set")
        layout.add_widget(self.web_view, 2)

        self.set_layout(layout)

        self.resize(800, 600)

    @QtCore.Slot(str, Coordinates)
    def show_location_on_map(self, name: str, coordinates: Coordinates):
        set_map(
            self.web_view,
            [coordinates],
            markers=[""],
            descriptions=[name],
            draggable=True,
        )
