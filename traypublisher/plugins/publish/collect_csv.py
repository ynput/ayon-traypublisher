import csv
import os
from pprint import pformat

import pyblish.api

from ayon_core.pipeline import AYONPyblishPluginMixin
from ayon_core.lib import BoolDef
from ayon_traypublisher import constants


class CollectCSV(pyblish.api.ContextPlugin, AYONPyblishPluginMixin):
    """Collect CSV rows as instances."""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Collect CSV"
    hosts = ["traypublisher"]

    def process(self, context):
        # Determine file path
        csv_path = context.data.get("csvFilePath")
        if not csv_path:
            self.log.warning("No CSV file path provided.")
            return

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            if reader.fieldnames is None:
                self.log.warning("CSV file has no columns.")
                return

            # Normalize column names to lowercase for case-insensitive matching
            normalized_fieldnames = [f.lower().strip() for f in reader.fieldnames]

            supported_columns = {
                "folder": ["folder", "foldername"],
                "task": ["task", "taskname"],
                "product_type": ["producttype", "product_type"],
                "product_name": ["productname", "product_name"],
                "family": ["family"],
                "description": ["description", "folder_description", "folderdescription"],
            }

            # Map actual column names to canonical keys
            column_mapping = {}
            for col in reader.fieldnames:
                col_lower = col.lower().strip()
                for canonical, aliases in supported_columns.items():
                    if col_lower in aliases:
                        column_mapping[canonical] = col
                        break

            # Validate required columns
            if "folder" not in column_mapping:
                raise ValueError("CSV file must contain a 'folder' column.")

            for row in reader:
                folder_name = row.get(column_mapping.get("folder", "")).strip()
                if not folder_name:
                    continue

                task_name = row.get(column_mapping.get("task", ""), "").strip()
                product_type = row.get(column_mapping.get("product_type", ""), "").strip()
                product_name = row.get(column_mapping.get("product_name", ""), "").strip()
                family = row.get(column_mapping.get("family", ""), "").strip()
                description = row.get(column_mapping.get("description", ""), "").strip()

                # Create data for folder
                folder_data = {
                    "name": folder_name,
                    "label": folder_name,
                    "description": description or None,  # Empty string becomes None
                }

                # If there's a task, include it in folder data
                if task_name:
                    folder_data["taskName"] = task_name

                # Create instance representing this row
                instance = context.create_instance(folder_name)
                instance.data["folderData"] = folder_data
                instance.data["productType"] = product_type or "workfile"
                instance.data["productName"] = product_name or folder_name
                if family:
                    instance.data["family"] = family

                self.log.info(
                    f"Collected folder '{folder_name}' with description "
                    f"'{description}'"
                )

        # Store parsed data back into context
        context.data["csvInstances"] = [
            inst.data for inst in context
        ]

        self.log.debug(
            f"CSV ingest collected: {pformat(context.data['csvInstances'])}"
        )
