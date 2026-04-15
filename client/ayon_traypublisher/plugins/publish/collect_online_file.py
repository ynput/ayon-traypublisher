# -*- coding: utf-8 -*-
import pyblish.api


class CollectOnlineFile(pyblish.api.InstancePlugin):
    """Collect online file and retain its file name."""
    label = "Collect Online File"
    order = pyblish.api.CollectorOrder - 0.495
    families = ["online"]
    hosts = ["traypublisher"]

    def process(self, instance: pyblish.api.Instance):
        if instance.data.get("creator_identifier") != "io.ayon.creators.traypublisher.online":
            return

        instance.data["families"].append("simple.instance")

        creator_attributes = instance.data["creator_attributes"]
        filepath_item = creator_attributes.pop("representation_file")
        # Pass the item as 'representation_files' for simple instances collector
        creator_attributes["representation_files"] = [filepath_item]
