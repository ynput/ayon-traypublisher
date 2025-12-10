from pydantic import validator
from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    folder_types_enum,
    task_types_enum,
)
from ayon_server.settings.validators import ensure_unique_names
from ayon_server.exceptions import BadRequestException


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


class ColumnConfigModel(BaseSettingsModel):
    """Allows to publish multiple video files in one go. <br />Name of matching
     asset is parsed from file names ('asset.mov', 'asset_v001.mov',
     'my_asset_to_publish.mov')"""

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
    """Allows to publish multiple video files in one go. <br />Name of matching
     asset is parsed from file names ('asset.mov', 'asset_v001.mov',
     'my_asset_to_publish.mov')"""

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
        "",
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
        default_factory=FolderTypeRegexItem,
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
        default_factory=TaskTypeRegexItem,
        description=(
            "Using Regex expressions to create missing tasks. \nThose can be used"
            " to define which task types are used for new folder+task creation"
            " depending on their names."
        )
    )


class PSDWorkfileCreatorPluginModel(BaseSettingsModel):
    """Creates the workfile and image publish instances together.

    For .psd which could be both workfile and image product type.
    """
    enabled: bool = SettingsField(
        title="Enabled",
        default=True,
    )
    default_variants: list[str] = SettingsField(
        title="Default variants",
        default_factory=list
    )


class IngestCSVPluginModel(BaseSettingsModel):
    """Allows to publish multiple video files in one go. <br />Name of matching
     asset is parsed from file names ('asset.mov', 'asset_v001.mov',
     'my_asset_to_publish.mov')"""

    enabled: bool = SettingsField(
        title="Enabled",
        default=False
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
    },
    "PSDWorkfileCreator": {
        "enabled": False,
        "default_variants": ["Main"]
    },
    "IngestCSV": {
        "enabled": True,
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
                    "name": "Task Name",
                    "type": "text",
                    "default": "",
                    "required_column": True,
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
        }
    },
    "TextureCreator": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
}
