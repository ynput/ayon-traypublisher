from typing import Any


def _convert_simple_creators_0_2_9(overrides):
    if "simple_creators" not in overrides:
        return
    
    create_overrides = overrides.setdefault("create", {})
    create_overrides["simple_creators"] = overrides.pop("simple_creators")


def _convert_editorial_creators_0_2_9(overrides):
    if "editorial_creators" not in overrides:
        return
    
    create_overrides = overrides.setdefault("create", {})
    create_overrides["editorial_creators"] = overrides.pop("editorial_creators")


def convert_settings_overrides(
    source_version: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    _convert_simple_creators_0_2_9(overrides)
    _convert_editorial_creators_0_2_9(overrides)
    return overrides
