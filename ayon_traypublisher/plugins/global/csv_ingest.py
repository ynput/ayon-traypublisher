import csv
import io
from ayon_traypublisher.plugins.global.actions import GlobalAction


class CsvIngestAction(GlobalAction):
    """Ingest folder structure from CSV file.

    Supports optional 'folderDescription' column to set folder descriptions.
    """

    def __init__(self):
        super().__init__()
        self.label = "Ingest CSV"
        self.description = "Create folders from CSV file with optional descriptions"
        self.icon = "file-text-o"
        self.order = 100

    def execute(self, context, data=None):
        file_path = data.get("filePath")
        if not file_path:
            raise ValueError("No file path provided")

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no headers")

            required = ["folderName"]
            optional = ["folderPath", "folderType", "folderDescription"]
            for col in required:
                if col not in reader.fieldnames:
                    raise ValueError(f"Missing required column: {col}")

            for row in reader:
                folder_name = row["folderName"].strip()
                if not folder_name:
                    continue
                folder_path = row.get("folderPath", "").strip() or None
                folder_type = row.get("folderType", "Folder").strip()
                folder_description = row.get("folderDescription", "").strip() or None

                # Create folder using the API
                self._create_folder(
                    folder_name,
                    folder_path=folder_path,
                    folder_type=folder_type,
                    description=folder_description
                )

        return {"success": True, "message": "CSV ingest completed."}

    def _create_folder(self, name, folder_path=None, folder_type="Folder", description=None):
        """Create a folder via the AYON API."""
        import ayon_api

        project_name = ayon_api.get_current_project_name()
        # Build parent folder path if any
        parent_id = None
        if folder_path:
            parent_folder = ayon_api.get_folder_by_path(project_name, folder_path)
            if parent_folder:
                parent_id = parent_folder["id"]
            else:
                raise ValueError(f"Parent folder not found: {folder_path}")

        # Prepare folder data
        folder_data = {
            "name": name,
            "folderType": folder_type,
            "parentId": parent_id,
            "description": description or ""
        }
        # Remove None values
        folder_data = {k: v for k, v in folder_data.items() if v is not None}

        try:
            ayon_api.create_folder(project_name, folder_data)
        except Exception as e:
            raise RuntimeError(f"Failed to create folder '{name}': {e}")
