import csv
import os
from ayon_core.pipeline.publish import PublishValidationError
from ayon_traypublisher.plugins.publish.extract_base import ExtractBase

class ExtractCsvIngest(ExtractBase):
    """Extract instances from CSV file with folder description support."""

    def process(self, instance):
        csv_path = instance.data.get("csvPath")
        if not csv_path or not os.path.exists(csv_path):
            raise PublishValidationError("CSV file path not found.")

        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            required_fields = {"folderPath", "productName"}
            if not required_fields.issubset(set(reader.fieldnames)):
                raise PublishValidationError(
                    "CSV must contain 'folderPath' and 'productName' columns."
                )

            for row in reader:
                folder_path = row["folderPath"].strip()
                product_name = row["productName"].strip()
                description = row.get("description", "").strip()

                # Create or get folder
                folder = instance.data["projectEntity"].get_folder_by_path(folder_path)
                if not folder:
                    folder_data = {
                        "path": folder_path,
                        "label": row.get("folderLabel", "") or folder_path,
                        "thumbnailId": None
                    }
                    # Set description if provided
                    if description:
                        folder_data["description"] = description
                    folder = instance.data["projectEntity"].create_folder(folder_data)
                else:
                    # Update description if column exists and folder exists
                    if description and "description" in row:
                        folder["description"] = description
                        instance.data["projectEntity"].update_folder(folder)

                # Create product
                product_data = {
                    "folderId": folder["id"],
                    "name": product_name,
                    "description": description if description else None
                }
                instance.data["projectEntity"].create_product(product_data)

        self.log.info("CSV ingest with folder description completed.")