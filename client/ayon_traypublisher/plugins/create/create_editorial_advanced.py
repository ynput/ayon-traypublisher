import os
import re
from copy import deepcopy
from itertools import zip_longest
from typing import Dict, List

import ayon_api
import clique
import opentimelineio as otio
from ayon_core.lib import (
    BoolDef,
    EnumDef,
    FileDef,
    NumberDef,
    TextDef,
    UILabelDef,
    UISeparatorDef,
)
from ayon_core.lib.transcoding import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from ayon_core.pipeline import CreatedInstance, CreatorError
from ayon_traypublisher.api.editorial import ShotMetadataSolver
from ayon_traypublisher.api.plugin import (
    HiddenTrayPublishCreator,
    TrayPublishCreator,
)

CREATOR_CLIP_ATTR_DEFS = [
    EnumDef(
        "fps",
        items=[
            {"value": "from_selection", "label": "From selected context"},
            {"value": 23.976, "label": "23.976"},
            {"value": 24, "label": "24"},
            {"value": 25, "label": "25"},
            {"value": 29.97, "label": "29.97"},
            {"value": 30, "label": "30"},
        ],
        label="FPS",
    ),
    NumberDef(
        "workfile_start_frame", default=1001, label="Workfile start frame"),
    NumberDef("handle_start", default=0, label="Handle start"),
    NumberDef("handle_end", default=0, label="Handle end"),
]

CLIP_ATTR_DEFS = [
    NumberDef(
        "frameStart",
        default=0,
        label="Frame start",
        disabled=True,
    ),
    NumberDef(
        "frameEnd",
        default=0,
        label="Frame end",
        disabled=True,
    ),
    NumberDef(
        "clipIn",
        default=0,
        label="Clip in",
        disabled=True,
    ),
    NumberDef(
        "clipOut",
        default=0,
        label="Clip out",
        disabled=True,
    ),
    NumberDef(
        "clipDuration",
        default=0,
        label="Clip duration",
        disabled=True,
    ),
    NumberDef(
        "sourceIn",
        default=0,
        label="Media source in",
        disabled=True,
    ),
    NumberDef(
        "sourceOut",
        default=0,
        label="Media source out",
        disabled=True,
    ),
]

CONTENT_TYPE_MAPPING = {
    "other": [
        "audio",
        "geometry",
        "workfile",
    ],
    "single": [
        "video",
        "image_single",
    ],
    "collection": [
        "image_sequence",
    ],
    "thumbnail": [
        "thumbnail",
    ]
}
VARIANTS_PATTERN = r"(?:_[^_v\.]+|\d+)?"
VERSION_IN_FILE_PATTERN = r".*v(\d{2,4}).*"


class EditorialClipInstanceCreatorBase(HiddenTrayPublishCreator):
    """Wrapper class for clip product type creators."""
    host_name = "traypublisher"

    def create(self, instance_data, source_data=None):
        product_name = instance_data["productName"]

        # Create new instance
        new_instance = CreatedInstance(
            data=instance_data,
            creator=self,
            product_type=self.product_base_type,
            product_name=product_name,
        )

        self._store_new_instance(new_instance)

        return new_instance

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            ),
            TextDef(
                "parent_instance",
                label="Linked to",
                disabled=True
            ),
        ]


class EditorialShotInstanceCreator(EditorialClipInstanceCreatorBase):
    """Shot product type class

    The shot metadata instance carrier.
    """
    identifier = "editorial_shot_advanced"
    product_type = "shot"
    product_base_type = "shot"
    label = "Editorial Shot"

    def get_instance_attr_defs(self):
        instance_attributes = [
            TextDef(
                "folderPath",
                label="Folder path",
                disabled=True,
            )
        ]
        instance_attributes.extend(CREATOR_CLIP_ATTR_DEFS)
        instance_attributes.extend(CLIP_ATTR_DEFS)
        return instance_attributes


class EditorialPlateInstanceCreator(EditorialClipInstanceCreatorBase):
    """Plate product type class

    Plate representation instance.
    """
    identifier = "editorial_plate_advanced"
    product_type = "plate"
    product_base_type = "plate"
    label = "Plate product"


class EditorialImageInstanceCreator(EditorialClipInstanceCreatorBase):
    """Image product type class

    Plate representation instance.
    """
    identifier = "editorial_image_advanced"
    product_type = "image"
    product_base_type = "image"
    label = "Image product"


