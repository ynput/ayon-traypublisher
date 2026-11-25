from pathlib import Path

import pyblish.api

from ayon_core.pipeline import publish
from ayon_core.pipeline.traits import (
    FileLocation,
    Geometry,
    Image,
    Persistent,
    Representation,
    Spatial,
    Static,
)


class CollectModel(pyblish.api.InstancePlugin, publish.AYONPyblishPluginMixin):
    """Collect model from file"""

    label = "Collect Model"
    order = pyblish.api.CollectorOrder + 0.492
    hosts = ["traypublisher"]

    def process(self, instance):
        if (
            instance.data.get("creator_identifier")
            != "io.ayon.creators.traypublisher.model"
        ):
            return

        creator_attributes = instance.data["creator_attributes"]

        reviewable_path = Path(creator_attributes["abs_reviewable_path"])
        file_extension = reviewable_path.suffix[1:]
        review_representation_data = dict(
            ext=file_extension,
            name=file_extension,
            stagingDir=reviewable_path.parent.as_posix(),
            files=reviewable_path.name,
            tags=["review"],
            outputName="review",
        )
        instance.data["representations"].append(review_representation_data)

        if "review" not in instance.data["families"]:
            instance.data["families"].append("review")

        if not instance.data.get("thumbnailSource"):
            instance.data["thumbnailSource"] = str(reviewable_path)

        # sorry, couldn't work out why this wasn't being
        # set elsewhere and extract review errors without these set
        instance.data["frameStart"] = 1
        instance.data["frameEnd"] = 1
        instance.data["frameStartHandle"] = 1
        instance.data["frameEndHandle"] = 1
        instance.data["fps"] = 24

        model_path = Path(creator_attributes["abs_model_path"])
        up_axis = creator_attributes["up_axis"]
        handedness = creator_attributes["handedness"]
        meters_per_unit = creator_attributes["meters_per_unit"]
        publish.add_trait_representations(
            instance,
            (
                Representation(
                    name=model_path.suffix[1:].lower(),
                    traits=[
                        Static(),
                        FileLocation(file_path=model_path),
                        Persistent(),
                        Geometry(),
                        Spatial(
                            up_axis=up_axis,
                            handedness=handedness,
                            meters_per_unit=meters_per_unit,
                        ),
                    ],
                ),
            ),
        )
