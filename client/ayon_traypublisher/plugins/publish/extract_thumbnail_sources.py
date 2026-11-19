import pyblish.api


class TraypublisherThumbnailSources(pyblish.api.ContextPlugin):
    label = "Thumbnail Sources"
    # Before ExtractThumbnailFromSource in core
    order = (pyblish.api.ExtractorOrder - 0.00001) - 0.00001
    hosts = ["traypublisher"]

    def process(self, context):
        # families from 'ExtractThumbnail'
        et_families = {
            "imagesequence", "render", "render2d", "prerender",
            "source", "clip", "take", "online", "image", "editorial_pkg"
        }
        for instance in context:
            if instance.data.get("thumbnailSource"):
                continue

            source = instance.data.get("traypublisherThumbnailSource")
            if not source:
                continue

            families = set(instance.data.get("families") or [])
            families.add(instance.data["family"])
            if families.intersection(et_families):
                continue
            instance.data["thumbnailSource"] = source
