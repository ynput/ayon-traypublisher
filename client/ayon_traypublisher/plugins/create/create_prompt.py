# -*- coding: utf-8 -*-
import inspect
from typing import Optional

from ayon_core.lib import FileDef, BoolDef, EnumDef
from ayon_core.pipeline import (
    CreatedInstance,
    CreatorError,
)
from ayon_core.pipeline.create import  get_product_name
from ayon_traypublisher.api.plugin import (
    TrayPublishCreator,
    HiddenTrayPublishCreator
)


class PromptWorkfileCreator(TrayPublishCreator):
    """Creates additional image publish instance for provided workfile."""

    identifier = "io.ayon.creators.traypublisher.gen_ai.prompt"
    label = "Prompt"
    group_label = "Workfile"
    icon = "fa.file"
    description = (
        "Creates 'workfile' product with prompt content."
    )
    product_type = "workfile"
    product_base_type = "workfile"
    settings_category = "traypublisher"

    default_variants = ["Main"]  # should be dynamically fetched

    def get_detail_description(self):
        return inspect.cleandoc("""# Prompt Workfile

        Basic creator for product type 'workfile' that contains prompt content.
        """)

    def create(self, product_name, instance_data, pre_create_data):
        repr_file = pre_create_data.get("filepath")
        if not repr_file:
            raise CreatorError("No files specified")

        instance_data["creator_attributes"] = {
            "filepath": repr_file,
        }

        used_generators = pre_create_data.get("generators", [])
        if not used_generators:
            raise CreatorError("No generators specified")

        instance_data["default_variants"] = self.default_variants

        workfile_instance = CreatedInstance(
            self.product_type, product_name, instance_data, self
        )

        self._store_new_instance(workfile_instance)

        self._create_output_instance(
            instance_data,
            pre_create_data,
            repr_file,
            used_generators
        )

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "filepath",
                folders=False,
                extensions=[".txt", ".md"],
                allow_sequences=False,
                single_item=True,
                label="Prompt file",
            ),
            EnumDef(
                "generators",
                items=[
                    ("nano_banana", "Nano Banana"),
                    ("gpt_3", "GPT-3"),
                    ("custom", "Custom"),
                ],
                default="nano_banana",
                label="Use Generators",
                multiselection=True,
            ),
            EnumDef(
                "product_types",
                items=[
                    ("image", "Image"),
                    ("render", "Render"),
                ],
                default="image",
                label="Output Product Types",
                multiselection=True,
            ),
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
                ""
            ),
            BoolDef(
                "use_generator_as_variant",
                default=True,
                label="Use Generator Label as Variant"
            ),
        ]

    def get_instance_attr_defs(self):
        return [
            FileDef(
                "filepath",
                folders=False,
                extensions=[".txt", ".md"],
                allow_sequences=False,
                single_item=True,
                label="Prompt file",
            )
        ]

    def _get_hidden_creator(self, identifier):
        creator = self.create_context.creators.get(identifier)
        if creator is None:
            self.log.debug(
                "Creator '%s' not found in create_context.creators", identifier
            )
        return creator

    def _create_output_instance(
        self, instance_data, pre_create_data, repr_file, used_generators
    ):
        """Create output instances for each generator and product type."""
        product_types = pre_create_data.get("product_types", [])
        add_review_family = pre_create_data.get("add_review_family", True)
        use_generator_as_variant = pre_create_data.get("use_generator_as_variant", True)

        project_entity = self.create_context.get_current_project_entity()
        folder_path: str = instance_data["folderPath"]
        task_name: Optional[str] = instance_data.get("task")
        task_entity = self.create_context.get_task_entity(
            folder_path, task_name
        )

        project_name = project_entity["name"]
        host_name = self.create_context.host_name

        for generator in used_generators:
            for product_type in product_types:
                creator = None
                if product_type == "image":
                    creator = self._get_hidden_creator(
                        "io.ayon.creators.traypublisher.gen_ai.image"
                    )
                if not creator:
                    raise CreatorError(f"{product_type} creator not found")

                variant = generator.title() if use_generator_as_variant else "Main"
                instance_data["default_variants"] = [variant]
                instance_data["creator_attributes"] = {
                    "filepath": repr_file,
                    "generator": generator,
                }
                if add_review_family:
                    instance_data["creator_attributes"]["add_review_family"] = True

                task_name = task_type = None
                if task_entity:
                    task_name = task_entity["name"]
                    task_type = task_entity["taskType"]

                product_name = get_product_name(
                    product_type=product_type,
                    project_name=project_name,
                    project_entity=project_entity,
                    task_name=task_name,
                    task_type=task_type,
                    host_name=host_name,
                    variant=variant,
                    product_base_type=product_type
                )

                creator.create(product_name, instance_data)


class GenAIImageCreator(HiddenTrayPublishCreator):
    """Creates image instance."""

    identifier = "io.ayon.creators.traypublisher.gen_ai.image"
    label = "Image"
    host_name = "traypublisher"
    product_type = "image"
    product_base_type = "image"

    def create(self, product_name, instance_data):

        new_instance = CreatedInstance(
            self.product_type,
            product_name,
            instance_data,
            creator=self,
            product_base_type=self.product_base_type,
        )

        self._store_new_instance(new_instance)

        return new_instance

    def get_instance_attr_defs(self):
        return [
            FileDef(
                "filepath",
                folders=False,
                extensions=[".txt", ".md"],
                allow_sequences=False,
                single_item=True,
                label="Prompt file",
            ),
            EnumDef(
                "generators",
                items=[
                    ("image", "Image"),
                    ("render", "Render"),
                ],
                default="nano_banana",
                label="Use Generators",
                visible=False,
            ),
            BoolDef("add_review_family", default=True, label="Review"),
        ]