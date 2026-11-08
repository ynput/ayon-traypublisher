import pyblish.api

from ayon_core.pipeline import (
    publish,
    PublishValidationError
)

from ayon_core.pipeline.colorspace import (
    get_ocio_config_colorspaces,
    get_ocio_config_views,
)


class ValidateColorspace(pyblish.api.InstancePlugin,
                         publish.AYONPyblishPluginMixin,
                         publish.ColormanagedPyblishPluginMixin):
    """Validate representation colorspaces"""

    label = "Validate representation colorspace"
    order = pyblish.api.ValidatorOrder
    hosts = ["traypublisher"]
    families = ["render", "plate", "reference", "image", "online"]

    def process(self, instance):

        config_colorspaces = {}  # cache of colorspaces per config path
        config_views = {}  # cache of display/view keys per config path
        for repre in instance.data.get("representations", {}):

            colorspace_data = repre.get("colorspaceData", {})
            if not colorspace_data:
                # Nothing to validate
                continue

            config_path = colorspace_data["config"]["path"]
            colorspace = colorspace_data.get("colorspace")
            display = colorspace_data.get("display")
            view = colorspace_data.get("view")

            if bool(display) != bool(view):
                message = (
                    f"Representation '{repre['name']}' colorspace data has "
                    f"only one of display '{display}' and view '{view}'. "
                    "Both display and view must be set."
                )
                raise PublishValidationError(
                    title="Representation display and view",
                    message=message,
                    description=message
                )

            if display and view:
                if colorspace:
                    self.log.debug(
                        f"Representation '{repre['name']}' has display and "
                        f"view set, colorspace '{colorspace}' is ignored."
                    )
                self._validate_display_view(
                    repre["name"], config_path, display, view, config_views
                )
            elif colorspace:
                self._validate_colorspace(
                    repre["name"], config_path, colorspace, config_colorspaces
                )

    def _validate_display_view(
        self, repre_name, config_path, display, view, config_views
    ):
        if config_path not in config_views:
            views = get_ocio_config_views(config_path)
            if not views:
                message = (
                    f"OCIO config '{config_path}' does not contain any "
                    "displays and views. This is an error in the OCIO "
                    "config. Contact your pipeline TD."
                )
                raise PublishValidationError(
                    title="Colorspace validation",
                    message=message,
                    description=message
                )
            config_views[config_path] = set(views)

        self.log.debug(
            f"Validating representation '{repre_name}' "
            f"display '{display}' and view '{view}'"
        )
        if f"{display}/{view}" not in config_views[config_path]:
            message = (
                f"Representation '{repre_name}' display '{display}' and "
                f"view '{view}' do not exist in OCIO config: {config_path}"
            )
            raise PublishValidationError(
                title="Representation display and view",
                message=message,
                description=message
            )

    def _validate_colorspace(
        self, repre_name, config_path, colorspace, config_colorspaces
    ):
        if config_path not in config_colorspaces:
            colorspaces = get_ocio_config_colorspaces(config_path)
            if not colorspaces.get("colorspaces"):
                message = (
                    f"OCIO config '{config_path}' does not contain any "
                    "colorspaces. This is an error in the OCIO config. "
                    "Contact your pipeline TD."
                )
                raise PublishValidationError(
                    title="Colorspace validation",
                    message=message,
                    description=message
                )
            config_colorspaces[config_path] = set(
                colorspaces["colorspaces"])

        self.log.debug(
            f"Validating representation '{repre_name}' "
            f"colorspace '{colorspace}'"
        )
        if colorspace not in config_colorspaces[config_path]:
            message = (
                f"Representation '{repre_name}' colorspace "
                f"'{colorspace}' does not exist in OCIO config: "
                f"{config_path}"
            )

            raise PublishValidationError(
                title="Representation colorspace",
                message=message,
                description=message
            )
