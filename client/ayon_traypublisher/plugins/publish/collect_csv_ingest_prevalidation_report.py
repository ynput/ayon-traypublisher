import pyblish.api
from ayon_core.pipeline.publish import (
    OptionalPyblishPluginMixin,
)


class CollectCSVIngestPrevalidationReport(
    OptionalPyblishPluginMixin,
    pyblish.api.InstancePlugin
):
    """Collect CSV Ingest prevalidation report data from instances.
    """

    label = "Collect CSV Ingest Prevalidation Report"
    order = pyblish.api.CollectorOrder + 0.499
    hosts = ["traypublisher"]
    families = ["csv_ingest"]

    settings_category = "traypublisher"

    def process(self, instance):
        # first get csvReportData if there are any from Creator phase
        report_data: dict[str, list] = instance.context.data.get(
            "csvReportData", {})
        if not report_data:
            for instance_ in instance.context:
                report_data = instance_.data.get("csvReportData", {})
                if report_data:
                    break
            instance.context.data["csvReportData"] = report_data

        prevalidation = instance.data["prevalidation"]

        failing_validation = False
        if prevalidation["existing_versions"]["mode"] == "ignore":
            report_row = self._existing_version_check(
                instance)
            if report_row:
                existing_rows: list[str] = report_data.setdefault(
                    "Existing Versions Validation", []
                )
                existing_rows.append(report_row)
                failing_validation = True

        if prevalidation["wrong_framerange"]["mode"] == "ignore":
            report_row = self._wrong_framerange_check(
                instance)
            if report_row:
                wrongrange_rows: list[str] = report_data.setdefault(
                    "Wrong Frame Range", []
                )
                wrongrange_rows.append(report_row)
                failing_validation = True

        # Skip publishing if requested
        if failing_validation:
            instance.context.remove(instance)

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
