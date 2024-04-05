from PySide6 import QtCore, QtWidgets, QtGui, QtWebEngineWidgets
from __feature__ import snake_case, true_property
from textwrap import shorten
from pathlib import Path


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

        layout = QtWidgets.QGridLayout()

        lblInfo = QtWidgets.QLabel()

        if not files:
            self.window_title = "Smart Geo Tag - Folder Location"
            lblInfo.text = f"Set location for images in folder {folder}"
        else:
            imgs = ",".join([Path(img).name for img in files])
            self.window_title = "Smart Geo Tag - Files Location"
            lblInfo.text = shorten(
                f"Set location for the images {imgs}",
                width=self.width,
                placeholder="...",
            )
            lblInfo.tool_tip = f"{imgs}"

        layout.add_widget(lblInfo, 0, 0)

        # widget = QtWidgets.QWidget(self)
        # widget.set_layout(layout)
        self.set_layout(layout)
        # self.set_central_widget(widget)

        self.resize(800, 600)
