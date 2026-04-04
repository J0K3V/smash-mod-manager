# runtime_hook.py — runs inside the exe before any app code
# Sets the working directory to the exe's folder so relative
# paths (dir_info_with_files_trimmed.json, Hashes_all.txt) still work.
import sys
import os

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
