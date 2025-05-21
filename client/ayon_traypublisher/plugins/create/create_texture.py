# -*- coding: utf-8 -*-
import inspect
import os
import copy
from typing import Optional

import clique

from ayon_core.lib import (
    FileDef,
    BoolDef,
    TextDef,
    UILabelDef,
    UISeparatorDef,
)
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
    description = "Texture files or UDIM sequences"
    extensions = [".mov", ".mp4", ".mxf", ".m4v", ".mpg", ".exr",
                  ".dpx", ".tif", ".png", ".jpg"]

    def get_detail_description(self):
        return inspect.cleandoc("""# Textures

        This will create a publish instances for textures, that is 
        either a single image, a sequence of UDIM tiles or multiple sets of 
        textures (each either UDIMs or single image) - like 
        diffuse+normal+roughness maps combined.
        
        This can be used to quickly create publish instances for a set of files
        where the filenames then define the variant names. For example, using
        a texture set:
        - asset_diffuse.1001-1004.exr
        - asset_specular.1001-1004.exr
        
        Which then creates `diffuse` and `specular` variant textures as a
        result.
        """)

    def create(self, product_name, instance_data, pre_create_data):
        # TODO: Allow processing single sequence without complex logic?
        folder_path: str = instance_data["folderPath"]
        task_name: Optional[str] = instance_data.get("task")
        folder_entity = self.create_context.get_folder_entity(folder_path)
        task_entity = self.create_context.get_task_entity(folder_path,
                                                          task_name)

        file_paths = pre_create_data.get("representation_files", [])

        # All files
        files = []
        for file_info in file_paths:
            files.extend(file_info["filenames"])
        common_prefix = os.path.commonprefix(files)
        common_suffix = os.path.commonprefix(
            [fname[::-1] for fname in files]
        )[::-1]
        self.log.debug("Found common prefix: %s", common_prefix)

        strip_common_prefix: bool = pre_create_data.pop(
            "strip_common_prefix", False)
        strip_common_suffix: bool = pre_create_data.pop(
            "strip_common_suffix", False)
        prefix = pre_create_data.pop("prefix", "")
        suffix = pre_create_data.pop("suffix", "")

        # Process the filepaths to individual instances
        for file_info in file_paths:
            filenames = file_info["filenames"]

            # clique.PATTERNS["frames"] but also allow `_` before digits
            pattern = r"[._](?P<index>(?P<padding>0*)\d+)\.\D+\d?$"
            collections, remainder = clique.assemble(
                filenames,
                minimum_items=1,
                assume_padded_when_ambiguous=True,
                patterns=[pattern],
            )
            if collections:
                if len(collections) != 1:
                    raise ValueError(
                        f"Expected exactly one collection, but found {len(collections)}."
                    )
                basename = collections[0].format("{head}").rstrip("._")
            else:
                if len(remainder) != 1:
                    raise ValueError(
                        f"Expected exactly one remaining file, but found {len(remainder)}."
                    )
                basename = os.path.splitext(remainder[0])[0]

            if strip_common_prefix:
                # Remove common prefix from the variant name
                basename = basename.removeprefix(common_prefix)
            if strip_common_suffix:
                # Remove common suffix from the variant name
                basename = basename.removesuffix(common_suffix)
            variant = "{}{}{}".format(prefix, basename, suffix)

            product_name = self.get_product_name(
                self.project_name,
                folder_entity,
                task_entity,
                variant,
                host_name=self.host_name,
            )
            _pre_create_data = copy.deepcopy(pre_create_data)
            _pre_create_data["representation_files"] = file_info
            _instance_data = copy.deepcopy(instance_data)
            _instance_data["variant"] = variant
            self._create_instance(
                product_name=product_name,
                instance_data=_instance_data,
                pre_create_data=_pre_create_data
            )

    def _create_instance(self, product_name, instance_data, pre_create_data):
        repr_file = pre_create_data.get("representation_files")
        if not repr_file:
            raise CreatorError("No files specified")

        # Pass pre-create attributes to instance creator attributes
        instance_data["creator_attributes"] = pre_create_data

        # Trigger the dedicated `texture_creator` collector plug-in
        instance_data.setdefault("families", []).append("texture_creator")

        # Create new instance
        new_instance = CreatedInstance(self.product_type, product_name,
                                       instance_data, self)
        self._store_new_instance(new_instance)

    def get_instance_attr_defs(self):
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
            ),
        ]

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "representation_files",
                folders=False,
                extensions=self.extensions,
                allow_sequences=True,
                single_item=False,
                label="Representations",
            ),
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            ),
            UISeparatorDef("_additionals"),
            UILabelDef("<b>Variant Name Options</b>"),
            BoolDef(
                "strip_common_prefix",
                default=True,
                label="Strip Common Prefix",
                tooltip=(
                    "Remove common prefix from the variant name.\n\n"
                    "This is useful when publishing a batch of textures "
                    "for an asset that all start with the asset name.\n"
                    "By stripping the common prefix, the variant name will "
                    "then exclude the asset name."
                )
            ),
            BoolDef(
                "strip_common_suffix",
                default=True,
                label="Strip Common Suffix",
                tooltip=(
                    "Remove common suffix from the variant name.\n\n"
                    "This is useful when publishing a batch of files "
                    "that all end with a similar suffix.\n"
                    "By stripping the common suffix, the variant name will "
                    "then exclude that part."
                )
            ),
            TextDef(
                "prefix",
                default="",
                label="Add prefix",
                tooltip=(
                    "Add a common prefix to all variant names."
                )
            ),
            TextDef(
                "suffix",
                default="",
                label="Add suffix",
                tooltip=(
                    "Add a common suffix to all variant names."
                )
            ),
        ]