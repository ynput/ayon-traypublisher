# -*- coding: utf-8 -*-
import pyblish.api
import os


class CollectOnlineFile(pyblish.api.InstancePlugin):
    """Collect online file and retain its file name."""
    label = "Collect Online File"
    order = pyblish.api.CollectorOrder
    families = ["online"]
    hosts = ["traypublisher"]

    def process(self, instance):
        creator_attributes: dict = instance.data["creator_attributes"]

        review = creator_attributes["add_review_family"]
        instance.data["review"] = review
        if "review" not in instance.data["families"]:
            instance.data["families"].append("review")
        self.log.info(f"Adding review: {review}")

        filepath_items = creator_attributes["representation_file"]
        if not isinstance(filepath_items, list):
            filepath_items = [filepath_items]

        for filepath_item in filepath_items:
            # Skip if filepath item does not have filenames
            filenames = filepath_item["filenames"]
            if not filenames:
                continue

            ext = os.path.splitext(filenames[0])[1].lstrip(".")
            if len(filenames) == 1:
                filenames = filenames[0]

            instance.data["representations"].append(
                {
                    "name": ext,
                    "ext": ext,
                    "files": filenames,
                    "stagingDir": filepath_item["directory"],
                    "tags": ["review"] if review else []
                }
            )
