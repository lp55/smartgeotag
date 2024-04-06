from PySide6 import QtCore, QtWidgets, QtGui, QtWebEngineWidgets
from __feature__ import snake_case, true_property
import typing
from pathlib import Path
from geo import get_image_gps


class PicturesModel(QtWidgets.QFileSystemModel):
    """
    Add a index column to the QFileSystemModel, so the user can know
    which selected image represents which tag
    """

    def column_count(
        self,
        parent: (
            QtCore.QModelIndex | QtCore.QPersistentModelIndex
        ) = QtCore.QModelIndex(),
    ) -> int:
        return super().column_count(parent) + 1

    def header_data(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> typing.Any:
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and section == self.column_count() - 1
        ):
            return "GeoTag"
        else:
            return super().header_data(section, orientation, role)

    def data(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> typing.Any:
        if index.is_valid() and index.column() == self.column_count(index.parent()) - 1:
            if role == QtCore.Qt.ItemDataRole.CheckStateRole:
                path = Path(self.root_path()) / index.sibling_at_column(0).data(
                    QtCore.Qt.ItemDataRole.DisplayRole
                )
                if path.is_file():
                    return (
                        QtCore.Qt.CheckState.Checked
                        if get_image_gps(Path(self.root_path()) / path) is not None
                        else QtCore.Qt.CheckState.Unchecked
                    )
                return QtCore.Qt.CheckState.Unchecked
            elif role == QtCore.Qt.ItemDataRole.DecorationRole:
                return QtWidgets.QFileIconProvider.IconType.Computer
            elif QtCore.Qt.ItemDataRole.TextAlignmentRole:
                return QtCore.Qt.AlignmentFlag.AlignHCenter

        return super().data(index, role)

    def get_number(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ):
        return index.sibling_at_column(4).data(role)
