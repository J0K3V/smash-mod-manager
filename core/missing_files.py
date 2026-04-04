"""
missing_files.py — Detects and copies missing files from a base folder or ZIP.

Inspired by Fix.Cmd batch script logic:
- Scans mod's model/body/cXX folder for existing files
- Compares against the base folder or ZIP (vanilla dump)
- Copies only what's missing — never overwrites
- Handles extra model parts (clown, tico, arsene, etc.) not just body

Works with the base folder assignment system so each fighter + base group
has a configured reference folder OR .zip file.
"""
import os
import shutil

from core import logger
from core import fighter_db
from core import settings


def _get_mod_parts(mod_path: str, fighter_name: str) -> list:
    model_dir = os.path.join(mod_path, "fighter", fighter_name, "model")
    parts = []
    if os.path.isdir(model_dir):
        parts = [d for d in os.listdir(model_dir)
                 if os.path.isdir(os.path.join(model_dir, d))]
    if not parts:
        parts = ["body"]
    return parts


# ── ZIP helpers ────────────────────────────────────────────────────────────────

def _is_zip(path: str) -> bool:
    return bool(path) and path.lower().endswith(".zip") and os.path.isfile(path)


def _zip_list_part_files(zip_source, fighter_name: str, part: str, slot: str) -> set[str]:
    """List files for fighter/model/part/slot inside a ZipFileSource."""
    base_path = f"fighter/{fighter_name}/model/{part}/{slot}"
    if not zip_source.is_dir(base_path):
        # Try without fighter prefix (user may have pointed to a generic zip)
        base_path = f"model/{part}/{slot}"
        if not zip_source.is_dir(base_path):
            base_path = f"{part}/{slot}"
            if not zip_source.is_dir(base_path):
                return set()
    return zip_source.list_files_recursive(base_path)


def _zip_copy_file(zip_source, fighter_name: str, part: str, slot: str,
                   rel_file: str, dst: str) -> bool:
    """Try to copy rel_file from a zip source for the given part/slot."""
    for base_path in [
        f"fighter/{fighter_name}/model/{part}/{slot}/{rel_file}",
        f"model/{part}/{slot}/{rel_file}",
        f"{part}/{slot}/{rel_file}",
    ]:
        if zip_source.copy_file(base_path, dst):
            return True
    return False


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_missing(mod_path: str, fighter_name: str, slot: str,
                   base_folder: str) -> dict[str, list[str]]:
    """
    Detect missing files by comparing mod vs base folder (or ZIP).

    Returns dict keyed by model part (e.g., "body", "clown"):
        { "body": ["file1.nutexb", "file2.numdlb"], ... }
    """
    missing = {}

    if not base_folder:
        logger.error("No base folder/ZIP configured.")
        return missing

    use_zip = _is_zip(base_folder)

    if not use_zip and not os.path.isdir(base_folder):
        logger.error(f"Base does not exist: {base_folder}")
        return missing

    # Get all model parts this fighter uses
    parts_in_mod = _get_mod_parts(mod_path, fighter_name)
    model_dir = os.path.join(mod_path, "fighter", fighter_name, "model")

    if use_zip:
        from core.file_source import ZipFileSource
        zs = ZipFileSource(base_folder)
        # Also discover which parts exist in the zip for this fighter
        zip_fighter = zs.detect_fighter() or fighter_name
        zip_parts = zs.detect_model_parts(zip_fighter)
        # Only check parts that exist in both mod and zip
        parts_to_check = [p for p in parts_in_mod if p in zip_parts] or parts_in_mod

        for part in parts_to_check:
            mod_slot_dir = os.path.join(model_dir, part, slot)
            mod_files = set()
            if os.path.isdir(mod_slot_dir):
                mod_files = _list_files_recursive(mod_slot_dir)

            zip_slots = zs.detect_slots(zip_fighter)
            base_slot = zip_slots[0] if zip_slots else slot
            base_files = _zip_list_part_files(zs, zip_fighter, part, base_slot)

            missing_in_part = sorted(base_files - mod_files)
            if missing_in_part:
                missing[part] = missing_in_part

        zs.close()
    else:
        for part in parts_in_mod:
            mod_slot_dir = os.path.join(model_dir, part, slot)

            base_part_dir = _find_base_part(base_folder, part, slot)
            if not base_part_dir:
                base_part_dir = _find_base_part(base_folder, part, None)
            if not base_part_dir:
                continue

            mod_files = set()
            if os.path.isdir(mod_slot_dir):
                mod_files = _list_files_recursive(mod_slot_dir)

            base_files = _list_files_recursive(base_part_dir)

            missing_in_part = sorted(base_files - mod_files)
            if missing_in_part:
                missing[part] = missing_in_part

    return missing


