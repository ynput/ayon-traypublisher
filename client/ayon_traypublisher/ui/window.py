"""Tray publisher is extending publisher tool.

Adds ability to select project using overlay widget with list of projects.

Tray publisher can be considered as host implementeation with creators and
publishing plugins.
"""
from typing import Optional

from qtpy import QtWidgets, QtGui
import qtawesome

from ayon_core.style import load_stylesheet
from ayon_core.resources import get_ayon_icon_filepath
from ayon_core.lib import AYONSettingsRegistry
from ayon_core.lib.events import QueuedEventSystem
from ayon_core.tools.common_models import ProjectsModel
from ayon_core.tools.utils import PlaceholderLineEdit

from .projects_widget import TrayPublisherProjectsWidget


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

    def set_selected_project(self, project_name: str):
        """ProjectsWidget from ayon-core requires this method.
        
        Tray Publisher does not need to implement it.

        """
        pass


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

        projects_widget = TrayPublisherProjectsWidget(
            controller, content_widget
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
        content_layout.addWidget(projects_widget, 1)
        content_layout.addWidget(btns_widget, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(content_widget, 1)

        projects_widget.double_clicked.connect(self._on_double_click)
        confirm_btn.clicked.connect(self._on_confirm_click)
        cancel_btn.clicked.connect(self._on_cancel_click)
        txt_filter.textChanged.connect(self._on_text_changed)

        self._projects_widget = projects_widget
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
        self._projects_widget.refresh()

        project_name = self._controller.get_last_user_project_name()
        if project_name:
            self._projects_widget.set_selected_project(project_name)

    def _on_double_click(self):
        self._set_selected_project()

    def _on_confirm_click(self):
        self._set_selected_project()

    def _on_cancel_click(self):
        self.reject()

    def _on_text_changed(self):
        self._projects_widget.set_name_filter(
            self._txt_filter.text()
        )

    def _set_selected_project(self):
        project_name = self._projects_widget.get_selected_project()
        if not project_name:
            return

        self._controller.set_last_user_project_name(project_name)

        self._project_name = project_name
        self.accept()
