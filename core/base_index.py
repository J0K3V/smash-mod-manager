"""
base_index.py — Scans a source folder to build a cached map of fighter model paths.
Handles extracted dump folders and ZIP files. Index is cached in AppData.
"""
import os
import re
import json
import sys
from datetime import datetime

from core import logger

if getattr(sys, "frozen", False):
    _APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SmashModManager")
else:
    _APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "appdata")

os.makedirs(_APP_DIR, exist_ok=True)
_INDEX_FILE = os.path.join(_APP_DIR, "base_index.json")

_SLOT_RE = re.compile(r'^c\d{2,3}$')

_index: dict = {}     # fighters[name][part][slot] = {type, path/zip/internal}
_source_root: str = ""
_scan_time: str = ""


def _record(fighter: str, part: str, slot: str, source: dict):
    _index.setdefault(fighter, {}).setdefault(part, {})[slot] = source


def _scan_dir_for_fighters(root: str, progress_cb=None):
    """Find fighter/*/model/*/cXX/ directories under root (non-recursive, targeted)."""
    fighter_dir = os.path.join(root, "fighter")
    if not os.path.isdir(fighter_dir):
        return
    try:
        for fighter_name in os.listdir(fighter_dir):
            model_dir = os.path.join(fighter_dir, fighter_name, "model")
            if not os.path.isdir(model_dir):
                continue
            for part_name in os.listdir(model_dir):
                part_dir = os.path.join(model_dir, part_name)
                if not os.path.isdir(part_dir):
                    continue
                for slot_name in os.listdir(part_dir):
                    if _SLOT_RE.match(slot_name):
                        slot_dir = os.path.join(part_dir, slot_name)
                        if os.path.isdir(slot_dir):
                            _record(fighter_name, part_name, slot_name,
                                    {"type": "dir", "path": slot_dir})
                            if progress_cb:
                                progress_cb(f"{fighter_name}/{part_name}/{slot_name}")
    except PermissionError:
        pass


def _scan_zip(zip_path: str, progress_cb=None):
    from core.file_source import ZipFileSource
    try:
        zs = ZipFileSource(zip_path)
        for fighter_name in zs.list_dir("fighter"):
            for part_name in zs.list_dir(f"fighter/{fighter_name}/model"):
                if not zs.is_dir(f"fighter/{fighter_name}/model/{part_name}"):
                    continue
                base = f"fighter/{fighter_name}/model/{part_name}"
                for slot_name in zs.list_dir(base):
                    if _SLOT_RE.match(slot_name) and zs.is_dir(f"{base}/{slot_name}"):
                        _record(fighter_name, part_name, slot_name, {
                            "type": "zip",
                            "zip": zip_path,
                            "internal": f"{base}/{slot_name}",
                        })
                        if progress_cb:
                            progress_cb(f"{fighter_name}/{part_name}/{slot_name} [ZIP]")
        zs.close()
    except Exception:
        pass


def _scan_zips_in(folder: str, progress_cb=None):
    """Scan all ZIP files directly inside folder."""
    try:
        for entry in os.scandir(folder):
            if entry.is_file() and entry.name.lower().endswith(".zip"):
                _scan_zip(entry.path, progress_cb)
    except PermissionError:
        pass


def scan(root: str, progress_cb=None) -> int:
    """
    Scan root folder. Searches for fighter paths in:
    - root/fighter/*/model/*/cXX/
    - root/*/fighter/*/model/*/cXX/  (one level of subdirs)
    - root/*.zip  and  root/*/*.zip  (ZIPs at root and one level deep)
    Returns number of entries recorded.
    """
    global _index, _source_root, _scan_time
    _index = {}

    logger.info(f"Scanning: {root}")

    _scan_dir_for_fighters(root, progress_cb)

    try:
        for entry in os.scandir(root):
            if entry.is_dir():
                _scan_dir_for_fighters(entry.path, progress_cb)
                _scan_zips_in(entry.path, progress_cb)
    except PermissionError:
        pass

    _scan_zips_in(root, progress_cb)

    _source_root = root
    _scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    total = sum(len(slots) for parts in _index.values() for slots in parts.values())
    logger.success(f"Scan done: {total} slot entries, {len(_index)} fighters")
    _save()
    return total


def _save():
    data = {
        "source_root": _source_root,
        "scan_time": _scan_time,
        "fighters": _index,
    }
    try:
        with open(_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warn(f"Could not save base index: {e}")


def load() -> bool:
    global _index, _source_root, _scan_time
    if _index:
        return True
    if not os.path.isfile(_INDEX_FILE):
        return False
    try:
        with open(_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _index = data.get("fighters", {})
        _source_root = data.get("source_root", "")
        _scan_time = data.get("scan_time", "")
        return True
    except Exception:
        return False


def get_source_root() -> str:
    return _source_root


def get_scan_time() -> str:
    return _scan_time


def is_loaded() -> bool:
    return bool(_index)


def find_slot(fighter: str, part: str, slot: str):
    """
    Find the best source for fighter/part/slot.
    Exact slot match first; falls back to first available slot.
    Returns source dict or None.
    """
    if not _index:
        load()
    part_data = _index.get(fighter, {}).get(part)
    if not part_data:
        return None
    if slot in part_data:
        return part_data[slot]
    # Fallback: first available slot
    first = sorted(part_data.keys())[0]
    return part_data[first]


def list_files_in_source(source: dict) -> set:
    from core.file_source import ZipFileSource, LocalFileSource
    if source["type"] == "dir":
        return LocalFileSource(source["path"]).list_files_recursive("")
    if source["type"] == "zip":
        zs = ZipFileSource(source["zip"])
        files = zs.list_files_recursive(source["internal"])
        zs.close()
        return files
    return set()


def copy_from_source(source: dict, rel_file: str, dst: str) -> bool:
    from core.file_source import ZipFileSource, LocalFileSource
    if source["type"] == "dir":
        return LocalFileSource(source["path"]).copy_file(rel_file, dst)
    if source["type"] == "zip":
        zs = ZipFileSource(source["zip"])
        ok = zs.copy_file(f"{source['internal']}/{rel_file}", dst)
        zs.close()
        return ok
    return False


def get_indexed_fighters() -> list:
    if not _index:
        load()
    return sorted(_index.keys())


def get_fighter_parts(fighter: str) -> list:
    if not _index:
        load()
    return sorted(_index.get(fighter, {}).keys())
