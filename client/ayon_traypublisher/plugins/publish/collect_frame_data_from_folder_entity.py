import pyblish.api


class CollectFrameDataFromAssetEntity(pyblish.api.InstancePlugin):
    """Collect Frame Data From `taskEntity` or `folderEntity` of instance.

    Frame range data will only be collected if the keys are not yet
    collected for the instance.
    """

    order = pyblish.api.CollectorOrder + 0.491
    label = "Collect Missing Frame Data From Folder/Task"
    families = [
        "plate",
        "pointcache",
        "vdbcache",
        "online",
        "render",
    ]
    hosts = ["traypublisher"]

    def process(self, instance):
        missing_keys = []
        for key in (
            "fps",
            "frameStart",
            "frameEnd",
            "handleStart",
            "handleEnd",
        ):
            if key not in instance.data:
                missing_keys.append(key)

        # Skip the logic if all keys are already collected.
        # NOTE: In editorial is not 'folderEntity' filled, so it would crash
        #   even if we don't need it.
        if not missing_keys:
            return

        keys_set = []

        folder_entity = instance.data["folderEntity"]
        task_entity = instance.data.get("taskEntity")
        context_attributes = (
            task_entity["attrib"] if task_entity else folder_entity["attrib"]
        )

        for key in missing_keys:
            if key in context_attributes:
                instance.data[key] = context_attributes[key]
                keys_set.append(key)

        if keys_set:
            self.log.debug(
                f"Frame range data {keys_set} "
                "has been collected from folder (or task) entity."
            )
