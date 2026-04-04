"""
mod_analyzer.py — Auto-detects fighter name, slots, effects, kirby hats,
UI files, sound files, extra model parts from a mod folder.
Returns a structured analysis dict.
"""
import os
import re
import json

from core import fighter_db
from core import logger


def detect_fighter(mod_path: str) -> str | None:
    """Detect the fighter name from fighter/ subfolder."""
    fighter_dir = os.path.join(mod_path, "fighter")
    if os.path.isdir(fighter_dir):
        for name in sorted(os.listdir(fighter_dir)):
            full = os.path.join(fighter_dir, name)
            if os.path.isdir(full) and name != "kirby":
                return name
        # If only kirby is there, still return it
        for name in os.listdir(fighter_dir):
            if os.path.isdir(os.path.join(fighter_dir, name)):
                return name
    # Fallback: scan effect/fighter/
    eff_dir = os.path.join(mod_path, "effect", "fighter")
    if os.path.isdir(eff_dir):
        for name in os.listdir(eff_dir):
            if os.path.isdir(os.path.join(eff_dir, name)):
                return name
    return None


def detect_slots(mod_path: str, fighter_name: str) -> list[str]:
    """Return sorted list of slot folders found (c00, c01, ...)."""
    slots = set()

    # Scan fighter/{name}/model/body/cXX
    body_dir = os.path.join(mod_path, "fighter", fighter_name, "model", "body")
    if os.path.isdir(body_dir):
        for entry in os.listdir(body_dir):
            if re.match(r'^c\d{2,3}$', entry):
                slots.add(entry)

    # Scan extra model parts too
    model_dir = os.path.join(mod_path, "fighter", fighter_name, "model")
    if os.path.isdir(model_dir):
        for part_name in os.listdir(model_dir):
            part_path = os.path.join(model_dir, part_name)
            if os.path.isdir(part_path):
                for entry in os.listdir(part_path):
                    if re.match(r'^c\d{2,3}$', entry):
                        slots.add(entry)

    # Also check top-level fighter/{name}/cXX
    fighter_root = os.path.join(mod_path, "fighter", fighter_name)
    if os.path.isdir(fighter_root):
        for entry in os.listdir(fighter_root):
            if re.match(r'^c\d{2,3}$', entry):
                slots.add(entry)

    return sorted(slots)


def detect_model_parts(mod_path: str, fighter_name: str) -> list[str]:
    """Return list of model part folder names (body, cape, tico, etc.)."""
    parts = []
    model_dir = os.path.join(mod_path, "fighter", fighter_name, "model")
    if os.path.isdir(model_dir):
        for entry in sorted(os.listdir(model_dir)):
            if os.path.isdir(os.path.join(model_dir, entry)):
                parts.append(entry)
    return parts


def has_effects(mod_path: str, fighter_name: str) -> bool:
    eff_dir = os.path.join(mod_path, "effect", "fighter", fighter_name)
    return os.path.isdir(eff_dir)


def detect_effect_details(mod_path: str, fighter_name: str) -> dict:
    """Detect .eff files, trail folders, effect model folders."""
    result = {"eff_files": [], "trails": [], "models": [], "is_slotted": False}
    eff_dir = os.path.join(mod_path, "effect", "fighter", fighter_name)
    if not os.path.isdir(eff_dir):
        return result

    for entry in os.listdir(eff_dir):
        full = os.path.join(eff_dir, entry)
        if entry.endswith(".eff"):
            result["eff_files"].append(entry)
            # Check if already slotted (contains _cXX)
            if re.search(r'_c\d{2}\.eff$', entry):
                result["is_slotted"] = True
        elif os.path.isdir(full) and entry.startswith("trail"):
            result["trails"].append(entry)
            if re.search(r'_c\d{2}$', entry):
                result["is_slotted"] = True
        elif os.path.isdir(full) and entry == "model":
            for sub in os.listdir(full):
                if os.path.isdir(os.path.join(full, sub)):
                    result["models"].append(sub)

    return result


