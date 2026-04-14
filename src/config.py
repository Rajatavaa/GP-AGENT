import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_sender_name():
    config = load_config()
    return config.get("sender_name", "")


def set_sender_name(name):
    config = load_config()
    config["sender_name"] = name
    save_config(config)


def get_attach_file():
    config = load_config()
    return config.get("attach_file", "")


def set_attach_file(path):
    config = load_config()
    config["attach_file"] = path
    save_config(config)


def validate_file_path(path):
    if not path:
        return False, "No path provided"
    expanded = os.path.expanduser(path)
    if not os.path.isfile(expanded):
        return False, f"File not found: {expanded}"
    if not os.access(expanded, os.R_OK):
        return False, f"Cannot read file: {expanded}"
    return True, expanded
