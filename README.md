# Smash Mod Manager v4

A modular desktop tool for Super Smash Bros. Ultimate modding.
Integrates reslotting, effect slotting, batch validation, missing file completion,
and config generation in one GUI.

## What's New in v4

- **Fighter Database** — Separated `fighter_db.py` with all base model groups, extra parts, display names, and UI aliases. No longer buried inside the GUI code.
- **Improved Effect Slotter** — Integrated with the logging system; no more `sys.exit()` crashes. Returns structured results.
- **Missing File Completion** — Full Python implementation of the Fix.Cmd logic. Handles all model parts (body, clown, tico, arsene, kazooie, etc.), not just body. Auto-detects base folder from saved settings.
- **Batch Validator** — Real implementation: validates folder structure, checks slot consistency across all model parts, detects empty slot folders, warns about missing config.json on extra slots, and can auto-fix slot mismatches.
- **Plugin System** — Drop `.py` files in `plugins/` to extend functionality. Plugins receive events like `on_mod_loaded` and `on_reslot`.
- **File Source Abstraction** — `file_source.py` with local + remote (Synology NAS) placeholder for future expansion.
- **Thread-safe Logger** — Proper locking for concurrent operations.
- **Cleaner Architecture** — GUI widgets extracted to `widgets.py`, theme to `theme.py`, fighter data to `fighter_db.py`.

## Requirements

- Python 3.9+
- No extra pip packages required for core functionality
- Optional: `tkinterdnd2` for drag & drop onto the window

```
pip install tkinterdnd2
```

## Setup

1. Place `Hashes_all.txt` in this folder (download from [archive-hashes](https://github.com/ultimate-research/archive-hashes/blob/master/Hashes_all))
2. The file `dir_info_with_files_trimmed.json` is already included (copy from v3 if needed).

## Run

```
python main.py
```

Or drag a mod folder onto `main.py` / `launch.bat` in Explorer.

## Project Structure

```
smash-mod-manager-v4/
├── main.py                              ← Entry point
├── launch.bat                           ← Windows launcher
├── settings.json                        ← Auto-generated on first run
├── dir_info_with_files_trimmed.json     ← You provide this
├── Hashes_all.txt                       ← You provide this
├── requirements.txt
├── core/
│   ├── __init__.py
│   ├── fighter_db.py                    ← Fighter database (groups, parts, names)
│   ├── reslotter.py                     ← Reslotter (BluJay/Coolsonickirby)
│   ├── eff_slotter.py                   ← Effect slotter (rewritten)
│   ├── mod_analyzer.py                  ← Auto-detect fighter, slots, effects, etc.
│   ├── missing_files.py                 ← Missing file detection + copy
│   ├── batch_validator.py               ← Batch validation + auto-fix
│   ├── plugin_loader.py                 ← Plugin system
│   ├── file_source.py                   ← File source abstraction (local + remote WIP)
│   ├── logger.py                        ← Thread-safe centralized logging
│   └── settings.py                      ← Persistent settings
├── gui/
│   ├── __init__.py
│   ├── app.py                           ← Main window, tabs, log panel
│   ├── theme.py                         ← Colors, fonts, style constants
│   └── widgets.py                       ← Reusable styled widget factories
├── plugins/
│   ├── __init__.py
│   └── example_plugin.py               ← Example plugin
└── logs/                                ← Session logs (auto-created)
```

## Features

### Reslot Tab
- Auto-detects fighter, slots, effects, kirby hat, UI, sound, camera
- Change slots with full config.json generation
- Handles vanilla and extra slots (c08+) with share-to-vanilla/added
- Options: include effects, include kirby hat, new config

### Effects Tab
- Renames `ef_fighter.eff` → `ef_fighter_cXX.eff`
- Renames `trail/` → `trail_cXX/`
- Renames effect model subfolders → `folder_cXX`
- Writes config.json entries
- Shows detected effect details after loading a mod

### Batch Tab
- Validates folder structure for a folder full of mods
- Checks slot consistency across body + extra model parts
- Detects mismatches between folder names and internal slots
- Auto-fix renames mismatched slot folders

### Missing Files Tab
- Detects missing files by comparing mod vs base folder
- Handles all model parts, not just body
- Auto-detects base folder from saved settings
- Copies only missing files — never overwrites existing

### Base Folders Tab
- Assign base folders per fighter + base group (e.g., Cloud FF7 vs AC)
- Dynamic group selector based on fighter name
- Shows which slots each group covers
- Persisted between sessions

### Plugins Tab
- Lists loaded plugins
- Reload button to hot-reload changes
- Open plugins folder button

## Credits

- [BluJay](https://github.com/blu-dev) & [Jozz](https://github.com/jozz024/ssbu-skin-reslotter) — Original reslotter
- [Coolsonickirby](https://github.com/CoolSonicKirby) — Dir addition reslotter modifications
- [ScanMountGoat/ArcExplorer](https://github.com/ScanMountGoat/ArcExplorer) — ARC file structure reference
- [archive-hashes](https://github.com/ultimate-research/archive-hashes) — File path hashes
- Fix.Cmd — Batch missing file copy logic (integrated into Python)
