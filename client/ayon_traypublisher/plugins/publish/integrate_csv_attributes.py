from __future__ import annotations

import pyblish.api
from ayon_api.operations import OperationsSession


class IntegrateCSVAttributes(pyblish.api.ContextPlugin):
    """Integrate CSV attributes into AYON entities.

    Runs once after all instances have been processed.
    A single OperationsSession is shared across all instances
    and only committed when at least one change is found.
    """

    label = "Integrate CSV Attributes"
    order = pyblish.api.IntegratorOrder
    hosts = ["traypublisher"]

    def process(self, context: pyblish.api.Context):
        project_name = context.data["projectName"]
        op_session = OperationsSession()

        for instance in context:
            task_data = instance.data.get("taskData")
            folder_data = instance.data.get("folderData")

            if task_data:
                task_entity = instance.data.get("taskEntity")
                if task_entity:
                    self._collect_entity_updates(
                        project_name, "task",
                        task_entity, task_data, op_session,
                    )

            if folder_data:
                folder_entity = instance.data.get("folderEntity")
                if folder_entity:
                    self._collect_entity_updates(
                        project_name, "folder",
                        folder_entity, folder_data, op_session,
                    )

        if not len(op_session):
            self.log.debug("No CSV attribute changes to commit.")
            return

        self.log.debug(
            "Committing %d CSV attribute change(s).",
            len(op_session),
        )
        op_session.commit()

    def _collect_entity_updates(
        self,
        project_name: str,
        entity_type: str,
        entity: dict,
        data: dict,
        op_session: OperationsSession,
    ) -> None:
        attrib = entity.get("attrib") or {}
        attrib_changes = {
            key: value
            for key, value in data.items()
            if value != attrib.get(key)
        }

        if not attrib_changes:
            return

        self.log.debug(
            "Queueing attrib update for %s '%s': %s",
            entity_type,
            entity.get("name", entity["id"]),
            attrib_changes,
        )
        op_session.update_entity(
            project_name,
            entity_type,
            entity["id"],
            {"attrib": attrib_changes},
        )
