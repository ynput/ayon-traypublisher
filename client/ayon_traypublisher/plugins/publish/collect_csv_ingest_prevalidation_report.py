from __future__ import annotations

from collections import defaultdict
from pprint import pformat

import pyblish.api
from ayon_core.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishError,
)


class CollectCSVIngestPrevalidationReport(
    OptionalPyblishPluginMixin,
    pyblish.api.ContextPlugin
):
    """Collect CSV Ingest prevalidation report data into context data.

    This plugin merges two sources of report data into a single dictionary
    stored at ``context.data["csvReportData"]``, keyed by the ID of each
    parent ``csv_ingest_file`` instance.

    The data is gathered across two phases:

    1. **Create phase** – Report data is collected by ``IngestCSV`` and
       stored on ``instance.data["csvReportData"]`` of each
       ``csv_ingest_file`` instance.
    2. **Publish phase** – Additional validation checks are performed here
       for each ``csv_ingest`` instance:

       - **Existing Versions** – Flags instances whose version already
         exists in the database (when the preset mode is set to
         ``"ignore"``).
       - **Wrong Frame Range** – Flags instances where the number of
         ingested files does not match the frame range duration defined
         in the database (when the preset mode is set to ``"ignore"``).

    Instances that fail any of the above validations are removed from the
    publish context and their failure details are recorded in the report.
    """

    label = "Collect CSV Ingest Prevalidation Report"
    order = pyblish.api.CollectorOrder + 0.499
    hosts = ["traypublisher"]

    settings_category = "traypublisher"

    def process(self, context: pyblish.api.Context):
        report_per_csv_ingest = defaultdict(dict)
        # at first we need to get csv_ingest_file instance and distribute
        # its csvReportData from creating phase to context data
        for instance in context:
            if not self._is_csv_ingest_file_instance(instance):
                continue

            csv_report_data = self._get_csv_instance_report(instance)

            if not csv_report_data:
                # Instance has nothing to report
                continue

            instance_id = instance.data["instance_id"]
            report_per_csv_ingest[instance_id] = csv_report_data

        # now we can distribute csvReportData from parent csv_ingest_file
        # instances to their csv_ingest instances
        for instance in list(context):
            if not self._is_csv_ingest_instance(instance):
                continue

            # parent instance id is added during creating phase only to
            # instances related to csv_ingest_file parent instance
            csv_parent_instance_id = instance.data.get("csv_parent_instance")
            if not csv_parent_instance_id:
                continue

            # for each instance make sure we do have correct csv preset data
            csv_preset_name = instance.data["csv_preset_name"]
            preset_data = self._get_csv_ingest_preset_data(
                context, csv_preset_name)

            # very unlikely this will happen but just in case we make sure
            # it exists. Only case would be if a admin would remove preset
            # just before the publish button was pushed
            if not preset_data:
                raise PublishError(
                    f"Preset does not exist anymore: {csv_preset_name}")

            prevalidation = preset_data["prevalidation"]

            # we need to make sure the data are available even nothing
            # was added from creator context processed in first pass
            report_data = report_per_csv_ingest[csv_parent_instance_id]
            plugin_enabled = self._is_instance_plugin_active(
                instance, "ValidateExistingVersion")
            failing_validation = False
            if (
                prevalidation["existing_versions"]["mode"] == "ignore"
                and plugin_enabled
            ):
                # only check existing version if related validator is enabled
                version = instance.data.get("version")
                if version is not None:
                    report_row = self._existing_version_check(instance)
                else:
                    report_row = ""
                if report_row:
                    existing_rows: list[str] = report_data.setdefault(
                        "Existing Versions Validation", []
                    )
                    existing_rows.append(report_row)
                    failing_validation = True

            plugin_enabled = self._is_instance_plugin_active(
                instance, "ValidateFrameRange")
            if (
                prevalidation["wrong_framerange"]["mode"] == "ignore"
                and plugin_enabled
            ):
                # only check existing version if related validator is enabled
                report_row = self._wrong_framerange_check(instance)
                if report_row:
                    wrongrange_rows: list[str] = report_data.setdefault(
                        "Wrong Frame Range", []
                    )
                    wrongrange_rows.append(report_row)
                    failing_validation = True

            # Skip publishing if ignored with report is chosen
            if failing_validation:
                context.remove(instance)

        self.log.debug(f"Collected {len(report_per_csv_ingest)} CSV ingest prevalidation reports")
        self.log.debug(f"Report data: {pformat(report_per_csv_ingest)}")

        # only store report data if there are any
        if report_per_csv_ingest:
            context.data["csvReportData"] = report_per_csv_ingest

    def _existing_version_check(
        self,
        instance: pyblish.api.Instance
    ) -> str:
        """Find duplicate version instances in the context."""

        # Skip the instance if is not active by data on the instance
        if not self.is_active(instance.data):
            return ""

        instance_context_data = {
            "folderPath": instance.data.get("folderPath"),
            "productName": instance.data.get("productName"),
            "productBaseType": instance.data.get("productBaseType"),
            "productType": instance.data.get("productType"),
            "version": instance.data.get("version"),
        }
        version = instance.data.get("version")
        latest_version = instance.data.get("latestVersion")
        if version is None:
            return ""
        if (
            latest_version is not None
            and int(version) <= int(latest_version)
        ):
            return (
                "Existing version found for context: "
                f"{instance_context_data}"
            )

        return ""

    def _wrong_framerange_check(
        self,
        instance: pyblish.api.Instance,
    ) -> str:
        """Check for instances with wrong frame range."""

        # Skip the instance if is not active by data on the instance
        if not self.is_active(instance.data):
            return ""

        # editorial would fail since they might not be in database yet
        new_hierarchy = instance.data.get("newHierarchyIntegration")
        if new_hierarchy:
            self.log.debug("Instance is creating new folder. Skipping.")
            return ""

        # Use attributes from task entity if set, otherwise from folder entity
        entity = (
            instance.data.get("taskEntity") or instance.data["folderEntity"]
        )
        attributes = entity["attrib"]
        frame_start = attributes["frameStart"]
        frame_end = attributes["frameEnd"]
        handle_start = attributes["handleStart"]
        handle_end = attributes["handleEnd"]
        duration = (frame_end - frame_start + 1) + handle_start + handle_end

        if instance.data["productBaseType"] == "csv_ingest_file":
            return ""

        repres = instance.data.get("representations")
        if not repres:
            self.log.info("No representations, skipping.")
            return ""

        for repre in repres:
            ext = repre['ext'].replace(".", '')

            if not ext or ext.lower() not in {
                "exr",
                "dpx",
                "jpg",
                "jpeg",
                "png",
                "tiff",
                "tga",
                "gif",
                "svg",
                "sxr"
            }:
                self.log.debug("Cannot check for extension {}".format(ext))
                continue

            files = repre["files"]
            if isinstance(files, str):
                continue
            frames = len(files)

            if frames != duration:
                instance_context_data = {
                    "folderPath": instance.data.get("folderPath"),
                    "productName": instance.data.get("productName"),
                    "productBaseType": instance.data.get("productBaseType"),
                    "productType": instance.data.get("productType"),
                    "version": instance.data.get("version"),
                }
                return (
                    f"Instance context: {instance_context_data} - Frame "
                    f"duration from DB:'{int(duration)}' doesn't match "
                    f"number of files:'{frames}' Please change frame "
                    "range for folder/task or limit no. of files"
                )
        return ""

    @staticmethod
    def _is_csv_ingest_file_instance(instance: pyblish.api.Instance) -> bool:
        return "csv_ingest_file" in instance.data.get("families", [])

    @staticmethod
    def _is_csv_ingest_instance(instance: pyblish.api.Instance) -> bool:
        return "csv_ingest" in instance.data.get("families", [])

    @staticmethod
    def _get_csv_instance_report(
            instance: pyblish.api.Instance) -> dict | None:
        return instance.data.get("csvReportData")

    @staticmethod
    def _get_csv_ingest_preset_data(
        context: pyblish.api.Context,
        csv_preset_name: str,
    ) -> dict | None:
        project_settings = context.data["project_settings"]
        tp_settings = project_settings["traypublisher"]
        ingest_presets = tp_settings["create"]["IngestCSV"]["presets"]
        return next(
            (p for p in ingest_presets if p["name"] == csv_preset_name),
            None
        )

    @staticmethod
    def _is_instance_plugin_active(
        instance: pyblish.api.Instance,
        plugin_name: str
    ) -> bool:
        """Check if the plugin is enabled for the given instance.

        Args:
            instance (pyblish.api.Instance): The instance to check.
            plugin_name (str): The name of the plugin to check.

        Returns:
            bool: True if the plugin is available an active
                for the instance.
        """
        # plugin might not be enabled in the publish context
        plugins = instance.context.data["create_context"].publish_plugins
        plugin = next(
            (
                pl for pl in plugins
                if pl.__name__ == plugin_name
            ),
            None
        )
        if plugin is None:
            return False

        # plugin might not be set as optional so it will not be added
        # to publish attributes
        if not plugin.optional:
            return True

        values = self.get_attr_values_from_data_for_plugin(
            plugin, instance.data
        )
        return values.get("active", False)
