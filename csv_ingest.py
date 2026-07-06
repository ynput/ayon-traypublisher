import csv
import os
from ayon_api import get_project, create_folder, update_folder
from ayon_traypublisher.plugins import BaseIngestPlugin

class CSVIngestPlugin(BaseIngestPlugin):
    """Plugin to ingest folders from a CSV file with optional description."""

    column_mapping = {
        "folder_path": "path",
        "folder_name": "name",
        "folder_description": "description",  # new mapping
        "folder_type": "folderType",
        "parent_path": "parentPath",
        "attrib_values": "attrib"
    }

    def ingest(self, filepath, project_name, **kwargs):
        project = get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        with open(filepath, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Normalize keys (strip and lowercase)
                row_normalized = {k.strip().lower(): v.strip() for k, v in row.items()}
                folder_data = {}
                for csv_col, internal_col in self.column_mapping.items():
                    value = row_normalized.get(csv_col)
                    if value:
                        folder_data[internal_col] = value

                if not folder_data:
                    continue

                # Determine parent path
                parent_path = folder_data.get("parentPath", "")
                if parent_path:
                    parent_path = parent_path.lstrip("/")
                folder_path = folder_data.get("path", "")
                if not folder_path and folder_data.get("name"):
                    # Build path from parent and name
                    if parent_path:
                        folder_path = f"{parent_path}/{folder_data['name']}"
                    else:
                        folder_path = folder_data['name']

                # Check if folder already exists
                existing_folder = self.get_folder_by_path(project_name, folder_path)
                if existing_folder:
                    # Optionally update description
                    description = folder_data.get("description")
                    if description:
                        update_folder(project_name, existing_folder["id"], description=description)
                    continue

                # Create folder
                folder_type = folder_data.get("folderType", "Folder")
                attributes = folder_data.get("attrib", {})
                new_folder = create_folder(
                    project_name,
                    folder_path,
                    folder_type=folder_type,
                    parent_path=parent_path,
                    attributes=attributes,
                    description=folder_data.get("description", "")
                )
                self.log.info(f"Created folder: {folder_path}")

    def get_folder_by_path(self, project_name, path):
        """Helper to find folder by path. Implement as needed."""
        from ayon_api import get_folders
        folders = get_folders(project_name, folder_paths=[path])
        if folders:
            return folders[0]
        return None
