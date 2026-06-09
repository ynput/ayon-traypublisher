from pydantic import validator

from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    folder_types_enum,
    task_types_enum,
)
from ayon_server.settings.validators import ensure_unique_names
from ayon_server.exceptions import BadRequestException


class ProductTypeItemModel(BaseSettingsModel):
    _layout = "compact"
    product_type: str = SettingsField(
        title="Product type",
        description="Product type name",
    )
    label: str = SettingsField(
        "",
        title="Label",
        description="Label to display in UI for the product type",
    )


class BatchMovieCreatorPlugin(BaseSettingsModel):
    """Allows to publish multiple video files in one go. <br />Name of matching
     asset is parsed from file names ('asset.mov', 'asset_v001.mov',
     'my_asset_to_publish.mov')"""

    default_variants: list[str] = SettingsField(
        title="Default variants",
        default_factory=list
    )
    default_tasks: list[str] = SettingsField(
        title="Default tasks",
        default_factory=list
    )
    extensions: list[str] = SettingsField(
        title="Extensions",
        default_factory=list
    )
    product_types: list[str] = SettingsField(
        title="Product types",
        default_factory=list
    )


class ColumnItemModel(BaseSettingsModel):
    """Allows to publish multiple video files in one go. <br />Name of matching
     asset is parsed from file names ('asset.mov', 'asset_v001.mov',
     'my_asset_to_publish.mov')"""

    _layout = "expanded"
    name: str = SettingsField(
        title="Name",
        default=""
    )

    type: str = SettingsField(
        title="Type",
        default=""
    )

    default: str = SettingsField(
        title="Default",
        default=""
    )

    required_column: bool = SettingsField(
        title="Required Column",
        default=False
    )

    validation_pattern: str = SettingsField(
        title="Validation Regex Pattern",
        default="^(.*)$"
    )


def _csv_precreate_on_failure_enum() -> list:
    return [
        {"label": "Raise Error", "value": "error"},
        {"label": "Ignore and report", "value": "ignore"},
    ]


class ExistingVersionsPrevalidationItemModel(BaseSettingsModel):
    """Prevalidation item model."""
    _layout = "expanded"

    mode: str = SettingsField(
        title="Existing Versions",
        default="error",
        enum_resolver=_csv_precreate_on_failure_enum,
    )


class WrongFramerangePrevalidationItemModel(BaseSettingsModel):
    """Prevalidation item model."""
    _layout = "expanded"

    mode: str = SettingsField(
        title="Wrong Framerange",
        default="error",
        enum_resolver=_csv_precreate_on_failure_enum,
    )


class FolderDoesNotExistsrevalidationItemModel(BaseSettingsModel):
    """Prevalidation item model."""
    _layout = "expanded"

    mode: str = SettingsField(
        title="Folder Does Not Exists",
        default="error",
        enum_resolver=_csv_precreate_on_failure_enum,
    )


class FolderNameDuplicityPrevalidationItemModel(BaseSettingsModel):
    """Prevalidation item model."""
    _layout = "expanded"

    mode: str = SettingsField(
        title="Folder Name Duplicity",
        default="error",
        enum_resolver=_csv_precreate_on_failure_enum,
    )


class MissingFrameRangeValuesPrevalidationItemModel(BaseSettingsModel):
    """Prevalidation item model."""
    _layout = "expanded"

    mode: str = SettingsField(
        title="Missing Frame Range Values",
        default="error",
        enum_resolver=_csv_precreate_on_failure_enum,
    )


