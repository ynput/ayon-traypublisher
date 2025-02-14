import os
from pathlib import Path
from typing import Optional

import ayon_api

from ayon_core.lib import get_ayon_launcher_args
from ayon_core.lib.execute import run_detached_process
from ayon_core.addon import (
    click_wrap,
    AYONAddon,
    ITrayAction,
    IHostAddon,
)

from .version import __version__

TRAYPUBLISH_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class TrayPublishAddon(AYONAddon, IHostAddon, ITrayAction):
    label = "Publisher"
    name = "traypublisher"
    version = __version__
    host_name = "traypublisher"

    _choose_dialog = None

    def tray_init(self):
        return

    def on_action_trigger(self):
        self._show_choose_project()

    def cli(self, click_group):
        cli_main = click_wrap.group(
            self._cli_main,
            name=self.name,
            help="TrayPublisher commands"
        )

        cli_main.command(
            self._cli_launch,
            name="launch",
            help="Launch TrayPublish tool UI.",
        ).option(
            "--project",
            help="Project name",
            envvar="AYON_PROJECT_NAME",
            default=None,
        )

        cli_main.command(
            self._ingest_csv,
            name="ingestcsv",
        ).option(
            "--filepath",
            help="Full path to CSV file with data",
            type=str,
            required=True
        ).option(
            "--project",
            help="Project name in which the context will be used",
            type=str,
            required=True
        ).option(
            "--folder-path",
            help="Asset name in which the context will be used",
            type=str,
            required=True
        ).option(
            "--task",
            help="Task name under Asset in which the context will be used",
            type=str,
            required=False
        ).option(
            "--ignore-validators",
            help="Option to ignore validators",
            type=bool,
            is_flag=True,
            required=False
        )
        click_group.add_command(cli_main.to_click_obj())

    def _cli_main(self):
        pass

    def _cli_launch(self, project: Optional[str] = None):
        from .api.main import launch_traypublisher_ui

        launch_traypublisher_ui(project)

    def _start_traypublisher(self, project_name: str):
        args = get_ayon_launcher_args(
            "addon", self.name, "launch", "--project", project_name
        )
        run_detached_process(args)

    def _get_choose_dialog(self):
        if self._choose_dialog is None:
            from ayon_traypublisher.ui import ChooseProjectWindow

            choose_dialog = ChooseProjectWindow()
            choose_dialog.accepted.connect(self._on_choose_dialog_accept)
            self._choose_dialog = choose_dialog
        return self._choose_dialog

    def _on_choose_dialog_accept(self):
        project_name = self._choose_dialog.get_selected_project_name()
        if project_name:
            self._start_traypublisher(project_name)

    def _show_choose_project(self):
        from qtpy import QtCore
        window = self._get_choose_dialog()
        window.show()
        window.setWindowState(
            window.windowState()
            & ~QtCore.Qt.WindowMinimized
            | QtCore.Qt.WindowActive
        )
        window.activateWindow()

    def _ingest_csv(
        self,
        filepath,
        project,
        folder_path,
        task,
        ignore_validators,
    ):
        """Ingest CSV file into project.

        This command will ingest CSV file into project. CSV file must be in
        specific format. See documentation for more information.
        """
        from .csv_publish import csvpublish

        # Allow user override through AYON_USERNAME when
        # current connection is made through a service user.
        username = os.environ.get("AYON_USERNAME")
        if username:
            con = ayon_api.get_server_api_connection()
            if con.is_service_user():
                con.set_default_service_username(username)

        # use Path to check if csv_filepath exists
        if not Path(filepath).exists():
            raise FileNotFoundError(f"File {filepath} does not exist.")

        csvpublish(
            filepath,
            project,
            folder_path,
            task,
            ignore_validators
        )
