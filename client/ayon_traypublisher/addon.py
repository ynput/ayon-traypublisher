import os

from pathlib import Path

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

    def tray_init(self):
        return

    def on_action_trigger(self):
        self.run_traypublisher()

    def run_traypublisher(self):
        args = get_ayon_launcher_args(
            "addon", self.name, "launch"
        )
        run_detached_process(args)

    def cli(self, click_group):
        click_group.add_command(cli_main.to_click_obj())


@click_wrap.group(
    TrayPublishAddon.name,
    help="TrayPublisher related commands.")
def cli_main():
    pass


@cli_main.command()
def launch():
    """Launch TrayPublish tool UI."""

    from ayon_traypublisher import ui

    ui.main()


@cli_main.command()
@click_wrap.option(
    "--filepath",
    help="Full path to CSV file with data",
    type=str,
    required=True
)
@click_wrap.option(
    "--project",
    help="Project name in which the context will be used",
    type=str,
    required=True
)
@click_wrap.option(
    "--folder-path",
    help="Asset name in which the context will be used",
    type=str,
    required=True
)
@click_wrap.option(
    "--task",
    help="Task name under Asset in which the context will be used",
    type=str,
    required=False
)
@click_wrap.option(
    "--ignore-validators",
    help="Option to ignore validators",
    type=bool,
    is_flag=True,
    required=False
)
def ingestcsv(
    filepath,
    project,
    folder_path,
    task,
    ignore_validators
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
