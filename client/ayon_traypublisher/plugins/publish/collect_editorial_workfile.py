import pyblish.api


class CollectEditorialWorkfile(pyblish.api.InstancePlugin):
    """Collect data for instances created by settings creators."""

    label = "Collect Editorial Workfile"
    order = pyblish.api.CollectorOrder - 0.46

    hosts = ["traypublisher"]
    families = ["workfile"]

    def process(self, instance):
        creator_identifier = instance.data["creator_identifier"]
        if creator_identifier != "editorial_workfile_advanced":
            return
        # Mark instance for 'ExtractOTIOFile'
        instance.data["families"].append("otio.timeline.workfile")
