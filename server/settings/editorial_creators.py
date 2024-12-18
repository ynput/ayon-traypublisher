from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum,
)


class ClipNameTokenizerItem(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField("", title="Token name")
    regex: str = SettingsField("", title="Token regex")


class ShotAddTasksItem(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField('', title="Task name")
    task_type: str = SettingsField(
        title="Task type",
        enum_resolver=task_types_enum
    )


class ShotRenameSubmodel(BaseSettingsModel):
    """Shot Rename Info

    When enabled, any discovered shots will be renamed based on the `shot rename template`.

    The template supports both the available 
    [template keys](https://ayon.ynput.io/docs/admin_settings_project_anatomy#available-template-keys) 
    and tokens defined under `Clip Name Tokenizer`.
    """
    enabled: bool = True
    shot_rename_template: str = SettingsField(
        "",
        title="Shot rename template"
    )


parent_type_enum = [
    {"value": "Project", "label": "Project"},
    {"value": "Folder", "label": "Folder"},
    {"value": "Episode", "label": "Episode"},
    {"value": "Sequence", "label": "Sequence"},
]


class TokenToParentConvertorItem(BaseSettingsModel):
    _layout = "compact"
    # TODO - was 'type' must be renamed in code to `parent_type`
    name: str = SettingsField(
        "",
        title="Token name",
        description="Unique name used in `Folder path template tokens`"
    )
    value: str = SettingsField(
        "",
        title="Token value",
        description="Template where any text, Anatomy keys and Tokens could be used"  # noqa
    )
    parent_type: str = SettingsField(
        "Project",
        title="Folder Type",
        enum_resolver=lambda: parent_type_enum
    )


class ShotHierarchySubmodel(BaseSettingsModel):
    """Shot Hierarchy Info

    Shot Hierarchy defines the folder path where each shot will be added.
    It uses the `Folder path template` to compute each path. 
    The `Folder path template` supports tokens defined in the `folder path template tokens` setting.

    - Each token in the `Folder path template` represents a folder in the hierarchy.
    - Each token's value supports both the available 
    [template keys](https://ayon.ynput.io/docs/admin_settings_project_anatomy#available-template-keys) 
    and tokens defined under `Clip Name Tokenizer`.
    """
    enabled: bool = True
    parents_path: str = SettingsField(
        "",
        title="Folder path template"
    )
    parents: list[TokenToParentConvertorItem] = SettingsField(
        default_factory=TokenToParentConvertorItem,
        title="Folder path template tokens"
    )


output_file_type = [
    {"value": ".mp4", "label": "MP4"},
    {"value": ".mov", "label": "MOV"},
    {"value": ".wav", "label": "WAV"}
]


class ProductTypePresetItem(BaseSettingsModel):
    _layout="compact"
    product_type: str = SettingsField("", title="Product type")
    # TODO add placeholder '< Inherited >'
    variant: str = SettingsField("", title="Variant")
    review: bool = SettingsField(True, title="Review")
    output_file_type: str = SettingsField(
        ".mp4",
        enum_resolver=lambda: output_file_type
    )


class EditorialSimpleCreatorPlugin(BaseSettingsModel):
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Variants"
    )
    clip_name_tokenizer: list[ClipNameTokenizerItem] = SettingsField(
        default_factory=ClipNameTokenizerItem,
        description="""Clip Name Tokenizer Info.

                    Use regex expressions to create tokens.
                    These tokens will be used later in the `Shot rename` creator or `Shot hierarchy`.
                    Each token must be enclosed by underscores (`_`).
                    """
    )    
    shot_rename: ShotRenameSubmodel = SettingsField(
        title="Shot Rename",
        default_factory=ShotRenameSubmodel
    )
    shot_hierarchy: ShotHierarchySubmodel = SettingsField(
        title="Shot Hierarchy",
        default_factory=ShotHierarchySubmodel
    )
    shot_add_tasks: list[ShotAddTasksItem] = SettingsField(
        title="Add tasks to shot",
        default_factory=ShotAddTasksItem,
        description="The following list of tasks will be added to each created shot."
    )
    product_type_presets: list[ProductTypePresetItem] = SettingsField(
        default_factory=list
    )


class TraypublisherEditorialCreatorPlugins(BaseSettingsModel):
    editorial_simple: EditorialSimpleCreatorPlugin = SettingsField(
        title="Editorial simple creator",
        default_factory=EditorialSimpleCreatorPlugin,
    )


DEFAULT_EDITORIAL_CREATORS = {
    "editorial_simple": {
        "default_variants": [
            "Main"
        ],
        "clip_name_tokenizer": [
            {"name": "_sequence_", "regex": "(sc\\d{3})"},
            {"name": "_shot_", "regex": "(sh\\d{3})"}
        ],
        "shot_rename": {
            "enabled": True,
            "shot_rename_template": "{project[code]}_{_sequence_}_{_shot_}"
        },
        "shot_hierarchy": {
            "enabled": True,
            "parents_path": "{project}/{folder}/{sequence}",
            "parents": [
                {
                    "parent_type": "Project",
                    "name": "project",
                    "value": "{project[name]}"
                },
                {
                    "parent_type": "Folder",
                    "name": "folder",
                    "value": "shots"
                },
                {
                    "parent_type": "Sequence",
                    "name": "sequence",
                    "value": "{_sequence_}"
                }
            ]
        },
        "shot_add_tasks": [],
        "product_type_presets": [
            {
                "product_type": "review",
                "variant": "Reference",
                "review": True,
                "output_file_type": ".mp4"
            },
            {
                "product_type": "plate",
                "variant": "",
                "review": False,
                "output_file_type": ".mov"
            },
            {
                "product_type": "audio",
                "variant": "",
                "review": False,
                "output_file_type": ".wav"
            }
        ]
    }
}
