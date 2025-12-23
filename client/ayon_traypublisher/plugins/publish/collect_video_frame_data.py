from __future__ import annotations
import os
import logging
from typing import Union

from ayon_core.pipeline import OptionalPyblishPluginMixin
from ayon_core.lib.transcoding import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    get_oiio_info_for_input,
)
from ayon_core.lib import (
    get_ffprobe_data,
    is_oiio_supported,
)

import pyblish.api
import attr


# This is a direct copy from `ayon_core.plugins.loader.export_otio`
# TODO: turn this into a core library function and import from there instead
#  even though here `oiiotool` is technically redundant because we're only
#  processing videos
def get_image_info_metadata(
    path_to_file,
    keys=None,
    logger=None,
):
    """Get flattened metadata from image file

    With combined approach via FFMPEG and OIIOTool.

    At first it will try to detect if the image input is supported by
    OpenImageIO. If it is then it gets the metadata from the image using
    OpenImageIO. If it is not supported by OpenImageIO then it will try to
    get the metadata using FFprobe.

    Args:
        path_to_file (str): Path to image file.
        keys (Iterable[str] | None): List of keys that should be returned. If
            None then all keys are returned. Keys are expected all lowercase.
            Additional keys are:
            - "framerate" - will be created from "r_frame_rate" or
                "framespersecond" and evaluated to float value.
        logger (logging.Logger): Logger used for logging.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

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
        metadata_stream = _ffprobe_metadata_conversion(video_stream)
        return metadata_stream

    metadata_stream = None
    ext = os.path.splitext(path_to_file)[-1].lower()
    if ext not in IMAGE_EXTENSIONS:
        logger.info(
            (
                'File extension "{}" is not supported by OpenImageIO.'
                " Trying to get metadata using FFprobe."
            ).format(ext)
        )
        ffprobe_stream = get_ffprobe_data(path_to_file, logger)
        if "streams" in ffprobe_stream and len(ffprobe_stream["streams"]) > 0:
            metadata_stream = _get_video_metadata_from_ffprobe(ffprobe_stream)

    if not metadata_stream and is_oiio_supported():
        oiio_stream = get_oiio_info_for_input(path_to_file, logger=logger)
        if "attribs" in (oiio_stream or {}):
            metadata_stream = {}
            for key, val in oiio_stream["attribs"].items():
                if "smpte:" in key.lower():
                    key = key.replace("smpte:", "")
                metadata_stream[key.lower()] = val
            for key, val in oiio_stream.items():
                if key == "attribs":
                    continue
                metadata_stream[key] = val
    else:
        logger.info(
            (
                "OpenImageIO is not supported on this system."
                " Trying to get metadata using FFprobe."
            )
        )
        ffprobe_stream = get_ffprobe_data(path_to_file, logger)
        if "streams" in ffprobe_stream and len(ffprobe_stream["streams"]) > 0:
            metadata_stream = _get_video_metadata_from_ffprobe(ffprobe_stream)

    if not metadata_stream:
        logger.warning("Failed to get metadata from image file.")
        return {}

    if keys is None:
        return metadata_stream

    # create framerate key from available ffmpeg:r_frame_rate
    # or oiiotool:framespersecond and evaluate its string expression
    # value into float value
    if (
        "r_frame_rate" in metadata_stream
        or "framespersecond" in metadata_stream
    ):
        rate_info = metadata_stream.get("r_frame_rate")
        if rate_info is None:
            rate_info = metadata_stream.get("framespersecond")

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

    # aggregate all required metadata from prepared metadata stream
    output = {}
    for key in keys:
        for k, v in metadata_stream.items():
            if key == k:
                output[key] = v
                break
            if isinstance(v, dict) and key in v:
                output[key] = v[key]
                break

    return output


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


@attr.define
class VideoData:
    frame_start: int
    frame_end: int
    fps: float


class CollectVideoData(
    pyblish.api.InstancePlugin,
    OptionalPyblishPluginMixin
):
    """Collect Original Video Frame Data

    If the representation includes video files then set `frameStart` and
    `frameEnd` for the instance to the start and end frame respectively from
    the video's timecode.
    """

    order = pyblish.api.CollectorOrder + 0.4905
    label = "Collect Original Video Frame Data"
    families = ["*"]
    hosts = ["traypublisher"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        frame_data = self.get_frame_data_from_repre_sequence(instance)
        if not frame_data:
            return

        for key, value in frame_data.items():
            instance.data[key] = value
            self.log.debug(f"Collected video data '{key}': {value} ")

    def get_frame_data_from_repre_sequence(self, instance):
        repres = instance.data.get("representations")
        if not repres:
            return {}

        first_repre = repres[0]
        if "ext" not in first_repre:
            self.log.warning(
                "Cannot find file extension in representation data"
            )
            return {}

        extension: str = first_repre["ext"]
        if f".{extension}" not in VIDEO_EXTENSIONS:
            self.log.debug(
                f"Representation extension '{extension}' is not a video"
                " extension. Skipping collecting of video data.")
            return {}

        video_filename = first_repre["files"]
        if isinstance(video_filename, list):
            if len(video_filename) > 1:
                self.log.debug(
                    "More than one video file found."
                    " Skipping collecting of video data."
                )
                return {}
            video_filename: str = video_filename[0]
        video_filepath = os.path.join(first_repre["stagingDir"],
                                      video_filename)
        video_data = self.get_video_data(video_filepath)
        return {
            "frameStart": video_data.frame_start,
            "frameEnd": video_data.frame_end,
            "handleStart": 0,
            "handleEnd": 0,
            "fps": video_data.fps
        }

    def get_video_data(self, video_filepath: str) -> VideoData:
        info = get_image_info_metadata(
            video_filepath,
            keys={"nb_frames", "timecode", "framerate"}
        )
        num_frames: int = int(info.get("nb_frames", 0))
        # TODO: Should this fall back to folder/task entity fps instead?
        fps: float = info.get("framerate", 25.0)
        timecode: Union[str, None] = info.get("timecode")

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