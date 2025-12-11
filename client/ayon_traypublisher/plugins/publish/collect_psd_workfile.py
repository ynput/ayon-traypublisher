import os

import pyblish.api
from ayon_core.pipeline import AYONPyblishPluginMixin


class CollectPSDWorkfile(
    pyblish.api.InstancePlugin, AYONPyblishPluginMixin
):
    """Collect file url for psd workfile + image instance combo.

    Creates representation for both workfile and image products. Adds review
    tag and family if product type is image.
    """

    label = "Collect PSD Workfile + Image Files"
    order = pyblish.api.CollectorOrder

    hosts = ["traypublisher"]
    # families = ["editorial"]

    def process(self, instance):
        if "psd_workfile_image" not in instance.data.get("creator_identifier"):
            return

        creator_attributes = instance.data["creator_attributes"]

        filepath_def = creator_attributes["filepath"]
        file_name = filepath_def["filenames"][0]
        _, ext = os.path.splitext(file_name)

        ext = ext.lstrip(".")
        repre = {
            "name": ext,
            "ext": ext,
            "files": file_name,
            "stagingDir": filepath_def["directory"],
            "tags": []
        }
        instance.data["representations"].append(repre)

        file_url = os.path.join(filepath_def["directory"], file_name)
        add_review_family = creator_attributes.get("add_review_family", False)
        if instance.data["productType"] == "image" and add_review_family:
            repre["tags"].append("review")
            instance.data["families"].append("review")
            if not instance.data.get("thumbnailSource"):
                instance.data["thumbnailSource"] = file_url

        instance.data["source"] = file_url

        self.log.debug("instance.data {}".format(instance.data))
