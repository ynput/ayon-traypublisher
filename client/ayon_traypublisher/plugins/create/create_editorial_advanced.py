import os
import re
import clique
from copy import deepcopy
from typing import Any, Dict
from pprint import pformat

import ayon_api
import opentimelineio as otio

from ayon_traypublisher.api.plugin import (
    TrayPublishCreator,
    HiddenTrayPublishCreator
)
from ayon_traypublisher.api.editorial import (
    ShotMetadataSolver
)
from ayon_core.pipeline import CreatedInstance
from ayon_core.lib import (
    get_ffprobe_data,
    convert_ffprobe_fps_value,

    FileDef,
    TextDef,
    NumberDef,
    EnumDef,
    BoolDef,
    UISeparatorDef,
    UILabelDef
)

CREATOR_CLIP_ATTR_DEFS = [
    EnumDef(
        "fps",
        items=[
            {"value": "from_selection", "label": "From selected context"},
            {"value": 23.997, "label": "23.976"},
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

COL_VARIANTS_PATTERN = "?[a-zA-Z0-9_]+"
REM_VARIANTS_PATTERN = "?[a-zA-Z0-9_.]+"
VERSION_IN_FILE_PATTERN = r".*v(\d{2,4}).*"

class EditorialClipInstanceCreatorBase(HiddenTrayPublishCreator):
    """Wrapper class for clip product type creators."""
    host_name = "traypublisher"

    def create(self, instance_data, source_data=None):
        product_name = instance_data["productName"]

        # Create new instance
        new_instance = CreatedInstance(
            self.product_type, product_name, instance_data, self
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
    identifier = "editorial_shot"
    product_type = "shot"
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
    identifier = "editorial_plate"
    product_type = "plate"
    label = "Plate product"


class EditorialImageInstanceCreator(EditorialClipInstanceCreatorBase):
    """Image product type class

    Plate representation instance.
    """
    identifier = "editorial_image"
    product_type = "image"
    label = "Image product"


class EditorialRenderInstanceCreator(EditorialClipInstanceCreatorBase):
    """Render product type class
    Render representation instance.
    """
    identifier = "editorial_render"
    product_type = "render"
    label = "Render product"


class EditorialAudioInstanceCreator(EditorialClipInstanceCreatorBase):
    """Audio product type class

    Audio representation instance.
    """
    identifier = "editorial_audio"
    product_type = "audio"
    label = "Audio product"


class EditorialModelInstanceCreator(EditorialClipInstanceCreatorBase):
    """Model product type class

    Model representation instance.
    """
    identifier = "editorial_model"
    product_type = "model"
    label = "Model product"


class EditorialCameraInstanceCreator(EditorialClipInstanceCreatorBase):
    """Camera product type class
    Camera representation instance.
    """
    identifier = "editorial_camera"
    product_type = "camera"
    label = "Camera product"


class EditorialWorkfileInstanceCreator(EditorialClipInstanceCreatorBase):
    """Plate product type class

    Plate representation instance.
    """
    identifier = "editorial_workfile"
    product_type = "workfile"
    label = "Workfile product"


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
        super(EditorialAdvancedCreator, self).__init__(*args, **kwargs)

    def apply_settings(self, project_settings):
        editorial_creators = deepcopy(
            project_settings["traypublisher"]["editorial_creators"]
        )
        creator_settings = editorial_creators.get(self.identifier)

        self.enabled = creator_settings.get("enabled", True)

        self._shot_metadata_solver.update_data(
            creator_settings["clip_name_tokenizer"],
            creator_settings["shot_rename"],
            creator_settings["shot_hierarchy"],
            creator_settings["shot_add_tasks"]
        )
        self.product_type_presets = creator_settings[
            "product_type_advanced_presets"]
        if default_variants := creator_settings.get("default_variants"):
            self.default_variants = default_variants

    def create(self, product_name, instance_data, pre_create_data):
        allowed_product_type_presets = self._get_allowed_product_type_presets(
            pre_create_data)
        self.log.warning(
            f"allowed_product_type_presets: {pformat(allowed_product_type_presets)}")

        clip_instance_properties = {
            k: v
            for k, v in pre_create_data.items()
            if k != "sequence_filepath_data"
            if k != "folder_path_data"
            if k not in self.get_product_presets_with_names()
        }
        self.log.warning(
            f"clip_instance_properties: {pformat(clip_instance_properties)}"
        )

        folder_path = instance_data["folderPath"]
        folder_entity = ayon_api.get_folder_by_path(
            self.project_name, folder_path
        )

        if pre_create_data["fps"] == "from_selection":
            # get 'fps' from folder attributes
            fps = folder_entity["attrib"]["fps"]
        else:
            fps = float(pre_create_data["fps"])

        instance_data.update({
            "fps": fps
        })

        # get path of sequence
        sequence_path_data = pre_create_data["sequence_filepath_data"]
        sequence_paths = self._get_path_from_file_data(
            sequence_path_data, multi=True)

        folder_path_data = pre_create_data["folder_path_data"]
        media_folder_paths = self._get_path_from_file_data(
            folder_path_data, multi=True)

        self.log.warning(media_folder_paths)

        # get all sequences into otio_timelines
        otio_timelines = []
        for sequence_path in sequence_paths:
            # get otio timeline
            otio_timeline = self._create_otio_timeline(sequence_path, fps)
            otio_timelines.append(otio_timeline)

        # Create all clip instances
        clip_instance_properties.update({
            "fps": fps,
            "variant": instance_data["variant"]
        })

        ignore_clip_no_content = pre_create_data["ignore_clip_no_content"]
        for media_folder_path in media_folder_paths:

            for otio_timeline in otio_timelines:

                # create clip instances
                self._get_clip_instances(
                    folder_entity,
                    otio_timeline,
                    media_folder_path,
                    clip_instance_properties,
                    allowed_product_type_presets,
                    os.path.basename(sequence_path),
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
            self.product_type, product_name, instance_data, self
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
        if extension == ".edl":
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
            str: path string
        """
        return_path_list = []

        if isinstance(file_path_data, list):
            return_path_list = [
                os.path.join(f["directory"], f["filenames"][0])
                for f in file_path_data
            ]

        if not return_path_list:
            raise FileExistsError(
                f"File path was not added: {file_path_data}")

        return return_path_list if multi else return_path_list[0]

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
        clip_names = [clip.name for clip in otio_timeline.find_clips()]

        # Create set of clip names for O(1) lookup
        clip_names_set = set(clip_names)
        self.log.warning(f"Clip names: {clip_names}")

        clip_folders = []
        # Iterate over all media files in media folder
        for root, folders, _ in os.walk(media_folder_path):
            # Use set intersection to find matching folder directly
            clip_folders.extend(
                folder.replace("\\", "/")
                for folder in folders
                if folder in clip_names_set
            )

        self.log.warning(f"Clip folders: {clip_folders}")

        if not clip_folders:
            self.log.warning("No clip folder paths found")
            return

        clip_content: Dict[str, Dict[str, list[str]]] = {}
        # list content of clip folder and search for product items
        for clip_folder in clip_folders:
            abs_clip_folder = os.path.join(
                media_folder_path, clip_folder).replace("\\", "/")

            matched_product_items = []
            for root, folders, files in os.walk(abs_clip_folder):
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

                    for folder in folders:
                        product_data = deepcopy(product_data_base)
                        # need to include more since variants might occure
                        pattern_search = re.compile(
                            f".*({re.escape(product_name)}{COL_VARIANTS_PATTERN}).*"
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
                        files,
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

                clip_content[clip_folder.replace(media_folder_path, "")] = (
                    matched_product_items
                )

        self.log.warning("Clip content:")
        self.log.warning(pformat(clip_content))

        # TODO: perhaps remove if no need for media source
        # media data for audio stream and reference solving
        # media_data = self._get_media_source_metadata(media_path)

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

                # TODO: perhaps remove if no need for media source
                # # get available frames info to clip data
                # self._create_otio_reference(
                #   otio_clip, media_path, media_data)

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

                for pres_product_data in product_type_presets:
                    self._make_product_instance(
                        pres_product_data,
                        deepcopy(base_instance_data),
                        parenting_data,
                        clip_related_content,
                    )

    def _include_files_for_processing(
        self,
        product_name,
        files,
        product_data_base,
        collecting_items,
        strict=True,
    ):
        """Supporting function for getting clip content.

        Args:
            product_name (str): product name
            partial_path (str): clip folder path
            files (list): list of files in clip folder to collect
            product_data_base (dict): product data
            collecting_items (list): list for collecting product data items
            strict (Optional[bool]): strict mode for filtering files
        """
        # compile regex pattern for matching product name
        col_pattern_search = re.compile(
            f".*({re.escape(product_name)}{COL_VARIANTS_PATTERN}).*")
        rem_pattern_search = re.compile(
            f".*({re.escape(product_name)}{REM_VARIANTS_PATTERN}).*")

        collections, reminders = clique.assemble(files)
        if not collections:
            # No sequences detected and we can't retrieve
            # frame range
            self.log.debug(
                "No sequences detected in the representation data."
                " Skipping collecting frame range data."
            )
            return

        # iterate all collections and search for pattern in file name head
        for collection in collections:
            # check if collection is not empty
            if not collection:
                continue
            # check if pattern in name head is present
            head = collection.format("{head}")
            tail = collection.format("{tail}")
            match = col_pattern_search.search(head)

            # if pattern is not present in file name head
            if strict and not match:
                continue

            # add collected files to list
            files_ = [
                file
                for file in files
                if file.startswith(head)
                if file.endswith(tail)
                if "thumb" not in file
            ]

            product_data = deepcopy(product_data_base)
            product_data["files"] = files_
            product_data["type"] = "collection"

            if strict and match:
                product_data["product_name"] = match.group(0)

            collecting_items.append(product_data)

        for reminder in reminders:
            # check if pattern in name head is present
            head, tail = os.path.splitext(reminder)
            match = rem_pattern_search.search(head)

            # if pattern is not present in file name head
            if strict and not match:
                continue

            # add collected files to list
            files_ = [
                file for file in files
                if file.startswith(head)
                if file.endswith(tail)
            ]

            product_data = deepcopy(product_data_base)
            product_data["files"] = files_
            product_data["type"] = "single"

            if strict and match:
                # we do not need to include dot pattern match
                # this is just for name.thumbnail.jpg match
                matched_pattern = match.group(0)
                if "." in matched_pattern:
                    match = col_pattern_search.search(head)
                    if match:
                        matched_pattern = match.group(0)

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

    def _create_otio_reference(
        self,
        otio_clip,
        media_path,
        media_data
    ):
        """Creating otio reference at otio clip.

        Args:
            otio_clip (otio.Clip): otio clip object
            media_path (str): media file path string
            media_data (dict): media metadata
        """
        start_frame = media_data["start_frame"]
        frame_duration = media_data["duration"]
        fps = media_data["fps"]

        available_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                start_frame, fps),
            duration=otio.opentime.RationalTime(
                frame_duration, fps)
        )
        # in case old OTIO or video file create `ExternalReference`
        media_reference = otio.schema.ExternalReference(
            target_url=media_path,
            available_range=available_range
        )
        otio_clip.media_reference = media_reference

    def _get_media_source_metadata(self, path):
        """Get all available metadata from file

        Args:
            path (str): media file path string

        Raises:
            AssertionError: ffprobe couldn't read metadata

        Returns:
            dict: media file metadata
        """
        return_data = {}

        try:
            media_data = get_ffprobe_data(
                path, self.log
            )

            # get video stream data
            video_streams = []
            audio_streams = []
            for stream in media_data["streams"]:
                codec_type = stream.get("codec_type")
                if codec_type == "audio":
                    audio_streams.append(stream)

                elif codec_type == "video":
                    video_streams.append(stream)

            if not video_streams:
                raise ValueError(
                    "Could not find video stream in source file."
                )

            video_stream = video_streams[0]
            return_data = {
                "video": True,
                "start_frame": 0,
                "duration": int(video_stream["nb_frames"]),
                "fps": float(
                    convert_ffprobe_fps_value(
                        video_stream["r_frame_rate"]
                    )
                )
            }

            # get audio  streams data
            if audio_streams:
                return_data["audio"] = True

        except Exception as exc:
            raise AssertionError((
                "FFprobe couldn't read information about input file: "
                f"\"{path}\". Error message: {exc}"
            ))

        return return_data

    def _make_product_instance(
        self,
        product_preset,
        base_instance_data,
        parenting_data,
        clip_content_items,
    ):
        pres_product_type = product_preset["product_type"]
        pres_product_name = product_preset["product_name"]
        pres_versioning = product_preset["versioning_type"]
        pres_representations = product_preset["representations"]

        # get version from files with use of pattern
        # and versioning type
        version = None
        if pres_versioning == "from_file":
            version = self._extract_version_from_files(clip_content_items)
        elif pres_versioning == "locked":
            version = product_preset["locked"]

        # Dictionary to group files by product name
        grouped_representations = {}

        # First pass: group matching files by product name and representation
        for item in clip_content_items:
            if pres_product_name not in item["preset_name"]:
                continue

            product_name = item["product_name"]
            if product_name not in grouped_representations:
                grouped_representations[product_name] = {
                    "representations": []
                }

            # Check each representation preset against the item
            for repre_preset in pres_representations:
                preset_repre_name = repre_preset["name"]
                # TODO: use the content type for filtering items
                #   currently it is matching thumbnail to sequence and thumbnail..
                repre_content_type = repre_preset["content_type"]

                # Prepare filters
                extensions_filter = [
                    ext if ext.startswith(".") else f".{ext}"
                    for ext in repre_preset.get("extensions", [])
                ]
                patterns_filter = repre_preset.get("patterns", [])

                # Filter matching files
                matching_files = []
                for file in item["files"]:
                    # Filter by extension
                    matches_ext = any(
                        str(file).lower().endswith(ext.lower())
                        for ext in extensions_filter
                    )
                    # Filter by pattern
                    matches_pattern = any(
                        re.match(pattern, file)
                        for pattern in patterns_filter
                    )

                    if matches_ext and matches_pattern:
                        matching_files.append(file)

                if matching_files:
                    grouped_representations[product_name]["representations"].append({
                        "name": preset_repre_name,
                        "files": matching_files,
                        "content_type": repre_content_type,
                        # for reviewable checking in next step
                        "repre_preset_name": preset_repre_name,
                    })

        # Second pass: create instances for each group
        for product_name, group_data in grouped_representations.items():
            if not group_data["representations"]:
                continue

            # check if product is reviewable
            reviewable = any(
                "review" in pres_rep["tags"]
                for rep_data in group_data["representations"]
                for pres_rep in pres_representations
                if pres_rep["name"] == rep_data["repre_preset_name"]
            )

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
                    "add_review_family": reviewable,
                },
                "version": version,
                "representations": group_data["representations"]
            })

            creator_identifier = f"editorial_{pres_product_type}"
            editorial_clip_creator = self.create_context.creators[
                creator_identifier]

            # Create instance in creator context
            editorial_clip_creator.create(instance_data)

            self.log.warning(f"Created instance: {pformat(instance_data)}")

    def _extract_version_from_files(self, clip_content_items):
        """Extract version information from files

        Files are searched in in clip content items input data.

        Args:
            clip_content_items (list[dict]): list of clip content data

        Returns:
            str: Highest version found in files, or None if no version found
        """
        all_found_versions = []
        for item in clip_content_items:
            for file in item["files"]:
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
        c_instance = self.create_context.creators["editorial_shot"].create(
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
            # Backwards compatible (Deprecated since 24/06/06)
            "newAssetPublishing": True,
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
            list: lit of dict with preset items
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
                label="Sequence file",
            ),
            FileDef(
                "folder_path_data",
                folders=True,
                single_item=False,
                extensions=[],
                allow_sequences=False,
                label="Folder path",
            ),
            # TODO: perhaps better would be timecode and fps input
            NumberDef("timeline_offset", default=0, label="Timeline offset"),
            UISeparatorDef(),
            UILabelDef("Clip instance attributes"),
            BoolDef(
                "ignore_clip_no_content",
                label="Ignore clips with no content",
                default=True
            ),
            UILabelDef("Products Search"),
            UISeparatorDef(),
        ]

        # transform all items in product type presets to join product
        # type and product variant together as single camel case string
        product_names = self.get_product_presets_with_names()

        # add variants swithers
        attr_defs.extend(BoolDef(item, label=item) for item in product_names)
        attr_defs.append(UISeparatorDef())

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