class PrevalidationModel(BaseSettingsModel):
    """Prevalidation model."""

    existing_versions: ExistingVersionsPrevalidationItemModel = SettingsField(
        title="Existing Versions",
        default_factory=ExistingVersionsPrevalidationItemModel,
    )
    wrong_framerange: WrongFramerangePrevalidationItemModel = SettingsField(
        title="Wrong Framerange",
        default_factory=WrongFramerangePrevalidationItemModel,
    )
    folder_not_exists: FolderDoesNotExistsrevalidationItemModel = SettingsField(  # noqa
        title="Folder Does Not Exists",
        default_factory=FolderDoesNotExistsrevalidationItemModel,
    )
    folder_name_duplicity: FolderNameDuplicityPrevalidationItemModel = SettingsField(  # noqa
        title="Folder Name Duplicity",
        default_factory=FolderNameDuplicityPrevalidationItemModel,
    )
    missing_frame_range_values: MissingFrameRangeValuesPrevalidationItemModel = SettingsField(  # noqa
        title="Missing Frame Range Values",
        default_factory=MissingFrameRangeValuesPrevalidationItemModel,
    )



class ColumnConfigModel(BaseSettingsModel):
    """Column configuration model"""

    csv_delimiter: str = SettingsField(
        title="CSV delimiter",
        default=","
    )

    columns: list[ColumnItemModel] = SettingsField(
        title="Columns",
        default_factory=list
    )

    @validator("columns")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


def list_type_enum():
    return [
        {"label": "Generic", "value": "generic"},
        {"label": "Review Session", "value": "review-session"},
    ]


def list_folder_scope_def():
    return [
        {"label": "Scope folder to all views", "value": "all"},
        {"label": "Scope to the list type", "value": "list_type"},
    ]


class EntityListFolderModel(BaseSettingsModel):
    """Folder must have label and can be scoped to views.

    Scope of the folder can be defined for all views or use just the view
        matching list type of created list. In case the list folder already
        exists the settings are not used and we just make sure the list can
        be seen under the folder.

    """
    _layout = "expanded"
    label: str = SettingsField(
        "",
        title="Folder label",
        description=(
            "The label of the folder to create. \n"
            "Also supports Anatomy formattable template keys.\n"
            "CSV ingest related keys: {csv_basename}, {csv_parent_dir}"
        ),
    )
    # Don't use explicit scope enum, rather ask if the folder should be seen
    #   everywhere or just in the list type matching created list.
    scope_def: str = SettingsField(
        "all",
        enum_resolver=list_folder_scope_def,
        title="Scope",
    )


class ListProfileModel(BaseSettingsModel):
    """List profile model."""

    _layout = "expanded"
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task Types",
        enum_resolver=task_types_enum,
        description=(
            "The current create context task type to filter against. This"
            " allows to filter the profile to only be valid if currently "
            " creating from within that task type."
        ),
        section="Filter",
    )
    task_names: list[str] = SettingsField(
        default_factory=list,
        title="Task names",
        description="The task names to match this profile to.",
    )
    product_base_types: list[str] = SettingsField(
        default_factory=list,
        title="Product base types",
        description=(
            "The product base types to match this profile to. When matched,"
            " the settings below would apply to the instance as default"
            " attributes."
        )
    )
    product_names: list[str] = SettingsField(
        default_factory=list,
        title="Product names",
        description="The product names to match this profile to.",
    )
    list_name: str = SettingsField(
        "{csv_basename}-{yy}{mm}{dd}",
        title="List Name",
        description=(
            "Anatomy formattable template for the name. \n"
            "CSV ingest related keys: {csv_basename}, {csv_parent_dir}"
        ),
        section="List configuration",
    )
    list_type: str = SettingsField(
        "generic",
        title="List type",
        description="Define what type of list this profile represents.",
        enum_resolver=list_type_enum,

    )
    list_folders: list[EntityListFolderModel] = SettingsField(
        default_factory=list,
        title="List folders",
        description="Folder hierarchy formed from top to bottom.",
    )


class ListConfigModel(BaseSettingsModel):
    """List configuration model."""

    enabled: bool = SettingsField(
        title="Enabled",
        default=False
    )
    profiles: list[ListProfileModel] = SettingsField(
        title="Profiles",
        default_factory=list
    )


