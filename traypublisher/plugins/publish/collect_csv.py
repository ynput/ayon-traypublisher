import csv
import pyblish.api
from ayon_traypublisher import constants
from ayon_core.pipeline import publish


class CollectCsvInstances(publish.AbstractCollector):
    """Collect CSV file entries and create instances."""

    order = pyblish.api.CollectorOrder
    label = "Collect CSV Instances"
    families = ["csv_ingest"]

    def process(self, context):
        csv_path = context.data.get("currentFile")
        if not csv_path or not csv_path.endswith(".csv"):
            return

        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                folder_name = row.get("folderName", "").strip()
                folder_type = row.get("folderType", "Folder").strip()
                description = row.get("description", "").strip()

                if not folder_name:
                    continue

                # Create instance for each folder entry
                instance = context.create_instance(folder_name)
                instance.data["family"] = "folder"
                instance.data["folderName"] = folder_name
                instance.data["folderType"] = folder_type
                instance.data["description"] = description

                # Additional data mapping from row
                instance.data["csvData"] = dict(row)

                # Mark that this instance should create a folder
                instance.data["createFolder"] = True
