import sys
import io
from pathlib import Path
from PySide6 import QtCore, QtWidgets, QtGui, QtWebEngineWidgets
from __feature__ import snake_case, true_property
from geo import (
    images_extensions,
    Coordinates,
    get_image_gps,
    GPS,
)
from location_gui import LocationWindow
from map import set_map


class MainWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)

        self.window_title = "Smart Geo Tag"
        self.resize(1024, 800)

        layout = QtWidgets.QGridLayout()

        self.folder_model = QtWidgets.QFileSystemModel()
        # pictures_path = QtCore.QStandardPaths.writable_location(
        #    QtCore.QStandardPaths.StandardLocation.PicturesLocation
        # )
        self.folder_model.set_root_path("")
        self.folder_model.set_filter(
            QtCore.QDir.Filter.AllDirs
            | QtCore.QDir.Filter.NoDotAndDotDot
            | QtCore.QDir.Filter.Drives
        )

        self.folder_tree = QtWidgets.QTreeView(parent=self)
        # folder_tree.size_adjust_policy = (
        #    QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
        # )
        # folder_tree.size_policy = QtWidgets.QSizePolicy.Policy.MinimumExpanding
        self.folder_tree.set_model(self.folder_model)
        # folder_tree.set_root_index(folder_model.index(""))
        # folder_tree.resize(800, 600)

        folder_header = self.folder_tree.header()
        folder_header.hide_section(1)
        folder_header.hide_section(2)
        folder_header.hide_section(3)

        layout.add_widget(self.folder_tree, 0, 0)

        self.web_view = QtWebEngineWidgets.QWebEngineView()
        self.web_view.set_html("No map data")

        v_layout = QtWidgets.QVBoxLayout()
        # v_layout.add_stretch(2)
        v_layout.add_widget(self.web_view)

        layout.add_layout(v_layout, 0, 1, 2, 1)

        self.pictures_model = QtWidgets.QFileSystemModel()  # PicturesModel()
        # pictures_model.set_root_path("")
        self.pictures_model.set_filter(QtCore.QDir.Filter.Files)
        extensions = [f"*{ext}" for ext in images_extensions]
        self.pictures_model.set_name_filters(extensions)
        self.pictures_model.name_filter_disables = False

        self.pictures_table = QtWidgets.QTableView(parent=self)
        self.pictures_table.set_model(self.pictures_model)
        self.pictures_table.edit_triggers = (
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.pictures_table.selection_behavior = (
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.pictures_table.selection_mode = (
            QtWidgets.QAbstractItemView.SelectionMode.MultiSelection
        )

        # pictures_tree.set_root_index(pictures_model.index(""))
        self.pictures_table.enabled = False

        # policy = QtWidgets.QSizePolicy(
        #    QtWidgets.QSizePolicy.Policy.Expanding,
        #    QtWidgets.QSizePolicy.Policy.Expanding,
        # )
        # pictures_header.size_policy = policy

        # pictures_header = pictures_tree.header()

        # for i in range(pictures_header.count()):
        #     pictures_header.set_section_resize_mode(
        #         i, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        #     )

        pictures_header = self.pictures_table.horizontal_header()
        for i in range(pictures_header.count()):
            pictures_header.set_section_resize_mode(
                i, QtWidgets.QHeaderView.ResizeMode.Stretch
            )

        pictures_header.set_section_resize_mode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        pictures_header.set_section_resize_mode(
            1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        pictures_header.set_section_resize_mode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        pictures_header.set_section_resize_mode(
            3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )

        pictures_header.hide_section(2)
        # pictures_header.stretch_last_section = True
        self.pictures_table.resize_columns_to_contents()

        layout.add_widget(self.pictures_table, 0, 2)

        self.folder_tree.activated.connect(
            lambda item: folder_selected(
                self,
                item,
            )
        )

        # pictures_tree.activated.connect(
        #    lambda item: image_selected(pictures_model, web_view, item)
        # )
        self.pictures_table.selection_model().selectionChanged.connect(
            lambda selected, deselected: image_selected(
                self,
                selected,
                deselected,
            )
        )

        folder_location = QtWidgets.QPushButton("Set folder location")
        folder_location.clicked.connect(lambda _: open_folder_location_dlg(self))
        layout.add_widget(folder_location, 1, 0)

        pictures_location = QtWidgets.QPushButton("Set images location")
        pictures_location.clicked.connect(lambda _: open_files_location_dlg(self))
        layout.add_widget(pictures_location, 1, 2)

        widget = QtWidgets.QWidget(self)
        widget.set_layout(layout)
        self.set_central_widget(widget)

        # images_model = QtWidgets.QFileSystemModel(widget)


def folder_selected(
    self: MainWindow,
    item: QtCore.QModelIndex,
):
    # print(folder_model.file_path(item))
    self.pictures_model.set_root_path(self.folder_model.file_path(item))
    self.pictures_table.set_root_index(
        self.pictures_model.index(self.folder_model.file_path(item))
    )
    # pictures_header = pictures_tree.header()
    # pictures_header.resize_sections(QtWidgets.QHeaderView.ResizeMode.Stretch)
    self.pictures_table.enabled = True

    self.web_view.set_html("No map data")

    self.pictures_table.visible = False
    self.pictures_table.resize_columns_to_contents()
    self.pictures_table.visible = True


def image_selected(
    self: MainWindow,
    # item: QtCore.QModelIndex,
    selected: QtCore.QItemSelection,
    deselected: QtCore.QItemSelection,
):
    # print(folder_model.file_path(item))
    # path = Path(pictures_model.file_path(item))
    markers = []
    rows = []

    for index in self.pictures_table.selected_indexes():
        path = Path(self.pictures_model.file_path(index))

        gps_info = get_image_gps(path)
        if gps_info:
            gps_data = GPS.from_exif(
                gps_info["GPSLatitude"],
                gps_info["GPSLatitudeRef"],
                gps_info["GPSLongitude"],
                gps_info["GPSLongitudeRef"],
            )
            markers.append(gps_data.coordinates)
            rows.append(index.row() + 1)
            # set_map(web_view, [gps_data.coordinates], [pictures_model.get_number(item)])
            # set_map(web_view, [gps_data.coordinates], [item.row()])

    if markers:
        set_map(self.web_view, markers, rows)
    else:
        self.web_view.set_html("No map data")


def open_folder_location_dlg(self: MainWindow):
    if not self.folder_tree.selected_indexes():
        return

    path = self.folder_model.file_path(self.folder_tree.selected_indexes()[0])
    print(path)
    dlg = LocationWindow(path)
    dlg.exec()


def open_files_location_dlg(self: MainWindow):
    if not self.folder_tree.selected_indexes():
        return

    if not self.pictures_table.selected_indexes():
        return

    folder = self.folder_model.file_path(self.folder_tree.selected_indexes()[0])

    files = [
        self.pictures_model.file_path(index)
        for index in self.pictures_table.selected_indexes()
    ]

    dlg = LocationWindow(folder, files)
    dlg.exec()


def load_gui():
    app = QtWidgets.QApplication([])
    widget = MainWindow()
    widget.show_maximized()

    sys.exit(app.exec())