def has_kirby_hat(mod_path: str, fighter_name: str) -> bool:
    kirby_model = os.path.join(mod_path, "fighter", "kirby", "model")
    if not os.path.isdir(kirby_model):
        return False
    for root, dirs, files in os.walk(kirby_model):
        for d in dirs:
            if f"copy_{fighter_name}_cap" in d:
                return True
    return False


def detect_kirby_hat_slots(mod_path: str, fighter_name: str) -> list[str]:
    """Return slot names found in kirby copy hat folders."""
    slots = set()
    kirby_model = os.path.join(mod_path, "fighter", "kirby", "model")
    if not os.path.isdir(kirby_model):
        return []
    for root, dirs, files in os.walk(kirby_model):
        for d in dirs:
            if f"copy_{fighter_name}_cap" in d:
                cap_path = os.path.join(root, d)
                for entry in os.listdir(cap_path):
                    if re.match(r'^c\d{2,3}$', entry):
                        slots.add(entry)
    return sorted(slots)


def has_ui(mod_path: str) -> bool:
    return os.path.isdir(os.path.join(mod_path, "ui"))


def has_sound(mod_path: str, fighter_name: str) -> bool:
    for subdir in ["sound/bank/fighter", "sound/bank/fighter_voice"]:
        sound_dir = os.path.join(mod_path, *subdir.split("/"))
        if os.path.isdir(sound_dir):
            for f in os.listdir(sound_dir):
                if fighter_name in f:
                    return True
    return False


def has_camera(mod_path: str, fighter_name: str) -> bool:
    cam = os.path.join(mod_path, "camera", "fighter", fighter_name)
    return os.path.isdir(cam)


def load_existing_config(mod_path: str) -> dict | None:
    cfg_path = os.path.join(mod_path, "config.json")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def analyze(mod_path: str) -> dict:
    """Full analysis of a mod folder. Returns structured dict."""
    result = {
        "path": mod_path,
        "folder_name": os.path.basename(mod_path),
        "fighter": None,
        "display_name": "",
        "slots": [],
        "model_parts": [],
        "has_effects": False,
        "effect_details": {},
        "has_kirby_hat": False,
        "kirby_hat_slots": [],
        "has_ui": False,
        "has_sound": False,
        "has_camera": False,
        "existing_config": None,
        "is_extra_slot": False,
        "base_group": None,
        "errors": [],
    }

    if not os.path.isdir(mod_path):
        result["errors"].append(f"Path does not exist: {mod_path}")
        return result

    fighter = detect_fighter(mod_path)
    if not fighter:
        result["errors"].append("Could not detect fighter name from folder structure.")
        return result

    result["fighter"] = fighter
    result["display_name"] = fighter_db.get_display_name(fighter)
    result["slots"] = detect_slots(mod_path, fighter)
    result["model_parts"] = detect_model_parts(mod_path, fighter)
    result["has_effects"] = has_effects(mod_path, fighter)
    result["effect_details"] = detect_effect_details(mod_path, fighter)
    result["has_kirby_hat"] = has_kirby_hat(mod_path, fighter)
    result["kirby_hat_slots"] = detect_kirby_hat_slots(mod_path, fighter)
    result["has_ui"] = has_ui(mod_path)
    result["has_sound"] = has_sound(mod_path, fighter)
    result["has_camera"] = has_camera(mod_path, fighter)
    result["existing_config"] = load_existing_config(mod_path)

    # Determine extra slot status and base group
    for slot in result["slots"]:
        num = fighter_db.slot_num(slot)
        if num >= 8:
            result["is_extra_slot"] = True
            break

    if result["slots"]:
        first_slot_num = fighter_db.slot_num(result["slots"][0])
        result["base_group"] = fighter_db.get_group_for_slot(fighter, first_slot_num)

    return result
