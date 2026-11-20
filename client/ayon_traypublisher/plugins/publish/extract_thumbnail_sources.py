import pyblish.api


class TraypublisherThumbnailSources(pyblish.api.ContextPlugin):
    """Use the reviewable as thumbnail source where nothing else can.

    Collectors store the reviewable's first file to
    'traypublisherThumbnailSource' instead of 'thumbnailSource'. That
    lets 'ExtractThumbnail' (ayon-core) create the thumbnail from the
    review, so its profiles and colorspace handling apply.

    'ExtractThumbnail' only processes instances of certain families. For
    the other instances (e.g. 'plate', 'model', 'workfile') the stored
    file is set as 'thumbnailSource', so 'ExtractThumbnailFromSource'
    creates the thumbnail as before.

    A thumbnail dropped in the publisher is already in 'thumbnailSource'
    and is never replaced.
    """

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
