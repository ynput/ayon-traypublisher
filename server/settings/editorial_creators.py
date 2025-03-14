from pydantic import validator

from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum,
)
from ayon_server.exceptions import BadRequestException


def get_product_type_enum():
    return [
        {"label": "Image", "value": "image"},
        {"label": "Plate", "value": "plate"},
        {"label": "Render", "value": "render"},
        {"label": "Audio", "value": "audio"},
        {"label": "Model", "value": "model"},
        {"label": "Camera", "value": "camera"},
        {"label": "Workfile", "value": "workfile"},
    ]

def get_content_type_enum():
    return [
        {"label": "Thumbnail", "value": "thumbnail"},
        {"label": "Single Image", "value": "image_single"},
        {"label": "Sequence of images", "value": "image_sequence"},
        {"label": "Video", "value": "video"},
        {"label": "Audio", "value": "audio"},
        {"label": "Geometry", "value": "geometry"},
        {"label": "Workfile", "value": "workfile"},
    ]


def get_output_file_type_enum():
   return [
        {"value": ".mp4", "label": "MP4"},
        {"value": ".mov", "label": "MOV"},
        {"value": ".wav", "label": "WAV"},
    ]


class RepresentationAdvancedItemModel(BaseSettingsModel):
    """Representation advanced settings.

    Configuration used for filtering rules so files in folder are converted to
    publishable representations with correct data definitions.
    """

    name: str = SettingsField(title="Name", default="")
    content_type: str = SettingsField(
        "video",
        title="Content type",
        enum_resolver=get_content_type_enum,
    )
    extensions: list[str] = SettingsField(
        title="Filter by extensions",
        default_factory=list,
        description=(
            "Only files with these extensions will be published. "
            "following are accepted: .ext, ext, EXT, .EXT"
        ),
        section="Filtering options",
    )
    patterns: list[str] = SettingsField(
        title="Filter by patterns",
        default_factory=list,
        description=(
            "Regular expression patterns to filter files. "
            "Search in filenames for matching files."
        ),
    )
    tags: list[str] = SettingsField(
        default_factory=list,
        title="Tags",
        description=(
            "Tags that will be added to the created representation."
            "\nAdd *review* tag to create review from the transcoded"
            " representation instead of the original."
        ),
        section="Representation options",
    )
    custom_tags: list[str] = SettingsField(
        title="Custom tags",
        default_factory=list,
        description=(
            "Additional custom tags can be used for advanced filtering "
            "in Extract Review output presets."
        ),
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


class ProductTypePresetItem(BaseSettingsModel):
    _layout = "compact"

    product_type: str = SettingsField("", title="Product type")
    # TODO add placeholder '< Inherited >'
    variant: str = SettingsField("", title="Variant")
    review: bool = SettingsField(True, title="Review")
    output_file_type: str = SettingsField(
        ".mp4",
        enum_resolver=get_output_file_type_enum
    )


class ProductTypeAdvancedPresetItem(BaseSettingsModel):
    default_enabled: bool = True
    product_type: str = SettingsField(
        "plate",
        title="Product type",
        enum_resolver=get_product_type_enum
    )
    variant: str = SettingsField("", title="Variant")
    versioning_type: str = SettingsField(
        "incremental",
        title="Versioning type",
        enum_resolver=lambda: [
            {"value": "incremental", "label": "Incremental"},
            {"value": "from_file", "label": "From files"},
            {"value": "locked", "label": "Locked"},
        ],
        description=(
            "Incremental - will increment version number by 1"
            "From file - will use version from the file name if any found"
            "Locked - will use locked version number"
        ),
        conditionalEnum=True,
    )
    locked: int = SettingsField(
        1,
        title="Locked version",
        description="Version number to be used for locked versioning",
    )
    representations: list[RepresentationAdvancedItemModel] = SettingsField(
        title="Representations", default_factory=list
    )


class EditorialSimpleCreatorPlugin(BaseSettingsModel):
    enabled: bool = True
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


class EditorialAdvancedCreatorPlugin(BaseSettingsModel):
    enabled: bool = True
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default Variants"
    )
    clip_name_tokenizer: list[ClipNameTokenizerItem] = SettingsField(
        default_factory=ClipNameTokenizerItem,
        description=(
            "Using Regex expression to create tokens. \nThose can be used"
            ' later in "Shot rename" creator \nor "Shot hierarchy".'
            '\n\nTokens should be decorated with "_" on each side'
        ),
    )
    shot_rename: ShotRenameSubmodel = SettingsField(
        title="Shot Rename", default_factory=ShotRenameSubmodel
    )
    shot_hierarchy: ShotHierarchySubmodel = SettingsField(
        title="Shot Hierarchy", default_factory=ShotHierarchySubmodel
    )
    shot_add_tasks: list[ShotAddTasksItem] = SettingsField(
        title="Add tasks to shot", default_factory=ShotAddTasksItem
    )
    product_type_advanced_presets: list[ProductTypeAdvancedPresetItem] = (
        SettingsField(
            title="Product type presets",
            default_factory=list
        )
    )

    @validator("product_type_advanced_presets")
    def validate_unique_product_names(cls, value):
        product_names = []
        for item in value:
            product_name = item.product_type + item.variant
            if product_name in product_names:
                raise BadRequestException(
                    "Duplicate product preset: \n"
                    f" > Product type: {item.product_type} \n"
                    f" > Variant: {item.variant}"
                )
            product_names.append(product_name)
        return value


