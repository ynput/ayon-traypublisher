# -*- coding: utf-8 -*-
"""CSV collector for tray publisher."""

import csv
import pyblish.api

from ayon_core.pipeline import KnownPublishError
from ayon_core.pipeline.create import get_product_name_from_context


class CollectCSV(pyblish.api.ContextPlugin):
    """Collect instances from a CSV file."""

    order = pyblish.api.CollectorOrder
    label = "Collect CSV"

    def process(self, context):
        # Get CSV file path from context data
        csv_path = context.data.get("csvFilePath")
        if not csv_path:
            raise KnownPublishError("No CSV file path provided.")

        # Read CSV file
        with open(csv_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Required columns
                folder_path = row.get("Folder")
                product_name = row.get("Product")
                family = row.get("Family")
                if not all([folder_path, product_name, family]):
                    raise KnownPublishError(
                        "CSV row missing required columns: Folder, Product, Family"
                    )

                # Folder description (new feature)
                folder_description = row.get("FolderDescription", "")

                # Create folder entity
                folder_entity = context.create_instance(
                    folder_path,
                    family="folder",
                )
                folder_entity.data["folderPath"] = folder_path
                folder_entity.data["folderDescription"] = folder_description

                # Create product instance
                product_data = {
                    "folderPath": folder_path,
                    "productName": product_name,
                    "family": family,
                    "representations": [],
                }
                product_instance = context.create_instance(
                    product_name,
                    family=family,
                    data=product_data,
                )

                # Optional columns
                description = row.get("Description", "")
                product_instance.data["description"] = description

                # Additional custom columns can be mapped via settings
                custom_attrs = context.data.get("customAttributes", {})
                for attr_name, attr_col in custom_attrs.items():
                    if attr_col in row:
                        product_instance.data[attr_name] = row[attr_col]

        self.log.info("Collected {} instances from CSV.".format(len(context)))
