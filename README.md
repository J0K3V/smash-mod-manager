# Smash Mod Manager

A modular desktop application for managing Super Smash Bros. Ultimate mods on Windows.
Handles reslotting, effect slotting, batch validation, missing file completion, and
`ui_chara_db.prcxml` slot management — all in one GUI, no command line required.

> **Based on [C-Shard's reslotter](https://github.com/CoolSonicKirby)** — this tool
> extends and wraps that foundation with a full GUI and additional automation features.

---

## Download

Grab the latest release from the [Releases](https://github.com/J0K3V/smash-mod-manager/releases) page.
No Python installation required — just run `SmashModManager.exe`.

---

## What It Does

### Reslot Tab
Auto-detects the fighter, slots, effects, Kirby hat, UI, sound, and camera data inside a mod folder.
Change the target slot and generate a full `config.json` in one click.
Handles vanilla slots (c00–c07) and extra slots (c08+) with share-to-vanilla / added-slot logic.

### Effects Tab
Renames effect files and folders to match a target slot:
- `ef_fighter.eff` → `ef_fighter_cXX.eff`
- `trail/` → `trail_cXX/`
- Effect model subfolders → `folder_cXX`

Writes the corresponding `config.json` entries automatically.

### Batch Tab
Validates an entire folder of mods at once:
- Checks folder structure and slot consistency across all model parts
- Detects mismatches between folder names and internal slot folders
- Auto-fix mode renames mismatched slot folders

### Missing Files Tab
Compares a mod against its base game folder and copies only the files that are missing.
Supports all model parts (body, clown, tico, arsene, kazooie, wing, etc.).
Never overwrites files that already exist in the mod.

### Base Folders Tab
Assign base game folders per fighter and base group (e.g., Cloud FF7 vs AC costume sets).
The group selector updates dynamically based on the selected fighter.
Settings are saved between sessions.

### PRCXML Validator *(plugin)*
Scans a folder of mods and compares detected fighter slots against `ui_chara_db.prcxml`.
- Detects slots missing from the PRCXML and adds them
- Detects over-provisioned `color_num` values and corrects them to match the actual mod count
- Re-validates automatically after applying fixes so you can confirm everything is correct

### Plugins Tab
Drop `.py` files into the `plugins/` folder to extend the app.
Use the Reload button to hot-reload changes without restarting.

---

## Requirements (running from source)

- Python 3.10+
- No extra pip packages required for core functionality
- Optional: `tkinterdnd2` for drag-and-drop support

```
pip install tkinterdnd2
```

You also need to provide these two files in the app folder (not included due to size):

| File | Where to get it |
|---|---|
| `Hashes_all.txt` | [archive-hashes](https://github.com/ultimate-research/archive-hashes/blob/master/Hashes_all) |
| `dir_info_with_files_trimmed.json` | Carry over from a previous install or generate with ArcExplorer |

---

## Running from Source

```
python main.py
```

Or drag a mod folder onto `launch.bat` in Explorer.

---

## Project Structure

```
smash-mod-manager/
├── main.py                          ← Entry point
├── launch.bat                       ← Windows launcher
├── core/
│   ├── fighter_db.py                ← Fighter database (groups, parts, display names)
│   ├── reslotter.py                 ← Core reslot logic
│   ├── eff_slotter.py               ← Effect slotter
│   ├── mod_analyzer.py              ← Auto-detect fighter, slots, effects, etc.
│   ├── missing_files.py             ← Missing file detection + copy
│   ├── batch_validator.py           ← Batch validation + auto-fix
│   ├── plugin_loader.py             ← Plugin loader
│   ├── logger.py                    ← Thread-safe centralized logging
│   └── settings.py                  ← Persistent settings
├── gui/
│   ├── app.py                       ← Main window, tabs, log panel
│   ├── theme.py                     ← Colors, fonts, style constants
│   └── widgets.py                   ← Reusable styled widget factories
├── plugins/                         ← Drop .py plugins here
└── assets/
    └── icon.ico
```

---

## Credits

- [C-Shard / CoolSonicKirby](https://github.com/CoolSonicKirby) — Reslotter this tool is based on
- [BluJay](https://github.com/blu-dev) & [Jozz](https://github.com/jozz024/ssbu-skin-reslotter) — Original reslotter
- [ScanMountGoat / ArcExplorer](https://github.com/ScanMountGoat/ArcExplorer) — ARC file structure reference
- [archive-hashes](https://github.com/ultimate-research/archive-hashes) — File path hashes

---

## License

MIT — see [LICENSE](LICENSE).
