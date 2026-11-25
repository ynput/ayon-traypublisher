import os
import platform
import shutil
from concurrent.futures import ThreadPoolExecutor

import pyblish.api

from ayon_core.lib import create_hard_link
from ayon_core.lib.file_transaction import wait_for_future_errors
from ayon_core.pipeline import publish
from ayon_core.pipeline.publish import PublishError
from ayon_core.pipeline.publish.lib import add_repre_files_for_cleanup

# tried in this order, each one when the previous fails
TRANSFER_METHODS = ("hardlink", "symlink", "copy")
IS_WINDOWS = platform.system() == "Windows"


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

    A read-only source file is always copied on Windows: a hard link
    shares the read-only flag of the source there, so the cleanup after
    the publish could not remove it.

    The first file of a representation finds the method that works, the
    other files (frames of a sequence) start from it and are transferred
    in a thread pool, like the core 'FileTransaction'.
    """

    label = "Extract CSV Ingest Staging Dir"
    # before any extractor writes next to the files of a representation
    order = pyblish.api.ExtractorOrder - 0.1
    hosts = ["traypublisher"]
    families = ["csv_ingest"]

    def process(self, instance):
        repres = [
            repre
            for repre in instance.data.get("representations", [])
            if "review" in (repre.get("tags") or [])
        ]
        # fail before anything is linked, so nothing stays behind
        missing = [
            path
            for repre in repres
            for path in self._get_source_paths(repre)
            if not os.path.isfile(path)
        ]
        if missing:
            listed = "\n".join(missing[:10])
            if len(missing) > 10:
                listed += f"\n... and {len(missing) - 10} more"
            raise PublishError(
                f"{len(missing)} source file(s) of the review are missing.",
                title="Missing source files",
                description=(
                    "These source files are not found any more, they were"
                    f" moved or renamed after the CSV was read:\n\n{listed}"
                ),
            )

        staging_dir = self.staging_dir(instance)
        copied = []
        for repre in repres:
            copied.extend(self._move_to_staging_dir(repre, staging_dir))
            # links and copies only: safe to remove after the publish
            add_repre_files_for_cleanup(instance, repre)

        read_only = [path for path in copied if self._is_read_only(path)]
        if read_only:
            self.log.warning(
                f"{len(read_only)} read-only source file(s) were copied to"
                f" the staging dir '{staging_dir}': a link to them could not"
                " be removed after the publish on Windows."
            )
        if len(copied) > len(read_only):
            self.log.warning(
                f"{len(copied) - len(read_only)} source file(s) were copied"
                f" to the staging dir '{staging_dir}' because it is on another"
                " volume. Set a custom staging dir profile on the source"
                " volume to link them instead."
            )

    @staticmethod
    def _get_source_paths(repre):
        files = repre["files"]
        if isinstance(files, str):
            files = [files]
        return [os.path.join(repre["stagingDir"], name) for name in files]

    @staticmethod
    def _is_read_only(path):
        # read-only only matters on Windows, where 'os.access' checks the
        # read-only flag of the file
        return IS_WINDOWS and not os.access(path, os.W_OK)

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

        transfers = [
            (os.path.join(src_dir, filename), os.path.join(dst_dir, filename))
            for filename in files
        ]
        # the first file finds the method, so the others do not retry the
        # ones that fail for this volume pair
        method = self._link_file(*transfers[0])
        methods = [method]
        if len(transfers) > 1:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(self._link_file, src, dst, method)
                    for src, dst in transfers[1:]
                ]
                wait_for_future_errors(executor, futures, logger=self.log)
            methods.extend(future.result() for future in futures)

        copied = [
            src for (src, _), used in zip(transfers, methods) if used == "copy"
        ]
        self.log.debug(
            f"Representation '{repre['name']}' staging dir moved"
            f" from '{src_dir}' to '{dst_dir}'."
        )
        repre["stagingDir"] = dst_dir
        repre["stagingDir_persistent"] = False
        return copied

    def _link_file(self, src_path, dst_path, method="hardlink"):
        """Link or copy the source file to the staging dir.

        Args:
            src_path (str): Source file.
            dst_path (str): File in the staging dir.
            method (str): Transfer method to try first, the ones after it
                in 'TRANSFER_METHODS' are the fallbacks.

        Returns:
            str: The method used, one of 'TRANSFER_METHODS'.

        """
        if os.path.lexists(dst_path):
            # linked by an earlier publish into a persistent staging dir
            if os.path.exists(dst_path) and os.path.samefile(
                src_path, dst_path
            ):
                return method
            # a stale copy or a broken link, never the source itself
            os.remove(dst_path)

        links = TRANSFER_METHODS[TRANSFER_METHODS.index(method) : -1]
        if self._is_read_only(src_path):
            links = ()
        for candidate in links:
            if candidate == "symlink" and IS_WINDOWS:
                continue
            try:
                if candidate == "hardlink":
                    create_hard_link(src_path, dst_path)
                else:
                    os.symlink(src_path, dst_path)
                return candidate
            except OSError:
                pass

        shutil.copyfile(src_path, dst_path)
        return "copy"
