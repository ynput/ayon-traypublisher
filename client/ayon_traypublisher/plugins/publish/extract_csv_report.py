from __future__ import annotations

import time
from pathlib import Path

import pyblish.api


class ExtractCSVReport(pyblish.api.ContextPlugin):
    """Extract CSV ingest report.

    Each report file is inheriting name from the corresponding
    ``csv_ingest_file`` instance.
    """

    label = "Extract CSV Report"
    order = pyblish.api.ExtractorOrder - 0.45
    hosts = ["traypublisher"]

    def process(self, context: pyblish.api.Context):
        report_data: dict[str, dict[str, list[str]]] = dict(
            context.data.get("csvReportData") or {}
        )

        if not report_data:
            self.log.info("No report data found.")
            return

        for parent_instance_id, parent_report_data in report_data.items():
            result = self._write_csv_instance_report(
                context, parent_instance_id, parent_report_data)

            if not result:
                self.log.warning(
                    "Failed to write report for instance "
                    f"{parent_instance_id}."
                )

    def _write_csv_instance_report(
        self,
        context: pyblish.api.Context,
        instance_id: str,
        instance_report_data: dict[str, list[str]]
    ) -> bool:
        """Write the CSV instance report to a file.

        Args:
            context (pyblish.api.Context): The context object.
            instance_id (str): The ID of the instance to write the report for.
            instance_report_data (dict[str, list[str]]): The report data
                to write.

        Returns:
            bool: True if the report was written successfully, False otherwise.
        """
        parent_instance = self._get_csv_ingest_file_instance(
            context, instance_id)
        if parent_instance is None:
            return False

        csv_file_data = parent_instance.data["csvFileData"]
        csv_filename = Path(csv_file_data["filename"])
        csv_staging_dir = csv_file_data["staging_dir"]
        csv_filepath = Path(csv_staging_dir) / csv_filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # add _report suffix and change extension to .txt
        csv_report_filepath = csv_filepath.with_stem(
            csv_filepath.stem + f"_report_{timestamp}").with_suffix(".txt")

        # create the report file and save the content to it
        with csv_report_filepath.open("w", encoding="utf-8") as f:
            for label, rows in instance_report_data.items():
                # write rows into a simple text file as markdown
                f.write(f"## {label}\n")
                for row in rows:
                    f.write("- " + row + "\n")
                f.write("\n\n")

        self.log.info(f"CSV report saved: {csv_report_filepath}")

        return True

    def _get_csv_ingest_file_instance(
        self, context: pyblish.api.Context, instance_id: str
    ) -> pyblish.api.Instance | None:
        for instance in context:
            if instance.data["instance_id"] == instance_id:
                self.log.info(
                    f"Found parent instance with {instance} "
                    f"(instance_id: {instance_id})"
                )
                return instance
        return None
