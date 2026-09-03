import os

import pyblish.api
from ayon_core.pipeline import AYONPyblishPluginMixin


class CollectMovieBatchPathWarnings(pyblish.api.ContextPlugin):
    """Report ambiguous batch movie folder matches to the publish report."""

    label = "Collect Movie Batch Path Warnings"
    order = pyblish.api.CollectorOrder - 0.1
    hosts = ["traypublisher"]

    def process(self, context):
        warnings = [
            instance.data["batch_movie_path_warning"]
            for instance in context
            if instance.data.get("batch_movie_path_warning")
        ]
        if warnings:
            self.log.warning(
                "Please check your instances - batch movie paths. "
                "Multiple folders matched, so the first matching folder "
                "was selected. The folder path can be adjusted in the "
                "instance settings.\n%s",
                "\n".join(warnings),
            )


class CollectMovieBatch(
    pyblish.api.InstancePlugin, AYONPyblishPluginMixin
):
    """Collect file url for batch movies and create representation.

    Adds review on instance and to repre.tags based on value of toggle button
    on creator.
    """

    label = "Collect Movie Batch Files"
    order = pyblish.api.CollectorOrder

    hosts = ["traypublisher"]

    def process(self, instance):
        if instance.data.get("creator_identifier") != "render_movie_batch":
            return

        creator_attributes = instance.data["creator_attributes"]

        file_url = creator_attributes["filepath"]
        file_name = os.path.basename(file_url)
        _, ext = os.path.splitext(file_name)

        repre = {
            "name": ext[1:],
            "ext": ext[1:],
            "files": file_name,
            "stagingDir": os.path.dirname(file_url),
            "tags": []
        }
        instance.data["representations"].append(repre)

        if creator_attributes["add_review_family"]:
            repre["tags"].append("review")
            instance.data["families"].append("review")
            if not instance.data.get("thumbnailSource"):
                instance.data["thumbnailSource"] = file_url

        instance.data["source"] = file_url

        self.log.debug("instance.data {}".format(instance.data))
