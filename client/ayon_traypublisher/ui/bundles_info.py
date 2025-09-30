import os
import copy
from dataclasses import dataclass
from typing import Optional, Any

import ayon_api
from ayon_api import get_bundles

from ayon_core.lib import get_settings_variant

_PLACEHOLDER = object()


class BundleNotFoundError(Exception):
    pass


@dataclass
class ProjectBundleInfo:
    project_name: str
    studio_bundle_name: str
    project_bundle_name: Optional[str]
    installer_version: Optional[str]
    addon_versions: dict[str, str]


class BundlesInfo:
    def __init__(
        self,
        studio_bundle_name: Optional[str] = None,
        variant: Optional[str] = None,
    ) -> None:
        if studio_bundle_name is None:
            studio_bundle_name = os.environ.get("AYON_STUDIO_BUNDLE_NAME")
            if studio_bundle_name is None:
                studio_bundle_name = os.environ.get("AYON_BUNDLE_NAME")

        if studio_bundle_name is None:
            msg = (
                "Studio bundle is not available and is not set"
                " in environment variables 'AYON_STUDIO_BUNDLE_NAME' or"
                " 'AYON_BUNDLE_NAME'."
            )
            raise ValueError(msg)

        if variant is None:
            variant = get_settings_variant()

        self._variant = variant
        self._studio_bundle_name = studio_bundle_name

        self._bundles_by_name = None
        self._studio_bundle_info = _PLACEHOLDER
        self._cache_by_project_name = {}

    def reset(self) -> None:
        self._bundles_by_name = None
        self._studio_bundle_info = _PLACEHOLDER
        self._cache_by_project_name = {}

    def get_project_addons(
        self,
        project_name: str,
        project_entity: Optional[dict[str, Any]] = None,
    ) -> ProjectBundleInfo:
        if project_name in self._cache_by_project_name:
            return self._cache_by_project_name[project_name]

        studio_bundle = self._get_studio_bundle_info()
        if studio_bundle is None:
            msg = f"Studio bundle '{self._studio_bundle_name}' not found."
            raise BundleNotFoundError(msg)

        if project_entity is None:
            project_entity = ayon_api.get_project(project_name)
        project_data = project_entity["data"]
        project_bundles_info = project_data.get("bundle") or {}
        project_bundle_name = project_bundles_info.get(self._variant)
        project_bundle_info = {}
        if project_bundle_name is not None:
            bundles_by_name = self._get_bundles_by_name()
            project_bundle_info = bundles_by_name.get(project_bundle_name)
            if not project_bundle_info:
                msg = f"Project bundle '{project_bundle_name}' not found."
                raise BundleNotFoundError(msg)

        installer_version = studio_bundle.get("installerVersion")
        addon_versions = studio_bundle.get("addons") or {}
        addon_overrides = {}
        if "installerVersion" in project_bundle_info:
            installer_version = project_bundle_info.get("installerVersion")

        if "addons" in project_bundle_info:
            addon_overrides = project_bundle_info.get("addons")

        for addon_name, addon_version in addon_overrides.items():
            if addon_version is None:
                addon_versions.pop(addon_name, None)
            addon_versions[addon_name] = addon_version

        output = ProjectBundleInfo(
            project_name=project_name,
            studio_bundle_name=self._studio_bundle_name,
            project_bundle_name=project_bundle_name,
            installer_version=installer_version,
            addon_versions=addon_versions,
        )
        self._cache_by_project_name[project_name] = output
        return output

    def _get_bundles_by_name(self) -> dict[str, dict[str, Any]]:
        if self._bundles_by_name is None:
            bundles_info = get_bundles().get("bundles") or []
            self._bundles_by_name = {
                bundle_info["name"]: bundle_info
                for bundle_info in bundles_info
            }
        return copy.deepcopy(self._bundles_by_name)

    def _get_studio_bundle_info(self) -> Optional[dict[str, Any]]:
        if self._studio_bundle_info is _PLACEHOLDER:
            bundles_by_name = self._get_bundles_by_name()
            self._studio_bundle_info = bundles_by_name.get(
                self._studio_bundle_name
            )
        return copy.deepcopy(self._studio_bundle_info)
