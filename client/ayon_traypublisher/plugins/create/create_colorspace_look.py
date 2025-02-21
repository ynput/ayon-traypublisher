# -*- coding: utf-8 -*-
"""Creator of colorspace look files.

This creator is used to publish colorspace look files thanks to
production type `ociolook`. All files are published as representation.
"""
from pathlib import Path
import ayon_api

from ayon_core.lib.attribute_definitions import (
    FileDef, EnumDef, TextDef, UISeparatorDef
)
from ayon_core.pipeline import (
    CreatedInstance,
    CreatorError
)
from ayon_core.pipeline.colorspace import (
    get_current_context_imageio_config_preset,
    get_ocio_config_colorspaces,
    get_colorspaces_enumerator_items,
)
from ayon_traypublisher.api.plugin import TrayPublishCreator


class CreateColorspaceLook(TrayPublishCreator):
    """Creates colorspace look files."""

    identifier = "io.ayon.creators.traypublisher.colorspace_look"
    label = "Colorspace Look"
    product_type = "ociolook"
    description = "Publishes color space look file."
    extensions = [".cc", ".cube", ".3dl", ".spi1d", ".spi3d", ".csp", ".lut"]
    enabled = False

    colorspace_items = [
        (None, "Not set")
    ]
    colorspace_attr_show = False
    config_items = None
    config_data = None

    def get_detail_description(self):
        return """# Colorspace Look

This creator publishes color space look file (LUT).
        """

    def get_icon(self):
        return "mdi.format-color-fill"

    def create(self, product_name, instance_data, pre_create_data):
        repr_file = pre_create_data.get("luts_file")
        if not repr_file:
            raise CreatorError("No files specified")

        files = repr_file.get("filenames")
        if not files:
            # this should never happen
            raise CreatorError("Missing files from representation")

        folder_path = instance_data["folderPath"]
        task_name = instance_data["task"]
        folder_entity = ayon_api.get_folder_by_path(
            self.project_name, folder_path)

        task_entity = None
        if task_name:
            task_entity = ayon_api.get_task_by_name(
                self.project_name, folder_entity["id"], task_name
            )

        product_name = self.get_product_name(
            project_name=self.project_name,
            folder_entity=folder_entity,
            task_entity=task_entity,
            variant=instance_data["variant"],
        )

        instance_data["creator_attributes"] = {
            "abs_lut_path": (
                Path(repr_file["directory"]) / files[0]).as_posix()
        }

        # Create new instance
        new_instance = CreatedInstance(self.product_type, product_name,
                                       instance_data, self)
        new_instance.transient_data["config_items"] = self.config_items
        new_instance.transient_data["config_data"] = self.config_data

        self._store_new_instance(new_instance)

    def collect_instances(self):
        super().collect_instances()
        for instance in self.create_context.instances:
            if instance.creator_identifier == self.identifier:
                instance.transient_data["config_items"] = self.config_items
                instance.transient_data["config_data"] = self.config_data

    def get_instance_attr_defs(self):
        return [
            EnumDef(
                "working_colorspace",
                self.colorspace_items,
                default="Not set",
                label="Working Colorspace",
            ),
            UISeparatorDef(
                label="Advanced1"
            ),
            TextDef(
                "abs_lut_path",
                label="LUT Path",
            ),
            EnumDef(
                "input_colorspace",
                self.colorspace_items,
                default="Not set",
                label="Input Colorspace",
            ),
            EnumDef(
                "direction",
                [
                    (None, "Not set"),
                    ("forward", "Forward"),
                    ("inverse", "Inverse")
                ],
                default="Not set",
                label="Direction"
            ),
            EnumDef(
                "interpolation",
                [
                    (None, "Not set"),
                    ("linear", "Linear"),
                    ("tetrahedral", "Tetrahedral"),
                    ("best", "Best"),
                    ("nearest", "Nearest")
                ],
                default="Not set",
                label="Interpolation"
            ),
            EnumDef(
                "output_colorspace",
                self.colorspace_items,
                default="Not set",
                label="Output Colorspace",
            ),
        ]

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "luts_file",
                folders=False,
                extensions=self.extensions,
                allow_sequences=False,
                single_item=True,
                label="Look Files",
            )
        ]

    def apply_settings(self, project_settings):
        config_data = None
        try:
            # This might crash because config path is not available
            #   for the machine
            config_data = get_current_context_imageio_config_preset(
                project_settings=project_settings
            )
        except Exception:
            self.log.warning(
                "Failed to get imageio config preset for current context",
                exc_info=True
            )

        if not config_data:
            self.enabled = False
            return

        filepath = config_data["path"]
        config_items = get_ocio_config_colorspaces(filepath)
        labeled_colorspaces = get_colorspaces_enumerator_items(
            config_items,
            include_aliases=True,
            include_roles=True
        )
        self.config_items = config_items
        self.config_data = config_data
        self.colorspace_items.extend(labeled_colorspaces)
        self.enabled = True
