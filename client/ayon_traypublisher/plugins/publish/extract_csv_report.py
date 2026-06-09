import time
from pathlib import Path

import pyblish.api
from ayon_core.pipeline import publish


class ExtractCSVReport(publish.Extractor):
    """Extract CSV ingest report.

    Merges two sources of report data into a single text file:

    - ``csvPrevalidationReportData`` – collected during the publish phase
      by ``CollectCSVIngestPrevalidationReport`` and stored on the context.
    - ``csvPrecreateReportData`` – collected during the create phase when
      the precreate validation is configured with ``Ignore and report``,
      stored directly on the CSV product instance.
    """

    label = "Extract CSV Report"
    order = pyblish.api.ExtractorOrder - 0.45
    families = ["csv_ingest_file"]
    hosts = ["traypublisher"]

    def process(self, instance):
        # Merge publish-phase and create-phase report data.
        report_data: dict = dict(
            instance.context.data.get("csvReportData") or {}
        )
        precreate_report = instance.data.get("csvPrecreateReportData") or {}
        for category, messages in precreate_report.items():
            report_data.setdefault(category, []).extend(messages)

        if not report_data:
            self.log.info("No report data found.")
            return

        csv_file_data = instance.data["csvFileData"]
        csv_filename = Path(csv_file_data["filename"])
        csv_staging_dir = csv_file_data["staging_dir"]
        csv_filepath = Path(csv_staging_dir) / csv_filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # add _report suffix and change extension to .txt
        csv_report_filepath = csv_filepath.with_stem(
            csv_filepath.stem + f"_report_{timestamp}").with_suffix(".txt")
        self.log.info("CSV report filepath: {}".format(csv_report_filepath))

        # create the report file and save the content to it
        with csv_report_filepath.open("w", encoding="utf-8") as f:
            for label, rows in report_data.items():
                # write rows into a simple text file as markdown
                f.write("## {}\n".format(label))
                for row in rows:
                    f.write("- " + row + "\n")
                f.write("\n\n")

        self.log.info("CSV report saved: {}".format(csv_report_filepath))
