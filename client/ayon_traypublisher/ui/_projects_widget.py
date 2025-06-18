from qtpy import QtWidgets, QtCore
from ayon_core.tools.utils import (
    ProjectsQtModel,
    ProjectSortFilterProxy,
    PROJECT_NAME_ROLE,
)

class TrayPublisherProjectsWidget(QtWidgets.QWidget):
    double_clicked = QtCore.Signal()

    def __init__(self, controller, parent):
        super().__init__(parent)
        # Create project models and view
        projects_model = ProjectsQtModel(controller)
        projects_proxy = ProjectSortFilterProxy()
        projects_proxy.setSourceModel(projects_model)
        projects_proxy.setFilterKeyColumn(0)

        projects_view = QtWidgets.QListView(self)
        projects_view.setObjectName("ChooseProjectView")
        projects_view.setModel(projects_proxy)
        projects_view.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        projects_view.doubleClicked.connect(self.double_clicked)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(projects_view, 1)

        self._projects_view = projects_view
        self._projects_model = projects_model
        self._projects_proxy = projects_proxy

        self._controller = controller

    def refresh(self):
        self._projects_model.refresh()
        # Sort projects after refresh
        self._projects_proxy.sort(0)

    def set_name_filter(self, text):
        self._projects_proxy.setFilterFixedString(text)

    def get_selected_project(self):
        index = self._projects_view.currentIndex()
        return index.data(PROJECT_NAME_ROLE)

    def set_selected_project(self, project_name: str):
        """Set the selected project in the view."""
        src_index = self._projects_model.get_index_by_project_name(
            project_name
        )
        index = self._projects_proxy.mapFromSource(src_index)
        if index.isValid():
            selection_model = self._projects_view.selectionModel()
            selection_model.select(
                index,
                QtCore.QItemSelectionModel.SelectCurrent
            )
            self._projects_view.setCurrentIndex(index)