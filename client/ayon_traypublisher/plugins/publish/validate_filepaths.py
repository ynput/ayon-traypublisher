import os
import pyblish.api
from ayon_core.pipeline import PublishValidationError


class ValidateFilePath(pyblish.api.InstancePlugin):
    """Validate existence of source filepaths on instance.

    Plugins looks into key 'sourceFilepaths' and validate if paths there
    actually exist on disk.

    Also validate if the key is filled but is empty. In that case also
    crashes so do not fill the key if unfilled value should not cause error.

    This is primarily created for Simple Creator instances.
    """

    label = "Validate Filepaths"
    order = pyblish.api.ValidatorOrder - 0.49

    hosts = ["traypublisher"]

    def process(self, instance):
        if "sourceFilepaths" not in instance.data:
            self.log.info((
                "Skipped validation of source filepaths existence."
                " Instance does not have collected 'sourceFilepaths'"
            ))
            return

        product_base_type = instance.data["productBaseType"]
        label = instance.data["name"]
        filepaths = instance.data["sourceFilepaths"]
        error_title = "File not filled"
        if not filepaths:
            message = (
                f"Source filepaths of '{product_base_type}'"
                f" instance \"{label}\" are not filled"
            )
            description = (
                "## Files were not filled"
                "\nThis mean that you didn't enter any files into required"
                " file input."
                "\n- Please refresh publishing and check instance"
                f" <b>{label}</b>"
            )
            raise PublishValidationError(message, error_title, description)

        not_found_files = [
            filepath
            for filepath in filepaths
            if not os.path.exists(filepath)
        ]
        if not_found_files:
            joined_paths = "\n".join(
                f"- {filepath}"
                for filepath in not_found_files
            )
            message = (
                f"Filepath of '{product_base_type}' instance \"{label}\""
                f" does not exist:\n{joined_paths}"
            )
            description = (
                f"## Files were not found\nFiles\n{joined_paths}"
                "\n\nCheck if the path is still available."
            )
            raise PublishValidationError(message, error_title, description)