def _find_base_part(base_folder: str, part_name: str, slot: str | None) -> str | None:
    """
    Try to locate the matching part folder inside the base folder.
    Handles various base folder layouts.
    """
    if slot:
        candidate = os.path.join(base_folder, "model", part_name, slot)
        if os.path.isdir(candidate):
            return candidate

    if slot:
        candidate = os.path.join(base_folder, part_name, slot)
        if os.path.isdir(candidate):
            return candidate

    candidate = os.path.join(base_folder, part_name)
    if os.path.isdir(candidate):
        return candidate

    if os.path.isdir(base_folder):
        entries = os.listdir(base_folder)
        if any(f.endswith(('.nutexb', '.numdlb', '.numatb', '.numshb', '.numshexb'))
               for f in entries):
            return base_folder

    return None


def _list_files_recursive(folder: str) -> set[str]:
    """List all files in a folder (relative paths)."""
    files = set()
    for dirpath, dirnames, filenames in os.walk(folder):
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), folder)
            files.add(rel.replace(os.sep, "/"))
    return files


def copy_missing(mod_path: str, fighter_name: str, slot: str,
                 base_folder: str, missing: dict[str, list[str]]) -> dict:
    """
    Copy missing files from base folder or ZIP to mod. Never overwrites.

    Returns {"copied": int, "skipped": int, "errors": []}
    """
    result = {"copied": 0, "skipped": 0, "errors": []}
    model_dir = os.path.join(mod_path, "fighter", fighter_name, "model")
    use_zip = _is_zip(base_folder)

    if use_zip:
        from core.file_source import ZipFileSource
        zs = ZipFileSource(base_folder)
        zip_fighter = zs.detect_fighter() or fighter_name
        zip_slots = zs.detect_slots(zip_fighter)
        base_slot = zip_slots[0] if zip_slots else slot

        for part_name, file_list in missing.items():
            dest_dir = os.path.join(model_dir, part_name, slot)
            os.makedirs(dest_dir, exist_ok=True)

            for rel_file in file_list:
                dst = os.path.join(dest_dir, rel_file.replace("/", os.sep))
                if os.path.isfile(dst):
                    result["skipped"] += 1
                    continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if _zip_copy_file(zs, zip_fighter, part_name, base_slot, rel_file, dst):
                    result["copied"] += 1
                    logger.info(f"  + {part_name}/{rel_file}")
                else:
                    result["errors"].append(f"Not found in ZIP: {part_name}/{rel_file}")

        zs.close()
    else:
        for part_name, file_list in missing.items():
            dest_dir = os.path.join(model_dir, part_name, slot)
            os.makedirs(dest_dir, exist_ok=True)

            base_part_dir = _find_base_part(base_folder, part_name, slot)
            if not base_part_dir:
                base_part_dir = _find_base_part(base_folder, part_name, None)
            if not base_part_dir:
                result["errors"].append(f"Cannot find base for {part_name}")
                continue

            for rel_file in file_list:
                src = os.path.join(base_part_dir, rel_file.replace("/", os.sep))
                dst = os.path.join(dest_dir, rel_file.replace("/", os.sep))

                if os.path.isfile(dst):
                    result["skipped"] += 1
                    continue

                if not os.path.isfile(src):
                    result["errors"].append(f"Source not found: {rel_file}")
                    continue

                try:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    result["copied"] += 1
                    logger.info(f"  + {part_name}/{rel_file}")
                except Exception as e:
                    result["errors"].append(f"Copy failed {rel_file}: {e}")

    return result


