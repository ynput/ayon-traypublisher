from pprint import pformat

import pyblish.api
from ayon_core.pipeline import publish


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
        self._process_attr_data(instance)

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

    def _process_attr_data(self, instance):
        """Populate attribute data to instance data."""

        attr_data = instance.data.get("csv_attributes", [])
        if not attr_data:
            return

        version_data = {}
        task_data = {}
        folder_data = {}
        for attr_item in attr_data:
            attr_name = attr_item["name"]
            attr_value = attr_item["value"]
            entity_type = attr_item["entity_type"]
            if entity_type == "version":
                version_data[attr_name] = attr_value
            elif entity_type == "task":
                task_data[attr_name] = attr_value
            elif entity_type == "folder":
                folder_data[attr_name] = attr_value

        if version_data:
            instance.data["versionData"] = version_data
        if task_data:
            instance.data["taskData"] = task_data
        if folder_data:
            instance.data["folderData"] = folder_data
