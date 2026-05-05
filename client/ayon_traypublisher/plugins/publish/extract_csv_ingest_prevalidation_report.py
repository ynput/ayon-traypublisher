import time
from pathlib import Path

import pyblish.api
from ayon_core.pipeline import publish


class ExtractCSVPrevalidationReport(publish.Extractor):
    """
    Extractor CSV ingest prevalidation report
    """

    label = "Extract CSV file"
    order = pyblish.api.ExtractorOrder - 0.45
    families = ["csv_ingest_file"]
    hosts = ["traypublisher"]

    def process(self, instance):
        prevalidation_report_data = instance.context.data.get(
            "csvPrevalidationReportData", {})
        if not prevalidation_report_data:
            self.log.info("No prevalidation report data found.")
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
            for label, rows in prevalidation_report_data.items():
                # write rows into a simple text file as markdown
                f.write("## {}\n".format(label))
                for row in rows:
                    f.write(", ".join(row) + "\n")
                f.write("\n")


        self.log.info("CSV report saved: {}".format(csv_report_filepath))
