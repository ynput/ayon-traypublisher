from pprint import pformat

import pyblish.api
from ayon_core.pipeline import publish
from ayon_traypublisher.api.structures import PassingDataValue


class CollectCSVIngestInstancesData(
    pyblish.api.InstancePlugin,
    publish.AYONPyblishPluginMixin,
    publish.ColormanagedPyblishPluginMixin
):
    """Collect CSV Ingest data from instance."""

    label = "Collect CSV Ingest instances data"
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["traypublisher"]
    families = ["csv_ingest"]

    def process(self, instance):

        # populate all attributes to instance data
        self._process_passing_data(instance)

        # populate representation data to instance data
        self._process_representation_data(instance)

    def _process_representation_data(self, instance):
        """Populate representation data to instance data."""

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

    def _process_passing_data(self, instance):
        """Populate attribute data to instance data."""

        passing_data: list[PassingDataValue] = instance.data.get(
            "csv_passing_data", [])
        if not passing_data:
            return

        version_data = {}
        instance_data = {}
        for data_item in passing_data:
            key_name = data_item["name"]
            item_value = data_item["value"]
            data_type = data_item["data_type"]
            if data_type == "version_data":
                version_data[key_name] = item_value
            elif data_type == "instance_data":
                instance_data[key_name] = item_value

        if version_data:
            instance.data["versionData"] = version_data
        if instance_data:
            for key, value in instance_data.items():
                instance.data[key] = value
