import csv
import os
from ayon_core.pipeline import publish
from ayon_core.lib import Logger

log = Logger.get_logger(__name__)


class CSVFolderIngest(publish.Plugin):
    """Ingest folders from a CSV file, supporting optional description column."""

    # Column names (case-insensitive)
    COLUMN_NAME = "folder_name"
    COLUMN_DESCRIPTION = "folder_description"

    def process(self, instance):
        filepath = instance.data.get("csvFilePath")
        if not filepath or not os.path.exists(filepath):
            log.warning("No CSV file path provided. Skipping.")
            return

        with open(filepath, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                log.error("CSV file has no headers.")
                return

            # Normalize headers to lowercase for case-insensitive matching
            normalized_headers = {h.strip().lower(): h for h in reader.fieldnames}
            name_col = normalized_headers.get(self.COLUMN_NAME.lower())
            desc_col = normalized_headers.get(self.COLUMN_DESCRIPTION.lower())

            if not name_col:
                log.error(f"CSV must have a '{self.COLUMN_NAME}' column.")
                return

            for row in reader:
                folder_name = row.get(name_col, "").strip()
                if not folder_name:
                    log.warning("Empty folder name encountered, skipping row.")
                    continue

                # Prepare folder data
                folder_data = {
                    "name": folder_name,
                    "label": folder_name,
                    "parent_id": instance.data.get("folderEntityId"),
                }

                # Extract description if column exists
                if desc_col and desc_col in row:
                    description = row[desc_col].strip()
                    if description:
                        folder_data["description"] = description

                # Create folder using AYON API
                # This assumes 'create_folder' is available via the project manager or context
                context = instance.data.get("context")
                if context:
                    project_name = context.get("projectName")
                    if project_name:
                        folder_id = context.create_folder(project_name, folder_data)
                        log.info(f"Created folder '{folder_name}' with id {folder_id}")
                    else:
                        log.error("No project name in context.")
                else:
                    log.error("No context available in instance data.")
