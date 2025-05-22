from __future__ import annotations
import os

import pyblish.api
import clique


class CollectTextureInstance(pyblish.api.InstancePlugin):
    """Collect texture instance representations as UDIMs."""

    label = "Collect Texture Instance"
    order = pyblish.api.CollectorOrder - 0.48
    families = ["texture_creator"]
    hosts = ["traypublisher"]

    def process(self, instance: pyblish.api.Instance):
        creator_attributes = instance.data["creator_attributes"]
        filepath_items = creator_attributes["representation_files"]
        if not isinstance(filepath_items, list):
            filepath_items = [filepath_items]

        representations = instance.data.setdefault("representations", [])
        is_udim: bool = creator_attributes.get("is_udim", True)
        for filepath_item in filepath_items:
            representation = self._create_representation_data(
                filepath_item,
                assume_sequence_as_udim=is_udim)
            if representation:
                representations.append(representation)

    def _create_representation_data(
        self, filepath_item, assume_sequence_as_udim
    ):
        """Create new representation data based on file item.

        This method processes the provided file item to generate a dictionary
        containing representation data. If the file item represents a UDIM
        texture sequence, the method collects UDIM frame indexes and attaches
        them to the representation data under the `udim` key.

        Args:
            filepath_item (dict[str, Any]): Item with information about
                representation paths.
            assume_sequence_as_udim (bool): Whether an input file sequence
                should be considered as UDIM sequence instead of animated
                frame range sequence.

        Returns:
            dict[str, Any]: Prepared base representation data, including
            fields such as `ext`, `name`, `stagingDir`, `files`, `tags`, and
            optionally `udim` if UDIMs are detected.
        """

        filenames = filepath_item["filenames"]
        if not filenames:
            return {}

        ext = os.path.splitext(filenames[0])[1].lstrip(".")
        if len(filenames) == 1:
            filenames = filenames[0]

        representation_data = {
            "ext": ext,
            "name": ext,
            "stagingDir": filepath_item["directory"],
            "files": filenames,
            "tags": []
        }

        if assume_sequence_as_udim:
            udims = self.collect_udims(representation_data)
            if udims:
                self.log.debug(f"Collected UDIMs: {udims}")
                representation_data["udim"] = udims

        return representation_data

    def collect_udims(self, representation: dict) -> list[str]:
        """Collect UDIMs from representation."""
        filenames = representation["files"]
        if not filenames or not isinstance(filenames, list):
            return []
        filenames: list[str]

        # clique.PATTERNS["frames"] but also allow `_` before digits
        # and enforce only detecting 4 digits
        pattern = r"[._](?P<index>(?P<padding>0*)\d+)\.\D+\d?$"
        collections, remainder = clique.assemble(
            filenames,
            minimum_items=1,
            patterns=[pattern],
        )
        if not collections:
            # Not a sequence filename
            self.log.debug(f"No UDIM sequence detected for {remainder}")
            return []

        if len(collections) != 1:
            raise ValueError(
                "Expected exactly one collection, "
                f"but found {collections}."
            )

        return [
            f"{frame:04d}" for frame in collections[0].indexes
        ]
