import inspect
import os
from typing import Optional

import clique

from ayon_core.lib import (
    FileDef,
    BoolDef,
    EnumDef,
    TextDef,
    UILabelDef,
    UISeparatorDef,
)

from ayon_traypublisher.api.plugin import TrayPublishCreator


class BatchInstanceCreator(TrayPublishCreator):
    """Creates instances from texture sets.

    Intended for full texture sets for an asset.
    """
    identifier = "batch_instances"
    label = "Batch Split"
    product_type = "batch"
    description = "Publish batch of files as separate instances"

    # Position batch creator after simple creators
    icon = "mdi.folder-multiple-image"
    order = 110

    extensions = {"png", "jpg", "jpeg", "tiff", "tif", "exr"}

    def create(self, product_name, data, pre_create_data):
        file_paths = pre_create_data.get("filepath")
        if not file_paths:
            return

        folder_path: str = data["folderPath"]
        task_name: Optional[str] = data.get("task")
        folder_entity = self.create_context.get_folder_entity(folder_path)
        task_entity = self.create_context.get_task_entity(folder_path,
                                                          task_name)

        # All files
        files = []
        for file_info in file_paths:
            files.extend(file_info["filenames"])
        common_prefix = os.path.commonprefix(files)
        common_suffix = os.path.commonprefix(
            [fname[::-1] for fname in files]
        )[::-1]
        self.log.debug("Found common prefix: %s", common_prefix)

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
                assert len(collections) == 1
                basename = collections[0].format("{head}").rstrip("._")
            else:
                assert len(remainder) == 1
                basename = os.path.splitext(remainder[0])[0]

            if pre_create_data["strip_common_prefix"]:
                # Remove common prefix from the variant name
                basename = basename.removeprefix(common_prefix)
            if pre_create_data["strip_common_suffix"]:
                # Remove common suffix from the variant name
                basename = basename.removesuffix(common_suffix)

            prefix = pre_create_data.get("prefix", "")
            suffix = pre_create_data.get("suffix", "")
            variant = "{}{}{}".format(prefix, basename, suffix)

            self.create_context.create(
                creator_identifier=pre_create_data["creator_type"],
                folder_entity=folder_entity,
                task_entity=task_entity,
                variant=variant,
                pre_create_data={
                    "representation_files": [file_info]
                }
            )

    def get_pre_create_attr_defs(self):
        from ayon_traypublisher.api.plugin import SettingsCreator

        items = []
        for creator in self.create_context.creators.values():
            if isinstance(creator, SettingsCreator):
                items.append({
                    "label": creator.label,
                    "value": creator.identifier
                })

        return [
            FileDef(
                "filepath",
                folders=False,
                single_item=False,
                extensions=self.extensions,
                allow_sequences=True,
                label="Files"
            ),
            EnumDef(
                "creator_type",
                items=items,
                label="Publish Type",
                default="settings_render",
                tooltip=(
                    "The Simple Creator (publish type) to create instances "
                    "with."
                )
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
                    "Remove suffix prefix from the variant name.\n\n"
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

    def get_detail_description(self):
        return inspect.cleandoc("""# Publish batch of files

        This can be used to quickly create publish instances for a set of files
        where the filenames then define the variant names. For example, using
        a texture set:
        - asset_diffuse.1001-1004.exr
        - asset_specular.1001-1004.exr
        
        The batch instance creator can then quickly generate a "diffuse" and
        "specular" instance accordingly.
        """)
