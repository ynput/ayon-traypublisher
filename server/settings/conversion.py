import logging
from typing import Any


logger = logging.getLogger(__name__)

def _convert_csv_ingest_0_3_9(overrides):
    csv_ingest_settings = overrides.get("create", {}).get("IngestCSV")
    if not csv_ingest_settings:
        return

    default_preset = {}
    columns_config = csv_ingest_settings.get("columns_config")
    representations_config = csv_ingest_settings.get("representations_config")
    folder_creation_config = csv_ingest_settings.get("folder_creation_config")

    changed = False
    if columns_config:
        default_preset["columns_config"] = columns_config
        changed = True

    if representations_config:
        default_preset["representations_config"] = representations_config
        changed = True

    if folder_creation_config:
        default_preset["folder_creation_config"] = folder_creation_config
        changed = True

    if changed:
        default_preset["name"] = "Default"
        overrides["create"]["IngestCSV"]["presets"] = [default_preset]


def convert_settings_overrides(
    source_version: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    _convert_csv_ingest_0_3_9(overrides)
    return overrides
