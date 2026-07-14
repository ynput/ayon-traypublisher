# -*- coding: utf-8 -*-
"""Creator of model files.

This creator is used to publish model files with specific orientation and units.
"""

from pathlib import Path

from ayon_core.lib.attribute_definitions import (
    FileDef,
    EnumDef,
    NumberDef,
    TextDef,
)
from ayon_core.lib.transcoding import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from ayon_core.pipeline import CreatedInstance, CreatorError
from ayon_traypublisher.api.plugin import TrayPublishCreator


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
        repr_file = pre_create_data.get("model_file")
        if not repr_file:
            raise CreatorError("No file specified")

        reviewable = pre_create_data.get("reviewable")

        product_type = instance_data.get("productType")
        if not product_type:
            product_type = self.product_base_type

        instance_data["creator_attributes"] = {}
        if reviewable and reviewable["filenames"]:
            instance_data["creator_attributes"]["abs_reviewable_path"] = (
                Path(reviewable["directory"]) / reviewable["filenames"][0]
            ).as_posix()
        files = repr_file.get("filenames")
        if not files:
            # this should never happen
            raise CreatorError("Missing files from representation")

        instance_data["creator_attributes"]["abs_model_path"] = (
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
        return (
            TextDef("abs_reviewable_path", label="Reviewable"),
            TextDef("abs_model_path", label="Model Path"),
            EnumDef(
                "up_axis",
                tuple("XYZ"),
                default="Z",
                label="Up Axis",
            ),
            EnumDef(
                "handedness",
                ("left", "right"),
                default="right",
                label="Handedness",
            ),
            NumberDef(
                "meters_per_unit",
                minimum=1 / 10**9,
                maximum=10**9,
                default=1.0,
                label="Meters per Unit",
            ),
        )

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "model_file",
                folders=False,
                extensions=self.extensions,
                allow_sequences=False,
                single_item=True,
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
