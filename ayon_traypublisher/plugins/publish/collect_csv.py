import csv
import logging
import pyblish.api
from ayon_core.lib import BoolDef
from ayon_traypublisher.plugins.publish.collect_base import BaseCollector

log = logging.getLogger(__name__)


class CollectCSV(BaseCollector):
    """Collect data from a CSV file for AYON publishing.

    Expects a CSV file with columns: hierarchy, task, description (optional).
    The hierarchy column defines the folder path (e.g., "Folder/Subfolder").
    The task column defines tasks to be created on the leaf folder.
    The description column (if present) sets the folder's description.
    """

    label = "Collect CSV"
    order = pyblish.api.CollectorOrder

    def process(self, context):
        context.data["csv_folder_occurrences"] = {}
        file_path = context.data.get("csvFilePath")
        if not file_path:
            log.debug("No CSV file path provided.")
            return

        with open(file_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            # Determine columns
            fieldnames = reader.fieldnames
            if not fieldnames:
                log.warning("CSV file is empty or has no headers.")
                return

            has_description = "description" in [f.strip().lower() for f in fieldnames]
            # Normalize header names
            normalized_headers = {}
            for f in fieldnames:
                normalized_headers[f.strip().lower()] = f

            required = ["hierarchy"]
            if not all(h in normalized_headers for h in required):
                log.error("CSV must contain at least 'hierarchy' column.")
                return

            for row_num, row in enumerate(reader, start=2):
                hierarchy = row.get(normalized_headers["hierarchy"], "").strip()
                if not hierarchy:
                    continue

                # Build folder path list
                folders = hierarchy.split("/")
                current_ancestors = []
                for idx, folder_name in enumerate(folders):
                    folder_name = folder_name.strip()
                    if not folder_name:
                        continue
                    # Construct full path
                    path_items = current_ancestors + [folder_name]
                    full_path = "/".join(path_items)
                    # Check if folder already processed
                    occurrences = context.data["csv_folder_occurrences"]
                    if full_path in occurrences:
                        # Folder already exists, just add tasks if on leaf
                        pass
                    else:
                        # Create new folder instance
                        folder_data = {
                            "name": folder_name,
                            "path": full_path,
                            "tasks": [],
                        }
                        # If description column exists and we are on leaf (last folder in row), set description
                        if has_description and idx == len(folders) - 1:
                            desc_key = normalized_headers.get("description")
                            if desc_key:
                                desc = row.get(desc_key, "").strip()
                                if desc:
                                    folder_data["description"] = desc
                        # Set hierarchy parent
                        if idx == 0:
                            folder_data["parent"] = None
                        else:
                            folder_data["parent"] = "/".join(current_ancestors)
                        occurrences[full_path] = folder_data
                        log.debug("Created folder: {} ({})".format(full_path, folder_data.get("description", "")))

                    current_ancestors.append(folder_name)

                # Handle tasks on leaf folder
                leaf_path = "/".join(folders)
                leaf_folder = occurrences.get(leaf_path)
                if leaf_folder and "task" in normalized_headers:
                    task_name = row.get(normalized_headers["task"], "").strip()
                    if task_name:
                        leaf_folder["tasks"].append(task_name)

        # Convert collected data to instances
        for full_path, folder_data in context.data["csv_folder_occurrences"].items():
            instance = context.create_instance(name=full_path)
            instance.data["folderPath"] = folder_data["path"]
            instance.data["folderName"] = folder_data["name"]
            instance.data["tasks"] = folder_data["tasks"]
            instance.data["description"] = folder_data.get("description", "")
            instance.data["parent"] = folder_data.get("parent")
            # Add to context for further processing
