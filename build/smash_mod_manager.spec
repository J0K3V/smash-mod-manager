# smash_mod_manager.spec
# PyInstaller spec for Smash Mod Manager
# Run from the project root:  pyinstaller build/smash_mod_manager.spec

import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), ".."))

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # Bundle the large data files inside the exe
        (os.path.join(ROOT, "dir_info_with_files_trimmed.json"), "."),
        (os.path.join(ROOT, "Hashes_all.txt"),                  "."),
    ],
    hiddenimports=[
        "core.reslotter",
        "core.mod_analyzer",
        "core.missing_files",
        "core.eff_slotter",
        "core.batch_validator",
        "core.fighter_db",
        "core.file_source",
        "core.base_index",
        "core.plugin_loader",
        "core.settings",
        "core.logger",
        "gui.app",
        "gui.theme",
        "gui.widgets",
    ],
    runtime_hooks=[os.path.join(ROOT, "build", "runtime_hook.py")],
    excludes=["matplotlib", "numpy", "pandas", "PIL", "scipy", "notebook"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SmashModManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no black console window
    onefile=True,
)
