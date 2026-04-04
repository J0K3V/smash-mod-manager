"""
example_plugin.py — Example plugin for Smash Mod Manager.

Shows how to create a plugin that reacts to events.
Place this file in the plugins/ folder.
"""

PLUGIN_NAME = "Example Logger"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Logs extra info when a mod is loaded"

_app = None


def register(app):
    """Called when the plugin is loaded."""
    global _app
    _app = app


def on_mod_loaded(analysis: dict):
    """Called whenever a mod folder is analyzed."""
    import core.logger as logger
    fighter = analysis.get("fighter", "?")
    slots = analysis.get("slots", [])
    parts = analysis.get("model_parts", [])
    logger.debug(f"[ExamplePlugin] {fighter}: {len(slots)} slots, parts={parts}")


def on_reslot(mod_path: str, fighter: str, src: str, tgt: str):
    """Called after a reslot operation completes."""
    import core.logger as logger
    logger.debug(f"[ExamplePlugin] Reslot complete: {fighter} {src}→{tgt}")
