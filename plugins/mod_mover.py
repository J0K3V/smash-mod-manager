"""
mod_mover.py — Move mods to another folder with selective checkboxes.

Allows selecting specific mods from a source folder and moving them to a destination.
Can load mod lists from text files.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import shutil
import threading

PLUGIN_NAME = "Mod Mover"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Move selected mods to another folder"

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


def show_mod_mover_dialog():
    """Show the Mod Mover UI."""
    if not _app:
        print("Error: App instance not available")
        return

    dialog = tk.Toplevel(_app.root)
    dialog.title("Mod Mover")
    dialog.geometry("800x700")
    dialog.configure(bg=(app_theme.BG if app_theme else "#1a1a1a"))
    dialog.minsize(700, 600)
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
        dialog, text="Mod Mover", bg=BG, fg=ACCENT,
        font=FONT_HEADER
    ).pack(pady=10)

    source_folder = tk.StringVar(value=(app_settings.get("mod_mover_last_source", "") if app_settings else ""))
    dest_folder = tk.StringVar(value=(app_settings.get("mod_mover_last_dest", "") if app_settings else ""))

    mod_vars = {}
    mod_list_frame = None
    mod_list_canvas = None

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

    # Source folder selection
    frame1 = tk.Frame(dialog, bg=BG)
    frame1.pack(fill="x", padx=15, pady=10)
    tk.Label(frame1, text="Source Folder:", bg=BG, fg=TEXT, font=FONT_UI).pack(anchor="w")
    source_label = tk.Label(frame1, text=_label_text(source_folder.get()), bg=BG, fg=TEXT_DIM, font=FONT_SMALL)
    source_label.pack(anchor="w", padx=(0, 5))

    def select_source():
        path = filedialog.askdirectory(parent=dialog, title="Select source folder with mods")
        _ensure_dialog_front()
        if path:
            source_folder.set(path)
            _persist_setting("mod_mover_last_source", path)
            source_label.config(text=_label_text(path))
            _refresh_mod_list()

    tk.Button(
        frame1, text="Browse...", command=select_source, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=10, pady=4, cursor="hand2"
    ).pack(anchor="w", pady=(5, 0))

    # Destination folder selection
    frame2 = tk.Frame(dialog, bg=BG)
    frame2.pack(fill="x", padx=15, pady=10)
    tk.Label(frame2, text="Destination Folder:", bg=BG, fg=TEXT, font=FONT_UI).pack(anchor="w")
    dest_label = tk.Label(frame2, text=_label_text(dest_folder.get()), bg=BG, fg=TEXT_DIM, font=FONT_SMALL)
    dest_label.pack(anchor="w", padx=(0, 5))

    def select_dest():
        path = filedialog.askdirectory(parent=dialog, title="Select destination folder")
        _ensure_dialog_front()
        if path:
            dest_folder.set(path)
            _persist_setting("mod_mover_last_dest", path)
            dest_label.config(text=_label_text(path))

    tk.Button(
        frame2, text="Browse...", command=select_dest, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=10, pady=4, cursor="hand2"
    ).pack(anchor="w", pady=(5, 0))

    # Control buttons
    control_frame = tk.Frame(dialog, bg=BG)
    control_frame.pack(fill="x", padx=15, pady=(5, 10))

    def _select_all():
        for var in mod_vars.values():
            var.set(True)

    def _deselect_all():
        for var in mod_vars.values():
            var.set(False)

    def _load_from_file():
        path = filedialog.askopenfilename(
            parent=dialog,
            title="Select mod list file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        _ensure_dialog_front()
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    mod_names = [line.strip() for line in f if line.strip()]
                _deselect_all()
                for mod_name in mod_names:
                    if mod_name in mod_vars:
                        mod_vars[mod_name].set(True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{e}", parent=dialog)

    tk.Button(
        control_frame, text="Select All", command=_select_all, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=10, pady=4, cursor="hand2"
    ).pack(side="left", padx=(0, 5))

    tk.Button(
        control_frame, text="Deselect All", command=_deselect_all, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=10, pady=4, cursor="hand2"
    ).pack(side="left", padx=(0, 5))

    tk.Button(
        control_frame, text="Load from File", command=_load_from_file, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=10, pady=4, cursor="hand2"
    ).pack(side="left")

    # Mod list with checkboxes
    list_label = tk.Label(dialog, text="Mods:", bg=BG, fg=TEXT, font=FONT_UI)
    list_label.pack(anchor="w", padx=15, pady=(10, 5))

    scroll_wrap = tk.Frame(dialog, bg=BG)
    scroll_wrap.pack(fill="both", expand=True, padx=15, pady=(0, 10))

    mod_list_canvas = tk.Canvas(scroll_wrap, bg=BG, highlightthickness=0, bd=0)
    scroll_bar = tk.Scrollbar(scroll_wrap, orient="vertical", command=mod_list_canvas.yview)
    mod_list_canvas.configure(yscrollcommand=scroll_bar.set)
    mod_list_canvas.pack(side="left", fill="both", expand=True)
    scroll_bar.pack(side="right", fill="y")

    mod_list_frame = tk.Frame(mod_list_canvas, bg=BG)
    body_window = mod_list_canvas.create_window((0, 0), window=mod_list_frame, anchor="nw")

    def _sync_scroll_region(_event=None):
        mod_list_canvas.configure(scrollregion=mod_list_canvas.bbox("all"))

    def _sync_body_width(event):
        mod_list_canvas.itemconfigure(body_window, width=event.width)

    mod_list_frame.bind("<Configure>", _sync_scroll_region)
    mod_list_canvas.bind("<Configure>", _sync_body_width)

    def _refresh_mod_list():
        nonlocal mod_list_frame, mod_list_canvas

        for widget in mod_list_frame.winfo_children():
            widget.destroy()
        mod_vars.clear()

        if not source_folder.get():
            return

        try:
            mod_entries = sorted([
                name for name in os.listdir(source_folder.get())
                if os.path.isdir(os.path.join(source_folder.get(), name))
            ])

            for mod_name in mod_entries:
                var = tk.BooleanVar(value=False)
                mod_vars[mod_name] = var
                cb = tk.Checkbutton(
                    mod_list_frame,
                    text=mod_name,
                    variable=var,
                    bg=BG,
                    fg=TEXT,
                    selectcolor=BG3,
                    activebackground=BG,
                    activeforeground=TEXT,
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    cursor="hand2",
                    font=FONT_SMALL,
                )
                cb.pack(anchor="w", padx=10, pady=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mods:\n{e}", parent=dialog)

    def _move_mods():
        if not source_folder.get():
            messagebox.showerror("Error", "Please select source folder", parent=dialog)
            return
        if not dest_folder.get():
            messagebox.showerror("Error", "Please select destination folder", parent=dialog)
            return

        selected_mods = [name for name, var in mod_vars.items() if var.get()]
        if not selected_mods:
            messagebox.showerror("Error", "Please select at least one mod", parent=dialog)
            return

        if not messagebox.askyesno(
            "Confirm",
            f"Move {len(selected_mods)} mod(s) to:\n{dest_folder.get()}?",
            parent=dialog
        ):
            return

        progress_win = tk.Toplevel(dialog)
        progress_win.title("Moving Mods")
        progress_win.geometry("600x200")
        progress_win.configure(bg=BG)
        progress_win.resizable(False, False)
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
        progress_text = tk.StringVar(value="0/0 mods")
        status_text = tk.StringVar(value="Starting...")

        tk.Label(progress_win, text="Moving Mods", bg=BG, fg=ACCENT, font=FONT_HEADER).pack(
            anchor="w", padx=12, pady=(10, 4)
        )
        tk.Label(progress_win, textvariable=progress_text, bg=BG, fg=TEXT, font=FONT_UI).pack(
            anchor="w", padx=12
        )
        ttk.Progressbar(
            progress_win,
            mode="determinate",
            maximum=100.0,
            variable=progress_var,
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

        def _push_event(event):
            with state["events_lock"]:
                state["events"].append(event)

        def _worker():
            result = {
                "moved": [],
                "failed": [],
                "error": "",
            }
            try:
                os.makedirs(dest_folder.get(), exist_ok=True)

                for idx, mod_name in enumerate(selected_mods, start=1):
                    if state["cancel"].is_set():
                        break

                    _push_event(("progress", idx, len(selected_mods), mod_name))
                    src_path = os.path.join(source_folder.get(), mod_name)
                    dst_path = os.path.join(dest_folder.get(), mod_name)

                    try:
                        if os.path.exists(dst_path):
                            shutil.rmtree(dst_path)
                        shutil.move(src_path, dst_path)
                        result["moved"].append(mod_name)
                    except Exception as e:
                        result["failed"].append(f"{mod_name}: {e}")

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

                if item[0] == "progress":
                    _, current, total, name = item
                    pct = (current / total) * 100.0 if total else 0.0
                    progress_var.set(pct)
                    progress_text.set(f"{current}/{total} mods")
                    status_text.set(f"Moving: {name}")
                elif item[0] == "done":
                    state["done"] = True
                    state["result"] = item[1]

            if not state["done"]:
                progress_win.after(100, _pump_queue)
                return

            result = state["result"] or {}

            if result.get("error"):
                messagebox.showerror("Error", f"Fatal error:\n{result['error']}", parent=progress_win)
                progress_win.destroy()
                return

            msg = f"Moved {len(result['moved'])} mod(s)"
            if result.get("failed"):
                msg += f"\n\nFailed {len(result['failed'])} mod(s):"
                for err in result["failed"][:5]:
                    msg += f"\n- {err}"
                if len(result["failed"]) > 5:
                    msg += f"\n... and {len(result['failed']) - 5} more"

            messagebox.showinfo("Complete", msg, parent=progress_win)
            progress_win.destroy()
            _refresh_mod_list()

        progress_win.after(100, _pump_queue)

    button_frame = tk.Frame(dialog, bg=BG)
    button_frame.pack(fill="x", padx=15, pady=10)
    tk.Button(
        button_frame, text="Cancel", command=dialog.destroy, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=20, pady=6, cursor="hand2", font=FONT_UI
    ).pack(side="left", padx=(0, 10))
    tk.Button(
        button_frame, text="Move Selected", command=_move_mods, bg=ACCENT, fg="#000000",
        relief="flat", bd=0, padx=20, pady=6, cursor="hand2", font=FONT_UI
    ).pack(side="left")

    _refresh_mod_list()
