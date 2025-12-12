import typing

from ayon_server.addons import BaseServerAddon
from ayon_server.actions import SimpleActionManifest
from ayon_server.entities import FolderEntity, TaskEntity

from .settings import TraypublisherSettings, DEFAULT_TRAYPUBLISHER_SETTING

if typing.TYPE_CHECKING:
    from ayon_server.actions import (
        ActionExecutor,
        ExecuteResponseModel,
    )


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
        """Execute an action provided by the addon."""
        context = executor.context

        project_name = context.project_name
        args = [
            "addon", "traypublisher", "launch",
            "--project", project_name,
        ]

        if executor.identifier == "traypublisher.folder":
            folder_id = context.entity_ids[0]
            folder = await FolderEntity.load(project_name, folder_id)
            args.extend(["--folder-path", folder.path])

        elif executor.identifier == "traypublisher.task":
            task_id = context.entity_ids[0]
            task = await TaskEntity.load(project_name, task_id)
            folder = await FolderEntity.load(project_name, task.folder_id)
            args.extend([
                "--folder-path", folder.path,
                "--task-name", task.name,
            ])

        return await executor.get_launcher_action_response(args=args)