class RepresentationItemModel(BaseSettingsModel):
    """Allows to publish multiple video files in one go.

    Name of matching asset is parsed from file names
    ('asset.mov', 'asset_v001.mov', 'my_asset_to_publish.mov')
    """

    _layout = "expanded"
    name: str = SettingsField(
        title="Name",
        default=""
    )

    extensions: list[str] = SettingsField(
        title="Extensions",
        default_factory=list
    )

    @validator("extensions")
    def validate_extension(cls, value):
        for ext in value:
            if not ext.startswith("."):
                raise BadRequestException(f"Extension must start with '.': {ext}")
        return value


class RepresentationConfigModel(BaseSettingsModel):
    """Representation configuration model"""

    tags_delimiter: str = SettingsField(
        title="Tags delimiter",
        default=";"
    )

    default_tags: list[str] = SettingsField(
        title="Default tags",
        default_factory=list
    )

    representations: list[RepresentationItemModel] = SettingsField(
        title="Representations",
        default_factory=list
    )

    @validator("representations")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class FolderTypeRegexItem(BaseSettingsModel):
    _layout = "compact"
    regex: str = SettingsField("", title="Folder Regex")
    folder_type: str = SettingsField(
        "Folder",
        title="Folder Type",
        enum_resolver=folder_types_enum,
        description=(
            "Project's Anatomy folder type to create when regex matches."),
    )


class TaskTypeRegexItem(BaseSettingsModel):
    _layout = "compact"
    regex: str = SettingsField("", title="Task Regex")
    task_type: str = SettingsField(
        "Generic",
        title="Task Type",
        enum_resolver=task_types_enum,
        description=(
            "New task type to create when regex matches."),
    )


class FolderCreationConfigModel(BaseSettingsModel):
    """Allow to create folder hierarchy when non-existing."""

    enabled: bool = SettingsField(
        title="Enabled folder creation",
        default=False,
    )
    folder_create_type: str = SettingsField(
        "Folder",
        title="Default Folder Type",
        enum_resolver=folder_types_enum,
        description=(
            "Default folder type for new folder(s) creation."),
        section="Folder Settings"
    )
    folder_type_regexes: list[FolderTypeRegexItem] = SettingsField(
        default_factory=list,
        description=(
            "Using Regex expressions to create missing folders. \nThose can be used"
            " to define which folder types are used for new folder creation"
            " depending on their names."
        )
    )
    task_create_type: str = SettingsField(
        "",
        title="Default Task Type",
        enum_resolver=task_types_enum,
        description=(
            "Default task type for new task(s) creation."),
        section="Task Settings"
    )
    task_type_regexes: list[TaskTypeRegexItem] = SettingsField(
        default_factory=list,
        description=(
            "Using Regex expressions to create missing tasks. \nThose can be used"
            " to define which task types are used for new folder+task creation"
            " depending on their names."
        )
    )


class PSDWorkfileCreatorPluginModel(BaseSettingsModel):
    """Creates the workfile and image publish instances together.

    For .psd which could be both workfile and image product base type.
    """
    enabled: bool = SettingsField(
        title="Enabled",
        default=True,
    )
    default_variants: list[str] = SettingsField(
        title="Default variants",
        default_factory=list,
    )
    workfile_product_types: list[str] = SettingsField(
        title="Workfile product types",
        default_factory=list,
    )
    image_product_types: list[str] = SettingsField(
        title="Image  product types",
        default_factory=list,
    )


class IngestCSVPresetModel(BaseSettingsModel):
    """Model for CSV ingest preset."""
    name: str = SettingsField(
        "Default",
        title="Name",
    )
    prevalidation: PrevalidationModel = SettingsField(
        title="Prevalidation",
        default_factory=PrevalidationModel,
        section="Prevalidation",
    )
    columns_config: ColumnConfigModel = SettingsField(
        title="Columns config",
        default_factory=ColumnConfigModel
    )
    representations_config: RepresentationConfigModel = SettingsField(
        title="Representations config",
        default_factory=RepresentationConfigModel
    )
    folder_creation_config: FolderCreationConfigModel = SettingsField(
        title="Folder creation config",
        default_factory=FolderCreationConfigModel
    )
    list_config: ListConfigModel = SettingsField(
        title="List config",
        default_factory=ListConfigModel
    )


