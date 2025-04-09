import os
import re
import csv
import collections
from io import StringIO
from copy import deepcopy, copy
from typing import Optional, List, Set, Dict, Union, Any

import clique
import ayon_api

from ayon_core.pipeline.create import get_product_name
from ayon_core.pipeline import CreatedInstance
from ayon_core.lib import FileDef, BoolDef, Logger
from ayon_core.lib.transcoding import (
    VIDEO_EXTENSIONS, IMAGE_EXTENSIONS
)
from ayon_core.pipeline.create import CreatorError
from ayon_traypublisher.api.plugin import TrayPublishCreator


log = Logger.get_logger(__name__)


def _get_row_value_with_validation(
    columns_config: Dict[str, Any],
    column_name: str,
    row_data: Dict[str, Any],
):
    """Get row value with validation"""

    # get column data from column config
    column_data = None
    for column in columns_config["columns"]:
        if column["name"] == column_name:
            column_data = column
            break

    if not column_data:
        raise CreatorError(
            f"Column '{column_name}' not found in column config."
        )

    # get column value from row
    column_value = row_data.get(column_name)
    column_required = column_data["required_column"]

    # check if column value is not empty string and column is required
    if column_value == "" and column_required:
        raise CreatorError(
            f"Value in column '{column_name}' is required."
        )

    # get column type
    column_type = column_data["type"]
    # get column validation regex
    column_validation = column_data["validation_pattern"]
    # get column default value
    column_default = column_data["default"]

    if column_type in ["number", "decimal"] and column_default in (0, '0'):
        column_default = None

    # check if column value is not empty string
    if column_value == "":
        # set default value if column value is empty string
        column_value = column_default

    # set column value to correct type following column type
    if column_type == "number" and column_value is not None:
        column_value = int(column_value)
    elif column_type == "decimal" and column_value is not None:
        column_value = float(column_value)
    elif column_type == "bool":
        column_value = column_value in ["true", "True"]

    # check if column value matches validation regex
    if (
        column_value is not None and
        not re.match(str(column_validation), str(column_value))
    ):
        raise CreatorError(
            f"Column '{column_name}' value '{column_value}'"
            f" does not match validation regex '{column_validation}'"
            f"\nRow data: {row_data}"
            f"\nColumn data: {column_data}"
        )

    return column_value


class RepreItem:
    def __init__(
        self,
        name,
        filepath,
        frame_start,
        frame_end,
        handle_start,
        handle_end,
        fps,
        thumbnail_path,
        colorspace,
        comment,
        slate_exists,
        tags,
    ):
        self.name = name
        self.filepath = filepath
        self.frame_start = frame_start
        self.frame_end = frame_end
        self.handle_start = handle_start
        self.handle_end = handle_end
        self.fps = fps
        self.thumbnail_path = thumbnail_path
        self.colorspace = colorspace
        self.comment = comment
        self.slate_exists = slate_exists
        self.tags = tags

    @classmethod
    def from_csv_row(cls, columns_config, repre_config, row):
        kwargs = {
            dst_key: _get_row_value_with_validation(
                columns_config, column_name, row
            )
            for dst_key, column_name in (
                # Representation information
                ("filepath", "File Path"),
                ("frame_start", "Frame Start"),
                ("frame_end", "Frame End"),
                ("handle_start", "Handle Start"),
                ("handle_end", "Handle End"),
                ("fps", "FPS"),

                # Optional representation information
                ("thumbnail_path", "Version Thumbnail"),
                ("colorspace", "Representation Colorspace"),
                ("comment", "Version Comment"),
                ("name", "Representation"),
                ("slate_exists", "Slate Exists"),
                ("repre_tags", "Representation Tags"),
            )
        }

        # Should the 'int' and 'float' conversion happen?
        # - looks like '_get_row_value_with_validation' is already handling it
        for key in {"frame_start", "frame_end", "handle_start", "handle_end"}:
            kwargs[key] = int(kwargs[key])

        kwargs["fps"] = float(kwargs["fps"])

        # Convert tags value to list
        tags_list = copy(repre_config["default_tags"])
        repre_tags: Optional[str] = kwargs.pop("repre_tags")
        if repre_tags:
            tags_list = []
            tags_delimiter = repre_config["tags_delimiter"]
            # strip spaces from repre_tags
            if tags_delimiter in repre_tags:
                tags = repre_tags.split(tags_delimiter)
                for _tag in tags:
                    tags_list.append(_tag.strip().lower())
            else:
                tags_list.append(repre_tags)
        kwargs["tags"] = tags_list
        return cls(**kwargs)


