from pprint import pformat
import pyblish.api


class CollectClipInstance(pyblish.api.InstancePlugin):
    """Collect clip instances and resolve its parent"""

    label = "Collect Clip Instances"
    order = pyblish.api.CollectorOrder - 0.081

    hosts = ["traypublisher"]
    families = [
        "plate",
        "review",
        "audio",
        "model",
        "camera",
        "render",
        "image",
        "workfile",
    ]

    def process(self, instance):
        creator_identifier = instance.data["creator_identifier"]
        if creator_identifier not in [
            "editorial_plate",
            "editorial_plate_advanced",
            "editorial_audio",
            "editorial_audio_advanced",
            "editorial_review",
            "editorial_model_advanced",
            "editorial_camera_advanced",
            "editorial_render_advanced",
            "editorial_image_advanced",
            "editorial_workfile_advanced",
        ]:
            return

        instance.data["families"].append("clip")

        parent_instance_id = instance.data["parent_instance_id"]
        edit_shared_data = instance.context.data["editorialSharedData"]
        instance.data.update(
            edit_shared_data[parent_instance_id]
        )

        if "editorialSourcePath" in instance.context.data.keys():
            instance.data["editorialSourcePath"] = (
                instance.context.data["editorialSourcePath"])
            instance.data["families"].append("trimming")

        if repres := instance.data.pop("prep_representations", None):
            representations = []
            for repre in repres:
                tags = repre.get("tags", [])
                custom_tags = repre.get("custom_tags", [])
                content_type = repre["content_type"]

                if content_type == "thumbnail":
                    tags.append("thumbnail")

                # single file type should be a string
                new_repre_files = files = repre["files"]
                if content_type != "image_sequence":
                    new_repre_files = files[0]

                # create new representation data
                new_repre_data = {
                    "ext": repre["ext"],
                    "name": repre["name"],
                    "files": new_repre_files,
                    "stagingDir": repre["dir_path"],
                    "tags": tags,
                    "custom_tags": custom_tags,
                }

                # add optional keys
                if "outputName" in repre.keys():
                    new_repre_data["outputName"] = repre["outputName"]

                representations.append(new_repre_data)

            instance.data["representations"] = representations

        self.log.debug(pformat(instance.data))
