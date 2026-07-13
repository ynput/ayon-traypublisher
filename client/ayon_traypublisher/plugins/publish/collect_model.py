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
    Tagged,
)

MODEL_KEY_PREFIX = "abs_model_path"
UP_AXIS_KEY_PREFIX = "up_axis"
HANDEDNESS_KEY_PREFIX = "handedness"
METERS_PER_UNIT_KEY_PREFIX = "meters_per_unit"


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
        representations = [
            Representation(
                name=file_extension,
                traits=[
                    Static(),
                    FileLocation(file_path=reviewable_path),
                    Persistent(),
                    Image(),
                    Tagged(tags=["reviewable"]),
                ],
            )
        ]

        if "review" not in instance.data["families"]:
            instance.data["families"].append("review")

        if not instance.data.get("thumbnailSource"):
            instance.data["thumbnailSource"] = str(reviewable_path)

        # Collect all model files
        model_path_by_suffix = {
            key.replace(MODEL_KEY_PREFIX, ""): Path(model_path)
            for key, model_path in creator_attributes.items()
            if key.startswith(MODEL_KEY_PREFIX)
        }

        if len(model_path_by_suffix) == 0:
            raise publish.PublishError("No model files found in creator attributes.")

        # Create a representation per file.
        for suffix, model_path in model_path_by_suffix.items():
            file_extension = model_path.suffix[1:].lower()
            up_axis = creator_attributes[f"{UP_AXIS_KEY_PREFIX}{suffix}"]
            handedness = creator_attributes[f"{HANDEDNESS_KEY_PREFIX}{suffix}"]
            meters_per_unit = creator_attributes[
                f"{METERS_PER_UNIT_KEY_PREFIX}{suffix}"
            ]
            suffix = suffix if len(model_path_by_suffix) > 1 else ""
            representations.append(
                Representation(
                    name=f"{file_extension}{suffix}",
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
                )
            )
        publish.add_trait_representations(instance, representations)
