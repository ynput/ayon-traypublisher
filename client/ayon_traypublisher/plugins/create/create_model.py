# -*- coding: utf-8 -*-
"""Creator of model files.

This creator is used to publish model files with specific orientation and units.
"""

from pathlib import Path

import ayon_api

from ayon_core.lib.attribute_definitions import (
    FileDef,
    EnumDef,
    NumberDef,
    TextDef,
    UISeparatorDef,
)
from ayon_core.lib.transcoding import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from ayon_core.pipeline import CreatedInstance, CreatorError
from ayon_traypublisher.api.plugin import TrayPublishCreator


MODEL_KEY_PREFIX = "abs_model_path"
UP_AXIS_KEY_PREFIX = "up_axis"
HANDEDNESS_KEY_PREFIX = "handedness"
METERS_PER_UNIT_KEY_PREFIX = "meters_per_unit"


class CreateModel(TrayPublishCreator):
    """Creates model files."""

    identifier = "io.ayon.creators.traypublisher.model"
    label = "Model"
    icon = "fa.cubes"
    product_base_type = "model"
    product_type = product_base_type
    description = "Publishes model file."
    extensions = [
        ".ma",
        ".mb",
        ".obj",
        ".abc",
        ".fbx",
        ".bgeo",
        ".bgeogz",
        ".bgeosc",
        ".usd",
        ".blend",
    ]

    def get_detail_description(self):
        return """# Model

This creator publishes model files.
        """

    def create(self, product_name, instance_data, pre_create_data):
        repr_files = pre_create_data.get("models_file")
        if not repr_files:
            raise CreatorError("No files specified")

        reviewable = pre_create_data.get("reviewable")

        folder_path = instance_data["folderPath"]
        task_name = instance_data["task"]
        folder_entity = ayon_api.get_folder_by_path(self.project_name, folder_path)

        task_entity = None
        if task_name:
            task_entity = ayon_api.get_task_by_name(
                self.project_name, folder_entity["id"], task_name
            )

        product_type = instance_data.get("productType")
        if not product_type:
            product_type = self.product_base_type

        product_name = self.get_product_name(
            project_name=self.project_name,
            folder_entity=folder_entity,
            task_entity=task_entity,
            variant=instance_data["variant"],
            product_type=product_type,
        )

        instance_data["creator_attributes"] = {}
        if reviewable and reviewable["filenames"]:
            instance_data["creator_attributes"]["abs_reviewable_path"] = (
                Path(reviewable["directory"]) / reviewable["filenames"][0]
            ).as_posix()
        for idx, repr_file in enumerate(repr_files):
            files = repr_file.get("filenames")
            if not files:
                # this should never happen
                raise CreatorError("Missing files from representation")

            instance_data["creator_attributes"][f"{MODEL_KEY_PREFIX}_{idx}"] = (
                Path(repr_file["directory"]) / files[0]
            ).as_posix()

        # Create new instance
        new_instance = CreatedInstance(
            product_base_type=self.product_base_type,
            product_type=product_type,
            product_name=product_name,
            data=instance_data,
            creator=self,
        )

        self._store_new_instance(new_instance)

    def get_attr_defs_for_instance(self, instance):
        attrs = [
            TextDef("abs_reviewable_path", label="Reviewable"),
        ]
        for (
            idx,
            _,
        ) in enumerate(
            key
            for key in instance.data["creator_attributes"]
            if key.startswith(MODEL_KEY_PREFIX)
        ):
            attrs.extend(
                (
                    UISeparatorDef(f"separator_{idx}"),
                    TextDef(f"{MODEL_KEY_PREFIX}_{idx}", label="Model Path"),
                    EnumDef(
                        f"{UP_AXIS_KEY_PREFIX}_{idx}",
                        tuple("XYZ"),
                        default="Z",
                        label="Up Axis",
                    ),
                    EnumDef(
                        f"{HANDEDNESS_KEY_PREFIX}_{idx}",
                        ("left", "right"),
                        default="right",
                        label="Handedness",
                    ),
                    NumberDef(
                        f"{METERS_PER_UNIT_KEY_PREFIX}_{idx}",
                        minimum=1 / 10**9,
                        maximum=10**9,
                        default=1.0,
                        label="Meters per Unit",
                    ),
                )
            )
        return attrs

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "models_file",
                folders=False,
                extensions=self.extensions,
                allow_sequences=False,
                single_item=False,
                label="Model File(s)",
            ),
            FileDef(
                "reviewable",
                folders=False,
                extensions=set(IMAGE_EXTENSIONS) | set(VIDEO_EXTENSIONS),
                allow_sequences=True,
                single_item=True,
                label="Reviewable representations",
                extensions_label="Single reviewable item",
            ),
        ]