class EditorialRenderInstanceCreator(EditorialClipInstanceCreatorBase):
    """Render product type class
    Render representation instance.
    """
    identifier = "editorial_render_advanced"
    product_type = "render"
    product_base_type = "render"
    label = "Render product"


class EditorialAudioInstanceCreator(EditorialClipInstanceCreatorBase):
    """Audio product type class

    Audio representation instance.
    """
    identifier = "editorial_audio_advanced"
    product_type = "audio"
    product_base_type = "audio"
    label = "Audio product"


class EditorialModelInstanceCreator(EditorialClipInstanceCreatorBase):
    """Model product type class

    Model representation instance.
    """
    identifier = "editorial_model_advanced"
    product_type = "model"
    product_base_type = "model"
    label = "Model product"

    def get_instance_attr_defs(self):
        return [
            TextDef(
                "parent_instance",
                label="Linked to",
                disabled=True
            ),
        ]


class EditorialCameraInstanceCreator(EditorialClipInstanceCreatorBase):
    """Camera product type class
    Camera representation instance.
    """
    identifier = "editorial_camera_advanced"
    product_type = "camera"
    product_base_type = "camera"
    label = "Camera product"

    def get_instance_attr_defs(self):
        return [
            TextDef(
                "parent_instance",
                label="Linked to",
                disabled=True
            ),
        ]

class EditorialWorkfileInstanceCreator(EditorialClipInstanceCreatorBase):
    """Workfile product type class

    Workfile representation instance.
    """
    identifier = "editorial_workfile_advanced"
    product_type = "workfile"
    product_base_type = "workfile"
    label = "Workfile product"

    def get_instance_attr_defs(self):
        return [
            TextDef(
                "parent_instance",
                label="Linked to",
                disabled=True
            ),
        ]

