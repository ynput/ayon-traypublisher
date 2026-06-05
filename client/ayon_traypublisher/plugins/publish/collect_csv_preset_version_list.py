from __future__ import annotations

from pathlib import Path
from typing import Any

import pyblish.api
from ayon_core.lib import StringTemplate, filter_profiles
from ayon_core.pipeline import publish
from ayon_core.pipeline.structures import ListConfig


class CollectCSVPresetVersionList(
    pyblish.api.InstancePlugin,
    publish.AYONPyblishPluginMixin,
):
    """Collect CSV Preset Version List from instance.
    """

    label = "Collect CSV Preset Version List"
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["traypublisher"]
    families = ["csv_ingest"]

    def process(self, instance):
        csv_preset_name = instance.data["csv_preset_name"]
        preset_data = self._get_csv_ingest_preset_data(
            instance, csv_preset_name)
        if not preset_data:
            return

        csv_source_path = Path(instance.data["source"])
        product_base_type = instance.data["productBaseType"]
        product_name = instance.data["productName"]
        task_name = instance.data["task"]
        task_type = None
        tasks = instance.data.get("tasks", {})
        if tasks:
            task_type = tasks.get(task_name, {}).get("type")

        if not preset_data["list_config"]["enabled"]:
            return

        profiles = preset_data["list_config"]["profiles"]
        filtering_criteria = {
            "product_base_types": product_base_type,
            "product_names": product_name,
            "task_names": task_name,
            "task_types": task_type,
        }
        profile = filter_profiles(
            profiles, filtering_criteria, logger=self.log
        )
        if not profile:
            return

        version_lists: list[ListConfig] = instance.data.setdefault(
            "versionLists", [])

        template_keys = {
            "csv_basename": csv_source_path.stem,
            "csv_parent_dir": csv_source_path.parent.name
        }
        parent_folders: list[str] | None
        if parent_folders := profile.get("parent_folders", None):
            parent_folders = [
                StringTemplate.format_template(
                    folder,
                    template_keys
                )
                for folder in parent_folders
            ]
        version_lists.append(
            ListConfig(
                name=StringTemplate.format_template(
                    profile["list_name"],
                    template_keys
                ),
                parent_folders=parent_folders,
                list_type=profile["list_type"],
            )
        )
        self.log.debug(f"Collected version lists: {version_lists}")

    @staticmethod
    def _get_csv_ingest_preset_data(
        instance: pyblish.api.Instance,
        csv_preset_name: str,
    ) -> dict | None:
        project_settings = instance.context.data["project_settings"]
        tp_settings = project_settings["traypublisher"]
        ingest_presets = tp_settings["create"]["IngestCSV"]["presets"]
        return next(
            (p for p in ingest_presets if p["name"] == csv_preset_name),
            None
        )
