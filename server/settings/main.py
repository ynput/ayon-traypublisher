from ayon_server.settings import BaseSettingsModel, SettingsField

from .imageio import TrayPublisherImageIOModel

from .creator_plugins import (
    TrayPublisherCreatePluginsModel,
    DEFAULT_CREATORS,
)
from .publish_plugins import (
    TrayPublisherPublishPlugins,
    DEFAULT_PUBLISH_PLUGINS,
)


class TraypublisherSettings(BaseSettingsModel):
    """Traypublisher Project Settings."""
    imageio: TrayPublisherImageIOModel = SettingsField(
        default_factory=TrayPublisherImageIOModel,
        title="Color Management (ImageIO)"
    )
    create: TrayPublisherCreatePluginsModel = SettingsField(
        title="Create",
        default_factory=TrayPublisherCreatePluginsModel
    )
    publish: TrayPublisherPublishPlugins = SettingsField(
        title="Publish Plugins",
        default_factory=TrayPublisherPublishPlugins
    )


DEFAULT_TRAYPUBLISHER_SETTING = {
    "create": DEFAULT_CREATORS,
    "publish": DEFAULT_PUBLISH_PLUGINS,
}