class EditorialAdvancedCreator(TrayPublishCreator):
    """Advanced Editorial creator class

    Advanced editorial workflow creator. This creator will process imput
    editorial file and match its clips to files in folder.

    Args:
        TrayPublishCreator (Creator): Tray publisher plugin class
    """
    enabled = True
    label = "Editorial Advanced"
    product_type = "editorial"
    product_base_type = "editorial"
    identifier = "editorial_advanced"
    default_variants = [
        "main"
    ]
    description = "Editorial files to generate shots."
    detailed_description = """
Supporting publishing new shots to project
or updating already created. Publishing will create OTIO file.
"""
    icon = "fa.file"
    product_type_presets = []

    def __init__(self, *args, **kwargs):
        self._shot_metadata_solver = ShotMetadataSolver(self.log)
        super().__init__(*args, **kwargs)

    def apply_settings(self, project_settings):
        editorial_creators = deepcopy(
            project_settings["traypublisher"]["editorial_creators"]
        )
        creator_settings = editorial_creators[self.identifier]

        self.enabled = creator_settings["enabled"]

        self._shot_metadata_solver.update_data(
            creator_settings["clip_name_tokenizer"],
            creator_settings["shot_rename"],
            creator_settings["shot_hierarchy"],
            creator_settings["shot_add_tasks"]
        )
        self.product_type_presets = creator_settings[
            "product_type_advanced_presets"]
        self.default_variants = creator_settings["default_variants"]

    def create(self, product_name, instance_data, pre_create_data):
        allowed_product_type_presets = self._get_allowed_product_type_presets(
            pre_create_data)

        ignored_keys = set(self.get_product_presets_with_names())
        ignored_keys |= {"sequence_filepath_data", "folder_path_data"}
        clip_instance_properties = {
            k: v
            for k, v in pre_create_data.items()
            if k not in ignored_keys
        }

        folder_path = instance_data["folderPath"]
        folder_entity = self.create_context.get_folder_entity(
            folder_path
        )

        if pre_create_data["fps"] == "from_selection":
            # get 'fps' from folder attributes
            fps = folder_entity["attrib"]["fps"]
        else:
            fps = float(pre_create_data["fps"])

        instance_data["fps"] = fps

        # get path of sequence
        sequence_paths = self._get_path_from_file_data(
            pre_create_data["sequence_filepath_data"],
            multi=True
        )

        media_folder_paths = self._get_path_from_file_data(
            pre_create_data["folder_path_data"],
            multi=True
        )

        # get all sequences into otio_timelines
        otio_timelines = []
        for sequence_path in sequence_paths:
            sequence_name = os.path.basename(sequence_path)
            # get otio timeline
            otio_timeline = self._create_otio_timeline(sequence_path, fps)
            otio_timelines.append((sequence_name, sequence_path, otio_timeline))

        # Create all clip instances
        clip_instance_properties.update({
            "fps": fps,
            "variant": instance_data["variant"]
        })

        ignore_clip_no_content = pre_create_data["ignore_clip_no_content"]
        for media_folder_path in media_folder_paths:
            for (sequence_name, sequence_path, otio_timeline) in otio_timelines:
                # create clip instances
                self._get_clip_instances(
                    folder_entity,
                    otio_timeline,
                    media_folder_path,
                    clip_instance_properties,
                    allowed_product_type_presets,
                    sequence_name,
                    ignore_clip_no_content,
                )

                # create otio editorial instance
                self._create_otio_instance(
                    product_name, instance_data, sequence_path, otio_timeline
                )

    def _create_otio_instance(
        self, product_name, instance_data, sequence_path, otio_timeline
    ):
        """Otio instance creating function

        Args:
            product_name (str): Product name.
            data (dict): instance data
            sequence_path (str): path to sequence file
            otio_timeline (otio.Timeline): otio timeline object
        """
        # Pass precreate data to creator attributes
        instance_data.update(
            {
                "sequenceFilePath": sequence_path,
                "otioTimeline": otio.adapters.write_to_string(otio_timeline),
            }
        )
        new_instance = CreatedInstance(
            data=instance_data,
            creator=self,
            product_type=self.product_base_type,
            product_name=product_name,
        )
        self._store_new_instance(new_instance)

    def _create_otio_timeline(self, sequence_path, fps):
        """Creating otio timeline from sequence path

        Args:
            sequence_path (str): path to sequence file
            fps (float): frame per second

        Returns:
            otio.Timeline: otio timeline object
        """
        # get editorial sequence file into otio timeline object
        extension = os.path.splitext(sequence_path)[1]

        kwargs = {}
        if extension.lower() == ".edl":
            # EDL has no frame rate embedded so needs explicit
            # frame rate else 24 is assumed.
            kwargs["rate"] = fps
            kwargs["ignore_timecode_mismatch"] = True

        return otio.adapters.read_from_file(sequence_path, **kwargs)

    def _get_path_from_file_data(self, file_path_data, multi=False):
        """Converting creator path data to single path string

        Args:
            file_path_data (FileDefItem): creator path data inputs
            multi (bool): switch to multiple files mode

        Raises:
            FileExistsError: in case nothing had been set

        Returns:
            Union[list[str], str]: Paths or single path based on
                'multi' value.
        """
        output_paths = []
        for item in file_path_data:
            dirpath = item["directory"]
            for filename in item["filenames"]:
                output_paths.append(os.path.join(dirpath, filename))

        if not output_paths:
            raise CreatorError(
                # The message is cryptic even for me might be worth to change
                f"File path was not added: {file_path_data}"
            )
        return output_paths if multi else output_paths[0]

    def _get_clip_instances(
        self,
        folder_entity,
        otio_timeline,
        media_folder_path,
        instance_data,
        product_type_presets,
        sequence_file_name,
        ignore_clip_no_content,
    ):
        """Helping function for creating clip instance

        Args:
            folder_entity (dict[str, Any]): Folder entity.
            otio_timeline (otio.Timeline): otio timeline object
            media_folder_path (str): Folder with media files
            instance_data (dict): clip instance data
            product_type_presets (list[dict]): list of dict settings
                product presets
            sequence_file_name (str): sequence file name
            ignore_clip_no_content (bool): ignore clips with no content
        """
        media_folder_path = media_folder_path.replace("\\", "/")

        # Get all tracks from otio timeline
        tracks = otio_timeline.video_tracks()


        # get all clipnames from otio timeline to list of strings
        clip_names_set = {clip.name for clip in otio_timeline.find_clips()}

        clip_folders = []
        # Iterate over all media files in media folder
        for root, folders, _ in os.walk(media_folder_path):
            # Use set intersection to find matching folder directly
            clip_folders.extend(
                folder
                for folder in folders
                if folder in clip_names_set
            )

        if not clip_folders:
            self.log.warning("No clip folder paths found")
            return

        clip_content: Dict[str, Dict[str, list[str]]] = {}
        # list content of clip folder and search for product items
        for clip_folder in clip_folders:
            abs_clip_folder = os.path.join(
                media_folder_path, clip_folder).replace("\\", "/")

            matched_product_items = []
            for root, foldernames, filenames in os.walk(abs_clip_folder):
                # iterate all product names in enabled presets
                for pres_product_data in product_type_presets:
                    product_name = pres_product_data["product_name"]

                    product_data_base = {
                        "preset_name": product_name,
                        "clip_dir_subpath": "",
                        "product_name": product_name,
                        "files": [],
                    }
                    root = root.replace("\\", "/")
                    cl_part_path = root.replace(abs_clip_folder, "")

                    for folder in foldernames:
                        product_data = deepcopy(product_data_base)
                        # need to include more since variants might occure
                        pattern_search = re.compile(
                            f".*({re.escape(product_name)}{VARIANTS_PATTERN}).*"
                        )
                        match = pattern_search.search(folder)
                        if not match:
                            continue

                        # form partial path without starting slash
                        partial_path = os.path.join(
                            cl_part_path.lstrip("/"), folder
                        ).replace("\\", "/")

                        # update product data it will be deepcopied later
                        # later in files processor
                        product_data.update(
                            {
                                "product_name": match.group(0),
                                "clip_dir_subpath": partial_path,
                            }
                        )
                        nested_files = list(
                                os.listdir(os.path.join(root, folder)))
                        self._include_files_for_processing(
                            product_name,
                            nested_files,
                            product_data,
                            matched_product_items,
                            strict=False,
                        )

                    product_data_base["clip_dir_subpath"] = "/"
                    self._include_files_for_processing(
                        product_name,
                        filenames,
                        product_data_base,
                        matched_product_items,
                    )

                # No matching product data can be skipped
                if not matched_product_items:
                    self.log.warning(
                        f"No matching product data found in {root}."
                        " Skipping folder."
                    )
                    continue

                clip_content[clip_folder] = matched_product_items

        for track in tracks:
            # set track name
            track.name = f"{sequence_file_name} - {otio_timeline.name}"

            try:
                track_start_frame = (
                    abs(track.source_range.start_time.value)
                )
                track_start_frame -= self.timeline_frame_start
            except AttributeError:
                track_start_frame = 0

            for otio_clip in track.find_clips():
                if not self._validate_clip_for_processing(otio_clip):
                    continue

                clip_related_content = clip_content.get(otio_clip.name)

                if ignore_clip_no_content:
                    if not clip_related_content:
                        continue

                    if not any(
                        item
                        for preset in product_type_presets
                        for item in clip_related_content
                        if preset["product_name"] in item["product_name"]
                    ):
                        self.log.warning(
                            f"Clip {otio_clip.name} has no related content."
                            " Skipping clip."
                        )
                        continue

                # convert timeline range to source range
                self._restore_otio_source_range(otio_clip)

                base_instance_data = self._get_base_instance_data(
                    otio_clip,
                    instance_data,
                    track_start_frame,
                    folder_entity
                )

                parenting_data = {
                    "instance_label": None,
                    "instance_id": None
                }

                self._make_shot_product_instance(
                    otio_clip,
                    deepcopy(base_instance_data),
                    parenting_data,
                )

                abs_clip_folder = os.path.join(
                    media_folder_path, otio_clip.name).replace("\\", "/")

                for pres_product_data in product_type_presets:
                    self._make_product_instance(
                        pres_product_data,
                        deepcopy(base_instance_data),
                        parenting_data,
                        clip_related_content,
                        abs_clip_folder,
                    )

    def _include_files_for_processing(
        self,
        product_name,
        filenames,
        product_data_base,
        collecting_items,
        strict=True,
    ):
        """Supporting function for getting clip content.

        Args:
            product_name (str): product name
            partial_path (str): clip folder path
            filenames (list): list of files in clip folder to collect
            product_data_base (dict): product data
            collecting_items (list): list for collecting product data items
            strict (Optional[bool]): strict mode for filtering files
        """
        # compile regex pattern for matching product name
        pattern_search = re.compile(
            f".*({re.escape(product_name)}{VARIANTS_PATTERN})"
        )
        # find intersection between files and sequences
        differences = find_string_differences(filenames)
        collections, reminders = clique.assemble(filenames)
        # iterate all collections and search for pattern in file name head
        for collection in collections:
            # check if collection is not empty
            if not collection:
                continue
            # check if pattern in name head is present
            head = collection.format("{head}")
            tail = collection.format("{tail}")
            match = pattern_search.search(head)

            # if pattern is not present in file name head
            if strict and not match:
                continue

            # add collected files to list
            # NOTE: Guess thumbnail file - potential danger.
            filtered_filenames = [
                file
                for file in filenames
                if file.startswith(head)
                if file.endswith(tail)
                if "thumb" not in file
            ]
            extension = os.path.splitext(filtered_filenames[0])[1]
            product_data = deepcopy(product_data_base)
            suffix = differences[head + tail]
            product_data.update({
                "type": "collection" if extension in IMAGE_EXTENSIONS else "other",
                "suffix": suffix,
                "files": filtered_filenames,
            })

            if strict and match:
                product_data["product_name"] = match.group(1)

            collecting_items.append(product_data)

        for reminder in reminders:
            # check if pattern in name head is present
            head, tail = os.path.splitext(reminder)
            match = pattern_search.search(head)

            # if pattern is not present in file name head
            if strict and not match:
                continue

            # add collected files to list
            filtered_filenames = [
                file for file in filenames
                if file.startswith(head)
                if file.endswith(tail)
            ]
            extension = os.path.splitext(filtered_filenames[0])[1]
            suffix = differences[filtered_filenames[0]]

            if match:
                # remove product name from suffix
                suffix = suffix.replace(match[1] or match[0], "")

            content_type = "other"
            if (
                extension in VIDEO_EXTENSIONS
                or extension in IMAGE_EXTENSIONS
            ):
                content_type = "single"

            # check if file is thumbnail
            if "thumb" in reminder:
                content_type = "thumbnail"

            product_data = deepcopy(product_data_base)
            product_data.update({
                "type": content_type,
                "suffix": suffix,
                "files": filtered_filenames,
            })

            if strict and match:
                # Extract matched pattern and handle special cases with dots
                # like name.thumbnail.jpg matches
                matched_pattern = match[1]

                product_data["product_name"] = matched_pattern

            collecting_items.append(product_data)

    def _restore_otio_source_range(self, otio_clip):
        """Infusing source range.

        Otio clip is missing proper source clip range so
        here we add them from from parent timeline frame range.

        Args:
            otio_clip (otio.Clip): otio clip object
        """
        otio_clip.source_range = otio_clip.range_in_parent()

    def _make_product_instance(
        self,
        product_preset,
        base_instance_data,
        parenting_data,
        clip_content_items,
        media_folder_path,
    ):
        """Creating product instances

        Args:
            product_preset (dict): product preset data
            base_instance_data (dict): base instance data
            parenting_data (dict): parenting data
            clip_content_items (list[dict]): list of clip content items
            media_folder_path (str): media folder path
        """
        pres_product_type = product_preset["product_type"]
        pres_product_name = product_preset["product_name"]
        pres_versioning = product_preset["versioning_type"]
        pres_representations = product_preset["representations"]

        # Dictionary to group files by product name
        grouped_representations = {}

        # First pass: group matching files by product name and representation
        for item in clip_content_items:
            item_type = item["type"]
            if pres_product_name != item["preset_name"]:
                continue

            product_name = item["product_name"]
            if product_name not in grouped_representations:
                grouped_representations[product_name] = {
                    "representations": []
                }

            # Check each representation preset against the item
            for repre_preset in pres_representations:
                preset_repre_name = repre_preset["name"]
                pres_repr_content_type = repre_preset["content_type"]
                pres_repr_tags = deepcopy(repre_preset.get("tags", []))
                pres_repr_custom_tags = deepcopy(
                    repre_preset.get("custom_tags", []))

                # Prepare filters
                extensions_filter = [
                    (ext if ext.startswith(".") else f".{ext}").lower()
                    for ext in repre_preset.get("extensions", [])
                ]
                patterns_filter = repre_preset.get("patterns", [])

                # Filter matching files
                matching_files = []
                for file in item["files"]:
                    # Validate content type matches item type mapping
                    if (
                        pres_repr_content_type not in CONTENT_TYPE_MAPPING[item_type]  # noqa
                    ):
                        continue

                    # Filter by extension
                    if not any(
                        str(file).lower().endswith(ext)
                        for ext in extensions_filter
                    ):
                        continue

                    # Filter by pattern
                    if patterns_filter and not any(
                        re.match(pattern, file)
                        for pattern in patterns_filter
                    ):
                        continue

                    matching_files.append(file)

                if not matching_files:
                    continue

                abs_dir_path = os.path.join(
                    media_folder_path, item["clip_dir_subpath"]
                ).replace("\\", "/")

                if item["clip_dir_subpath"] == "/":
                    abs_dir_path = media_folder_path

                # get extension from first file
                repre_ext = os.path.splitext(
                    matching_files[0])[1].lstrip(".").lower()

                if len(matching_files) == 1:
                    matching_files = matching_files[0]

                repre_data = {
                    "ext": repre_ext,
                    "name": preset_repre_name,
                    "files": matching_files,
                    "content_type": pres_repr_content_type,
                    # for reviewable checking in next step
                    "repre_preset_name": preset_repre_name,
                    "dir_path": abs_dir_path,
                    "tags": pres_repr_tags,
                    "custom_tags": pres_repr_custom_tags,
                }
                # Add optional output name suffix
                suffix = item["suffix"]
                if suffix and "thumb" not in suffix:
                    repre_data["outputName"] = suffix
                    repre_data["name"] += f"_{suffix}"
                grouped_representations[product_name][
                    "representations"].append(repre_data)

        # Second pass: create instances for each group
        for product_name, group_data in grouped_representations.items():
            representations = group_data["representations"]
            if not representations:
                continue

            # skip case where only thumbnail is present
            if (
                len(representations) == 1
                and representations[0]["content_type"] == "thumbnail"
            ):
                continue

            # get version from files with use of pattern
            # and versioning type
            version = None
            if pres_versioning == "from_file":
                version = self._extract_version_from_files(representations)
            elif pres_versioning == "locked":
                version = product_preset["locked"]

            # check if product is reviewable
            reviewable = False
            for rep_data in representations:
                for pres_rep in pres_representations:
                    if pres_rep["name"] == rep_data["repre_preset_name"]:
                        if "review" in pres_rep["tags"]:
                            reviewable = True
                            break
                if reviewable:
                    break

            # Get basic instance product data
            instance_data = deepcopy(base_instance_data)
            self._set_product_data_to_instance(
                instance_data,
                pres_product_type,
                product_name=product_name,
            )

            # Add review family and other data
            instance_data.update({
                "parent_instance_id": parenting_data["instance_id"],
                "creator_attributes": {
                    "parent_instance": parenting_data["instance_label"],
                },
                "version": version,
                "prep_representations": representations,
            })

            if pres_product_type not in ["model", "workfile", "camera"]:
                instance_data["creator_attributes"]["add_review_family"] = (
                    reviewable
                )

            creator_identifier = f"editorial_{pres_product_type}_advanced"
            editorial_clip_creator = self.create_context.creators[
                creator_identifier]

            # Create instance in creator context
            editorial_clip_creator.create(instance_data)

    def _extract_version_from_files(self, representations):
        """Extract version information from files

        Files are searched in in trimmed file repesentation data.

        Args:
            representations (list[dict]): list of representation data

        Returns:
            str: Highest version found in files, or None if no version found
        """
        all_found_versions = []
        for repre in representations:
            for file in repre["files"]:
                match = re.match(VERSION_IN_FILE_PATTERN, file)
                if match:
                    all_found_versions.append(int(match.group(1)))

        all_found_versions = set(all_found_versions)
        if all_found_versions:
            return max(all_found_versions)

        return None

    def _make_shot_product_instance(
        self,
        otio_clip,
        base_instance_data,
        parenting_data,
    ):
        """Making shot product instance from input preset

        Args:
            otio_clip (otio.Clip): otio clip object
            base_instance_data (dict): instance data
            parenting_data (dict): shot instance parent data

        Returns:
            CreatedInstance: creator instance object
        """
        instance_data = deepcopy(base_instance_data)
        label = self._set_product_data_to_instance(
            instance_data,
            "shot",
            product_name="shotMain",
        )
        instance_data["otioClip"] = otio.adapters.write_to_string(otio_clip)
        c_instance = self.create_context.creators["editorial_shot_advanced"].create(
            instance_data
        )
        parenting_data.update(
            {
                "instance_label": label,
                "instance_id": c_instance.data["instance_id"]
            }
        )
        return c_instance

    def _set_product_data_to_instance(
        self,
        instance_data,
        product_type,
        variant=None,
        product_name=None,
    ):
        """Product name maker

        Args:
            instance_data (dict): instance data
            product_type (str): product type
            variant (Optional[str]): product variant
                default is "main"
            product_name (Optional[str]): product name

        Returns:
            str: label string
        """
        if not variant:
            if product_name:
                variant = product_name.split(product_type)[-1].lower()
            else:
                variant = "main"

        folder_path = instance_data["creator_attributes"]["folderPath"]

        # product name
        product_name = product_name or f"{product_type}{variant.capitalize()}"
        label = f"{folder_path} {product_name}"

        instance_data.update(
            {
                "label": label,
                "variant": variant,
                "productType": product_type,
                "productName": product_name,
            }
        )

        return label

    def _get_base_instance_data(
        self,
        otio_clip,
        instance_data,
        track_start_frame,
        folder_entity,
    ):
        """Factoring basic set of instance data.

        Args:
            otio_clip (otio.Clip): otio clip object
            instance_data (dict): precreate instance data
            track_start_frame (int): track start frame

        Returns:
            dict: instance data

        """
        parent_folder_path = folder_entity["path"]
        parent_folder_name = parent_folder_path.rsplit("/", 1)[-1]

        # get clip instance properties
        handle_start = instance_data["handle_start"]
        handle_end = instance_data["handle_end"]
        timeline_offset = instance_data["timeline_offset"]
        workfile_start_frame = instance_data["workfile_start_frame"]
        fps = instance_data["fps"]
        variant_name = instance_data["variant"]

        # basic unique folder name
        clip_name = os.path.splitext(otio_clip.name)[0]
        project_entity = ayon_api.get_project(self.project_name)

        shot_name, shot_metadata = self._shot_metadata_solver.generate_data(
            clip_name,
            {
                "anatomy_data": {
                    "project": {
                        "name": self.project_name,
                        "code": project_entity["code"]
                    },
                    "parent": parent_folder_name,
                    "app": self.host_name
                },
                "selected_folder_entity": folder_entity,
                "project_entity": project_entity
            }
        )

        timing_data = self._get_timing_data(
            otio_clip,
            timeline_offset,
            track_start_frame,
            workfile_start_frame
        )

        # create creator attributes
        creator_attributes = {
            "workfile_start_frame": workfile_start_frame,
            "fps": fps,
            "handle_start": int(handle_start),
            "handle_end": int(handle_end)
        }
        # add timing data
        creator_attributes.update(timing_data)

        # create base instance data
        base_instance_data = {
            "shotName": shot_name,
            "variant": variant_name,
            "task": None,
            "newHierarchyIntegration": True,
            "trackStartFrame": track_start_frame,
            "timelineOffset": timeline_offset,

            # creator_attributes
            "creator_attributes": creator_attributes
        }
        # update base instance data with context data
        # and also update creator attributes with context data
        creator_attributes["folderPath"] = shot_metadata.pop("folderPath")
        base_instance_data["folderPath"] = parent_folder_path

        # add creator attributes to shared instance data
        base_instance_data["creator_attributes"] = creator_attributes
        # add hierarchy shot metadata
        base_instance_data.update(shot_metadata)

        return base_instance_data

    def _get_timing_data(
        self,
        otio_clip,
        timeline_offset,
        track_start_frame,
        workfile_start_frame
    ):
        """Returning available timing data

        Args:
            otio_clip (otio.Clip): otio clip object
            timeline_offset (int): offset value
            track_start_frame (int): starting frame input
            workfile_start_frame (int): start frame for shot's workfiles

        Returns:
            dict: timing metadata
        """
        # frame ranges data
        clip_in = otio_clip.range_in_parent().start_time.value
        clip_in += track_start_frame
        clip_out = otio_clip.range_in_parent().end_time_inclusive().value
        clip_out += track_start_frame

        # add offset in case there is any
        if timeline_offset:
            clip_in += timeline_offset
            clip_out += timeline_offset

        clip_duration = otio_clip.duration().value
        source_in = otio_clip.trimmed_range().start_time.value
        source_out = source_in + clip_duration

        # define starting frame for future shot
        frame_start = (
            clip_in if workfile_start_frame is None
            else workfile_start_frame
        )
        frame_end = frame_start + (clip_duration - 1)

        return {
            "frameStart": int(frame_start),
            "frameEnd": int(frame_end),
            "clipIn": int(clip_in),
            "clipOut": int(clip_out),
            "clipDuration": int(otio_clip.duration().value),
            "sourceIn": int(source_in),
            "sourceOut": int(source_out)
        }

    def _get_allowed_product_type_presets(self, pre_create_data):
        """Filter out allowed product type presets.

        Args:
            pre_create_data (dict): precreate attributes inputs

        Returns:
            list: Filtered list of extended preset items.
        """
        return [
            # return dict with name of preset and add preset dict
            {"product_name": product_name, **preset}
            for product_name, preset in self.get_product_presets_with_names().items()  # noqa
            if pre_create_data[product_name]
        ]

    def _validate_clip_for_processing(self, otio_clip):
        """Validate otio clip attributes

        Args:
            otio_clip (otio.Clip): otio clip object

        Returns:
            bool: True if all passing conditions
        """
        if otio_clip.name is None:
            return False

        if isinstance(otio_clip, otio.schema.Gap):
            return False

        # skip all generators like black empty
        if isinstance(
            otio_clip.media_reference,
                otio.schema.GeneratorReference):
            return False

        # Transitions are ignored, because Clips have the full frame
        # range.
        if isinstance(otio_clip, otio.schema.Transition):
            return False

        return True

    def get_pre_create_attr_defs(self):
        """Creating pre-create attributes at creator plugin.

        Returns:
            list: list of attribute object instances
        """
        # Use same attributes as for instance attrobites
        attr_defs = [
            FileDef(
                "sequence_filepath_data",
                folders=False,
                extensions=[".edl", ".xml", ".aaf", ".fcpxml"],
                allow_sequences=False,
                single_item=False,
                label="Edit Project Files",
            ),
            FileDef(
                "folder_path_data",
                folders=True,
                single_item=False,
                extensions=[],
                allow_sequences=False,
                label="Media Source Folder",
            ),
            # TODO: perhaps better would be timecode and fps input
            NumberDef("timeline_offset", default=0, label="Timeline offset"),
            UISeparatorDef("one"),
            UILabelDef("Clip instance attributes"),
            BoolDef(
                "ignore_clip_no_content",
                label="Ignore clips with no content",
                default=True
            ),
            UILabelDef("Products Search"),
            UISeparatorDef("two"),
        ]

        # transform all items in product type presets to join product
        # type and product variant together as single camel case string
        product_names = self.get_product_presets_with_names()

        # add variants swithers
        attr_defs.extend(
            BoolDef(
                name,
                label=name,
                default=preset["default_enabled"],
            )
            for name, preset in product_names.items()
        )
        attr_defs.append(UISeparatorDef("three"))

        attr_defs.extend(CREATOR_CLIP_ATTR_DEFS)
        return attr_defs

    def get_product_presets_with_names(self):
        """Get product type presets names.
        Returns:
            dict: dict with product names and preset items
        """
        output = {}
        for item in self.product_type_presets:
            product_name = (
                f"{item['product_type']}"
                f"{(item['variant']).capitalize()}"
            )
            output[product_name] = item
        return output


