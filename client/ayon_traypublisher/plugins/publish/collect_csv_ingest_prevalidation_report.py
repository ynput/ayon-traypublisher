from pprint import pformat
import pyblish.api


class CollectCSVIngestPrevalidationReport(pyblish.api.ContextPlugin):
    """Collect CSV Ingest prevalidation report data from instances.
    """

    label = "Collect CSV Ingest instances data"
    order = pyblish.api.CollectorOrder + 0.5
    hosts = ["traypublisher"]
    families = ["csv_ingest"]

    settings_category = "traypublisher"

    validators = []

    def process(self, context):

        if "duplicate_versions" in self.validators:
            report_data: dict[str, list] = context.data.setdefault(
                "csvPrevalidationReportData", {})
            report_rows = self._duplicate_version_instances(context)
            if report_rows:
                report_data.update({
                    "duplicate_versions": report_rows
                })
        else:
            for instance in context:
                self.log.debug(pformat(instance.data))

    def _duplicate_version_instances(self, context: pyblish.api.Context):
        """Find duplicate version instances in the context."""
        report_rows = []
        duplicate_instances = []
        seen_versions = set()

        for instance in context:
            instance_context_data = {
                "folderPath": instance.data.get("folderPath"),
                "productName": instance.data.get("productName"),
                "productBaseType": instance.data.get("productBaseType"),
                "productType": instance.data.get("productType"),
                "version": instance.data.get("version"),
            }
            if instance_context_data not in seen_versions:
                seen_versions.add(instance_context_data)
            else:
                instance.data["duplicateMsg"] = (
                    "Duplicate version found for context: "
                    f"{instance_context_data}"
                )
                duplicate_instances.append(instance)

        # if any duplicate instances are found then remove it from context
        if duplicate_instances:
            for instance in duplicate_instances:
                report_rows.append(instance.data["duplicateMsg"])
                context.remove(instance)

        return report_rows
