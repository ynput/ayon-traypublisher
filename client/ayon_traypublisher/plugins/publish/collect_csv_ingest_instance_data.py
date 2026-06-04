from pprint import pformat

import pyblish.api
from ayon_core.lib import StringTemplate
from ayon_core.pipeline import publish
from ayon_core.pipeline.structures import ListConfig


class CollectCSVIngestInstancesData(
    pyblish.api.InstancePlugin,
    publish.AYONPyblishPluginMixin,
    publish.ColormanagedPyblishPluginMixin
):
    """Collect CSV Ingest data from instance.
    """

    label = "Collect CSV Ingest instances data"
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["traypublisher"]
    families = ["csv_ingest"]

    def process(self, instance):
        self._collect_version_lists(instance)

        # expecting [(colorspace, repre_data), ...]
        prepared_repres_data_items = instance.data[
            "prepared_data_for_repres"]

        frame_start = None
        frame_end = None
        for prep_repre_data in prepared_repres_data_items:
            type = prep_repre_data["type"]
            colorspace = prep_repre_data["colorspace"]
            repre_data = prep_repre_data["representation"]

            # thumbnails should be skipped
            if type == "media":
                # colorspace name is passed from CSV column
                self.set_representation_colorspace(
                    repre_data, instance.context, colorspace
                )
            elif type == "media" and colorspace is None:
                # TODO: implement colorspace file rules file parsing
                self.log.warning(
                    "Colorspace is not defined in csv for following"
                    f" representation: {pformat(repre_data)}"
                )
                pass
            elif type == "thumbnail":
                # thumbnails should be skipped
                pass

            if (
                repre_data.get("tags") and
                "review" in repre_data.get("tags", [])
            ):
                if "frameStart" in repre_data and "frameEnd" in repre_data:
                    frame_start = repre_data["frameStart"]
                    frame_end = repre_data["frameEnd"]

            instance.data["representations"].append(repre_data)

        if frame_start is not None and frame_end is not None:
            instance.data["frameStart"] = frame_start
            instance.data["frameEnd"] = frame_end

    def _collect_version_lists(self, instance):
        version_lists_template = instance.data.get(
            "versionListsTemplate")

        version_lists: list[ListConfig] = instance.data.setdefault(
            "versionLists", [])

        if version_lists:
            self.log.debug(f"Version lists already collected: {version_lists}")
            return

        name = version_lists_template["name"]
        template_keys = {
            "csv_basename": version_lists_template["csv_basename"],
            "csv_parent_dir": version_lists_template["csv_parent_dir"],
        }
        parent_folders: list[str] | None
        if parent_folders := version_lists_template.get(
            "parent_folders", None):
            parent_folders = [
                StringTemplate.format_template(
                    folder,
                    template_keys
                )
                for folder in parent_folders
            ]
        version_lists.append(
            ListConfig(
                name=StringTemplate.format_template(
                    name,
                    template_keys
                ),
                parent_folders=parent_folders,
                list_type=version_lists_template["list_type"],
            )
        )
        self.log.debug(f"Collected version lists: {version_lists}")
