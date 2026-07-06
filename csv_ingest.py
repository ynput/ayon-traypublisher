import csv
import logging
from typing import Dict, Any, List

from ayon_api import get_project, get_folder_by_path, create_folder, update_folder

log = logging.getLogger(__name__)


def ingest_csv(project_name: str, csv_path: str) -> None:
    """Ingest folder hierarchy from CSV, including descriptions.

    Expected CSV columns: 'folder', 'parent', 'description' (optional).
    The 'description' column is used to set the description on the folder entity.
    """
    project = get_project(project_name)
    if not project:
        raise ValueError(f"Project '{project_name}' not found.")

    with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            folder_name = row.get('folder', '').strip()
            parent_name = row.get('parent', '').strip() or None
            description = row.get('description', '').strip() or None

            if not folder_name:
                log.warning("Skipping row with empty folder name: %s", row)
                continue

            # Resolve parent path
            if parent_name:
                parent_path = f"{parent_name}/{folder_name}"
            else:
                parent_path = folder_name

            # Check if folder exists
            existing = get_folder_by_path(project_name, parent_path)
            if existing:
                if description is not None:
                    update_folder(project_name, existing['id'], description=description)
                    log.info(f"Updated description for folder '{parent_path}'")
            else:
                # Create folder
                folder_data = {
                    'name': folder_name,
                    'path': parent_path,
                    'parent': parent_name,
                    'description': description or '',
                }
                create_folder(project_name, folder_data)
                log.info(f"Created folder '{parent_path}'")
