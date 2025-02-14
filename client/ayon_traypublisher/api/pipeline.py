import os
import json
import tempfile
import atexit

import pyblish.api

from ayon_core.pipeline import (
    register_creator_plugin_path,
)
from ayon_core.host import HostBase, IPublishHost


ROOT_DIR = os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))
PUBLISH_PATH = os.path.join(ROOT_DIR, "plugins", "publish")
CREATE_PATH = os.path.join(ROOT_DIR, "plugins", "create")


class TrayPublisherHost(HostBase, IPublishHost):
    name = "traypublisher"

    def install(self):
        os.environ["AYON_HOST_NAME"] = self.name

        pyblish.api.register_host("traypublisher")
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        register_creator_plugin_path(CREATE_PATH)

    def get_context_title(self):
        return self.get_current_project_name()

    def get_context_data(self):
        return HostContext.get_context_data()

    def update_context_data(self, data, changes):
        HostContext.save_context_data(data)

    def set_project_name(self, project_name):
        # TODO Deregister project specific plugins and register new project
        #   plugins
        os.environ["AYON_PROJECT_NAME"] = project_name


class HostContext:
    _context_json_path = None

    @staticmethod
    def _on_exit():
        if (
            HostContext._context_json_path
            and os.path.exists(HostContext._context_json_path)
        ):
            os.remove(HostContext._context_json_path)

    @classmethod
    def get_context_json_path(cls):
        if cls._context_json_path is None:
            output_file = tempfile.NamedTemporaryFile(
                mode="w", prefix="traypub_", suffix=".json"
            )
            output_file.close()
            cls._context_json_path = output_file.name
            atexit.register(HostContext._on_exit)
            print(cls._context_json_path)
        return cls._context_json_path

    @classmethod
    def _get_data(cls, group=None):
        json_path = cls.get_context_json_path()
        data = {}
        if not os.path.exists(json_path):
            with open(json_path, "w") as json_stream:
                json.dump(data, json_stream)
        else:
            with open(json_path, "r") as json_stream:
                content = json_stream.read()
            if content:
                data = json.loads(content)
        if group is None:
            return data
        return data.get(group)

    @classmethod
    def _save_data(cls, group, new_data):
        json_path = cls.get_context_json_path()
        data = cls._get_data()
        data[group] = new_data
        with open(json_path, "w") as json_stream:
            json.dump(data, json_stream)

    @classmethod
    def add_instance(cls, instance):
        instances = cls.get_instances()
        instances.append(instance)
        cls.save_instances(instances)

    @classmethod
    def get_instances(cls):
        return cls._get_data("instances") or []

    @classmethod
    def save_instances(cls, instances):
        cls._save_data("instances", instances)

    @classmethod
    def get_context_data(cls):
        return cls._get_data("context") or {}

    @classmethod
    def save_context_data(cls, data):
        cls._save_data("context", data)


def list_instances():
    return HostContext.get_instances()


def update_instances(update_list):
    updated_instances = {}
    for instance, _changes in update_list:
        updated_instances[instance.id] = instance.data_to_store()

    instances = HostContext.get_instances()
    for instance_data in instances:
        instance_id = instance_data["instance_id"]
        if instance_id in updated_instances:
            new_instance_data = updated_instances[instance_id]
            old_keys = set(instance_data.keys())
            new_keys = set(new_instance_data.keys())
            instance_data.update(new_instance_data)
            for key in (old_keys - new_keys):
                instance_data.pop(key)

    HostContext.save_instances(instances)


def remove_instances(instances):
    if not isinstance(instances, (tuple, list)):
        instances = [instances]

    current_instances = HostContext.get_instances()
    for instance in instances:
        instance_id = instance.data["instance_id"]
        found_idx = None
        for idx, _instance in enumerate(current_instances):
            if instance_id == _instance["instance_id"]:
                found_idx = idx
                break

        if found_idx is not None:
            current_instances.pop(found_idx)
    HostContext.save_instances(current_instances)


def get_context_data():
    return HostContext.get_context_data()


def update_context_data(data, changes):
    HostContext.save_context_data(data)
