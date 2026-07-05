import csv
import os
from ayon_core.pipeline import KnownPublishError
from ayon_traypublisher.plugins.publish.collect_common import (
    BasePublishPlugin,
    collect_folders,
)


class CollectCsv(BasePublishPlugin):
    """Collect instances from CSV file."""

    order = 1.0
    label = "Collect CSV"

    def process(self, instance):
        csv_path = instance.data.get("csvPath")
        if not csv_path:
            raise KnownPublishError("No CSV path provided.")
        if not os.path.isfile(csv_path):
            raise KnownPublishError(f"CSV file not found: {csv_path}")

        with open(csv_path, "r") as csv_file:
            reader = csv.DictReader(csv_file)
            folders = []
            for row in reader:
                folder_name = row.get("folder_name")
                if not folder_name:
                    raise KnownPublishError(
                        "Missing 'folder_name' column in CSV."
                    )
                folder_path = row.get("folder_path", "")
                folder_type = row.get("folder_type", "Folder")
                # Read description if present
                description = row.get("description", "")

                folder_data = {
                    "name": folder_name,
                    "path": folder_path,
                    "type": folder_type,
                }
                if description:
                    folder_data["description"] = description

                folders.append(folder_data)

        instance.data["folderDataList"] = folders
        self.log.info(f"Collected {len(folders)} folders from CSV.")

    def create_folder(self, folder_data, project_name):
        """Create folder with description if present."""
        from ayon_api import get_server_api

        api = get_server_api()
        folder_name = folder_data["name"]
        folder_path = folder_data.get("path")
        folder_type = folder_data.get("type", "Folder")
        description = folder_data.get("description", "")

        folder_entity = api.create_folder(
            project_name,
            folder_name,
            folder_type=folder_type,
            parent_path=folder_path,
            description=description,
        )
        return folder_entity
