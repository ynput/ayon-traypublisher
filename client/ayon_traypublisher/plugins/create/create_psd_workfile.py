# -*- coding: utf-8 -*-
import inspect
from typing import Optional

from ayon_core.lib import FileDef
from ayon_core.pipeline import (
    CreatedInstance,
    CreatorError,
)
from ayon_traypublisher.api.plugin import (
    TrayPublishCreator,
    HiddenTrayPublishCreator
)


class PSDWorkfileCreator(TrayPublishCreator):
    """Creates additional image publish instance for provided workfile."""

    identifier = "io.ayon.creators.traypublisher.psd_workfile_image.workfile"
    label = "PSD Workfile + Image"
    group_label = "Workfile"
    icon = "fa.file"
    description = (
        "Creates additional image publish instances for provided workfile."
    )
    product_type = "workfile"
    product_base_type = "workfile"
    settings_category = "traypublisher"

    default_variants = ["Main"]

    def get_detail_description(self):
        return inspect.cleandoc("""# Workfile + Image

        Basic creator that creates image publish instances alongside the main
        workfile instance. 
        
        Matches existing workflow in WebPublisher 
            ayon+settings://webpublisher/publish/CollectPublishedFiles/task_type_to_product_type/0/value/0/additional_product_types
    
        .psd workfile could be used both as `workfile` and `image` product.
        Different combos are not currently expected.
        """)

    def create(self, product_name, instance_data, pre_create_data):
        repr_file = pre_create_data.get("filepath")
        if not repr_file:
            raise CreatorError("No files specified")

        instance_data["creator_attributes"] = {
            "filepath": repr_file,
        }

        instance_data["default_variants"] = self.default_variants

        workfile_instance = CreatedInstance(
            self.product_type, product_name, instance_data, self
        )

        self._store_new_instance(workfile_instance)

        image_creator = self._get_hidden_creator(
            "io.ayon.creators.traypublisher.psd_workfile_image.image"
        )
        if not image_creator:
            raise CreatorError("Image creator not found")

        image_creator.create(None, instance_data)

    def _get_hidden_creator(self, identifier):
        creator = self.create_context.creators.get(identifier)
        if creator is None:
            self.log.debug(
                "Creator '%s' not found in create_context.creators", identifier
            )
        return creator

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "filepath",
                folders=False,
                extensions=[".psd"],
                allow_sequences=False,
                single_item=True,
                label="PSD file",
            )
        ]

    def get_instance_attr_defs(self):
        return self.get_pre_create_attr_defs()


class ImageComboCreator(HiddenTrayPublishCreator):
    """Creates image instance."""

    identifier = "io.ayon.creators.traypublisher.psd_workfile_image.image"
    label = "Image"
    host_name = "traypublisher"
    product_type = "image"
    product_base_type = "image"

    def create(self, _product_name, instance_data):
        project_entity = self.create_context.get_current_project_entity()
        folder_path: str = instance_data["folderPath"]
        task_name: Optional[str] = instance_data.get("task")
        # get_current_folder_entity returns None
        folder_entity = self.create_context.get_folder_entity(folder_path)
        task_entity = self.create_context.get_task_entity(
            folder_path, task_name
        )

        project_name = project_entity["name"]
        host_name = self.create_context.host_name

        variant = (
            instance_data.get("variant") or
            next(iter(instance_data["default_variants"]), None)
        )

        product_name = self.get_product_name(
            project_name=project_name,
            project_entity=project_entity,
            folder_entity=folder_entity,
            task_entity=task_entity,
            host_name=host_name,
            variant=variant
        )
        new_instance = CreatedInstance(
            self.product_type, product_name, instance_data, self
        )

        self._store_new_instance(new_instance)

        return new_instance

    def get_instance_attr_defs(self):
        return [
            FileDef(
                "filepath",
                folders=False,
                extensions=[".psd"],
                allow_sequences=False,
                single_item=True,
                label="PSD file",
            )
        ]