class IngestCSVPluginModel(BaseSettingsModel):
    """CSV ingest plugin."""

    enabled: bool = SettingsField(
        title="Enabled",
        default=False
    )

    presets: list[IngestCSVPresetModel] = SettingsField(
        title="Presets",
        default_factory=list
    )


class TextureCreatorPluginModel(BaseSettingsModel):
    """Texture files or UDIM sequences creator"""
    enabled: bool = SettingsField(
        title="Enabled",
        default=True,
    )
    default_variants: list[str] = SettingsField(
        title="Default variants",
        default_factory=list
    )
    extensions: list[str] = SettingsField(
        title="Extensions",
        default_factory=list,
        description=(
            "List of file extensions that are allowed as textures."
        )
    )
    product_type_items: list[ProductTypeItemModel] = SettingsField(
        default_factory=list,
        title="Product type items",
        description=(
            "Optional list of product types that this plugin can create."
        )
    )


class TrayPublisherCreatePluginsModel(BaseSettingsModel):
    BatchMovieCreator: BatchMovieCreatorPlugin = SettingsField(
        title="Batch Movie Creator",
        default_factory=BatchMovieCreatorPlugin
    )
    PSDWorkfileCreator: PSDWorkfileCreatorPluginModel = SettingsField(
        title="PSD Workfile + Image Creator",
        default_factory=PSDWorkfileCreatorPluginModel,
    )
    IngestCSV: IngestCSVPluginModel = SettingsField(
        title="Ingest CSV",
        default_factory=IngestCSVPluginModel
    )
    TextureCreator: TextureCreatorPluginModel = SettingsField(
        title="Texture",
        default_factory=TextureCreatorPluginModel,
    )


