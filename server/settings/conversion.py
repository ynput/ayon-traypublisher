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


def _convert_simple_creators_0_4_0(overrides):
    simple_creators = overrides.get("simple_creators")
    if not simple_creators:
        return

    for plugin in simple_creators:
        if "product_base_type" in plugin or "product_type" not in plugin:
            return
        plugin["product_base_type"] = plugin.pop("product_type")


def _convert_editorial_0_4_0(overrides):
    editorial_creators = overrides.get("editorial_creators", {})
    editorial_advanced = editorial_creators.get("editorial_advanced", {})
    if "product_type_advanced_presets" in editorial_advanced:
        presets = editorial_advanced.pop("product_type_advanced_presets")
        for preset in presets:
            preset["product_base_type"] = preset.pop("product_type")
        editorial_advanced["product_base_type_advanced_presets"] = presets

    editorial_simple = editorial_creators.get("editorial_simple", {})
    if "product_base_type_presets" in editorial_simple:
        presets = editorial_simple.pop("product_base_type_presets")
        for preset in presets:
            preset["product_base_type"] = preset.pop("product_type")
        editorial_simple["product_base_type_presets"] = presets


def convert_settings_overrides(
    source_version: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    _convert_csv_ingest_0_3_9(overrides)
    _convert_simple_creators_0_4_0(overrides)
    _convert_editorial_0_4_0(overrides)
    return overrides
