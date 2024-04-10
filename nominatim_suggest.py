from PySide6 import QtCore, QtWidgets, QtGui
from __feature__ import snake_case, true_property
from geo import get_suggestions, Coordinates


class NominatimSuggest(QtCore.QObject):
    def __init__(self, parent: "NominatimLineEdit"):
        super().__init__(parent)

        self.widget = parent

        self.popup = QtWidgets.QTreeWidget()
        self.popup.set_window_flags(QtCore.Qt.WindowType.Popup)
        self.popup.focus_policy = QtCore.Qt.FocusPolicy.NoFocus
        self.popup.set_focus_proxy(parent)
        self.popup.mouse_tracking = True

        self.popup.column_count = 1
        self.popup.uniform_row_heights = True
        self.popup.root_is_decorated = False
        self.popup.edit_triggers = QtWidgets.QTreeWidget.EditTrigger.NoEditTriggers
        self.popup.selection_behavior = (
            QtWidgets.QTreeWidget.SelectionBehavior.SelectRows
        )
        self.popup.set_frame_style(
            QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Plain
        )
        self.popup.horizontal_scroll_bar_policy = (
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.popup.header().hide()

        self.popup.install_event_filter(self)

        self.popup.itemClicked.connect(self.item_selected)

        self.timer = QtCore.QTimer()
        self.timer.single_shot_ = True
        self.timer.interval = 500
        self.timer.timeout.connect(self.auto_suggest)

        self.widget.textEdited.connect(self.timer.start)

    def event_filter(self, obj: QtCore.QObject, event: QtCore.QEvent):
        if obj is not self.popup:
            return False

        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            self.popup.hide()
            self.widget.set_focus()
            return True

        if event.type() == QtCore.QEvent.Type.KeyPress:
            key = QtGui.QKeyEvent(event).key()
            if key in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return):
                self.item_selected()
                return True
            elif key == QtCore.Qt.Key.Key_Escape:
                self.popup.hide()
                self.widget.set_focus()
                return True
            elif key in (
                QtCore.Qt.Key.Key_Up,
                QtCore.Qt.Key.Key_Down,
                QtCore.Qt.Key.Key_Home,
                QtCore.Qt.Key.Key_End,
                QtCore.Qt.Key.Key_PageUp,
                QtCore.Qt.Key.Key_PageDown,
            ):
                pass
            else:
                self.widget.set_focus()
                self.widget.event(event)
                self.popup.hide()

        return False

    @QtCore.Slot()
    def item_selected(self):
        self.timer.stop()
        self.popup.hide()
        self.widget.set_focus()
        item = self.popup.current_item
        if item:
            name = item.text(0)
            coordinates = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            self.widget.text = name
            self.widget.set_property("coordinates", coordinates)
            self.widget.location_selected.emit(name, coordinates)
            self.widget.returnPressed.emit()

    @QtCore.Slot()
    def auto_suggest(self):
        location = self.widget.text
        suggestions = get_suggestions(location)
        self.show_completion_list(suggestions)

    def show_completion_list(self, suggestions: list[tuple[str, Coordinates]]):
        if not suggestions:
            return

        palette = self.widget.palette
        color = palette.color(
            QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText
        )

        self.popup.updates_enabled = False
        self.popup.clear()

        for name, coord in suggestions:
            item = QtWidgets.QTreeWidgetItem(self.popup)
            item.set_text(0, name)
            item.set_data(0, QtCore.Qt.ItemDataRole.UserRole, coord)
            item.set_foreground(0, color)

        self.popup.current_item = self.popup.top_level_item(0)
        self.popup.resize_column_to_contents = 0
        self.popup.updates_enabled = True

        self.popup.move(self.widget.map_to_global(QtCore.QPoint(0, self.widget.height)))
        self.popup.set_focus()
        self.popup.show()


class NominatimLineEdit(QtWidgets.QLineEdit):
    location_selected = QtCore.Signal(str, Coordinates)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = NominatimSuggest(self)
        self.placeholder_text = "Type location..."
        self.set_focus()
