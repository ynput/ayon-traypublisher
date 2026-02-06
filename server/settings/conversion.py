import logging
from typing import Any


logger = logging.getLogger(__name__)

def _convert_csv_ingest_0_3_9(overrides):
    csv_ingest_settings = overrides.get("create", {}).get("IngestCSV", {})
    if not csv_ingest_settings:
        return
    if "presets" in csv_ingest_settings:
        return

    default_preset = {}
    if "columns_config" in csv_ingest_settings:
        default_preset["columns_config"] = csv_ingest_settings.pop(
            "columns_config")

    if "representations_config" in csv_ingest_settings:
        default_preset["representations_config"] = csv_ingest_settings.pop(
            "representations_config")

    if "folder_creation_config" in csv_ingest_settings:
        default_preset["folder_creation_config"] = csv_ingest_settings.pop(
            "folder_creation_config")

    if default_preset:
        default_preset["name"] = "Default"
        overrides["create"]["IngestCSV"]["presets"] = [default_preset]


def convert_settings_overrides(
    source_version: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    _convert_csv_ingest_0_3_9(overrides)
    return overrides
