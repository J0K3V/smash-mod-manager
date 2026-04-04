@echo off
:: ─────────────────────────────────────────────────────────────────────
::  Smash Mod Manager — build script
::  Run this from the project root or double-click it.
::  Output: build\dist\SmashModManager.exe
:: ─────────────────────────────────────────────────────────────────────

cd /d "%~dp0.."

echo Installing PyInstaller if needed...
pip install pyinstaller --quiet

echo.
echo Building exe...
python -m PyInstaller build\smash_mod_manager.spec --distpath build\dist --workpath build\work --noconfirm

echo.
if exist "build\dist\SmashModManager.exe" (
    echo  Done.  build\dist\SmashModManager.exe
) else (
    echo  Build failed — check output above.
)
pause
