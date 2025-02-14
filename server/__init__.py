from ayon_server.addons import BaseServerAddon
from ayon_server.actions import SimpleActionManifest

from .settings import TraypublisherSettings, DEFAULT_TRAYPUBLISHER_SETTING


class Traypublisher(BaseServerAddon):
    settings_model = TraypublisherSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_TRAYPUBLISHER_SETTING)

    async def get_simple_actions(
        self,
        project_name: str | None = None,
        variant: str = "production",
    ) -> list["SimpleActionManifest"]:
        if not project_name:
            return []
        icon = {
            "type": "material-symbols",
            "name": "upload_2",
            "color": "#ffffff",
        }
        kwargs = {
            "label": "Tray Publisher",
            "category": "Desktop tools",
            "icon": icon,
            "order": 100,
            "entity_subtypes": None,
            "allow_multiselection": False,
        }
        return [
            SimpleActionManifest(
                identifier="traypublisher.project",
                entity_type="project",
                **kwargs
            ),
            SimpleActionManifest(
                identifier="traypublisher.folder",
                entity_type="folder",
                **kwargs
            ),
            SimpleActionManifest(
                identifier="traypublisher.task",
                entity_type="task",
                **kwargs
            ),
        ]

    async def execute_action(
        self,
        executor: "ActionExecutor",
    ) -> "ExecuteResponseModel":
        """Execute an action provided by the addon"""
        context = executor.context
        project_name = context.project_name

        return await executor.get_launcher_action_response(
            args=[
                "addon", "traypublisher",
                "launch", "--project", project_name,
            ]
        )