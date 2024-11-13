# -*- coding: utf-8 -*-
import pyblish.api


class CollectReviewInfo(pyblish.api.InstancePlugin):
    """Collect data required for review instances.

    ExtractReview plugin requires frame start/end, fps on instance data which
    are missing on instances from TrayPublishes.

    Warning:
        This is temporary solution to "make it work". Contains removed changes
            from https://github.com/ynput/OpenPype/pull/4383 reduced only for
            review instances.
    """

    label = "Collect Review Info"
    order = pyblish.api.CollectorOrder + 0.491
    families = ["review"]
    hosts = ["traypublisher"]

    def process(self, instance):

        entity = (
            instance.data.get("taskEntity")
            or instance.data.get("folderEntity")
        )
        if instance.data.get("frameStart") is not None or not entity:
            self.log.debug("Missing required data on instance")
            return

        context_attributes = entity["attrib"]
        # Store collected data for logging
        collected_data = {}
        for key in (
            "fps",
            "frameStart",
            "frameEnd",
            "handleStart",
            "handleEnd",
        ):
            if key in instance.data or key not in context_attributes:
                continue
            value = context_attributes[key]
            collected_data[key] = value
            instance.data[key] = value
        self.log.debug("Collected data: {}".format(str(collected_data)))
