import csv
import os

import pyblish.api
from ayon_core.pipeline import publish
from ayon_core.hosts.traypublisher.api.plugin import TrayPublishBase


class CollectCSV(publish.AbstractCollector):
    """Collect instances from CSV file.

    Expects CSV with columns: folder, task, product, variant, comment,
    folderDescription (optional), etc.
    """

    order = pyblish.api.CollectorOrder
    label = "Collect CSV"
    hosts = ["traypublisher"]

    def process(self, context):
        csv_path = os.environ.get("AYON_CSV_PATH")
        if not csv_path:
            return

        with open(csv_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                folder_name = row.get("folder")
                task_name = row.get("task")
                product_name = row.get("product")
                variant = row.get("variant")
                comment = row.get("comment", "")
                folder_description = row.get("folderDescription", "")

                if not all([folder_name, task_name, product_name, variant]):
                    self.log.warning("Skipping incomplete row: %s", row)
                    continue

                # Create instance
                instance_data = {
                    "folderPath": f"/{folder_name}",
                    "task": task_name,
                    "productName": product_name,
                    "productVariant": variant,
                    "comment": comment
                }

                # Optional folder description
                if folder_description:
                    instance_data["folderAttributes"] = {
                        "description": folder_description
                    }

                instance = context.create_instance(
                    f"{folder_name}_{product_name}_{variant}",
                    **instance_data
                )

                self.log.info("Created instance: %s", instance)
