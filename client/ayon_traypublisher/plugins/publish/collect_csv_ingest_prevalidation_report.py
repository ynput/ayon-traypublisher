from __future__ import annotations

import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pprint import pformat

import pyblish.api
from ayon_core.lib import get_ffprobe_data
from ayon_core.lib.transcoding import VIDEO_EXTENSIONS
from ayon_core.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishError,
)


_VIDEO_EXTENSIONS = {ext.lower().lstrip(".") for ext in VIDEO_EXTENSIONS}
_FFPROBE_WORKERS = 4


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
       - **Readable Videos** – Runs ``ffprobe`` on the video files of
         each instance, so unreadable ones are found before extraction
         starts. With mode ``"error"`` publishing stops with the list of
         all unreadable files, with ``"ignore"`` the instances are removed
         and reported. Skipped by default, it is heavy for big batches.

    Instances that fail any of the above validations are removed from the
    publish context and their failure details are recorded in the report.
    """

    label = "Collect CSV Ingest Prevalidation Report"
    order = pyblish.api.CollectorOrder + 0.499
    hosts = ["traypublisher"]

    settings_category = "traypublisher"

    def process(self, context: pyblish.api.Context):
        report_per_csv_ingest = defaultdict(dict)
        unreadable_errors: list[str] = []
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

            readable_mode = prevalidation["readable_videos"]["mode"]
            if readable_mode in {"error", "ignore"}:
                report_rows = self._unreadable_videos_check(
                    instance, readable_mode)
                if report_rows and readable_mode == "ignore":
                    unreadable_rows: list[str] = report_data.setdefault(
                        "Unreadable Videos", []
                    )
                    unreadable_rows.extend(report_rows)
                    failing_validation = True
                elif report_rows:
                    unreadable_errors.extend(report_rows)

            # Skip publishing if ignored with report is chosen
            if failing_validation:
                context.remove(instance)

        if unreadable_errors:
            # all unreadable videos are reported at once, before any
            # extraction work is done
            raise PublishError(
                f"Detected {len(unreadable_errors)} broken video file(s).",
                title="Broken video files",
                description=(
                    "## Broken video files detected\n"
                    "Some of the ingested video files cannot be read by "
                    "`ffprobe`, so publishing was stopped before any "
                    "extraction started.\n\n"
                    "Replace or remove the broken files, or set the preset "
                    "`Readable Videos (ffprobe)` to `Ignore and report` to "
                    "publish the rest.\n\n"
                    "The affected file paths are listed in the details "
                    "and in the publish log."
                ),
                detail="\n".join(unreadable_errors),
            )

        self.log.debug(
            f"Collected {len(report_per_csv_ingest)} CSV ingest "
            f"prevalidation reports"
        )
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
            latest_version is not None and
            int(version) == int(latest_version)
        ):
            return (
                f"Version '{version}' already exists for context: "
                f"{instance_context_data}"
            )

        if (
            latest_version is not None and
            int(version) < int(latest_version)
        ):
            return (
                f"Higher version '{latest_version}' already exists disallowing"
                f" version '{version}' for context:"
                f" {instance_context_data}"
            )

        return ""

    def _unreadable_videos_check(
        self,
        instance: pyblish.api.Instance,
        mode: str,
    ) -> list[str]:
        """Find video files of the instance that ffprobe cannot read.

        Each unreadable file is logged, as an error for mode ``"error"``
        and as a warning for mode ``"ignore"``, so it shows in the
        publish report.

        Returns:
            list[str]: One report row per unreadable file.
        """
        # Skip the instance if is not active by data on the instance
        if not self.is_active(instance.data):
            return []

        filepaths = []
        for repre in instance.data.get("representations") or []:
            ext = str(repre.get("ext") or "").lower().lstrip(".")
            if ext not in _VIDEO_EXTENSIONS:
                continue
            files = repre["files"]
            if isinstance(files, str):
                files = [files]
            staging_dir = repre["stagingDir"]
            filepaths.extend(os.path.join(staging_dir, name) for name in files)

        if not filepaths:
            return []

        with ThreadPoolExecutor(max_workers=_FFPROBE_WORKERS) as executor:
            results = list(executor.map(self._ffprobe_problem, filepaths))

        product_name = instance.data.get("productName")
        log_method = self.log.error if mode == "error" else self.log.warning
        rows = []
        for filepath, problem in zip(filepaths, results):
            if problem:
                row = f"File '{filepath}' cannot be read by ffprobe: {problem}"
                log_method(row)
                rows.append(row)

        if rows:
            self.log.debug(
                f"Checked {len(filepaths)} video file(s) of "
                f"'{product_name}', {len(rows)}/{len(filepaths)} unreadable."
            )
        else:
            self.log.debug(
                f"Checked {len(filepaths)} video file(s) of "
                f"'{product_name}'. All readable."
            )
        return rows

    def _ffprobe_problem(self, filepath: str) -> str:
        """Return the reason ffprobe cannot read the file, else empty."""
        if not os.path.isfile(filepath):
            return "file does not exist"
        try:
            data = get_ffprobe_data(filepath, self.log)
        except Exception as exc:
            return str(exc) or exc.__class__.__name__
        if data.get("error"):
            return str(data["error"].get("string") or data["error"])
        if not any(
            stream.get("codec_type") == "video"
            for stream in data.get("streams") or []
        ):
            return "no video stream found"
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

    def _is_instance_plugin_active(
        self,
        instance: pyblish.api.Instance,
        plugin_name: str
    ) -> bool:
        """Check if the plugin is enabled for the given instance.

        Args:
            instance (pyblish.api.Instance): The instance to check.
            plugin_name (str): The name of the plugin to check.

        Returns:
            bool: True if the plugin is available and active
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