DEFAULT_CREATORS = {
    "BatchMovieCreator": {
        "default_variants": ["Main"],
        "default_tasks": ["Compositing"],
        "extensions": [".mov"],
        "product_types": [],
    },
    "PSDWorkfileCreator": {
        "enabled": False,
        "default_variants": ["Main"],
        "workfile_product_types": [],
        "image_product_types": [],
    },
    "IngestCSV": {
        "enabled": True,
        "presets": [
            {
                "name": "Default",
                "prevalidation": {
                    "existing_versions": {"mode": "error"},
                    "wrong_framerange": {"mode": "error"},
                    "folder_not_exists": {"mode": "error"},
                    "folder_name_duplicity": {"mode": "error"},
                    "missing_frame_range_values": {"mode": "error"},
                },
                "columns_config": {
                    "csv_delimiter": ",",
                    "columns": [
                        {
                            "name": "File Path",
                            "type": "text",
                            "default": "",
                            "required_column": True,
                            "validation_pattern": "^([a-zA-Z\\:\\ 0-9#\\-\\._\\\\/]*)$"
                        },
                        {
                            "name": "Folder Path",
                            "type": "text",
                            "default": "",
                            "required_column": True,
                            "validation_pattern": "^([a-zA-Z0-9_\\/]*)$"
                        },
                        {
                            "name": "Folder Name",
                            "type": "text",
                            "default": "",
                            "required_column": False,
                            "validation_pattern": "^([a-zA-Z0-9_]*)$"
                        },
                        {
                            "name": "Task Name",
                            "type": "text",
                            "default": "",
                            "required_column": True,
                            "validation_pattern": "^(.*)$"
                        },
                        {
                            "name": "Product Base Type",
                            "type": "text",
                            "default": "",
                            "required_column": False,
                            "validation_pattern": "^(.*)$"
                        },
                        {
                            "name": "Product Type",
                            "type": "text",
                            "default": "",
                            "required_column": False,
                            "validation_pattern": "^(.*)$"
                        },
                        {
                            "name": "Variant",
                            "type": "text",
                            "default": "",
                            "required_column": False,
                            "validation_pattern": "^(.*)$"
                        },
                        {
                            "name": "Version",
                            "type": "number",
                            "default": "0",
                            "required_column": False,
                            "validation_pattern": "^(\\d{1,3})$"
                        },
                        {
                            "name": "Version Comment",
                            "type": "text",
                            "default": "",
                            "required_column": False,
                            "validation_pattern": "^(.*)$"
                        },
                        {
                            "name": "Version Thumbnail",
                            "type": "text",
                            "default": "",
                            "required_column": False,
                            "validation_pattern": "^([a-zA-Z\\:\\ 0-9#\\-\\._\\\\/]*)$"
                        },
                        {
                            "name": "Frame Start",
                            "type": "number",
                            "default": "0",
                            "required_column": True,
                            "validation_pattern": "^(\\d{1,8})$"
                        },
                        {
                            "name": "Frame End",
                            "type": "number",
                            "default": "0",
                            "required_column": True,
                            "validation_pattern": "^(\\d{1,8})$"
                        },
                        {
                            "name": "Handle Start",
                            "type": "number",
                            "default": "0",
                            "required_column": True,
                            "validation_pattern": "^(\\d)$"
                        },
                        {
                            "name": "Handle End",
                            "type": "number",
                            "default": "0",
                            "required_column": True,
                            "validation_pattern": "^(\\d)$"
                        },
                        {
                            "name": "FPS",
                            "type": "decimal",
                            "default": "0.0",
                            "required_column": True,
                            "validation_pattern": "^[0-9]*\\.[0-9]+$|^[0-9]+$"
                        },
                        {
                            "name": "Slate Exists",
                            "type": "bool",
                            "default": "True",
                            "required_column": False,
                            "validation_pattern": "(True|False)"
                        },
                        {
                            "name": "Representation",
                            "type": "text",
                            "default": "",
                            "required_column": False,
                            "validation_pattern": "^(.*)$"
                        },
                        {
                            "name": "Representation Colorspace",
                            "type": "text",
                            "default": "",
                            "required_column": False,
                            "validation_pattern": "^(.*)$"
                        },
                        {
                            "name": "Representation Tags",
                            "type": "text",
                            "default": "",
                            "required_column": False,
                            "validation_pattern": "^(.*)$"
                        },
                        {
                            "name": "Shot Height",
                            "type": "number",
                            "default": "0",
                            "required_column": False,
                            "validation_pattern": "^(\\d*)$"
                        },
                        {
                            "name": "Shot Width",
                            "type": "number",
                            "default": "0",
                            "required_column": False,
                            "validation_pattern": "^(\\d*)$"
                        },
                        {
                            "name": "Shot Pixel Aspect",
                            "type": "decimal",
                            "default": "0",
                            "required_column": False,
                            "validation_pattern": "^(\\d*.?\\d*)$"
                        },
                    ]
                },
                "representations_config": {
                    "tags_delimiter": ";",
                    "default_tags": [
                        "review"
                    ],
                    "representations": [
                        {
                            "name": "preview",
                            "extensions": [
                                ".mp4",
                                ".mov"
                            ]
                        },
                        {
                            "name": "exr",
                            "extensions": [
                                ".exr"
                            ]
                        },
                        {
                            "name": "edit",
                            "extensions": [
                                ".mov"
                            ]
                        },
                        {
                            "name": "review",
                            "extensions": [
                                ".mov"
                            ]
                        },
                        {
                            "name": "nuke",
                            "extensions": [
                                ".nk"
                            ]
                        }
                    ]
                },
                "folder_creation_config": {
                    "enabled": False,
                    "folder_type_regexes": [
                        {"regex": "(sh.*)", "folder_type": "Shot"},
                        {"regex": "(seq.*)", "folder_type": "Sequence"}
                    ],
                    "folder_create_type": "Folder",
                    "task_type_regexes": [],
                    "task_create_type": "Generic",
                },
                "list_config": {
                    "enabled": False,
                    "profiles": [],
                },
            }
        ]
    },
    "TextureCreator": {
        "enabled": True,
        "default_variants": [
            "Main"
        ],
        "extensions": [
            ".mov", ".mp4", ".mxf", ".m4v", ".mpg", ".exr", ".dpx", ".tif",
            ".png", ".jpg", ".tga", ".tx"
        ]
    },
}
