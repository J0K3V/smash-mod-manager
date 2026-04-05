"""
Smash Mod Manager v4 — Entry point.
Run:    python main.py
With:   python main.py "path/to/mod"
Or drag a mod folder onto this script.
"""
import sys
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def main():
    initial_path = ""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if os.path.isdir(arg):
            initial_path = arg

    # Apply theme before building the GUI so all constants are correct
    import core.settings as settings
    from gui.theme import apply_theme
    apply_theme(
        settings.get("theme", "Dark"),
        settings.get("font_size", 11),
    )

    # Try tkinterdnd2 first for drag-and-drop support
    root = None
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        import tkinter as tk
        root = tk.Tk()

    from gui.app import ModManagerApp
    app = ModManagerApp(root, initial_path=initial_path)

    # Window icon — works both from source and PyInstaller onefile bundle
    _icon = os.path.join(_ROOT, "assets", "icon.ico")
    if not os.path.isfile(_icon):
        try:
            _icon = os.path.join(sys._MEIPASS, "assets", "icon.ico")
        except AttributeError:
            _icon = ""
    if _icon and os.path.isfile(_icon):
        try:
            root.iconbitmap(_icon)
        except Exception:
            pass

    root.mainloop()


if __name__ == "__main__":
    main()
