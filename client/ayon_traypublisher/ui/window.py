"""Tray publisher is extending publisher tool.

Adds ability to select project using overlay widget with list of projects.

Tray publisher can be considered as host implementeation with creators and
publishing plugins.
"""
from typing import Optional

from qtpy import QtWidgets, QtCore, QtGui
import qtawesome

from ayon_core.style import load_stylesheet
from ayon_core.resources import get_ayon_icon_filepath
from ayon_core.lib import AYONSettingsRegistry
from ayon_core.lib.events import QueuedEventSystem
from ayon_core.tools.common_models import ProjectsModel
from ayon_core.tools.utils import (
    PlaceholderLineEdit,
    ProjectsQtModel,
    ProjectSortFilterProxy,
    PROJECT_NAME_ROLE,
)


class TrayPublisherRegistry(AYONSettingsRegistry):
    def __init__(self):
        super().__init__("traypublisher")


class ChooseProjectController:
    def __init__(self):
        self._event_system = QueuedEventSystem()
        self._projects_model = ProjectsModel(self)
        self._registry = AYONSettingsRegistry("traypublisher")

    def get_project_items(self, sender=None):
        return self._projects_model.get_project_items(sender)

    def emit_event(self, topic, data=None, source=None):
        """Use implemented event system to trigger event."""

        if data is None:
            data = {}
        self._event_system.emit(topic, data, source)

    def register_event_callback(self, topic, callback):
        self._event_system.add_callback(topic, callback)

    def get_last_user_project_name(self) -> Optional[str]:
        try:
            return self._registry.get_item("project_name")
        except ValueError:
            pass

    def set_last_user_project_name(self, project_name: str):
        self._registry.set_item("project_name", project_name)


class ChooseProjectWindow(QtWidgets.QDialog):
    default_width = 400
    default_height = 600

    def __init__(self, controller=None):
        super().__init__()

        self.setWindowTitle("Choose project for Tray Publisher")
        self.setWindowIcon(QtGui.QIcon(get_ayon_icon_filepath()))

        if controller is None:
            controller = ChooseProjectController()

        content_widget = QtWidgets.QWidget(self)

        header_label = QtWidgets.QLabel("Choose project", content_widget)
        header_label.setObjectName("ChooseProjectLabel")
        # Create project models and view
        projects_model = ProjectsQtModel(controller)
        projects_proxy = ProjectSortFilterProxy()
        projects_proxy.setSourceModel(projects_model)
        projects_proxy.setFilterKeyColumn(0)

        projects_view = QtWidgets.QListView(content_widget)
        projects_view.setObjectName("ChooseProjectView")
        projects_view.setModel(projects_proxy)
        projects_view.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )

        btns_widget = QtWidgets.QWidget(content_widget)

        confirm_btn = QtWidgets.QPushButton("Confirm", btns_widget)
        cancel_btn = QtWidgets.QPushButton("Cancel", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addStretch(1)
        btns_layout.addWidget(cancel_btn, 0)
        btns_layout.addWidget(confirm_btn, 0)

        txt_filter = PlaceholderLineEdit(content_widget)
        txt_filter.setPlaceholderText("Quick filter projects..")
        txt_filter.setClearButtonEnabled(True)
        txt_filter.addAction(
            qtawesome.icon("fa.filter", color="gray"),
            QtWidgets.QLineEdit.LeadingPosition
        )

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        content_layout.addWidget(header_label, 0)
        content_layout.addWidget(txt_filter, 0)
        content_layout.addWidget(projects_view, 1)
        content_layout.addWidget(btns_widget, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(content_widget, 1)

        projects_view.doubleClicked.connect(self._on_double_click)
        confirm_btn.clicked.connect(self._on_confirm_click)
        cancel_btn.clicked.connect(self._on_cancel_click)
        txt_filter.textChanged.connect(self._on_text_changed)

        self._projects_view = projects_view
        self._projects_model = projects_model
        self._projects_proxy = projects_proxy
        self._cancel_btn = cancel_btn
        self._confirm_btn = confirm_btn
        self._txt_filter = txt_filter

        self._controller = controller
        self._project_name = None
        self._first_show = True

    def get_selected_project_name(self) -> Optional[str]:
        return self._project_name

    def showEvent(self, event):
        if self._first_show:
            self.resize(self.default_width, self.default_height)
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setStyleSheet(load_stylesheet())
        self._refresh_projects()

    def _refresh_projects(self):
        self._projects_model.refresh()
        # Sort projects after refresh
        self._projects_proxy.sort(0)

        project_name = self._controller.get_last_user_project_name()
        if not project_name:
            return

        src_index = self._projects_model.get_index_by_project_name(
            project_name
        )
        index = self._projects_proxy.mapFromSource(src_index)
        if index.isValid():
            selection_model = self._projects_view.selectionModel()
            selection_model.select(
                index,
                QtCore.QItemSelectionModel.SelectCurrent
            )
            self._projects_view.setCurrentIndex(index)

    def _on_double_click(self):
        self._set_selected_project()

    def _on_confirm_click(self):
        self._set_selected_project()

    def _on_cancel_click(self):
        self.reject()

    def _on_text_changed(self):
        self._projects_proxy.setFilterRegularExpression(
            self._txt_filter.text())

    def _set_selected_project(self):
        index = self._projects_view.currentIndex()

        project_name = index.data(PROJECT_NAME_ROLE)
        if not project_name:
            return

        self._controller.set_last_user_project_name(project_name)

        self._project_name = project_name
        self.accept()
