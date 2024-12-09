from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum,
)
from ayon_server.exceptions import BadRequestException
from pydantic import validator


product_type_enum = [
    {"label": "Image", "value": "image"},
    {"label": "Plate", "value": "plate"},
    {"label": "Render", "value": "render"},
    {"label": "Audio", "value": "audio"},
    {"label": "Model", "value": "model"},
    {"label": "Camera", "value": "camera"},
    {"label": "Workfile", "value": "workfile"},
]

content_type_enum = [
    {"label": "Thumbnail", "value": "thumbnail"},
    {"label": "Single Image", "value": "image_single"},
    {"label": "Sequence of images", "value": "image_sequence"},
    {"label": "Video", "value": "video"},
    {"label": "Audio", "value": "audio"},
    {"label": "Geometry", "value": "geometry"},
    {"label": "Workfile", "value": "workfile"},
]


output_file_type = [
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
        enum_resolver=lambda: content_type_enum,
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
    name: str = SettingsField("", title="Tokenizer name")
    regex: str = SettingsField("", title="Tokenizer regex")


class ShotAddTasksItem(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField('', title="Key")
    task_type: str = SettingsField(
        title="Task type",
        enum_resolver=task_types_enum
    )


class ShotRenameSubmodel(BaseSettingsModel):
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
    parent_type: str = SettingsField(
        "Project",
        enum_resolver=lambda: parent_type_enum
    )
    name: str = SettingsField(
        "",
        title="Parent token name",
        description="Unique name used in `Parent path template`"
    )
    value: str = SettingsField(
        "",
        title="Parent token value",
        description="Template where any text, Anatomy keys and Tokens could be used"  # noqa
    )


class ShotHierarchySubmodel(BaseSettingsModel):
    enabled: bool = True
    parents_path: str = SettingsField(
        "",
        title="Parents path template",
        description="Using keys from \"Token to parent convertor\" or tokens directly"  # noqa
    )
    parents: list[TokenToParentConvertorItem] = SettingsField(
        default_factory=TokenToParentConvertorItem,
        title="Token to parent convertor"
    )


class ProductTypePresetItem(BaseSettingsModel):
    _layout = "compact"

    product_type: str = SettingsField("", title="Product type")
    # TODO add placeholder '< Inherited >'
    variant: str = SettingsField("", title="Variant")
    review: bool = SettingsField(True, title="Review")
    output_file_type: str = SettingsField(
        ".mp4",
        enum_resolver=lambda: output_file_type
    )


class ProductTypeAdvancedPresetItem(BaseSettingsModel):
    product_type: str = SettingsField(
        "plate",
        title="Product type",
        enum_resolver=lambda: product_type_enum
    )
    variant: str = SettingsField("", title="Variant")
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
        description=(
            "Using Regex expression to create tokens. \nThose can be used"
            " later in \"Shot rename\" creator \nor \"Shot hierarchy\"."
            "\n\nTokens should be decorated with \"_\" on each side"
        )
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
        default_factory=ShotAddTasksItem
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
