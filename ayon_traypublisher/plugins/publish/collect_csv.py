import pyblish.api
import csv
import os

from ayon_core.lib import prepare_template_data
from ayon_core.pipeline import registered_host
from ayon_core.pipeline.create import CreatorError


class CollectCSVFile(pyblish.api.ContextPlugin):
    """Collect instances from CSV file."""

    order = pyblish.api.CollectorOrder
    label = "CSV File"
    hosts = ["traypublisher"]

    def process(self, context):
        host = registered_host()
        new_instances = []
        folder_paths = set()

        csv_path = host.get_current_file_path()
        if not csv_path or not csv_path.endswith(".csv"):
            return

        with open(csv_path, newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Required columns
                folder_path = row.get("folderPath")
                product_name = row.get("productName")
                product_type = row.get("productType")
                if not all([folder_path, product_name, product_type]):
                    self.log.warning("Skipping row due missing required columns")
                    continue

                # Build instance data
                new_instance_data = {
                    "folderPath": folder_path,
                    "productName": product_name,
                    "productType": product_type,
                    "representations": []
                }

                # Optional: folder description
                folder_description = row.get("folderDescription", "").strip()
                if folder_description:
                    new_instance_data["folderDescription"] = folder_description

                # Collect other optional columns
                for key, value in row.items():
                    if key not in ("folderPath", "productName", "productType", "folderDescription"):
                        if value:
                            new_instance_data[key] = value

                new_instances.append(new_instance_data)
                folder_paths.add(folder_path)

        # Create instance objects
        for instance_data in new_instances:
            instance = context.create_instance(**instance_data)
            self.log.info(f"Created instance: {instance}")

        # Set folder descriptions on context (will be applied by other plugins)
        for folder_path in folder_paths:
            folder_descriptions = [
                inst["folderDescription"]
                for inst in new_instances
                if inst.get("folderDescription") and inst["folderPath"] == folder_path
            ]
            # Use the first non-empty description found
            if folder_descriptions:
                context.data["folder_data"][folder_path] = {
                    "description": folder_descriptions[0]
                }
            else:
                if "folder_data" not in context.data:
                    context.data["folder_data"] = {}
                context.data["folder_data"].setdefault(folder_path, {})
