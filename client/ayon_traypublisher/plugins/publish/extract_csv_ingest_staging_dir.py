import os
import platform
import shutil

import pyblish.api

from ayon_core.lib import create_hard_link
from ayon_core.pipeline import publish
from ayon_core.pipeline.publish.lib import add_repre_files_for_cleanup


class ExtractCSVIngestStagingDir(publish.Extractor):
    """Keep CSV ingest outputs out of the source media folders.

    Representations of a CSV ingest point at the source media, so their
    'stagingDir' is the folder of the original files. The core extractors
    (Extract Review, Extract Burnin) write their outputs into the
    'stagingDir' of the representation they process, which put review
    files next to the source media.

    Every representation tagged 'review' gets its files linked into a
    folder of its own in the instance staging dir, and its 'stagingDir'
    points there, so everything made from it is written there.

    A file is hard linked when the staging dir is on the volume of the
    source (no extra space), else symbolic linked (not on Windows), else
    copied. To keep a large ingest from being copied to a local temp
    drive, set a custom staging dir profile on the source volume:
    `ayon+settings://core/tools/publish/custom_staging_dir_profiles`.
    """

    label = "Extract CSV Ingest Staging Dir"
    # before any extractor writes next to the files of a representation
    order = pyblish.api.ExtractorOrder - 0.1
    hosts = ["traypublisher"]
    families = ["csv_ingest"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        copied = []
        for repre in instance.data.get("representations", []):
            if "review" not in (repre.get("tags") or []):
                continue
            copied.extend(self._move_to_staging_dir(repre, staging_dir))
            # links and copies only: safe to remove after the publish
            add_repre_files_for_cleanup(instance, repre)

        if copied:
            self.log.warning(
                f"{len(copied)} source file(s) were copied to the staging"
                f" dir '{staging_dir}' because it is on another volume."
                " Set a custom staging dir profile on the source volume"
                " to link them instead."
            )

    def _move_to_staging_dir(self, repre, staging_dir):
        """Point the representation to linked files in the staging dir.

        Returns:
            list[str]: Source paths which had to be copied.

        """
        src_dir = os.path.normpath(repre["stagingDir"])
        dst_dir = os.path.normpath(os.path.join(staging_dir, repre["name"]))
        if src_dir == dst_dir:
            return []

        os.makedirs(dst_dir, exist_ok=True)
        files = repre["files"]
        if isinstance(files, str):
            files = [files]

        copied = []
        for filename in files:
            src_path = os.path.join(src_dir, filename)
            dst_path = os.path.join(dst_dir, filename)
            if not self._link_file(src_path, dst_path):
                copied.append(src_path)

        self.log.debug(
            f"Representation '{repre['name']}' staging dir moved"
            f" from '{src_dir}' to '{dst_dir}'."
        )
        repre["stagingDir"] = dst_dir
        repre["stagingDir_persistent"] = False
        return copied

    def _link_file(self, src_path, dst_path):
        """Link or copy the source file to the staging dir.

        Returns:
            bool: False when the file had to be copied.

        """
        if os.path.lexists(dst_path):
            # linked by an earlier publish into a persistent staging dir
            if os.path.exists(dst_path) and os.path.samefile(
                src_path, dst_path
            ):
                return True
            # a stale copy or a broken link, never the source itself
            os.remove(dst_path)

        try:
            create_hard_link(src_path, dst_path)
            return True
        except OSError:
            pass

        if platform.system().lower() != "windows":
            try:
                os.symlink(src_path, dst_path)
                return True
            except OSError:
                pass

        shutil.copyfile(src_path, dst_path)
        return False