class TraypublisherEditorialCreatorPlugins(BaseSettingsModel):
    editorial_simple: EditorialSimpleCreatorPlugin = SettingsField(
        title="Editorial simple creator",
        default_factory=EditorialSimpleCreatorPlugin,
    )
    editorial_advanced: EditorialAdvancedCreatorPlugin = SettingsField(
        title="Editorial advanced creator",
        default_factory=EditorialAdvancedCreatorPlugin,
    )


DEFAULT_EDITORIAL_CREATORS = {
    "editorial_simple": {
        "enabled": True,
        "default_variants": ["Main"],
        "clip_name_tokenizer": [
            {"name": "_sequence_", "regex": "(sc\\d{3})"},
            {"name": "_shot_", "regex": "(sh\\d{3})"},
        ],
        "shot_rename": {
            "enabled": True,
            "shot_rename_template": "{project[code]}_{_sequence_}_{_shot_}",
        },
        "shot_hierarchy": {
            "enabled": True,
            "parents_path": "{project}/{folder}/{sequence}",
            "parents": [
                {
                    "parent_type": "Project",
                    "name": "project",
                    "value": "{project[name]}",
                },
                {"parent_type": "Folder", "name": "folder", "value": "shots"},
                {
                    "parent_type": "Sequence",
                    "name": "sequence",
                    "value": "{_sequence_}",
                },
            ],
        },
        "shot_add_tasks": [],
        "product_type_presets": [
            {
                "product_type": "review",
                "variant": "Reference",
                "review": True,
                "output_file_type": ".mp4",
            },
            {
                "product_type": "plate",
                "variant": "",
                "review": False,
                "output_file_type": ".mov",
            },
            {
                "product_type": "audio",
                "variant": "",
                "review": False,
                "output_file_type": ".wav",
            },
        ],
    },
    "editorial_advanced": {
        "enabled": True,
        "default_variants": ["Main"],
        "clip_name_tokenizer": [
            {"name": "_sequence_", "regex": "(\\d{4})(?=_\\d{4})"},
            {"name": "_shot_", "regex": "(\\d{4})(?!_\\d{4})"},
        ],
        "shot_rename": {
            "enabled": True,
            "shot_rename_template": "{project[code]}_{_sequence_}_{_shot_}",
        },
        "shot_hierarchy": {
            "enabled": True,
            "parents_path": "{project}/{folder}/{sequence}",
            "parents": [
                {
                    "parent_type": "Project",
                    "name": "project",
                    "value": "{project[name]}",
                },
                {"parent_type": "Folder", "name": "folder", "value": "shots"},
                {
                    "parent_type": "Sequence",
                    "name": "sequence",
                    "value": "{_sequence_}",
                },
            ],
        },
        "shot_add_tasks": [],
        "product_type_advanced_presets": [
            {
                "default_enabled": True,
                "product_type": "plate",
                "variant": "Reference",
                "representations": [
                    {
                        "name": "Reference",
                        "content_type": "video",
                        "extensions": [
                            "mov",
                            "mp4",
                        ],
                        "patterns": [
                            ".*",
                        ],
                        "tags": ["review"],
                        "custom_tags": []
                    }
                ]
            },
        ],
    },
}
