from __future__ import annotations
import os
import dataclasses
from typing import Union

from ayon_core.lib.transcoding import VIDEO_EXTENSIONS
from ayon_core.lib import get_ffprobe_data, BoolDef

from ayon_core.pipeline.publish import AYONPyblishPluginMixin
from ayon_core.pipeline.context_tools import (
    get_current_task_entity,
    get_current_folder_entity
)

import pyblish.api

# Remove dot from extensions
_VIDEO_EXTENSIONS = {
    ext.lstrip(".")
    for ext in VIDEO_EXTENSIONS
}

def get_video_info_metadata(
    path_to_file,
    logger,
):
    """Get flattened metadata from video file using ffprobe.

    Args:
        path_to_file (str): Path to image file.
        logger (logging.Logger): Logger used for logging.
    """

    def _ffprobe_metadata_conversion(metadata):
        """Convert ffprobe metadata unified format."""
        output = {}
        for key, val in metadata.items():
            if key in ("tags", "disposition"):
                output.update(val)
            else:
                output[key] = val
        return output

    def _get_video_metadata_from_ffprobe(ffprobe_stream):
        """Extract video metadata from ffprobe stream.

        Args:
            ffprobe_stream (dict): Stream data obtained from ffprobe.

        Returns:
            dict: Video metadata extracted from the ffprobe stream.
        """
        video_stream = None
        for stream in ffprobe_stream["streams"]:
            if stream["codec_type"] == "video":
                video_stream = stream
                break
        return _ffprobe_metadata_conversion(video_stream)

    ffprobe_stream = get_ffprobe_data(path_to_file, logger)
    if not ffprobe_stream.get("streams"):
        logger.warning("Failed to get metadata from video file.")
        return {}

    metadata_stream = _get_video_metadata_from_ffprobe(ffprobe_stream)

    # create framerate key from available ffmpeg:r_frame_rate
    # evaluate its string expression value into float value
    if (
        "r_frame_rate" in metadata_stream
    ):
        rate_info = metadata_stream.get("r_frame_rate")
        # calculate framerate from string expression
        if "/" in str(rate_info):
            time, frame = str(rate_info).split("/")
            rate_info = float(time) / float(frame)

        try:
            metadata_stream["framerate"] = float(str(rate_info))
        except Exception as e:
            logger.warning(
                "Failed to evaluate '{}' value to framerate. Error: {}".format(
                    rate_info, e
                )
            )

    return metadata_stream


def timecode_to_frame(timecode: str, fps: float) -> int:
    """Convert a timecode with fps to a frame number.

    Args:
        timecode (str): The timecode HH:MM:SS:FF format to be converted,
            like "00:01:00:00".
        fps (float): The frames per second to convert to frames with.

    Returns:
         int: The frame number.
    """
    hours, minutes, seconds, frames = (int(t) for t in timecode.split(":"))
    frames += seconds * fps
    frames += minutes * 60 * fps
    frames += hours * 3600 * fps
    return int(frames)


@dataclasses.dataclass
class VideoData:
    frame_start: int
    frame_end: int
    fps: float


class CollectTraypublisherVideoFrameData(
    pyblish.api.ContextPlugin, AYONPyblishPluginMixin
):
    """Collect video families."""

    label = "Collect Video Families"
    order = pyblish.api.CollectorOrder - 0.25
    hosts = ["traypublisher"]
    optional = True

    @classmethod
    def get_attr_defs_for_instance(
        cls, create_context: "CreateContext", instance: "CreatedInstance"  # noqa: F821
    ):
        if not cls.instance_supported(create_context, instance):
            return []
        return [
            BoolDef(
                "collect_video_framerange",
                label="Collect Original Video Frame Data",
                default=True,
                visible=cls.optional,
            )
        ]

    @classmethod
    def instance_supported(
        cls, create_context: "CreateContext", instance: "CreatedInstance"  # noqa: F821
    ):
        # Show only for instances from settings based create plugins
        if instance.creator_identifier in {
            "io.ayon.creators.traypublisher.online",
            "render_movie_batch",
            "editorial_plate",
        }:
            return True

        if not instance.data.get("settings_creator"):
            return False

        # Get extensions from settings creator
        plugin = create_context.creators[instance.creator_identifier]
        extensions = {
            ext.lower().lstrip(".")
            for ext in plugin.extensions
        }
        return bool(extensions & _VIDEO_EXTENSIONS)

    def process(self, context):
        for instance in context:
            data = self.get_attr_values_from_data(instance.data)
            if data.get("collect_video_framerange"):
                # add the collector to collect video frame data
                instance.data["families"].append("collect.video.framerange")