def auto_detect_base_folder(fighter_name: str, slot: str) -> str:
    """
    Try to auto-detect the correct base folder/ZIP from saved settings
    using the fighter's base group for the given slot.
    """
    slot_num = fighter_db.slot_num(slot)
    group = fighter_db.get_group_for_slot(fighter_name, slot_num)
    path = settings.get_base_folder(fighter_name, group["key"])
    if path and (os.path.isdir(path) or _is_zip(path)):
        return path

    # Fallback to default c00 group
    path = settings.get_base_folder(fighter_name, "c00")
    if path and (os.path.isdir(path) or _is_zip(path)):
        return path

    return ""


def detect_missing_indexed(mod_path: str, fighter_name: str, slot: str) -> dict:
    from core import base_index
    from core.file_source import ZipFileSource, LocalFileSource

    parts_in_mod = _get_mod_parts(mod_path, fighter_name)
    model_dir = os.path.join(mod_path, "fighter", fighter_name, "model")

    missing = {}
    _zip_cache = {}

    for part in parts_in_mod:
        source = base_index.find_slot(fighter_name, part, slot)
        if source is None:
            continue

        mod_slot_dir = os.path.join(model_dir, part, slot)
        mod_files = _list_files_recursive(mod_slot_dir) if os.path.isdir(mod_slot_dir) else set()

        if source["type"] == "dir":
            base_files = LocalFileSource(source["path"]).list_files_recursive("")
        elif source["type"] == "zip":
            zp = source["zip"]
            if zp not in _zip_cache:
                _zip_cache[zp] = ZipFileSource(zp)
            base_files = _zip_cache[zp].list_files_recursive(source["internal"])
        else:
            continue

        missing_in_part = sorted(base_files - mod_files)
        if missing_in_part:
            missing[part] = missing_in_part

    for zs in _zip_cache.values():
        zs.close()
    return missing


def copy_missing_indexed(mod_path: str, fighter_name: str, slot: str,
                         missing: dict) -> dict:
    from core import base_index
    from core.file_source import ZipFileSource, LocalFileSource

    result = {"copied": 0, "skipped": 0, "errors": []}
    model_dir = os.path.join(mod_path, "fighter", fighter_name, "model")
    _zip_cache = {}

    for part_name, file_list in missing.items():
        source = base_index.find_slot(fighter_name, part_name, slot)
        if source is None:
            result["errors"].append(f"No base for {part_name}")
            continue

        dest_dir = os.path.join(model_dir, part_name, slot)
        os.makedirs(dest_dir, exist_ok=True)

        if source["type"] == "zip":
            zp = source["zip"]
            if zp not in _zip_cache:
                _zip_cache[zp] = ZipFileSource(zp)
            fs = _zip_cache[zp]
        elif source["type"] == "dir":
            fs = LocalFileSource(source["path"])
        else:
            continue

        for rel_file in file_list:
            dst = os.path.join(dest_dir, rel_file.replace("/", os.sep))
            if os.path.isfile(dst):
                result["skipped"] += 1
                continue
            parent = os.path.dirname(dst)
            if parent != dest_dir:
                os.makedirs(parent, exist_ok=True)
            if source["type"] == "zip":
                ok = fs.copy_file(f"{source['internal']}/{rel_file}", dst)
            else:
                ok = fs.copy_file(rel_file, dst)
            if ok:
                result["copied"] += 1
                logger.info(f"  + {part_name}/{rel_file}")
            else:
                result["errors"].append(f"Not found: {part_name}/{rel_file}")

    for zs in _zip_cache.values():
        zs.close()
    return result