class ProductItem:
    def __init__(
        self,
        folder_path: str,
        task_name: str,
        version: int,
        variant: str,
        product_type: str,
        task_type: Optional[str] = None,
        width: int = None,
        height: int = None,
        pixel_aspect: float = None,
    ):
        self.folder_path = folder_path
        self.task_name = task_name
        self.task_type = task_type
        self.version = version
        self.variant = variant
        self.product_type = product_type
        self.repre_items: List[RepreItem] = []
        self.has_promised_context = False
        self.parents = None
        self._unique_name = None
        self._pre_product_name = None
        self.width = width
        self.height = height
        self.pixel_aspect = pixel_aspect

    @property
    def unique_name(self) -> str:
        if self._unique_name is None:
            self._unique_name = "/".join([
                self.folder_path,
                self.task_name,
                f"{self.variant}{self.product_type}{self.version}".replace(
                    " ", ""
                ).lower()
            ])
        return self._unique_name

    @property
    def instance_name(self):
        if self._pre_product_name is None:
            self._pre_product_name = (
                f"{self.task_name}{self.variant}"
                f"{self.product_type}{self.version}"
            ).replace(" ", "").lower()
        return self._pre_product_name

    def add_repre_item(self, repre_item: RepreItem):
        self.repre_items.append(repre_item)

    @classmethod
    def from_csv_row(cls, columns_config, row):
        kwargs = {
            dst_key: _get_row_value_with_validation(
                columns_config, column_name, row
            )
            for dst_key, column_name in (
                # Context information
                ("folder_path", "Folder Path"),
                ("width", "Shot Width"),
                ("height", "Shot Height"),
                ("pixel_aspect", "Shot Pixel Aspect"),
                ("task_name", "Task Name"),
                ("version", "Version"),
                ("variant", "Variant"),
                ("product_type", "Product Type"),
            )
        }
        return cls(**kwargs)


