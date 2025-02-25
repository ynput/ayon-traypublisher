import os
from pprint import pformat
import pyblish.api
from ayon_core.pipeline import publish
from ayon_core.pipeline import colorspace

LUT_KEY_PREFIX = "abs_lut_path"


class CollectColorspaceLook(pyblish.api.InstancePlugin,
                            publish.AYONPyblishPluginMixin):
    """Collect OCIO colorspace look from LUT file
    """

    label = "Collect Colorspace Look"
    order = pyblish.api.CollectorOrder
    hosts = ["traypublisher"]
    families = ["ociolook"]

    def process(self, instance):
        creator_attrs = instance.data["creator_attributes"]

        # Get config items
        config_items = instance.data["transientData"]["config_items"]
        config_data = instance.data["transientData"]["config_data"]

        # Get global working colorspace
        if creator_attrs["working_colorspace"]:
            color_data = colorspace.convert_colorspace_enumerator_item(
                creator_attrs["working_colorspace"],
                config_items
            )
            working_colorspace = color_data
            config_data["colorspace"] = working_colorspace["name"]
        else:
            working_colorspace = None

        # Collect all LUT files
        all_files_url = {
            key: value
            for key, value in creator_attrs.items()
            if key.startswith(LUT_KEY_PREFIX)
        }

        # Create a representation per file.
        representations = []
        ocio_look_items = []

        for key, file_url in all_files_url.items():

            file_idx = key.replace(
                LUT_KEY_PREFIX,
                ""
            )
            file_name = os.path.basename(file_url)
            base_name, ext = os.path.splitext(file_name)

            # set output name with base_name which was cleared
            # of all symbols and all parts were capitalized
            output_name = (base_name.replace("_", " ")
                                    .replace(".", " ")
                                    .replace("-", " ")
                                    .title()
                                    .replace(" ", ""))

            # Get LUT colorspace items
            converted_color_data = {}
            for colorspace_key in (
                f"input_colorspace{file_idx}",
                f"output_colorspace{file_idx}"
            ):
                if creator_attrs[colorspace_key]:
                    color_data = colorspace.convert_colorspace_enumerator_item(
                        creator_attrs[colorspace_key], config_items)
                    converted_color_data[colorspace_key] = color_data
                else:
                    converted_color_data[colorspace_key] = None

            # create lut representation data
            lut_repre_name = f"LUTfile{file_idx}"
            lut_repre = {
                "name": lut_repre_name,
                "output": output_name,

                # When integrating multiple LUT files
                # with a common extension, there will
                # be a duplication clash when integrating.
                # Enforce the outputName to prevent this.
                "outputName": lut_repre_name,
                "ext": ext.lstrip("."),
                "files": file_name,
                "stagingDir": os.path.dirname(file_url),
                "tags": []
            }
            representations.append(lut_repre)
            ocio_look_items.append(
                {
                    "name": lut_repre_name,
                    "ext": ext.lstrip("."),
                    "lut_suffix": lut_repre_name,
                    "input_colorspace": converted_color_data[
                        f"input_colorspace{file_idx}"],
                    "output_colorspace": converted_color_data[
                        f"output_colorspace{file_idx}"],
                    "direction": creator_attrs[f"direction{file_idx}"],
                    "interpolation": creator_attrs[f"interpolation{file_idx}"],
                    "config_data": config_data
                }
            )

        instance.data.update({
            "representations": representations,
            "ocioLookWorkingSpace": working_colorspace,
            "ocioLookItems": ocio_look_items
        })

        self.log.debug(pformat(instance.data))
