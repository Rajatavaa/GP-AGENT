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
