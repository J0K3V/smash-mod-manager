"""
mod_list_generator.py — Generate a list of mod folders from a directory.

Scans a mods folder and creates a text file listing all mod folders.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading

PLUGIN_NAME = "Mod List Generator"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Generate a list of mod folders to a text file"

_app = None

try:
    from gui import theme as app_theme
except Exception:
    app_theme = None

try:
    from core import settings as app_settings
except Exception:
    app_settings = None


def register(app):
    """Called when plugin is loaded. Receives the app instance."""
    global _app
    _app = app


def show_mod_list_dialog():
    """Show the Mod List Generator UI."""
    if not _app:
        print("Error: App instance not available")
        return

    dialog = tk.Toplevel(_app.root)
    dialog.title("Mod List Generator")
    dialog.geometry("700x600")
    dialog.configure(bg=(app_theme.BG if app_theme else "#1a1a1a"))
    dialog.minsize(600, 500)
    dialog.resizable(True, True)
    dialog.transient(_app.root)
    dialog.grab_set()
    dialog.focus_force()

    BG = app_theme.BG if app_theme else "#1a1a1a"
    BG2 = app_theme.BG2 if app_theme else "#202028"
    BG3 = app_theme.BG3 if app_theme else "#2a2a2a"
    ACCENT = app_theme.ACCENT if app_theme else "#ffa500"
    TEXT = app_theme.TEXT if app_theme else "#ffffff"
    TEXT_DIM = app_theme.TEXT_DIM if app_theme else "#888888"
    BORDER = app_theme.BORDER if app_theme else "#3a3a3a"
    FONT_UI = app_theme.FONT_UI if app_theme else ("Segoe UI", 10)
    FONT_SMALL = app_theme.FONT_SMALL if app_theme else ("Segoe UI", 9)
    FONT_HEADER = app_theme.FONT_HEADER if app_theme else ("Segoe UI", 14, "bold")

    tk.Label(
        dialog, text="Mod List Generator", bg=BG, fg=ACCENT,
        font=FONT_HEADER
    ).pack(pady=10)

    mods_folder = tk.StringVar(value=(app_settings.get("mod_list_last_mods_folder", "") if app_settings else ""))

    def _persist_setting(key: str, value: str):
        if app_settings is not None:
            app_settings.put(key, value)

    def _label_text(path: str) -> str:
        if not path:
            return "(not selected)"
        base = os.path.basename(path)
        return base if base else path

    def _ensure_dialog_front():
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()

    frame1 = tk.Frame(dialog, bg=BG)
    frame1.pack(fill="x", padx=15, pady=10)
    tk.Label(frame1, text="Mods Folder:", bg=BG, fg=TEXT, font=FONT_UI).pack(anchor="w")
    mods_label = tk.Label(frame1, text=_label_text(mods_folder.get()), bg=BG, fg=TEXT_DIM, font=FONT_SMALL)
    mods_label.pack(anchor="w", padx=(0, 5))

    def select_mods():
        path = filedialog.askdirectory(parent=dialog, title="Select folder with mods")
        _ensure_dialog_front()
        if path:
            mods_folder.set(path)
            _persist_setting("mod_list_last_mods_folder", path)
            mods_label.config(text=_label_text(path))

    tk.Button(
        frame1, text="Browse...", command=select_mods, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=10, pady=4, cursor="hand2"
    ).pack(anchor="w", pady=(5, 0))

    info_frame = tk.Frame(dialog, bg=BG)
    info_frame.pack(fill="x", padx=15, pady=10)
    tk.Label(
        info_frame,
        text="Scans the selected folder and generates a list of all mod folders.",
        bg=BG, fg=TEXT_DIM, font=FONT_SMALL, justify="left", anchor="w"
    ).pack(fill="x")

    def generate():
        if not mods_folder.get():
            messagebox.showerror("Error", "Please select a mods folder", parent=dialog)
            return

        progress_win = tk.Toplevel(dialog)
        progress_win.title("Generating List")
        progress_win.geometry("600x350")
        progress_win.configure(bg=BG)
        progress_win.resizable(True, True)
        progress_win.transient(dialog)
        progress_win.grab_set()

        state = {
            "events": [],
            "events_lock": threading.Lock(),
            "done": False,
            "result": None,
            "cancel": threading.Event(),
        }

        progress_var = tk.DoubleVar(value=0.0)
        progress_text = tk.StringVar(value="0 mods found")
        status_text = tk.StringVar(value="Scanning...")

        tk.Label(progress_win, text="Generating Mod List", bg=BG, fg=ACCENT, font=FONT_HEADER).pack(
            anchor="w", padx=12, pady=(10, 4)
        )
        tk.Label(progress_win, textvariable=progress_text, bg=BG, fg=TEXT, font=FONT_UI).pack(
            anchor="w", padx=12
        )
        ttk.Progressbar(
            progress_win,
            mode="indeterminate",
            length=500,
        ).pack(anchor="w", padx=12, pady=(8, 6))
        tk.Label(
            progress_win,
            textvariable=status_text,
            bg=BG,
            fg=TEXT_DIM,
            font=FONT_SMALL,
            justify="left",
            anchor="w",
            wraplength=500,
        ).pack(fill="x", padx=12)

        list_text = tk.Text(
            progress_win,
            bg=BG2,
            fg=TEXT,
            insertbackground=TEXT,
            font=(app_theme.FONT_MONO if app_theme else ("Consolas", 9)),
            relief="flat",
            bd=1,
            state="disabled",
            wrap="word",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            height=12,
        )

        action_row = tk.Frame(progress_win, bg=BG)

        def _push_event(event):
            with state["events_lock"]:
                state["events"].append(event)

        def _worker():
            result = {
                "mods": [],
                "total": 0,
                "error": "",
            }
            try:
                mods_path = mods_folder.get()
                if not os.path.isdir(mods_path):
                    result["error"] = "Path is not a valid directory"
                    return result

                mod_entries = sorted([
                    name for name in os.listdir(mods_path)
                    if os.path.isdir(os.path.join(mods_path, name))
                ])

                result["total"] = len(mod_entries)
                result["mods"] = mod_entries

                return result
            except Exception as e:
                result["error"] = str(e)
                return result

        worker_thread = threading.Thread(target=lambda: _push_event(("done", _worker())), daemon=True)
        worker_thread.start()

        def _pump_queue():
            while True:
                with state["events_lock"]:
                    if not state["events"]:
                        item = None
                    else:
                        item = state["events"].pop(0)
                if item is None:
                    break

                if item[0] == "done":
                    state["done"] = True
                    state["result"] = item[1]

            if not state["done"]:
                progress_win.after(100, _pump_queue)
                return

            result = state["result"] or {}

            if result.get("error"):
                status_text.set(f"Error: {result['error']}")
                tk.Button(
                    action_row,
                    text="Close",
                    command=progress_win.destroy,
                    bg=BG3,
                    fg=TEXT,
                    relief="flat",
                    bd=0,
                    padx=18,
                    pady=6,
                    cursor="hand2",
                    font=FONT_UI,
                ).pack(side="left")
                return

            mods = result.get("mods", [])
            progress_text.set(f"{len(mods)} mod(s) found")
            status_text.set("Ready to save")

            list_text.pack(fill="both", expand=True, padx=12, pady=(10, 6))
            list_text.config(state="normal")
            for mod in mods:
                list_text.insert("end", mod + "\n")
            list_text.config(state="disabled")

            action_row.pack(fill="x", padx=12, pady=(0, 10))

            def _save():
                path = filedialog.asksaveasfilename(
                    parent=progress_win,
                    title="Save mod list",
                    filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                    defaultextension=".txt"
                )
                if path:
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            for mod in mods:
                                f.write(mod + "\n")
                        messagebox.showinfo("Success", f"List saved to:\n{path}", parent=progress_win)
                        progress_win.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to save:\n{e}", parent=progress_win)

            tk.Button(
                action_row,
                text="Save to File",
                command=_save,
                bg=ACCENT,
                fg="#000000",
                relief="flat",
                bd=0,
                padx=18,
                pady=6,
                cursor="hand2",
                font=FONT_UI,
            ).pack(side="left", padx=(0, 8))

            tk.Button(
                action_row,
                text="Close",
                command=progress_win.destroy,
                bg=BG3,
                fg=TEXT,
                relief="flat",
                bd=0,
                padx=18,
                pady=6,
                cursor="hand2",
                font=FONT_UI,
            ).pack(side="left")

        progress_win.after(100, _pump_queue)

    button_frame = tk.Frame(dialog, bg=BG)
    button_frame.pack(fill="x", padx=15, pady=10)
    tk.Button(
        button_frame, text="Cancel", command=dialog.destroy, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=20, pady=6, cursor="hand2", font=FONT_UI
    ).pack(side="left", padx=(0, 10))
    tk.Button(
        button_frame, text="Generate List", command=generate, bg=ACCENT, fg="#000000",
        relief="flat", bd=0, padx=20, pady=6, cursor="hand2", font=FONT_UI
    ).pack(side="left")


def show_mod_list_generator_dialog():
    """Compatibility alias for plugin discovery."""
    show_mod_list_dialog()
