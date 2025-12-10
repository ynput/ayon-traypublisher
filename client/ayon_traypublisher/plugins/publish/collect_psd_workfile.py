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

        workfile_file = creator_attributes["workfile_file"]
        file_name = workfile_file["filenames"][0]
        _, ext = os.path.splitext(file_name)

        ext = ext.lstrip(".")
        repre = {
            "name": ext,
            "ext": ext,
            "files": file_name,
            "stagingDir": workfile_file["directory"],
            "tags": []
        }
        instance.data["representations"].append(repre)

        file_url = os.path.join(workfile_file["directory"], file_name)
        if instance.data["productType"] == "image":
            repre["tags"].append("review")
            instance.data["families"].append("review")
            if not instance.data.get("thumbnailSource"):
                instance.data["thumbnailSource"] = file_url

        instance.data["source"] = file_url

        self.log.debug("instance.data {}".format(instance.data))
