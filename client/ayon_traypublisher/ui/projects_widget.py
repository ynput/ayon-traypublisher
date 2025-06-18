# Handle backwards compatibility for the projects widget import
# - 'ProjectsWidget' is available since ayon-core 1.3.3
try:
    from ayon_core.tools.utils import ProjectsWidget

    class TrayPublisherProjectsWidget(ProjectsWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._projects_view.setObjectName("ChooseProjectView")

except ImportError:
    from ._projects_widget import TrayPublisherProjectsWidget


__all__ = (
    "TrayPublisherProjectsWidget",
)
