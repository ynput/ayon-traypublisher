import copy
import os
import re
import collections
from typing import Any, Optional

import ayon_api

from ayon_core.lib import (
    FileDef,
    BoolDef,
    EnumDef,
)
from ayon_core.pipeline import (
    CreatedInstance,
    CreatorError
)
from ayon_core.pipeline.create import (
    get_product_name,
    TaskNotSetError,
)

from ayon_traypublisher.api.plugin import TrayPublishCreator
from ayon_traypublisher.batch_parsing import (
    get_folder_entity_from_filename
)


class BatchMovieCreator(TrayPublishCreator):
    """Creates instances from movie file(s).

    Intended for .mov files, but should work for any video file.
    Doesn't handle image sequences though.
    """
    identifier = "render_movie_batch"
    label = "Batch Movies"
    product_base_type = "render"
    product_type = product_base_type
    description = "Publish batch of video files"

    create_allow_context_change = False
    version_regex = re.compile(r"^(.+)_v([0-9]+)$")
    # Position batch creator after simple creators
    order = 110
    product_types = []

    def get_icon(self):
        return "fa.file"

    def create(self, product_name, data, pre_create_data):
        file_paths = pre_create_data.get("filepath")
        if not file_paths:
            return

        data_by_folder_id = collections.defaultdict(list)
        for file_info in file_paths:
            instance_data = copy.deepcopy(data)
            file_name = file_info["filenames"][0]
            filepath = os.path.join(file_info["directory"], file_name)
            instance_data["creator_attributes"] = {"filepath": filepath}

            folder_entity, version = get_folder_entity_from_filename(
                self.project_name, file_name, self.version_regex
            )

            if version:
                instance_data["version"] = version

            if not folder_entity:
                raise CreatorError(
                    f"Couldn't find folder entity for '{file_name}'"
                )
                continue
            data_by_folder_id[folder_entity["id"]].append(
                (instance_data, folder_entity)
            )

        all_task_entities = ayon_api.get_tasks(
            self.project_name, folder_ids=set(data_by_folder_id.keys())
        )
        task_entity_by_folder_id = collections.defaultdict(dict)
        for task_entity in all_task_entities:
            folder_id = task_entity["folderId"]
            task_name = task_entity["name"].lower()
            task_entity_by_folder_id[folder_id][task_name] = task_entity

        project_entity = self.create_context.get_current_project_entity()
        project_settings = self.create_context.get_current_project_settings()
        for folder_id, instance_tuples in data_by_folder_id.items():
            for (instance_data, folder_entity) in instance_tuples:
                task_entities_by_name = task_entity_by_folder_id[folder_id]
                task_name = None
                task_entity = None
                for default_task_name in self.default_tasks:
                    _name = default_task_name.lower()
                    if _name in task_entities_by_name:
                        task_entity = task_entities_by_name[_name]
                        task_name = task_entity["name"]
                        break
                product_type = instance_data.get("productType")
                if not product_type:
                    product_type = self.product_base_type
                product_name = self._get_product_name(
                    self.project_name,
                    project_settings,
                    project_entity,
                    folder_entity,
                    task_entity,
                    data["variant"],
                    product_type,
                )

                instance_data["folderPath"] = folder_entity["path"]
                instance_data["task"] = task_name

                # Create new instance
                new_instance = CreatedInstance(
                    product_base_type=self.product_base_type,
                    product_type=product_type,
                    product_name=product_name,
                    data=instance_data,
                    creator=self,
                )
                self._store_new_instance(new_instance)

    def _get_product_name(
        self,
        project_name: str,
        project_settings: dict[str, Any],
        project_entity: dict[str, Any],
        folder_entity: dict[str, Any],
        task_entity: Optional[dict[str, Any]],
        variant: str,
        product_type: str,
    ) -> str:
        """Create product name according to standard template process"""
        kwargs = dict(
            project_name=project_name,
            project_entity=project_entity,
            folder_entity=folder_entity,
            task_entity=task_entity,
            product_base_type=self.product_base_type,
            product_type=product_type,
            variant=variant,
            host_name=self.create_context.host_name,
            project_settings=project_settings,
        )
        try:
            product_name = get_product_name(**kwargs)
        except TaskNotSetError:
            # Create instance with fake task
            # - instance will be marked as invalid so it can't be published
            #   but user have ability to change it
            # NOTE: This expect that there is not task 'Undefined' on folder
            kwargs["task_entity"] = {
                "type": "Undefined",
                "name": "Undefined",
                "label": "Undefined",
            }

            product_name = get_product_name(**kwargs)

        return product_name

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            )
        ]

    def get_pre_create_attr_defs(self):
        product_types = self.product_types
        if not product_types:
            product_types = ["render"]

        # Use same attributes as for instance attributes
        return [
            FileDef(
                "filepath",
                folders=False,
                single_item=False,
                extensions=self.extensions,
                allow_sequences=False,
                label="Filepath"
            ),
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            ),
            EnumDef(
                "product_type",
                items=product_types,
                label="Product type",
            ),
        ]

    def get_detail_description(self) -> str:
        return """# Publish batch of .mov to multiple folders.

        File names must then contain only folder name, or folder name + version.
        (eg. 'chair.mov', 'chair_v001.mov', not really safe `my_chair_v001.mov`
        """
