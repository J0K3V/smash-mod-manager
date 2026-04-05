# smash_mod_manager.spec
# PyInstaller spec for Smash Mod Manager
# Run from the project root:  pyinstaller build/smash_mod_manager.spec

import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), ".."))

# Only bundle data files if they exist next to the project root
_datas = []
for _fname in ("dir_info_with_files_trimmed.json", "Hashes_all.txt"):
    _full = os.path.join(ROOT, _fname)
    if os.path.isfile(_full):
        _datas.append((_full, "."))

# Bundle assets folder (icon, etc.)
_assets = os.path.join(ROOT, "assets")
if os.path.isdir(_assets):
    _datas.append((_assets, "assets"))

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=_datas,
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

_icon = os.path.join(ROOT, "assets", "icon.ico")

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
    icon=_icon if os.path.isfile(_icon) else None,
)
