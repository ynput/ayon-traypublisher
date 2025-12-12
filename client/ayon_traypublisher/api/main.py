from __future__ import annotations
import os
import typing
from typing import Optional, Union

import ayon_api
from qtpy import QtWidgets, QtCore

from ayon_core.addon import ensure_addons_are_process_ready
from ayon_core.pipeline import install_host
from ayon_core.tools.utils import get_ayon_qt_app
# from ayon_core.tools.utils.host_tools import show_publisher

from ayon_traypublisher.ui import ChooseProjectWindow

from .pipeline import TrayPublisherHost

if typing.TYPE_CHECKING:
    from ayon_traypublisher import TrayPublishAddon


class _LaunchContext:
    def __init__(
        self,
        addon: TrayPublishAddon,
        app: QtWidgets.QApplication,
        project_name: Union[str, None],
        folder_path: Union[str, None],
        task_name: Union[str, None],
    ):
        init_timer = QtCore.QTimer()

        init_timer.timeout.connect(self._on_timer)

        self._addon = addon
        self._app = app
        self._project_name = project_name
        self._folder_path = folder_path
        self._task_name = task_name
        self._init_timer = init_timer
        self._publisher_window = None

    def start(self):
        self._init_timer.start()

    def _on_timer(self):
        self._init_timer.stop()

        if not self._project_name:
            window = ChooseProjectWindow()
            window.exec_()
            project_name = window.get_selected_project_name()
            if not project_name:
                print("Project is not selected, exiting.")
                self._app.exit(0)
                return

            self._project_name = project_name

        project = ayon_api.get_project(self._project_name)
        if not project:
            print(f"Project '{self._project_name}' not found, exiting.")
            self._app.exit(1)
            return

        os.environ["AYON_PROJECT_NAME"] = self._project_name
        if self._folder_path:
            os.environ["AYON_FOLDER_PATH"] = self._folder_path
        if self._task_name:
            os.environ["AYON_TASK_NAME"] = self._task_name

        ensure_addons_are_process_ready(
            addon_name=self._addon.name,
            addon_version=self._addon.version,
            project_name=self._project_name,
        )

        host = TrayPublisherHost()
        install_host(host)

        self._show_publisher()

    def _show_publisher(self):
        """Reimplement 'show_publisher' function from host tools.

        The function in ayon-core has a bug that validates if host does match
            ILoadHost interface, which is not the case for TrayPublisherHost.
            It should be changed to validate IPublishHost interface instead.

        Make sure ayon-core minimum required version is to the one where it is
            fixed when this function is removed.

        """
        from ayon_core.tools.publisher.window import PublisherWindow

        window = PublisherWindow()
        window.make_sure_is_visible()
        # Store the window to keep it in memory
        self._publisher_window = window


def launch_traypublisher_ui(
    addon: TrayPublishAddon,
    project_name: Union[str, None],
    folder_path: Optional[str] = None,
    task_name: Optional[str] = None,
):
    app_instance = get_ayon_qt_app()
    context = _LaunchContext(
        addon,
        app_instance,
        project_name,
        folder_path,
        task_name,
    )
    context.start()
    app_instance.exec_()
