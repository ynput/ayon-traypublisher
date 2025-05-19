# -*- coding: utf-8 -*-
import inspect

from ayon_core.lib.attribute_definitions import FileDef, BoolDef
from ayon_core.pipeline import (
    CreatedInstance,
    CreatorError
)
from ayon_traypublisher.api.plugin import TrayPublishCreator


class TextureCreator(TrayPublishCreator):
    """Creates texture instances from files, supporting UDIM sequences."""

    identifier = "io.ayon.creators.traypublisher.texture"
    label = "Texture"
    product_type = "texture"
    icon = "fa.file"
    description = "Single texture file or UDIM sequence"
    extensions = [".mov", ".mp4", ".mxf", ".m4v", ".mpg", ".exr",
                  ".dpx", ".tif", ".png", ".jpg"]

    def get_detail_description(self):
        return inspect.cleandoc("""# Single texture instance.

        This will create a single publish instance for a texture, that is 
        either a single image or a sequence of UDIM tiles. As such, this is not
        multiples - like diffuse+normal+roughness maps combined. Those would
        each need to go into their own instance.
        
        You can use a batch instance creator to quickly create multiple
        instances if you have many textures of a Texture Set to publish, like
        separate diffuse, normal and roughness images or UDIM sequences.
        """)

    def create(self, product_name, instance_data, pre_create_data):
        repr_file = pre_create_data.get("representation_files")
        if not repr_file:
            raise CreatorError("No files specified")

        # Trigger the dedicated `texture_creator` collector plug-in
        instance_data.setdefault("families", []).append("texture_creator")

        # Create new instance
        new_instance = CreatedInstance(self.product_type, product_name,
                                       instance_data, self)
        self._store_new_instance(new_instance)

    def get_instance_attr_defs(self):
        return self.get_pre_create_attr_defs()

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "representation_files",
                folders=False,
                extensions=self.extensions,
                allow_sequences=True,
                single_item=True,
                label="Representation",
            ),
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            )
        ]