class CollectVideoData(pyblish.api.InstancePlugin):
    """Collect Original Video Frame Data

    If the representation includes video files then set `frameStart` and
    `frameEnd` for the instance to the start and end frame respectively from
    the video's timecode.
    """

    order = pyblish.api.CollectorOrder + 0.4905
    label = "Collect Original Video Frame Data"
    families = ["collect.video.framerange"]

    def process(self, instance):
        frame_data = self.get_frame_data_from_representations(instance)
        if not frame_data:
            return

        for key, value in frame_data.items():
            if key not in instance.data:
                instance.data[key] = value
                self.log.debug(f"Collected video data '{key}': {value}")

    def get_frame_data_from_representations(self, instance: pyblish.api.Instance) -> dict:
        """Get frame data from a representation sequence.

        Args:
            instance (pyblish.api.Instance): The instance to extract frame data from.

        Returns:
            dict: A dictionary containing the frame data.
        """
        repres = instance.data.get("representations")
        if not repres:
            return {}

        # Iterate through all representations to find a valid video
        for repre in repres:
            if "name" not in repre:
                self.log.debug(
                    "Cannot find file extension in representation data"
                )
                continue

            extension: str = repre["ext"]
            if extension not in _VIDEO_EXTENSIONS:
                self.log.debug(
                    f"Representation extension '{extension}' is not a video"
                    " extension. Skipping this representation.")
                continue

            video_filename = repre["files"]
            if isinstance(video_filename, list):
                if len(video_filename) > 1:
                    self.log.debug(
                        "More than one video file found in representation."
                        " Skipping this representation."
                    )
                    continue
                video_filename: str = video_filename[0]
            video_filepath = os.path.join(repre["stagingDir"],
                                          video_filename)
            if not os.path.isfile(video_filepath):
                self.log.debug(
                    f"Video file '{video_filepath}' does not exist."
                    " Skipping this representation."
                )
                continue

            video_data = self.get_video_data(video_filepath)
            if video_data is None:
                continue

            return {
                "frameStart": video_data.frame_start,
                "frameEnd": video_data.frame_end,
                "handleStart": 0,
                "handleEnd": 0,
                "fps": video_data.fps
            }

        # No valid video representation found
        return {}

    def get_video_data(self, video_filepath: str) -> VideoData | None:
        """Get video data from a video file.

        Args:
            video_filepath (str): video filepath to extract data from

        Returns:
            VideoData | None: Video data extracted from the video file.
                If critical video data (fps) is not found, returns None.
        """
        info = get_video_info_metadata(video_filepath, self.log)
        num_frames: int = int(info.get("nb_frames", 0))
        fps: float = info.get("framerate")
        timecode: Union[str, None] = info.get("timecode")

        # Skip if fps is not available - it's essential for frame calculations
        if fps is None:
            self.log.warning(
                f"Could not extract framerate from '{video_filepath}'."
                " Skipping collecting of video data."
            )
            return None

        # TODO: Should this align with the folder/task entity frame start
        #  by default instead?
        start_frame: int = 0
        if timecode:
            # Parse timecode and use it as start frame
            start_frame = timecode_to_frame(timecode, fps)

        return VideoData(
            frame_start=start_frame,
            frame_end=start_frame+num_frames+1,
            fps=fps,
            # TODO: Also capture resolution?
            #width=info["width"],
            #height=info["height"],
        )
