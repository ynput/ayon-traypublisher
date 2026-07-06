"""CSV ingest module for creating folders with optional description."""

import csv
import os
from ayon_api import get_project, get_folder_by_name, create_folder, update_folder

def ingest_csv(csv_path, project_name, user):
    """Ingest CSV file and create/update folders.

    Expected columns: folder, description (optional), product, version, etc.
    """
    project = get_project(project_name)
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            folder_name = row.get('folder')
            description = row.get('description', '').strip()
            # Check if folder exists
            existing = get_folder_by_name(project_name, folder_name)
            if existing:
                if description:
                    update_folder(project_name, existing['id'], {
                        'attrib': {'description': description}
                    })
            else:
                folder_data = {
                    'name': folder_name,
                    'folderType': 'Folder',
                    'parentId': project['folder']['id'],
                    'attrib': {}
                }
                if description:
                    folder_data['attrib']['description'] = description
                create_folder(project_name, folder_data)
            # Continue with product/version creation as before...
            # (omitted for brevity)