class IngestCSV(TrayPublishCreator):
    """CSV ingest creator class"""

    icon = "fa.file"

    label = "CSV Ingest"
    product_type = "csv_ingest_file"
    identifier = "io.ayon.creators.traypublisher.csv_ingest"

    default_variants = ["Main"]

    description = "Ingest products' data from CSV file"
    detailed_description = """
Ingest products' data from CSV file following column and representation
configuration in project settings.
"""

    # Position in the list of creators.
    order = 10

    # settings for this creator
    columns_config = {}
    representations_config = {}
    folder_creation_config = {}

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            )
        ]

    def get_pre_create_attr_defs(self):
        """Creating pre-create attributes at creator plugin.

        Returns:
            list: list of attribute object instances
        """
        # Use same attributes as for instance attributes
        return [
            FileDef(
                "csv_filepath_data",
                folders=False,
                extensions=[".csv"],
                allow_sequences=False,
                single_item=True,
                label="CSV File",
            ),
        ]

    def create(
        self,
        product_name: str,
        instance_data: Dict[str, Any],
        pre_create_data: Dict[str, Any]
    ):
        """Create product from each row found in the CSV.

        Args:
            product_name (str): The subset name.
            instance_data (dict): The instance data.
            pre_create_data (dict):
        """

        csv_filepath_data = pre_create_data.get("csv_filepath_data", {})

        csv_dir = csv_filepath_data.get("directory", "")
        if not os.path.exists(csv_dir):
            raise CreatorError(
                f"Directory '{csv_dir}' does not exist."
            )
        filename = csv_filepath_data.get("filenames", [])
        self._process_csv_file(
            product_name, instance_data, csv_dir, filename[0]
        )

    def _pass_data_to_csv_instance(
        self,
        instance_data: Dict[str, Any],
        staging_dir: str,
        filename: str
    ):
        """Pass CSV representation file to instance data"""

        representation = {
            "name": "csv",
            "ext": "csv",
            "files": filename,
            "stagingDir": staging_dir,
            "stagingDir_persistent": True,
        }

        instance_data.update({
            "label": f"CSV: {filename}",
            "representations": [representation],
            "stagingDir": staging_dir,
            "stagingDir_persistent": True,
        })

    def _process_csv_file(
        self,
        product_name: str,
        instance_data: Dict[str, Any],
        csv_dir: str,
        filename: str
    ):
        """Process CSV file.

        Args:
            product_name (str): The subset name.
            instance_data (dict): The instance data.
            csv_dir (str): The csv directory.
            filename (str): The filename.

        """
        # create new instance from the csv file via self function
        self._pass_data_to_csv_instance(
            instance_data,
            csv_dir,
            filename
        )

        csv_instance = CreatedInstance(
            self.product_type, product_name, instance_data, self
        )

        csv_instance["csvFileData"] = {
            "filename": filename,
            "staging_dir": csv_dir,
        }

        # create instances from csv data via self function
        instances = self._create_instances_from_csv_data(csv_dir, filename)
        for instance in instances:
            self._store_new_instance(instance)
        self._store_new_instance(csv_instance)

    def _resolve_repre_path(
        self, csv_dir: str, filepath: Union[str, None]
    ) -> Union[str, None]:
        if not filepath:
            return filepath

        # Validate only existence of file directory as filename
        #   may contain frame specific char (e.g. '%04d' or '####').
        filedir, filename = os.path.split(filepath)
        if not filedir or filedir == ".":
            # If filedir is empty or "." then use same directory as
            #   csv path
            filepath = os.path.join(csv_dir, filepath)

        elif not os.path.exists(filedir):
            # If filepath does not exist, first try to find it in the
            #   same directory as the csv file is, but keep original
            #   value otherwise.
            new_filedir = os.path.join(csv_dir, filedir)
            if os.path.exists(new_filedir):
                filepath = os.path.join(new_filedir, filename)

        return filepath

    def _get_folder_type_from_regex_settings(self, folder_name: str) -> str:
        """ Get the folder type that matches the regex settings.

        Args:
            folder_name (str): The folder name.

        Returns:
            str. The folder type to use.
        """
        for folder_setting in self.folder_creation_config["folder_type_regexes"]:
            if re.match(folder_setting["regex"], folder_name):
                folder_type = folder_setting["folder_type"]
                return folder_type

        return self.folder_creation_config["folder_create_type"]

    def _compute_parents_data(self, project_name: str, product_item: ProductItem) -> list:
        """ Compute parent data when new hierarchy has to be created during the
            publishing process.

        Args:
            project_name (str): The project name.
            product_item (ProductItem): The product item to inspect.

        Returns:
            list. The parent list if any

        Raise:
            ValueError: When provided folder_path parent do not exist.
        """
        parent_folder_names = product_item.folder_path.lstrip("/").split("/")
        # Rename name of folder itself
        parent_folder_names.pop(-1)
        if not parent_folder_names:
            return []

        parent_paths = []
        parent_path = ""
        for name in parent_folder_names:
            path = f"{parent_path}/{name}"
            parent_paths.append(path)
            parent_path = path

        folders_by_path = {
            folder["path"]: folder
            for folder in ayon_api.get_folders(
                project_name,
                folder_paths=parent_paths,
                fields={"folderType", "path"}
            )
        }
        parent_data = []
        for path in parent_paths:
            folder_entity = folders_by_path.get(path)
            name = path.rsplit("/", 1)[-1]

            # Folder exists, retrieve data from existing.
            if folder_entity:
                folder_type = folder_entity["folderType"]

            # Define folder type from settings.
            else:
                folder_type = self._get_folder_type_from_regex_settings(name)

            item = {
                "entity_name": name,
                "folder_type": folder_type,
            }
            parent_data.append(item)

        return parent_data


    def _get_data_from_csv(
        self, csv_dir: str, filename: str
    ) -> Dict[str, ProductItem]:
        """Generate instances from the csv file"""
        # get current project name and code from context.data
        project_name = self.create_context.get_current_project_name()
        csv_path = os.path.join(csv_dir, filename)

        # make sure csv file contains columns from following list
        required_columns = [
            column["name"]
            for column in self.columns_config["columns"]
            if column["required_column"]
        ]

        # read csv file
        with open(csv_path, "r") as csv_file:
            csv_content = csv_file.read()

        # read csv file with DictReader
        csv_reader = csv.DictReader(
            StringIO(csv_content),
            delimiter=self.columns_config["csv_delimiter"]
        )

        # fix fieldnames
        # sometimes someone can keep extra space at the start or end of
        # the column name
        all_columns = [
            " ".join(column.rsplit())
            for column in csv_reader.fieldnames
        ]

        # return back fixed fieldnames
        csv_reader.fieldnames = all_columns

        # check if csv file contains all required columns
        if any(column not in all_columns for column in required_columns):
            raise CreatorError(
                f"Missing required columns: {required_columns}"
            )

        product_items_by_name: Dict[str, ProductItem] = {}
        for row in csv_reader:
            _product_item: ProductItem = ProductItem.from_csv_row(
                self.columns_config, row
            )
            unique_name = _product_item.unique_name
            if unique_name not in product_items_by_name:
                product_items_by_name[unique_name] = _product_item
            product_item: ProductItem = product_items_by_name[unique_name]
            product_item.add_repre_item(
                RepreItem.from_csv_row(
                    self.columns_config,
                    self.representations_config,
                    row
                )
            )

        folder_paths: Set[str] = {
            product_item.folder_path
            for product_item in product_items_by_name.values()
        }
        folder_ids_by_path: Dict[str, str] = {
            folder_entity["path"]: folder_entity["id"]
            for folder_entity in ayon_api.get_folders(
                project_name, folder_paths=folder_paths, fields={"id", "path"}
            )
        }
        missing_paths: Set[str] = folder_paths - set(folder_ids_by_path.keys())

        task_names: Set[str] = {
            product_item.task_name
            for product_item in product_items_by_name.values()
        }
        task_entities_by_folder_id = collections.defaultdict(list)
        for task_entity in ayon_api.get_tasks(
            project_name,
            folder_ids=set(folder_ids_by_path.values()),
            task_names=task_names,
            fields={"folderId", "name", "taskType"}
        ):
            folder_id = task_entity["folderId"]
            task_entities_by_folder_id[folder_id].append(task_entity)

        missing_tasks: Set[str] = set()
        if missing_paths and not self.folder_creation_config["enabled"]:
            error_msg = (
                "Folder creation is disabled but found missing folder(s): %r" %
                ",".join(missing_paths)
            )
            raise CreatorError(error_msg)

        for product_item in product_items_by_name.values():
            folder_path = product_item.folder_path

            if folder_path in missing_paths:
                product_item.has_promised_context = True
                product_item.task_type = None
                product_item.parents = self._compute_parents_data(
                    project_name,
                    product_item
                )
                continue

            task_name = product_item.task_name
            folder_id = folder_ids_by_path[folder_path]
            task_entities = task_entities_by_folder_id[folder_id]
            task_entity = next(
                (
                    task_entity
                    for task_entity in task_entities
                    if task_entity["name"] == task_name
                ),
                None
            )
            if task_entity is None:
                missing_tasks.add("/".join([folder_path, task_name]))
            else:
                product_item.task_type = task_entity["taskType"]

        if missing_tasks:
            ending = "" if len(missing_tasks) == 1 else "s"
            joined_paths = "\n".join(sorted(missing_tasks))
            raise CreatorError(
                f"Task{ending} not found.\n{joined_paths}"
            )

        for product_item in product_items_by_name.values():
            repre_paths: Set[str] = set()
            duplicated_paths: Set[str] = set()
            for repre_item in product_item.repre_items:
                # Resolve relative paths in csv file
                repre_item.filepath = self._resolve_repre_path(
                    csv_dir, repre_item.filepath
                )
                repre_item.thumbnail_path = self._resolve_repre_path(
                    csv_dir, repre_item.thumbnail_path
                )

                filepath = repre_item.filepath
                if filepath in repre_paths:
                    duplicated_paths.add(filepath)
                repre_paths.add(filepath)

            if duplicated_paths:
                ending = "" if len(duplicated_paths) == 1 else "s"
                joined_names = "\n".join(sorted(duplicated_paths))
                raise CreatorError(
                    f"Duplicate filename{ending} in csv file.\n{joined_names}"
                )

        return product_items_by_name

    def _add_thumbnail_repre(
        self,
        thumbnails: Set[str],
        instance: CreatedInstance,
        repre_item: RepreItem,
        multiple_thumbnails: bool,
    ) -> Union[str, None]:
        """Add thumbnail to instance.

        Add thumbnail as representation and set 'thumbnailPath' if is not set
            yet.

        Args:
            thumbnails (Set[str]): Set of all thumbnail paths that should
                create representation.
            instance (CreatedInstance): Instance from create plugin.
            repre_item (RepreItem): Representation item.
            multiple_thumbnails (bool): There are multiple representations
                with thumbnail.

        Returns:
            Uniom[str, None]: Explicit output name for thumbnail
                representation.

        """
        if not thumbnails:
            return None

        thumbnail_path = repre_item.thumbnail_path
        if not thumbnail_path or thumbnail_path not in thumbnails:
            return None

        thumbnails.remove(thumbnail_path)

        thumb_dir, thumb_file = os.path.split(thumbnail_path)
        thumb_basename, thumb_ext = os.path.splitext(thumb_file)

        # NOTE 'explicit_output_name' and custom repre name was set only
        #   when 'multiple_thumbnails' is True and 'review' tag is present.
        # That was changed to set 'explicit_output_name' is set when
        #   'multiple_thumbnails' is True.
        # is_reviewable = "review" in repre_item.tags

        repre_name = "thumbnail"
        explicit_output_name = None
        if multiple_thumbnails:
            repre_name = f"thumbnail_{thumb_basename}"
            explicit_output_name = repre_item.name

        thumbnail_repre_data = {
            "name": repre_name,
            "ext": thumb_ext.lstrip("."),
            "files": thumb_file,
            "stagingDir": thumb_dir,
            "stagingDir_persistent": True,
            "tags": ["thumbnail", "delete"],
        }
        if explicit_output_name:
            thumbnail_repre_data["outputName"] = explicit_output_name

        instance["prepared_data_for_repres"].append({
            "type": "thumbnail",
            "colorspace": None,
            "representation": thumbnail_repre_data,
        })
        # also add thumbnailPath for ayon to integrate
        if not instance.get("thumbnailPath"):
            instance["thumbnailPath"] = thumbnail_path

        return explicit_output_name

    def _add_representation(
        self,
        instance: CreatedInstance,
        repre_item: RepreItem,
        explicit_output_name: Optional[str] = None
    ):
        """Get representation data

        Args:
            repre_item (RepreItem): Representation item based on csv row.
            explicit_output_name (Optional[str]): Explicit output name.
                For grouping purposes with reviewable components.

        """
        # get extension of file
        basename: str = os.path.basename(repre_item.filepath)
        extension: str = os.path.splitext(basename)[-1].lower()

        # validate filepath is having correct extension based on output
        repre_config_data: Union[Dict[str, Any], None] = None
        for repre in self.representations_config["representations"]:
            if repre["name"] == repre_item.name:
                repre_config_data = repre
                break

        if not repre_config_data:
            raise CreatorError(
                f"Representation '{repre_item.name}' not found "
                "in config representation data."
            )

        validate_extensions: List[str] = repre_config_data["extensions"]
        if extension not in validate_extensions:
            raise CreatorError(
                f"File extension '{extension}' not valid for "
                f"output '{validate_extensions}'."
            )

        is_sequence: bool = extension in IMAGE_EXTENSIONS
        # convert ### string in file name to %03d
        # this is for correct frame range validation
        # example: file.###.exr -> file.%03d.exr
        file_head = basename.split(".")[0]
        if "#" in basename:
            padding = len(basename.split("#")) - 1
            seq_padding = f"%0{padding}d"
            basename = basename.replace("#" * padding, seq_padding)
            file_head = basename.split(seq_padding)[0]
            is_sequence = True
        elif "%" in basename:
            pattern = re.compile(r"%\d+d|%d")
            padding = pattern.findall(basename)
            if not padding:
                raise CreatorError(
                    f"File sequence padding not found in '{basename}'."
                )
            file_head = basename.split("%")[0]
            is_sequence = True
        else:
            # in case it is still image
            is_sequence = False

        # make absolute path to file
        dirname: str = os.path.dirname(repre_item.filepath)

        # check if dirname exists
        if not os.path.isdir(dirname):
            raise CreatorError(
                f"Directory '{dirname}' does not exist."
            )

        frame_start: Union[int, None] = None
        frame_end: Union[int, None] = None
        files: Union[str, List[str]] = basename
        if is_sequence:
            # get only filtered files form dirname
            files_from_dir = [
                filename
                for filename in os.listdir(dirname)
                if filename.startswith(file_head)
            ]
            # collect all data from dirname
            cols, _ = clique.assemble(files_from_dir)
            if not cols:
                raise CreatorError(
                    f"No collections found in directory '{dirname}'."
                )

            col = cols[0]
            files = list(col)
            frame_start = min(col.indexes)
            frame_end = max(col.indexes)

        tags: List[str] = deepcopy(repre_item.tags)
        # if slate in repre_data is True then remove one frame from start
        if repre_item.slate_exists:
            tags.append("has_slate")

        # get representation data
        representation_data: Dict[str, Any] = {
            "name": repre_item.name,
            "ext": extension[1:],
            "files": files,
            "stagingDir": dirname,
            "stagingDir_persistent": True,
            "tags": tags,
        }
        if extension in VIDEO_EXTENSIONS:
            representation_data.update({
                "fps": repre_item.fps,
                "outputName": repre_item.name,
            })

        if explicit_output_name:
            representation_data["outputName"] = explicit_output_name

        if frame_start:
            representation_data["frameStart"] = frame_start
        if frame_end:
            representation_data["frameEnd"] = frame_end

        instance["prepared_data_for_repres"].append({
            "type": "media",
            "colorspace": repre_item.colorspace,
            "representation": representation_data,
        })

    def _prepare_representations(
        self, product_item: ProductItem, instance: CreatedInstance
    ):
        # Collect thumbnail paths from all representation items
        #   to check if multiple thumbnails are present.
        # Once representation is created for certain thumbnail it is removed
        #   from the set.
        thumbnails: Set[str] = {
            repre_item.thumbnail_path
            for repre_item in product_item.repre_items
            if repre_item.thumbnail_path
        }
        multiple_thumbnails: bool = len(thumbnails) > 1

        for repre_item in product_item.repre_items:
            explicit_output_name = self._add_thumbnail_repre(
                thumbnails,
                instance,
                repre_item,
                multiple_thumbnails,
            )

            # get representation data
            self._add_representation(
                instance,
                repre_item,
                explicit_output_name
            )

    def _get_task_type_from_task_name(self, task_name: str):
        """ Retrieve task type from task name.

        Args:
            task_name (str): The task name.

        Returns:
            str. The task type computed from settings.
        """
        for task_setting in self.folder_creation_config["task_type_regexes"]:
            if re.match(task_setting["regex"], task_name):
                task_type = task_setting["task_type"]
                break
        else:
            task_type = self.folder_creation_config["task_create_type"]

        return task_type

    def _create_instances_from_csv_data(self, csv_dir: str, filename: str):
        """Create instances from csv data"""
        # from special function get all data from csv file and convert them
        # to new instances
        product_items_by_name: Dict[str, ProductItem] = (
            self._get_data_from_csv(csv_dir, filename)
        )

        instances = []
        project_name: str = self.create_context.get_current_project_name()
        for product_item in product_items_by_name.values():
            folder_path: str = product_item.folder_path
            version: int = product_item.version
            product_name: str = get_product_name(
                project_name,
                product_item.task_name,
                product_item.task_type,
                self.host_name,
                product_item.product_type,
                product_item.variant
            )

            if version is not None:
                label: str = f"{folder_path}_{product_name}_v{version:>03}"
            else:
                label: str = f"{folder_path}_{product_name}_v[next]"

            repre_items: List[RepreItem] = product_item.repre_items
            first_repre_item: RepreItem = repre_items[0]
            version_comment: Union[str, None] = next(
                (
                    repre_item.comment
                    for repre_item in repre_items
                    if repre_item.comment
                ),
                None
            )

            slate_exists: bool = any(
                repre_item.slate_exists
                for repre_item in repre_items
            )

            is_reviewable: bool = any(
                True
                for repre_item in repre_items
                if "review" in repre_item.tags
            )

            families: List[str] = ["csv_ingest"]
            if slate_exists:
                # adding slate to families mainly for loaders to be able
                # to filter out slates
                families.append("slate")

            if is_reviewable:
                # review family needs to be added for ExtractReview plugin
                families.append("review")

            instance_data = {
                "name": product_item.instance_name,
                "folderPath": folder_path,
                "families": families,
                "label": label,
                "task": product_item.task_name,
                "variant": product_item.variant,
                "source": "csv",
                "frameStart": first_repre_item.frame_start,
                "frameEnd": first_repre_item.frame_end,
                "handleStart": first_repre_item.handle_start,
                "handleEnd": first_repre_item.handle_end,
                "fps": first_repre_item.fps,
                "version": version,
                "comment": version_comment,
                "prepared_data_for_repres": []
            }

            if product_item.has_promised_context:
                hierarchy, folder_name = folder_path.rsplit("/", 1)
                families.append("shot")
                instance_data.update(
                    {
                        "newHierarchyIntegration": True,
                        "hierarchy": hierarchy,
                        "parents": product_item.parents,
                        "families": families,
                        "heroTrack": True,
                    }
                )

                if product_item.pixel_aspect:
                    instance_data["pixelAspect"] = product_item.pixel_aspect

                if product_item.width and product_item.height:
                    instance_data.update(
                        {
                            "resolutionWidth": product_item.width,
                            "resolutionHeight": product_item.height,
                        }
                    )
                elif product_item.width or product_item.height:
                    log.warning(
                        "Ignoring incomplete provided resolution %rx%r for shot %s.",
                        product_item.width,
                        product_item.height,
                        folder_name
                    )

                folder_type = self._get_folder_type_from_regex_settings(folder_name)
                instance_data["folder_type"] = folder_type

                if product_item.task_name:
                    task_type = self._get_task_type_from_task_name(
                        product_item.task_name
                    )
                    tasks = instance_data.setdefault("tasks", {})
                    tasks[product_item.task_name] = {
                        "type": task_type
                    }

            # create new instance
            new_instance: CreatedInstance = CreatedInstance(
                product_item.product_type,
                product_name,
                instance_data,
                self
            )
            self._prepare_representations(product_item, new_instance)

            if product_item.has_promised_context:
                new_instance.transient_data["has_promised_context"] = True

            instances.append(new_instance)

        return instances
