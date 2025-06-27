import os

import pyblish.api
import pyblish.util

from ayon_core.lib.attribute_definitions import FileDefItem
from ayon_core.pipeline import install_host
from ayon_core.pipeline.create import CreateContext

from ayon_traypublisher.api import TrayPublisherHost


def csvpublish(
    filepath,
    project_name,
    folder_path,
    task_name=None,
    ignore_validators=False
):
    """Publish CSV file.

    Args:
        filepath (str): Path to CSV file.
        project_name (str): Project name.
        folder_path (str): Folder path.
        task_name (Optional[str]): Task name.
        ignore_validators (Optional[bool]): Option to ignore validators.

    """
    os.environ["AYON_PROJECT_NAME"] = project_name

    # initialization of host
    host = TrayPublisherHost()
    install_host(host)

    # form precreate data with field values
    file_field = FileDefItem.from_paths([filepath], False).pop().to_dict()
    precreate_data = {
        "csv_filepath_data": file_field,
    }

    # create context initialization
    create_context = CreateContext(host, headless=True)
    folder_entity = create_context.get_folder_entity(folder_path)

    if not folder_entity:
        ValueError(
            f"Folder path '{folder_path}' doesn't "
            f"exists at project '{project_name}'."
        )

    task_entity = create_context.get_task_entity(
        folder_path,
        task_name,
    )

    if not task_entity:
        ValueError(
            f"Task name '{task_name}' doesn't "
            f"exists at folder '{folder_path}'."
        )

    create_context.create(
        "io.ayon.creators.traypublisher.csv_ingest",
        "Main",
        folder_entity=folder_entity,
        task_entity=task_entity,
        pre_create_data=precreate_data,
    )

    # publishing context initialization
    pyblish_context = pyblish.api.Context()
    pyblish_context.data["create_context"] = create_context

    targets = None
    # redefine targets (skip 'local' to disable validators)
    if ignore_validators:
        targets = ["default", "ingest"]

    # publishing
    pyblish.util.publish(
        context=pyblish_context,
        targets=targets,
        plugins=create_context.publish_plugins,
    )