def find_string_differences(files: List[str]) -> Dict[str, str]:
    """
    Find common parts and differences between all strings in a list.
    Returns dictionary with original strings as keys and unique parts as values.
    The unique parts will:
    - not include file extensions
    - be stripped of whitespace
    - be stripped of dots and underscores from both ends
    - stripped of sequence numbers and padding
    """
    if not files:
        return {}

    # convert first all files to collections and reminders
    files_collected = []
    collections, reminders = clique.assemble(files)
    for collection in collections:
        head = collection.format("{head}")
        tail = collection.format("{tail}")
        files_collected.append(head + tail)
    for reminder in reminders:
        files_collected.append(reminder)

    # Remove extensions and convert to list for processing
    processed_files = [os.path.splitext(f)[0] for f in files_collected]

    # Find common prefix using zip_longest to compare all characters at once
    prefix = ""
    for chars in zip_longest(*processed_files):
        chars_s = set(chars)
        # Ignore shorter filenames
        chars_s.discard(None)
        # End if a character in all filenames is not the same
        if len(chars_s) != 1:
            break
        prefix += next(iter(chars_s))

    # Find common suffix by reversing strings
    reversed_files = [f[::-1] for f in processed_files]
    suffix = ""
    for chars in zip_longest(*reversed_files):
        if len(set(chars) - {None}) != 1:
            break
        suffix = chars[0] + suffix

    # Create result dictionary
    prefix_len = len(prefix)
    suffix_len = len(suffix)
    result = {}

    for original, processed in zip(files_collected, processed_files):
        # Extract the difference
        diff = (
            processed[prefix_len:-suffix_len] if suffix
            else processed[prefix_len:]
        )
        # Clean up the difference
        # remove version pattern from the diff
        version_pattern = re.compile(r".*(v\d{2,4}).*")
        if match := re.match(version_pattern, diff):
            # version string included v##
            version_str = match[1]
            diff = diff.replace(version_str, "")

        # Remove whitespace, dots and underscores
        diff = diff.strip().strip("._")

        result[original] = diff

    return result
