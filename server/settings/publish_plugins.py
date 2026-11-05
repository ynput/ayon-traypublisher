from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
)


class ValidatePluginModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = True
    optional: bool = SettingsField(True, title="Optional")
    active: bool = SettingsField(True, title="Active")


class ValidateFrameRangeModel(ValidatePluginModel):
    """Allows to publish multiple video files in one go. Name of matching
     folder is parsed from file names ('folder.mov', 'folder_v001.mov',
     'my_folder_to_publish.mov')"""


class CollectThumbnailSourceModel(BaseSettingsModel):
    """Use the reviewable file as the thumbnail source.

    Enabled: the thumbnail is made from the reviewable file (its first
    file for a sequence) as it is,
    before any transcoding, resized by 'Extract Thumbnail From Source'
    (ayon-core). Disabled: the thumbnail is made by 'Extract Thumbnail'
    (ayon-core) from the transcoded review, so it follows the colorspace
    conversion. It is then made only for the product types that plugin
    accepts, at its own size settings. An explicit thumbnail dropped in
    the publisher is always used.
    """
    use_reviewable_as_thumbnail_source: bool = SettingsField(
        True,
        title="Use reviewable as thumbnail source",
    )


class ExtractEditorialPckgFFmpegModel(BaseSettingsModel):
    video_filters: list[str] = SettingsField(
        default_factory=list,
        title="Video filters"
    )
    audio_filters: list[str] = SettingsField(
        default_factory=list,
        title="Audio filters"
    )
    input: list[str] = SettingsField(
        default_factory=list,
        title="Input arguments"
    )
    output: list[str] = SettingsField(
        default_factory=list,
        title="Output arguments"
    )


class ExtractEditorialPckgOutputDefModel(BaseSettingsModel):
    _layout = "expanded"
    ext: str = SettingsField("", title="Output extension")

    ffmpeg_args: ExtractEditorialPckgFFmpegModel = SettingsField(
        default_factory=ExtractEditorialPckgFFmpegModel,
        title="FFmpeg arguments"
    )


class ExtractEditorialPckgConversionModel(BaseSettingsModel):
    """Set output definition if resource files should be converted."""
    conversion_enabled: bool = SettingsField(
        True, title="Conversion enabled")
    output: ExtractEditorialPckgOutputDefModel = SettingsField(
        default_factory=ExtractEditorialPckgOutputDefModel,
        title="Output Definitions",
    )


class TrayPublisherPublishPlugins(BaseSettingsModel):
    CollectCSVIngestPrevalidationReport: ValidatePluginModel = SettingsField(
        default_factory=ValidatePluginModel,
        title="Collect CSV Ingest Prevalidation Report",
    )
    CollectSequenceFrameData: ValidatePluginModel = SettingsField(
        default_factory=ValidatePluginModel,
        title="Collect Original Sequence Frame Data",
    )
    CollectSimpleInstanceRepresentations: CollectThumbnailSourceModel = (
        SettingsField(
            default_factory=CollectThumbnailSourceModel,
            title="Collect Simple Instance Representations",
        )
    )
    ValidateFrameRange: ValidateFrameRangeModel = SettingsField(
        title="Validate Frame Range",
        default_factory=ValidateFrameRangeModel,
    )
    ValidateExistingVersion: ValidatePluginModel = SettingsField(
        title="Validate Existing Version",
        default_factory=ValidatePluginModel,
    )

    ExtractEditorialPckgConversion: ExtractEditorialPckgConversionModel = (
        SettingsField(
            default_factory=ExtractEditorialPckgConversionModel,
            title="Extract Editorial Package Conversion"
        )
    )


DEFAULT_PUBLISH_PLUGINS = {
    "CollectCSVIngestPrevalidationReport": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "CollectSequenceFrameData": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "CollectSimpleInstanceRepresentations": {
        "use_reviewable_as_thumbnail_source": True
    },
    "ValidateFrameRange": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateExistingVersion": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ExtractEditorialPckgConversion": {
        "conversion_enabled": False,
        "output": {
            "ext": "mp4",
            "ffmpeg_args": {
              "video_filters": [],
              "audio_filters": [],
              "input": [
                "-apply_trc gamma22"
              ],
              "output": [
                "-pix_fmt yuv420p",
                "-crf 18",
                "-g 1",
              ]
            }
        }
    }
}
