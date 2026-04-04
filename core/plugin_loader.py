"""
plugin_loader.py — Simple plugin system for extensibility.

Plugins are Python files placed in the plugins/ folder.
Each plugin must define:
  PLUGIN_NAME: str
  PLUGIN_VERSION: str
  def register(app): called when plugin is loaded, receives the app instance

Optional:
  PLUGIN_DESCRIPTION: str
  def on_mod_loaded(analysis: dict): called when a mod is analyzed
  def on_reslot(mod_path, fighter, src, tgt): called after reslot
"""
import os
import sys
import importlib
import importlib.util

from core import logger

_plugins: list = []

if getattr(sys, "frozen", False):
    _plugin_dir = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "SmashModManager", "plugins")
else:
    _plugin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins")


class PluginInfo:
    """Metadata about a loaded plugin."""
    def __init__(self, name, version, description, module):
        self.name = name
        self.version = version
        self.description = description
        self.module = module


def discover_plugins() -> list[str]:
    """Return list of plugin .py files found in the plugins/ folder."""
    if not os.path.isdir(_plugin_dir):
        os.makedirs(_plugin_dir, exist_ok=True)
        return []
    return [
        f for f in os.listdir(_plugin_dir)
        if f.endswith(".py") and not f.startswith("_")
    ]


def load_plugins(app=None) -> list[PluginInfo]:
    """Load all discovered plugins."""
    global _plugins
    _plugins = []

    for filename in discover_plugins():
        try:
            path = os.path.join(_plugin_dir, filename)
            spec = importlib.util.spec_from_file_location(
                f"plugins.{filename[:-3]}", path
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            name = getattr(mod, "PLUGIN_NAME", filename)
            version = getattr(mod, "PLUGIN_VERSION", "?")
            desc = getattr(mod, "PLUGIN_DESCRIPTION", "")

            info = PluginInfo(name, version, desc, mod)
            _plugins.append(info)

            # Call register if it exists
            register_fn = getattr(mod, "register", None)
            if register_fn and app:
                register_fn(app)

            logger.info(f"Plugin loaded: {name} v{version}")

        except Exception as e:
            logger.warn(f"Failed to load plugin {filename}: {e}")

    return _plugins


def get_loaded_plugins() -> list[PluginInfo]:
    return list(_plugins)


def notify(event_name: str, **kwargs):
    """Notify all plugins of an event (e.g., 'on_mod_loaded')."""
    for info in _plugins:
        handler = getattr(info.module, event_name, None)
        if handler:
            try:
                handler(**kwargs)
            except Exception as e:
                logger.warn(f"Plugin {info.name} error on {event_name}: {e}")
