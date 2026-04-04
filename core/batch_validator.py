"""
batch_validator.py — Batch validation and slot fixing for folders of mods.

Scans a folder full of mods and for each one:
1. Validates folder structure (fighter/name/model/body/cXX)
2. Checks if internal slot numbers match the mod folder name
3. Reports issues and can auto-rename/reslot mismatches
4. Handles extra model parts (not just body)
"""
import os
import re
import shutil

from core import logger
from core import mod_analyzer
from core import fighter_db


class ValidationResult:
    """Result for a single mod's validation."""
    __slots__ = ("mod_name", "mod_path", "fighter", "slots", "status",
                 "issues", "can_fix")

    STATUS_OK = "ok"
    STATUS_WARN = "warn"
    STATUS_ERROR = "error"

    def __init__(self, mod_name: str, mod_path: str):
        self.mod_name = mod_name
        self.mod_path = mod_path
        self.fighter = None
        self.slots = []
        self.status = self.STATUS_OK
        self.issues = []
        self.can_fix = False

    def add_issue(self, msg: str, level: str = "warn"):
        self.issues.append({"msg": msg, "level": level})
        if level == "error":
            self.status = self.STATUS_ERROR
        elif level == "warn" and self.status != self.STATUS_ERROR:
            self.status = self.STATUS_WARN

    def summary(self) -> str:
        if self.status == self.STATUS_OK:
            info = f"{self.fighter} {', '.join(self.slots)}" if self.fighter else "?"
            return f"✓  {self.mod_name}  ({info})"
        elif self.status == self.STATUS_WARN:
            return f"⚠  {self.mod_name}  —  {self.issues[0]['msg']}"
        else:
            return f"✗  {self.mod_name}  —  {self.issues[0]['msg']}"


def validate_mod(mod_path: str) -> ValidationResult:
    """Validate a single mod's folder structure."""
    mod_name = os.path.basename(mod_path)
    r = ValidationResult(mod_name, mod_path)

    analysis = mod_analyzer.analyze(mod_path)

    if analysis["errors"]:
        r.add_issue(analysis["errors"][0], "error")
        return r

    r.fighter = analysis["fighter"]
    r.slots = analysis["slots"]

    # Check if the mod folder name implies a specific slot
    folder_slot_match = re.search(r'c\d{2,3}', mod_name)
    if folder_slot_match and analysis["slots"]:
        expected_slot = folder_slot_match.group()
        # Check that the mod actually contains that slot
        if expected_slot not in analysis["slots"]:
            r.add_issue(
                f"Folder name implies {expected_slot} but found slots: {', '.join(analysis['slots'])}",
                "warn"
            )
            r.can_fix = True

    # Check model parts consistency
    model_dir = os.path.join(mod_path, "fighter", r.fighter, "model")
    if os.path.isdir(model_dir):
        for part in os.listdir(model_dir):
            part_path = os.path.join(model_dir, part)
            if not os.path.isdir(part_path):
                continue
            part_slots = set()
            for entry in os.listdir(part_path):
                if re.match(r'^c\d{2,3}$', entry):
                    part_slots.add(entry)
            # All parts should have the same slots
            if part_slots and part_slots != set(analysis["slots"]):
                r.add_issue(
                    f"model/{part} has slots {sorted(part_slots)} vs body {analysis['slots']}",
                    "warn"
                )

    # Check for empty slot folders
    for slot in analysis["slots"]:
        body_slot = os.path.join(mod_path, "fighter", r.fighter, "model", "body", slot)
        if os.path.isdir(body_slot) and not os.listdir(body_slot):
            r.add_issue(f"Empty slot folder: model/body/{slot}", "warn")

    # Check config.json presence for extra slots
    if analysis["is_extra_slot"] and not analysis["existing_config"]:
        r.add_issue("Extra slot (c08+) without config.json", "warn")

    return r


def validate_batch(mods_folder: str,
                   progress_callback=None) -> list[ValidationResult]:
    """
    Validate all mods in a folder.

    Args:
        mods_folder: Path containing mod subfolders
        progress_callback: Optional callable(current, total, mod_name)
    """
    results = []
    entries = sorted([
        e for e in os.listdir(mods_folder)
        if os.path.isdir(os.path.join(mods_folder, e))
    ])
    total = len(entries)

    for i, mod_name in enumerate(entries):
        mod_path = os.path.join(mods_folder, mod_name)
        if progress_callback:
            progress_callback(i + 1, total, mod_name)

        r = validate_mod(mod_path)
        results.append(r)
        logger.info(r.summary())

    # Summary
    ok = sum(1 for r in results if r.status == ValidationResult.STATUS_OK)
    warns = sum(1 for r in results if r.status == ValidationResult.STATUS_WARN)
    errors = sum(1 for r in results if r.status == ValidationResult.STATUS_ERROR)
    logger.success(f"Batch done: {ok} OK, {warns} warnings, {errors} errors out of {total}")

    return results


def fix_slot_mismatch(mod_path: str, fighter_name: str,
                      current_slot: str, target_slot: str) -> bool:
    """
    Rename internal slot folders from current_slot to target_slot.
    Handles body + all extra model parts.
    """
    try:
        model_dir = os.path.join(mod_path, "fighter", fighter_name, "model")
        if not os.path.isdir(model_dir):
            return False

        renamed = 0
        for part in os.listdir(model_dir):
            part_path = os.path.join(model_dir, part)
            if not os.path.isdir(part_path):
                continue

            old_slot_path = os.path.join(part_path, current_slot)
            new_slot_path = os.path.join(part_path, target_slot)

            if os.path.isdir(old_slot_path) and not os.path.exists(new_slot_path):
                os.rename(old_slot_path, new_slot_path)
                logger.info(f"  Renamed model/{part}/{current_slot} → {target_slot}")
                renamed += 1

        return renamed > 0

    except Exception as e:
        logger.error(f"Fix failed: {e}")
        return False
