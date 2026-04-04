"""
settings.py — Persistent settings via JSON.
Supports base folder assignment per fighter/group, hashes path, theme, etc.
Seeds default base folder entries for all multi-group fighters on first run.
"""
import json
import os
import sys

# When running as a compiled exe, save settings in %APPDATA%\SmashModManager
# so they survive exe updates or moves.
# When running from source, save in the project root.
if getattr(sys, "frozen", False):
    _APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SmashModManager")
    os.makedirs(_APP_DIR, exist_ok=True)
    _SETTINGS_FILE = os.path.join(_APP_DIR, "settings.json")
else:
    _SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "settings.json")

_DEFAULTS = {
    "last_mod_dir": "",
    "hashes_file": "",
    "base_folders": {},          # {"cloud_c00_ff7": "C:/path", ...}
    "max_slots": 256,
    "theme": "dark",
    "last_batch_dir": "",
    "smart_output_rename": False,
    "split_slots": False,
    "auto_kirby_hat": True,
    "auto_restart_theme": False,
    "base_folders_seeded": False,  # Track if defaults have been seeded
    "version": "4.1.2",
}

_data: dict = {}

_STALE_PREFIXES = (
    "eflame_first_", "eflame_only_",
    "elight_first_", "elight_only_",
)


def _seed_default_base_folders():
    """
    Populate base_folders with all multi-group fighters (empty paths).
    Only runs once on first launch. User-added entries are preserved.
    """
    from core.fighter_db import get_default_base_folder_entries

    defaults = get_default_base_folder_entries()
    bf = _data.get("base_folders", {})

    changed = False

    for k in [k for k in list(bf.keys()) if any(k.startswith(p) for p in _STALE_PREFIXES)]:
        del bf[k]
        changed = True

    for key, val in defaults.items():
        if key not in bf:
            bf[key] = val
            changed = True

    _data["base_folders"] = bf
    if not _data.get("base_folders_seeded"):
        _data["base_folders_seeded"] = True
        changed = True

    if changed:
        save()


def load():
    global _data
    _data = dict(_DEFAULTS)
    if os.path.isfile(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            _data.update(saved)
        except Exception:
            pass

    # Seed defaults and apply any cleanup migrations
    _seed_default_base_folders()


def save():
    try:
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get(key: str, default=None):
    return _data.get(key, default)


def put(key: str, value):
    """Set a value and persist immediately."""
    _data[key] = value
    save()


def get_base_folder(fighter: str, group_key: str) -> str:
    """Retrieve the base folder path for a fighter + group_key combo."""
    key = f"{fighter}_{group_key}"
    return _data.get("base_folders", {}).get(key, "")


def set_base_folder(fighter: str, group_key: str, path: str):
    """Assign a base folder for a fighter + group_key combo."""
    key = f"{fighter}_{group_key}"
    if "base_folders" not in _data:
        _data["base_folders"] = {}
    _data["base_folders"][key] = path
    save()


def set_base_folder_by_key(key: str, path: str):
    """Assign a base folder directly by its full key."""
    if "base_folders" not in _data:
        _data["base_folders"] = {}
    _data["base_folders"][key] = path
    save()


def remove_base_folder(key: str):
    """Remove a base folder entry by its full key."""
    bf = _data.get("base_folders", {})
    if key in bf:
        del bf[key]
        save()


def restore_default_base_folders():
    """
    Re-add all default entries that are missing.
    Does NOT overwrite paths the user already assigned.
    Does NOT remove user-added custom entries.
    """
    _seed_default_base_folders()


load()
