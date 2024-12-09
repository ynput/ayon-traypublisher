import os
import re
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
        for seq_path in sequence_paths:
            # get otio timeline
            otio_timeline = self._create_otio_timeline(
                seq_path, fps)
            otio_timelines.append(otio_timeline)

        # Create all clip instances
        clip_instance_properties.update({
            "fps": fps,
            "variant": instance_data["variant"]
        })

        for media_folder_path in media_folder_paths:

            for otio_timeline in otio_timelines:

                # create clip instances
                self._get_clip_instances(
                    folder_entity,
                    otio_timeline,
                    media_folder_path,
                    clip_instance_properties,
                    allowed_product_type_presets,
                    os.path.basename(seq_path),
                )

                # create otio editorial instance
                self._create_otio_instance(
                    product_name,
                    instance_data,
                    seq_path,
                    media_folder_path,
                    otio_timeline
                )

    def _create_otio_instance(
        self,
        product_name,
        data,
        sequence_path,
        otio_timeline
    ):
        """Otio instance creating function

        Args:
            product_name (str): Product name.
            data (dict): instance data
            sequence_path (str): path to sequence file
            otio_timeline (otio.Timeline): otio timeline object
        """
        # Pass precreate data to creator attributes
        data.update({
            "sequenceFilePath": sequence_path,
            "otioTimeline": otio.adapters.write_to_string(otio_timeline)
        })
        new_instance = CreatedInstance(
            self.product_type, product_name, data, self
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
        for root, folders, _files in os.walk(media_folder_path):
            # NOTE: _files should not be needed at this point

            # Use set intersection to find matching folder directly
            matching_clip_dir = next(
                (folder for folder in folders if folder in clip_names_set),
                None
            )

            if not matching_clip_dir:
                continue

            clip_folders.append(matching_clip_dir.replace("\\", "/"))

        self.log.warning(f"Clip folders: {clip_folders}")

        if not clip_folders:
            self.log.warning("No clip folder paths found")
            return

        clip_content: Dict[str, Dict[str, list[str]]] = {}
        # list content of clip folder and search for product items
        for clip_folder in clip_folders:
            abs_clip_folder = os.path.join(
                media_folder_path, clip_folder).replace("\\", "/")
            clip_folder_data = clip_content[
                clip_folder.replace(media_folder_path, "")] = {}

            matched_product_data = {}
            for root, folders, files in os.walk(abs_clip_folder):
                # iterate all product names in enabled presets
                for product_data in product_type_presets:
                    product_name = product_data.get("name")
                    if not product_name:
                        continue

                    product_data = matched_product_data.setdefault(
                        product_name, {}
                    )
                    root = root.replace("\\", "/")
                    cl_part_path = root.replace(abs_clip_folder, "")

                    if cl_part_path == "":
                        cl_part_path = "/"

                    # Use set intersection to find matching folder directly
                    if matching_prod_fldr := [
                        folder
                        for folder in folders
                        if re.search(re.escape(product_name), folder)
                    ]:
                        for folder in matching_prod_fldr:
                            partial_path = os.path.join(
                                cl_part_path, folder
                            ).replace("\\", "/")
                            nested_files = list(
                                os.listdir(os.path.join(root, folder)))
                            self._include_files_for_processing(
                                product_name,
                                partial_path,
                                nested_files,
                                product_data,
                                strict=False,
                            )

                    self._include_files_for_processing(
                        product_name,
                        cl_part_path,
                        files,
                        product_data,
                    )

                # No matching product data can be skipped
                if not matched_product_data:
                    continue

                clip_folder_data.update(matched_product_data)

        self.log.warning("Clip content:")
        self.log.warning(pformat(clip_content))

        media_path = source_folder_path
        # media data for audio stream and reference solving
        media_data = self._get_media_source_metadata(media_path)

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

                # get available frames info to clip data
                self._create_otio_reference(otio_clip, media_path, media_data)

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

                for product_type_preset in product_type_presets:
                    # exclude audio product type if no audio stream
                    if (
                        product_type_preset["product_type"] == "audio"
                        and not media_data.get("audio")
                    ):
                        continue

                    self._make_product_instance(
                        otio_clip,
                        product_type_preset,
                        deepcopy(base_instance_data),
                        parenting_data
                    )

    def _include_files_for_processing(
        self, product_name, partial_path, files, product_data, strict=True
    ):
        self.log.warning(f">> files: {files}")

        if strict:
            files = [
                file for file in files
                if re.search(re.escape(product_name), file)
            ]
        if files:
            cl_prod_folder_list = product_data.setdefault(partial_path, [])
            cl_prod_folder_list += files

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
        otio_clip,
        product_type_preset,
        instance_data,
        parenting_data
    ):
        """Making product instance from input preset

        Args:
            otio_clip (otio.Clip): otio clip object
            product_type_preset (dict): single product type preset
            instance_data (dict): instance data
            parenting_data (dict): shot instance parent data

        Returns:
            CreatedInstance: creator instance object
        """
        product_type = product_type_preset["product_type"]
        label = self._make_product_naming(
            product_type_preset,
            instance_data
        )
        instance_data["label"] = label

        # add file extension filter only if it is not shot product type
        if product_type == "shot":
            instance_data["otioClip"] = (
                otio.adapters.write_to_string(otio_clip))
            c_instance = self.create_context.creators[
                "editorial_shot"].create(
                    instance_data)
            parenting_data.update({
                "instance_label": label,
                "instance_id": c_instance.data["instance_id"]
            })
        else:
            # add review family if defined
            instance_data.update({
                "outputFileType": product_type_preset["output_file_type"],
                "parent_instance_id": parenting_data["instance_id"],
                "creator_attributes": {
                    "parent_instance": parenting_data["instance_label"],
                    "add_review_family": product_type_preset.get("review")
                }
            })

            creator_identifier = f"editorial_{product_type}"
            editorial_clip_creator = self.create_context.creators[
                creator_identifier]
            c_instance = editorial_clip_creator.create(
                instance_data)

        return c_instance

    def _make_product_naming(self, product_type_preset, instance_data):
        """Product name maker

        Args:
            product_type_preset (dict): single preset item
            instance_data (dict): instance data

        Returns:
            str: label string
        """
        folder_path = instance_data["creator_attributes"]["folderPath"]

        variant_name = instance_data["variant"]
        product_type = product_type_preset["product_type"]

        # get variant name from preset or from inheritance
        _variant_name = product_type_preset.get("variant") or variant_name

        # product name
        product_name = "{}{}".format(
            product_type, _variant_name.capitalize()
        )
        label = "{} {}".format(
            folder_path,
            product_name
        )

        instance_data.update({
            "label": label,
            "variant": _variant_name,
            "productType": product_type,
            "productName": product_name,
        })

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
            {"product_type": "shot"},
            *[
                # return dict with name of preset and add preset dict
                {
                    "name": product_name,
                    **preset
                }

                for product_name, preset in self.get_product_presets_with_names().items()
                if pre_create_data[product_name]
            ],
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
