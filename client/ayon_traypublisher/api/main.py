import os
from typing import Optional

from qtpy import QtWidgets, QtCore

from ayon_core.pipeline import install_host
from ayon_core.tools.utils import get_ayon_qt_app
# from ayon_core.tools.utils.host_tools import show_publisher

from ayon_traypublisher.ui import ChooseProjectWindow

from .pipeline import TrayPublisherHost


class _LaunchContext:
    def __init__(
        self,
        app: QtWidgets.QApplication,
        project_name: Optional[str],
    ):
        init_timer = QtCore.QTimer()

        init_timer.timeout.connect(self._on_timer)

        self._project_name = project_name
        self._app = app
        self._init_timer = init_timer
        self._publisher_window = None

    def start(self):
        self._init_timer.start()

    def _on_timer(self):
        self._init_timer.stop()

        if not self._project_name:
            window = ChooseProjectWindow()
            window.exec_()
            self._project_name = window.get_selected_project_name()

        if not self._project_name:
            self.log.info("Project is not selected, exiting.")
            self._app.exit(0)
            return

        os.environ["AYON_PROJECT_NAME"] = self._project_name
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


def launch_traypublisher_ui(project_name: Optional[str]):
    app_instance = get_ayon_qt_app()
    context = _LaunchContext(app_instance, project_name)
    context.start()
    app_instance.exec_()
