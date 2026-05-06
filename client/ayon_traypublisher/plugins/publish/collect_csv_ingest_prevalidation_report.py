from pprint import pformat
import pyblish.api
from ayon_core.pipeline.publish import (
    OptionalPyblishPluginMixin,
)

class CollectCSVIngestPrevalidationReport(
    OptionalPyblishPluginMixin,
    pyblish.api.ContextPlugin
):
    """Collect CSV Ingest prevalidation report data from instances.
    """

    label = "Collect CSV Ingest Prevalidation Report"
    order = pyblish.api.CollectorOrder + 0.499
    hosts = ["traypublisher"]
    families = ["csv_ingest"]

    settings_category = "traypublisher"

    validators = []

    def process(self, context):

        if "existing_versions" in self.validators:
            report_data: dict[str, list] = context.data.setdefault(
                "csvPrevalidationReportData", {})
            report_rows = self._existing_version_check(context)
            if report_rows:
                report_data.update({
                    "Existing Versions Validation": report_rows
                })
        if "wrong_framerange" in self.validators:
            report_data: dict[str, list] = context.data.setdefault(
                "csvPrevalidationReportData", {})
            report_rows = self._wrong_framerange_check(context)
            if report_rows:
                report_data.update({
                    "Wrong Frame Range": report_rows
                })

    def _existing_version_check(self, context: pyblish.api.Context):
        """Find duplicate version instances in the context."""
        report_rows = []
        duplicate_instances = []

        for instance in context:
            # Skip the instance if is not active by data on the instance
            if not self.is_active(instance.data):
                continue

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
                instance.data["existingVersionMsg"] = (
                    "Existing version found for context: "
                    f"{instance_context_data}"
                )
                duplicate_instances.append(instance)

        # if any duplicate instances are found then remove it from context
        if duplicate_instances:
            for instance in duplicate_instances:
                publish_attributes = instance.data["publish_attributes"]
                report_rows.append(instance.data["existingVersionMsg"])
                publish_attributes["ValidateExistingVersion"]["active"] = False
                # context.remove(instance)

        return report_rows

    def _wrong_framerange_check(self, context: pyblish.api.Context):
        """Check for instances with wrong frame range."""
        report_rows = []
        wrong_framerange_instances = []

        for instance in context:
            # Skip the instance if is not active by data on the instance
            if not self.is_active(instance.data):
                continue

            # editorial would fail since they might not be in database yet
            new_hierarchy = instance.data.get("newHierarchyIntegration")
            if new_hierarchy:
                self.log.debug("Instance is creating new folder. Skipping.")
                continue

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
                continue

            repres = instance.data.get("representations")
            if not repres:
                self.log.info("No representations, skipping.")
                return

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
                    msg = (
                        "Instance context: {} - Frame duration from DB:'{}' doesn't match number of files:'{}'"
                        " Please change frame range for folder/task or limit no. of files"
                    ).format(instance_context_data, int(duration), frames)

                    wrong_framerange_instances.append(
                        {
                            "instance": instance,
                            "msg": msg
                        }
                    )

        if wrong_framerange_instances:
            for fail_data in wrong_framerange_instances:
                self.log.debug(f"Wrong frame range instance: {fail_data}")
                instance = fail_data["instance"]
                publish_attributes = instance.data["publish_attributes"]
                report_rows.append(fail_data["msg"])
                publish_attributes["ValidateFrameRange"]["active"] = False
                # context.remove(fail_data["instance"])

        return report_rows
