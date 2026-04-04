"""
eff_slotter.py — Effect file slotter for Smash Ultimate mods.

Renames effect files to slot-specific names:
  ef_fighter.eff → ef_fighter_cXX.eff
  trail/         → trail_cXX/
  model/subfolder → subfolder_cXX

Also writes the corresponding config.json entries.
"""
import os
import json

from core import logger


def find_all_files(root_path: str) -> list[str]:
    """Recursively find all files under a path."""
    result = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        for f in filenames:
            result.append(os.path.join(dirpath, f))
    return result


def slot_effects(mod_path: str, fighter_name: str, slot: int) -> dict:
    """
    Rename effect files to slot-specific names.

    Args:
        mod_path: Root of the mod folder
        fighter_name: Internal fighter name (e.g., "zelda")
        slot: Target slot number (e.g., 8 for c08)

    Returns:
        dict with "added_files", "renamed", "errors"
    """
    result = {"added_files": [], "renamed": [], "errors": []}
    slot_str = f"c{str(slot).zfill(2)}"

    effect_folder = os.path.join(mod_path, "effect", "fighter", fighter_name)
    if not os.path.isdir(effect_folder):
        result["errors"].append(f"No effect folder found: {effect_folder}")
        return result

    added_files = []

    # 1. Rename .eff file
    eff_file_name = f"ef_{fighter_name}.eff"
    eff_path = os.path.join(effect_folder, eff_file_name)
    if os.path.isfile(eff_path):
        new_name = f"ef_{fighter_name}_{slot_str}.eff"
        new_path = os.path.join(effect_folder, new_name)
        os.rename(eff_path, new_path)
        added_files.append(new_path)
        result["renamed"].append((eff_file_name, new_name))
        logger.info(f"  {eff_file_name} → {new_name}")

    # 2. Rename trail folder
    trail_path = os.path.join(effect_folder, "trail")
    if os.path.isdir(trail_path):
        new_trail_name = f"trail_{slot_str}"
        new_trail_path = os.path.join(effect_folder, new_trail_name)
        os.rename(trail_path, new_trail_path)
        added_files.extend(find_all_files(new_trail_path))
        result["renamed"].append(("trail", new_trail_name))
        logger.info(f"  trail/ → {new_trail_name}/")

    # 3. Rename model subfolders
    model_path = os.path.join(effect_folder, "model")
    if os.path.isdir(model_path):
        # Only rename immediate children, not nested
        for entry in list(os.listdir(model_path)):
            entry_path = os.path.join(model_path, entry)
            if os.path.isdir(entry_path):
                new_name = f"{entry}_{slot_str}"
                new_entry_path = os.path.join(model_path, new_name)
                os.rename(entry_path, new_entry_path)
                added_files.extend(find_all_files(new_entry_path))
                result["renamed"].append((f"model/{entry}", f"model/{new_name}"))
                logger.info(f"  model/{entry}/ → model/{new_name}/")

    result["added_files"] = added_files
    return result


def write_effect_config(mod_path: str, fighter_name: str, slot: int,
                        added_files: list[str]):
    """Write a config.json with new-dir-files entries for the slotted effects."""
    slot_str = f"c{str(slot).zfill(2)}"
    dir_key = f"fighter/{fighter_name}/{slot_str}"

    # Build relative paths
    rel_files = []
    for filepath in added_files:
        rel = os.path.relpath(filepath, mod_path).replace(os.sep, "/")
        rel_files.append(rel)

    config = {
        "new-dir-files": {
            dir_key: rel_files
        }
    }

    cfg_path = os.path.join(mod_path, "config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    logger.success(f"config.json written with {len(rel_files)} effect entries")
    return cfg_path


def run(mod_path: str, fighter_name: str, slot: int) -> dict:
    """
    Main entry point: slot effects and write config.

    Returns dict with results.
    """
    logger.info(f"Slotting effects: {fighter_name} → c{str(slot).zfill(2)}")
    result = slot_effects(mod_path, fighter_name, slot)

    if result["errors"]:
        for e in result["errors"]:
            logger.error(e)
        return result

    if result["added_files"]:
        write_effect_config(mod_path, fighter_name, slot, result["added_files"])
    else:
        logger.warn("No effect files found to rename.")

    return result
