"""
app.py — Main GUI window for Smash Mod Manager v4.
Dark industrial theme. Integrated log panel. Drag & drop support.
All tabs: Reslot, Effects, Batch, Missing Files, Base Folders, Plugins.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import json
import re

# Add parent to path so core imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import core.logger as logger
import core.settings as settings
import core.mod_analyzer as analyzer
import core.fighter_db as fighter_db

from gui.theme import *
from gui.widgets import (
    styled_button, styled_entry, styled_combo, styled_check,
    styled_label, styled_listbox, separator, section_header, Tooltip,
    CheckList,
)


class ModManagerApp:
    """Main application class."""

    def __init__(self, root: tk.Tk, initial_path: str = ""):
        self.root = root
        self._analysis = None

        # ── Shared variables ──────────────────────────────────────────────────
        self.mod_path = tk.StringVar(value=initial_path)
        self.fighter_var = tk.StringVar()
        self.source_slot_var = tk.StringVar()
        self.target_slot_var = tk.StringVar()
        self.share_slot_var = tk.StringVar()
        self.include_effects_var = tk.BooleanVar(value=True)
        self.include_kirby_var = tk.BooleanVar(value=True)
        self.new_config_var = tk.BooleanVar(value=False)
        self.hashes_var = tk.StringVar(value=settings.get("hashes_file", ""))
        self.reslot_all_var = tk.BooleanVar(value=False)
        self.reslot_all_start_var = tk.StringVar(value="c08")
        self.split_slots_var = tk.BooleanVar(value=settings.get("split_slots", False))
        self.split_slots_var.trace_add("write",
            lambda *_: settings.put("split_slots", self.split_slots_var.get()))

        # Effects tab
        self.eff_fighter_var = tk.StringVar()
        self.eff_slot_var = tk.StringVar(value="c08")
        # Batch tab
        self.batch_path_var = tk.StringVar(value=settings.get("last_batch_dir", ""))

        # Missing files tab
        self.missing_fighter_var = tk.StringVar()
        self.missing_slot_var = tk.StringVar(value="c00")
        self.missing_base_var = tk.StringVar()

        # Base folders tab
        self.bf_fighter_var = tk.StringVar()
        self.bf_group_var = tk.StringVar(value="c00  (default)")
        self.bf_path_var = tk.StringVar()
        self.bf_hint_var = tk.StringVar()

        # Build UI
        self._build_window()
        self._build_layout()
        logger.subscribe(self._on_log)

        # Load plugins
        try:
            from core import plugin_loader
            plugin_loader.load_plugins(app=self)
        except Exception as e:
            logger.warn(f"Plugin system: {e}")

        if initial_path:
            self.root.after(200, lambda: self._load_mod(initial_path))

    # ═════════════════════════════════════════════════════════════════════════
    #  WINDOW SETUP
    # ═════════════════════════════════════════════════════════════════════════
    def _build_window(self):
        self.root.title("Smash Mod Manager v4")
        self.root.configure(bg=BG)
        geo = settings.get("window_geometry", "960x740")
        self.root.geometry(geo)
        self.root.minsize(820, 620)
        if settings.get("window_maximized", False):
            self.root.after(50, lambda: self.root.state("zoomed"))

        # Drag & drop (optional tkinterdnd2)
        try:
            self.root.drop_target_register('DND_Files')
            self.root.dnd_bind('<<Drop>>', self._on_drop)
        except Exception:
            pass

        # Menu bar
        menubar = tk.Menu(self.root, bg=BG2, fg=TEXT,
                          activebackground=BG3, activeforeground=ACCENT, bd=0)
        file_menu = tk.Menu(menubar, tearoff=0, bg=BG2, fg=TEXT,
                            activebackground=BG3, activeforeground=ACCENT)
        file_menu.add_command(label="Open Mod Folder…", command=self._browse_mod)
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self._open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=BG2, fg=TEXT,
                            activebackground=BG3, activeforeground=ACCENT)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    # ═════════════════════════════════════════════════════════════════════════
    #  MAIN LAYOUT
    # ═════════════════════════════════════════════════════════════════════════
    def _build_layout(self):
        # ── Main pane: tabs + log ─────────────────────────────────────────────
        main_pane = tk.PanedWindow(
            self.root, orient="vertical", bg=BG,
            sashwidth=4, sashrelief="flat", sashpad=2,
        )
        main_pane.pack(fill="both", expand=True)

        # Tabs
        nb_frame = tk.Frame(main_pane, bg=BG)
        main_pane.add(nb_frame, minsize=300)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.TNotebook", background=BG, borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background=BG2, foreground=TEXT_DIM,
                        padding=[14, 6], font=FONT_UI, borderwidth=0)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", BG3)],
                  foreground=[("selected", ACCENT)])

        self.nb = ttk.Notebook(nb_frame, style="Dark.TNotebook")
        self.nb.pack(fill="both", expand=True)

        self._build_reslot_tab()
        self._build_effects_tab()
        self._build_batch_tab()
        self._build_missing_tab()
        self._build_basefolders_tab()
        self._build_plugins_tab()

        # Log panel
        log_frame = tk.Frame(main_pane, bg=BG2)
        main_pane.add(log_frame, minsize=120)
        self._build_log_panel(log_frame)

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB: RESLOT
    # ═════════════════════════════════════════════════════════════════════════
    def _build_reslot_tab(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text="  Reslot  ")
        pad = dict(padx=20, pady=8)

        # ── Mod folder row ────────────────────────────────────────────────────
        mod_row = tk.Frame(tab, bg=BG2, pady=7, padx=12)
        mod_row.pack(fill="x")
        styled_label(mod_row, "MOD FOLDER", bg=BG2).pack(side="left")
        path_entry = styled_entry(mod_row, self.mod_path, font=FONT_MONO)
        path_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        path_entry.bind("<Return>", lambda e: self._load_mod(self.mod_path.get()))
        styled_button(mod_row, "Browse", self._browse_mod).pack(side="left", padx=(0, 6))
        styled_button(mod_row, "Load", lambda: self._load_mod(self.mod_path.get()),
                      accent=True).pack(side="left")

        # ── Info strip ────────────────────────────────────────────────────────
        self.info_frame = tk.Frame(tab, bg=BG3, pady=4, padx=12)
        self.info_frame.pack(fill="x")
        self.info_label = tk.Label(
            self.info_frame,
            text="No mod loaded — browse or drag a folder",
            bg=BG3, fg=TEXT_DIM, font=FONT_SMALL, anchor="w",
        )
        self.info_label.pack(side="left")

        separator(tab).pack(fill="x", padx=20, pady=(8, 0))

        # Fighter
        row1 = tk.Frame(tab, bg=BG)
        row1.pack(fill="x", **pad)
        styled_label(row1, "Fighter", width=14, anchor="w").pack(side="left")
        self.fighter_entry = styled_entry(row1, self.fighter_var)
        self.fighter_entry.pack(side="left", fill="x", expand=True)

        # Slots row
        row2 = tk.Frame(tab, bg=BG)
        row2.pack(fill="x", **pad)

        styled_label(row2, "Source Slot", width=14, anchor="w").pack(side="left")
        self.source_combo = styled_combo(row2, self.source_slot_var, SLOT_OPTIONS)
        self.source_combo.pack(side="left", padx=(0, 20))

        styled_label(row2, "Target Slot", width=12, anchor="w").pack(side="left")
        self.target_combo = styled_combo(row2, self.target_slot_var, SLOT_OPTIONS)
        self.target_combo.pack(side="left", padx=(0, 20))

        styled_label(row2, "Share From", width=12, anchor="w").pack(side="left")
        self.share_combo = styled_combo(row2, self.share_slot_var, SLOT_OPTIONS)
        self.share_combo.pack(side="left")

        # Reslot All row — shown only when the mod has more than one slot
        self.reslot_all_row = tk.Frame(tab, bg=BG)
        # (packed dynamically in _load_mod)
        styled_label(self.reslot_all_row, "", width=14, bg=BG).pack(side="left")
        styled_check(
            self.reslot_all_row, "Reslot all detected slots", self.reslot_all_var
        ).pack(side="left", padx=(0, 20))
        styled_label(self.reslot_all_row, "starting at", bg=BG, fg=TEXT_DIM).pack(
            side="left", padx=(0, 8))
        styled_combo(self.reslot_all_row, self.reslot_all_start_var, SLOT_OPTIONS, width=6).pack(
            side="left")
        # Split slots row — shown below Reslot All row when mod has more than one slot
        self.split_slots_row = tk.Frame(tab, bg=BG)
        # (packed dynamically in _load_mod)
        styled_label(self.split_slots_row, "", width=14, bg=BG).pack(side="left")
        chk_split = styled_check(
            self.split_slots_row, "Split into separate folders", self.split_slots_var
        )
        chk_split.pack(side="left", padx=(0, 12))
        Tooltip(chk_split,
            "Each slot is reslotted into its own output folder.\n"
            "Shared files (webp, png, txt, toml) are copied to every folder.\n"
            "Not compatible with Smart rename.")

        self._reslot_slots_row = row2   # anchor for insertion

        # Options
        row3 = tk.Frame(tab, bg=BG)
        row3.pack(fill="x", **pad)
        styled_label(row3, "Options", width=14, anchor="w").pack(side="left")
        styled_check(row3, "Include Kirby Hat", self.include_kirby_var).pack(side="left", padx=(0, 16))
        styled_check(row3, "New Config", self.new_config_var).pack(side="left")

        # Divider
        separator(tab).pack(fill="x", padx=20, pady=4)

        # Actions
        btn_row = tk.Frame(tab, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=10)
        styled_button(btn_row, "⚙  Change Slots", self._run_reslot,
                       accent=True, width=18).pack(side="left", padx=(0, 10))
        styled_button(btn_row, "📄  Rewrite Config", self._run_reconfig,
                       width=18).pack(side="left", padx=(0, 10))

        # Detected slots display
        self.slots_frame = tk.Frame(tab, bg=BG)
        self.slots_frame.pack(fill="x", padx=20, pady=(4, 0))

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB: EFFECTS
    # ═════════════════════════════════════════════════════════════════════════
    def _build_effects_tab(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text="  Effects  ")
        pad = dict(padx=20, pady=8)

        # ── Mod folder row (same var as Reslot) ───────────────────────────────
        mod_row = tk.Frame(tab, bg=BG2, pady=7, padx=12)
        mod_row.pack(fill="x")
        styled_label(mod_row, "MOD FOLDER", bg=BG2).pack(side="left")
        eff_path_entry = styled_entry(mod_row, self.mod_path, font=FONT_MONO)
        eff_path_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        eff_path_entry.bind("<Return>", lambda e: self._load_mod(self.mod_path.get()))
        styled_button(mod_row, "Browse", self._browse_mod).pack(side="left", padx=(0, 6))
        styled_button(mod_row, "Load", lambda: self._load_mod(self.mod_path.get()),
                      accent=True).pack(side="left")

        separator(tab).pack(fill="x", padx=20, pady=(8, 0))

        styled_label(
            tab, "Slot effect files (ef_fighter.eff, trail/, model/ subfolders).",
        ).pack(fill="x", **pad)

        # Fighter
        row1 = tk.Frame(tab, bg=BG)
        row1.pack(fill="x", **pad)
        styled_label(row1, "Fighter", width=14, anchor="w").pack(side="left")
        styled_entry(row1, self.eff_fighter_var).pack(side="left", fill="x", expand=True)

        # Target slot
        row2 = tk.Frame(tab, bg=BG)
        row2.pack(fill="x", **pad)
        styled_label(row2, "Target Slot", width=14, anchor="w").pack(side="left")
        styled_combo(row2, self.eff_slot_var, SLOT_OPTIONS).pack(side="left", padx=(0, 20))

        separator(tab).pack(fill="x", padx=20, pady=4)

        # Actions
        btn_row = tk.Frame(tab, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=10)
        styled_button(btn_row, "⚡  Slot Effects", self._run_eff_slotter,
                       accent=True, width=18).pack(side="left")

        # Effect details display
        self.eff_details_frame = tk.Frame(tab, bg=BG)
        self.eff_details_frame.pack(fill="x", padx=20, pady=(12, 0))

        # Note
        styled_label(
            tab,
            "Renames ef_fighter.eff → ef_fighter_cXX.eff, trail → trail_cXX,\n"
            "model subfolders → folder_cXX. Writes config.json.",
            justify="left",
        ).pack(fill="x", padx=20, pady=(12, 0))

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB: BATCH VALIDATOR
    # ═════════════════════════════════════════════════════════════════════════
    def _build_batch_tab(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text="  Batch  ")
        pad = dict(padx=20, pady=8)

        section_header(tab, "BATCH VALIDATOR / SLOT RENAMER").pack(fill="x", **pad)
        styled_label(
            tab,
            "Point to a single mod folder OR a folder that contains multiple mods.\n"
            "Validates structure, checks slot consistency, detects mismatches.\n"
            "Handles all model parts (body, pipe, clown, etc.).",
            justify="left", anchor="w",
        ).pack(fill="x", padx=20)

        separator(tab).pack(fill="x", padx=20, pady=10)

        # Mods folder
        row = tk.Frame(tab, bg=BG)
        row.pack(fill="x", **pad)
        styled_label(row, "Mods Folder", width=14, anchor="w").pack(side="left")
        styled_entry(row, self.batch_path_var, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=(0, 8))

        def _browse_batch():
            p = filedialog.askdirectory(title="Select folder containing mods")
            if p:
                self.batch_path_var.set(p)
                settings.put("last_batch_dir", p)
        styled_button(row, "…", _browse_batch).pack(side="left")

        # Results list header + select helpers
        hdr_row = tk.Frame(tab, bg=BG)
        hdr_row.pack(fill="x", padx=20, pady=(12, 2))
        styled_label(hdr_row, "Validation Results", anchor="w").pack(
            side="left", fill="x", expand=True)
        styled_button(hdr_row, "All", lambda: self._batch_checklist.select_all(True),
                      small=True).pack(side="left", padx=(0, 4))
        styled_button(hdr_row, "None", lambda: self._batch_checklist.select_all(False),
                      small=True).pack(side="left")

        self._batch_checklist = CheckList(tab)
        self._batch_checklist.frame.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        # Actions
        btn_row = tk.Frame(tab, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(0, 12))
        styled_button(btn_row, "🔍  Validate", self._run_batch_validate,
                       width=16).pack(side="left", padx=(0, 10))
        styled_button(btn_row, "🔧  Fix Selected", self._run_batch_fix,
                       accent=True, width=16).pack(side="left")

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB: MISSING FILES
    # ═════════════════════════════════════════════════════════════════════════
    def _build_missing_tab(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text="  Missing Files  ")
        pad = dict(padx=20, pady=8)

        section_header(tab, "MISSING FILE COMPLETION").pack(fill="x", **pad)
        styled_label(
            tab,
            "Detects missing files (eyes, skin, hair, etc.) and copies from base folder.\n"
            "Existing files are never overwritten. Handles all model parts (body, clown, etc.).",
            justify="left", anchor="w",
        ).pack(fill="x", padx=20)

        separator(tab).pack(fill="x", padx=20, pady=10)

        # ── Resizable split: single mod (top) / batch (bottom) ───────────────
        pane = tk.PanedWindow(tab, orient="vertical", bg=BG3,
                              sashwidth=6, sashrelief="flat", bd=0)
        pane.pack(fill="both", expand=True, padx=0, pady=(0, 4))

        # ── Top pane: single mod ──────────────────────────────────────────────
        top_pane = tk.Frame(pane, bg=BG)
        pane.add(top_pane, minsize=180, stretch="always")

        single_header = tk.Frame(top_pane, bg=BG)
        single_header.pack(fill="x", padx=20, pady=(0, 4))
        tk.Label(single_header, text="SINGLE MOD", bg=BG, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left")

        # Fighter + slot
        row1 = tk.Frame(top_pane, bg=BG)
        row1.pack(fill="x", **pad)
        styled_label(row1, "Fighter", width=14, anchor="w").pack(side="left")
        styled_entry(row1, self.missing_fighter_var).pack(side="left", fill="x", expand=True)

        row2 = tk.Frame(top_pane, bg=BG)
        row2.pack(fill="x", **pad)
        styled_label(row2, "Slot", width=14, anchor="w").pack(side="left")
        styled_combo(row2, self.missing_slot_var, SLOT_OPTIONS).pack(side="left", padx=(0, 20))
        styled_button(row2, "Auto-detect Base", self._auto_detect_base).pack(side="left")

        # Base folder
        row3 = tk.Frame(top_pane, bg=BG)
        row3.pack(fill="x", **pad)
        styled_label(row3, "Base Folder", width=14, anchor="w").pack(side="left")
        styled_entry(row3, self.missing_base_var, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=(0, 8))

        def _browse_base():
            p = filedialog.askdirectory(title="Select base folder for this fighter/slot")
            if p:
                self.missing_base_var.set(p)
        styled_button(row3, "…", _browse_base).pack(side="left")

        # Missing files list
        styled_label(top_pane, "Detected Missing Files", anchor="w").pack(
            fill="x", padx=20, pady=(8, 2))

        list_container, self.missing_listbox = styled_listbox(top_pane)
        list_container.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        # Single mod actions
        btn_row = tk.Frame(top_pane, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(0, 6))
        styled_button(btn_row, "🔍  Detect Missing", self._run_detect_missing,
                       width=18).pack(side="left", padx=(0, 10))
        styled_button(btn_row, "📋  Copy Missing", self._run_copy_missing,
                       accent=True, width=18).pack(side="left")

        # ── Bottom pane: batch mode ───────────────────────────────────────────
        bot_pane = tk.Frame(pane, bg=BG2)
        pane.add(bot_pane, minsize=70, stretch="never")

        batch_header = tk.Frame(bot_pane, bg=BG2)
        batch_header.pack(fill="x", padx=20, pady=(8, 4))
        tk.Label(batch_header, text="BATCH MODE", bg=BG2, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left")
        tk.Label(batch_header,
                 text="— processes all mods in a folder using saved base files",
                 bg=BG2, fg=TEXT_MUTED, font=FONT_SMALL).pack(side="left", padx=(6, 0))

        batch_row = tk.Frame(bot_pane, bg=BG2)
        batch_row.pack(fill="x", padx=20, pady=(0, 10))
        styled_label(batch_row, "Mods Folder", width=14, anchor="w").pack(side="left")
        styled_entry(batch_row, self.batch_path_var, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=(0, 8))

        def _browse_batch_missing():
            p = filedialog.askdirectory(title="Select folder containing mods")
            if p:
                self.batch_path_var.set(p)
                settings.put("last_batch_dir", p)
        styled_button(batch_row, "…", _browse_batch_missing).pack(side="left", padx=(0, 8))
        styled_button(batch_row, "📋  Batch Copy Missing",
                       self._run_batch_missing, accent=True).pack(side="left")

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB: BASE FOLDERS
    # ═════════════════════════════════════════════════════════════════════════
    def _build_basefolders_tab(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text="  Base Files  ")
        pad = dict(padx=20, pady=8)

        section_header(tab, "BASE SOURCE").pack(fill="x", padx=20, pady=(10, 2))
        styled_label(
            tab,
            "Point to a folder containing your vanilla fighter files.\n"
            "Can be a full game dump, a folder of ZIPs, or a mix of both.",
            justify="left", anchor="w",
        ).pack(fill="x", padx=20)

        separator(tab).pack(fill="x", padx=20, pady=8)

        # Source folder row
        src_row = tk.Frame(tab, bg=BG)
        src_row.pack(fill="x", **pad)
        styled_label(src_row, "Source Folder", width=14, anchor="w").pack(side="left")

        from core import base_index as _bi
        _bi.load()
        self._base_src_var = tk.StringVar(value=_bi.get_source_root())
        styled_entry(src_row, self._base_src_var, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=(0, 8))

        def _browse_src():
            p = filedialog.askdirectory(title="Select base source folder")
            if p:
                self._base_src_var.set(p)
                self._on_base_src_changed(p)
        styled_button(src_row, "Browse", _browse_src).pack(side="left")

        # Status row
        self._base_status_var = tk.StringVar()
        self._update_base_status()
        status_row = tk.Frame(tab, bg=BG)
        status_row.pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(status_row, textvariable=self._base_status_var,
                 bg=BG, fg=TEXT_DIM, font=FONT_SMALL, anchor="w").pack(side="left")

        separator(tab).pack(fill="x", padx=20, pady=4)

        # Action buttons
        btn_row = tk.Frame(tab, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=6)
        styled_button(btn_row, "🔍  Scan Now", self._run_base_scan).pack(
            side="left", padx=(0, 10))
        styled_button(btn_row, "⚙  Configure / View Index",
                       self._open_base_config_window).pack(side="left")


    def _update_base_status(self):
        from core import base_index as _bi
        if not _bi.is_loaded():
            _bi.load()
        root = _bi.get_source_root()
        scan_time = _bi.get_scan_time()
        if not root:
            self._base_status_var.set("No source configured. Browse to a folder and click Scan.")
            return
        count = len(_bi.get_indexed_fighters())
        if count:
            self._base_status_var.set(
                f"Indexed {count} fighters  ·  Last scan: {scan_time}")
        else:
            self._base_status_var.set(f"Source set but not scanned yet: {root}")

    def _on_base_src_changed(self, path: str):
        skip_confirm = settings.get("skip_scan_confirm", False)
        if not skip_confirm:
            msg = (
                f"Scan this folder for fighter model files?\n\n{path}\n\n"
                "This may take a moment for large dumps (full data.arc extraction).\n"
                "A progress window will appear."
            )
            if not messagebox.askyesno("Scan base source?", msg):
                return
        self._run_base_scan_path(path)

    def _run_base_scan(self):
        path = self._base_src_var.get().strip()
        if not path or not os.path.isdir(path):
            messagebox.showerror("Error", "Set a valid source folder first.")
            return
        self._run_base_scan_path(path)

    def _run_base_scan_path(self, path: str):
        import threading

        prog_win = tk.Toplevel(self.root)
        prog_win.title("Scanning…")
        prog_win.geometry("420x130")
        prog_win.resizable(False, False)
        prog_win.configure(bg=BG)
        prog_win.grab_set()

        tk.Label(prog_win, text="Scanning base source folder…",
                 bg=BG, fg=TEXT, font=FONT_SMALL).pack(pady=(18, 4))
        prog_var = tk.StringVar(value="Starting…")
        tk.Label(prog_win, textvariable=prog_var, bg=BG, fg=TEXT_DIM,
                 font=FONT_SMALL, wraplength=380).pack(pady=4)
        prog_bar = tk.Frame(prog_win, bg=BG)
        prog_bar.pack(fill="x", padx=20, pady=4)
        bar_inner = tk.Frame(prog_bar, bg=ACCENT, height=4)
        bar_inner.pack(fill="x")

        last = 0

        def _progress(msg: str):
            nonlocal last
            last += 1
            if last % 100 == 0:
                self.root.after(0, lambda m=msg: prog_var.set(m))

        def _work():
            from core import base_index as _bi
            _bi.scan(path, _progress)
            def _done():
                prog_win.destroy()
                self._update_base_status()
                logger.success("Base index ready.")
            self.root.after(0, _done)

        threading.Thread(target=_work, daemon=True).start()

    def _open_base_config_window(self):
        from core import base_index as _bi
        from core import fighter_db

        if not _bi.is_loaded():
            _bi.load()

        win = tk.Toplevel(self.root)
        win.title("Base Index — Fighter Status")
        win.geometry("600x520")
        win.configure(bg=BG)

        # Header
        section_header(win, "BASE INDEX STATUS").pack(fill="x", padx=16, pady=(10, 2))

        root_lbl = _bi.get_source_root() or "(no source configured)"
        tk.Label(win, text=f"  Source: {root_lbl}",
                 bg=BG, fg=TEXT_DIM, font=FONT_SMALL, anchor="w").pack(fill="x", padx=16)
        scan_t = _bi.get_scan_time()
        if scan_t:
            tk.Label(win, text=f"  Last scan: {scan_t}",
                     bg=BG, fg=TEXT_DIM, font=FONT_SMALL, anchor="w").pack(fill="x", padx=16)

        separator(win).pack(fill="x", padx=16, pady=6)

        # Fighter list
        tk.Label(win, text="  Fighter", bg=BG2, fg=TEXT_DIM, font=FONT_SMALL,
                 anchor="w").pack(fill="x", padx=16)

        list_outer = tk.Frame(win, bg=BG3)
        list_outer.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        canvas = tk.Canvas(list_outer, bg=BG3, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(list_outer, orient="vertical",
                                  command=canvas.yview, bg=BG3, troughcolor=BG,
                                  relief="flat", bd=0, width=10)
        inner = tk.Frame(canvas, bg=BG3)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        def _on_mw(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mw, add="+")
        win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        indexed = set(_bi.get_indexed_fighters())

        for fighter_name in fighter_db.ROSTER_ORDER:
            found = fighter_name in indexed
            parts = _bi.get_fighter_parts(fighter_name) if found else []
            display = fighter_db.get_display_name(fighter_name)

            row = tk.Frame(inner, bg=BG3)
            row.pack(fill="x", padx=4, pady=1)

            dot_color = GREEN if found else RED
            tk.Label(row, text="●", bg=BG3, fg=dot_color,
                     font=FONT_SMALL).pack(side="left", padx=(4, 6))
            tk.Label(row, text=f"{display}  ({fighter_name})",
                     bg=BG3, fg=TEXT if found else TEXT_DIM,
                     font=FONT_SMALL, anchor="w", width=28).pack(side="left")
            if found:
                tk.Label(row, text=", ".join(parts) if parts else "—",
                         bg=BG3, fg=TEXT_DIM, font=FONT_SMALL, anchor="w").pack(side="left")

        separator(win).pack(fill="x", padx=16, pady=4)

        # Settings row: skip confirm checkbox
        bot_row = tk.Frame(win, bg=BG)
        bot_row.pack(fill="x", padx=16, pady=(0, 8))
        skip_var = tk.BooleanVar(value=settings.get("skip_scan_confirm", False))
        chk = styled_check(bot_row, "Skip scan confirmation dialog", skip_var)
        chk.pack(side="left")
        skip_var.trace_add("write", lambda *_: settings.put("skip_scan_confirm", skip_var.get()))

        styled_button(bot_row, "Close", win.destroy).pack(side="right")
        styled_button(bot_row, "🔍 Rescan", lambda: (win.destroy(), self._run_base_scan())).pack(
            side="right", padx=(0, 8))

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB: PLUGINS
    # ═════════════════════════════════════════════════════════════════════════
    def _build_plugins_tab(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text="  Plugins  ")
        pad = dict(padx=20, pady=8)

        section_header(tab, "LOADED PLUGINS").pack(fill="x", **pad)
        styled_label(
            tab,
            "Drop .py files in the plugins folder to extend the tool.",
            justify="left", anchor="w",
        ).pack(fill="x", padx=20)

        separator(tab).pack(fill="x", padx=20, pady=8)

        list_container, self.plugin_listbox = styled_listbox(tab)
        list_container.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        btn_row = tk.Frame(tab, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(0, 12))
        styled_button(btn_row, "🔄  Reload Plugins", self._reload_plugins,
                       width=20).pack(side="left", padx=(0, 10))
        styled_button(btn_row, "📂  Open Plugins Folder", self._open_plugins_folder,
                       width=22).pack(side="left")

        self._refresh_plugin_list()

    # ═════════════════════════════════════════════════════════════════════════
    #  LOG PANEL
    # ═════════════════════════════════════════════════════════════════════════
    def _build_log_panel(self, parent):
        header = tk.Frame(parent, bg=BG2)
        header.pack(fill="x")
        tk.Label(header, text="OUTPUT LOG", bg=BG2, fg=TEXT_DIM,
                 font=FONT_SMALL, padx=12, pady=4).pack(side="left")
        styled_button(header, "Clear", self._clear_log, small=True).pack(
            side="right", padx=8, pady=3)

        # Filter checkboxes
        self._log_filter_vars = {}
        filters = [("OK", GREEN), ("WARN", ORANGE), ("ERROR", RED), ("INFO", TEXT_DIM)]
        for tag, color in filters:
            var = tk.BooleanVar(value=True)
            self._log_filter_vars[tag] = var
            cb = tk.Checkbutton(
                header, text=tag, variable=var, bg=BG2, fg=color,
                activebackground=BG2, activeforeground=color,
                selectcolor=BG3, relief="flat", bd=0,
                font=FONT_SMALL, cursor="hand2",
                command=lambda t=tag, v=var: self._set_log_filter(t, v.get()),
            )
            cb.pack(side="right", padx=(0, 4))

        self.log_text = tk.Text(
            parent, bg=BG, fg=TEXT, font=FONT_MONO,
            relief="flat", bd=0, state="disabled",
            wrap="word", padx=10, pady=6, highlightthickness=0,
        )
        self.log_text.pack(fill="both", expand=True)

        sb = tk.Scrollbar(self.log_text, command=self.log_text.yview,
                          bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10)
        sb.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=sb.set)

        # Color tags
        self.log_text.tag_config("INFO",  foreground=TEXT)
        self.log_text.tag_config("OK",    foreground=GREEN)
        self.log_text.tag_config("WARN",  foreground=ORANGE)
        self.log_text.tag_config("ERROR", foreground=RED)
        self.log_text.tag_config("DEBUG", foreground=TEXT_DIM)

    def _set_log_filter(self, tag: str, visible: bool):
        self.log_text.tag_configure(tag, elide=not visible)

    # ═════════════════════════════════════════════════════════════════════════
    #  LOGGING
    # ═════════════════════════════════════════════════════════════════════════
    def _on_log(self, level: str, line: str):
        def _write():
            self.log_text.config(state="normal")
            self.log_text.insert("end", line + "\n", level)
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _write)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    # ═════════════════════════════════════════════════════════════════════════
    #  MOD LOADING
    # ═════════════════════════════════════════════════════════════════════════
    def _browse_mod(self):
        path = filedialog.askdirectory(
            title="Select mod root folder",
            initialdir=settings.get("last_mod_dir", "./"),
        )
        if path:
            self.mod_path.set(path)
            self._load_mod(path)

    def _browse_hashes(self):
        path = filedialog.askopenfilename(
            title="Select Hashes_all.txt",
            filetypes=[("Text files", "*.txt"), ("All", "*.*")],
        )
        if path:
            self.hashes_var.set(path)
            settings.put("hashes_file", path)

    def _on_drop(self, event):
        path = event.data.strip().strip("{}")
        if os.path.isdir(path):
            self.mod_path.set(path)
            self._load_mod(path)

    def _load_mod(self, path: str):
        if not path or not os.path.isdir(path):
            logger.warn(f"Invalid path: {path}")
            return

        settings.put("last_mod_dir", path)
        logger.info(f"Loading: {path}")
        self._analysis = analyzer.analyze(path)
        a = self._analysis

        if a["errors"]:
            for e in a["errors"]:
                logger.error(e)
            self.info_label.config(fg=RED, text=" | ".join(a["errors"]))
            return

        # Populate all fields across tabs
        self.fighter_var.set(a["fighter"] or "")
        self.eff_fighter_var.set(a["fighter"] or "")
        self.missing_fighter_var.set(a["fighter"] or "")

        if a["slots"]:
            self.source_slot_var.set(a["slots"][0])
            last_num = fighter_db.slot_num(a["slots"][-1])
            next_slot = fighter_db.slot_str(last_num + 1)
            self.target_slot_var.set(next_slot)
            self.share_slot_var.set(a["slots"][0])
            self.missing_slot_var.set(a["slots"][0])

            if len(a["slots"]) > 1:
                self.reslot_all_start_var.set(next_slot)
                self.reslot_all_row.pack(
                    fill="x", padx=20, pady=(0, 2),
                    after=self._reslot_slots_row)
                self.split_slots_row.pack(
                    fill="x", padx=20, pady=(0, 4),
                    after=self.reslot_all_row)
            else:
                self.reslot_all_var.set(False)
                self.reslot_all_row.pack_forget()
                self.split_slots_row.pack_forget()

        # Try to auto-fill base folder from saved settings
        if a["fighter"] and a["slots"]:
            from core import missing_files
            auto_base = missing_files.auto_detect_base_folder(
                a["fighter"], a["slots"][0])
            if auto_base:
                self.missing_base_var.set(auto_base)

        # Build info strip
        tags = []
        tags.append(f"✦ {a['display_name']}")
        tags.append(f"slots: {', '.join(a['slots']) if a['slots'] else 'none'}")
        if a["model_parts"]:
            tags.append(f"parts: {', '.join(a['model_parts'])}")
        if a["has_effects"]:
            eff = a["effect_details"]
            eff_info = "effects ✓"
            if eff.get("is_slotted"):
                eff_info += " (slotted)"
            tags.append(eff_info)
        if a["has_kirby_hat"]:
            tags.append("kirby hat ✓")
        if a["has_ui"]:
            tags.append("ui ✓")
        if a["has_sound"]:
            tags.append("sound ✓")
        if a["has_camera"]:
            tags.append("camera ✓")
        if a["is_extra_slot"]:
            tags.append("⚠ extra slot")
        if a["existing_config"]:
            tags.append("config.json ✓")

        self.info_label.config(fg=ACCENT, text="  │  ".join(tags))

        # Refresh slot badges
        for w in self.slots_frame.winfo_children():
            w.destroy()
        styled_label(self.slots_frame, "Detected slots:").pack(side="left", padx=(0, 8))
        for slot in a["slots"]:
            num = fighter_db.slot_num(slot)
            color = ACCENT2 if num >= 8 else ACCENT
            tk.Label(
                self.slots_frame, text=slot, bg=BG3, fg=color,
                font=FONT_SMALL, padx=6, pady=2, relief="flat",
            ).pack(side="left", padx=3)

        # Refresh effect details
        for w in self.eff_details_frame.winfo_children():
            w.destroy()
        if a["has_effects"]:
            eff = a["effect_details"]
            details = []
            if eff["eff_files"]:
                details.append(f".eff files: {', '.join(eff['eff_files'])}")
            if eff["trails"]:
                details.append(f"trails: {', '.join(eff['trails'])}")
            if eff["models"]:
                details.append(f"effect models: {', '.join(eff['models'])}")
            for d in details:
                styled_label(self.eff_details_frame, d, fg=ACCENT3).pack(
                    anchor="w", pady=1)

        logger.success(f"{a['display_name']}  {a['slots']}")

        # Notify plugins
        try:
            from core import plugin_loader
            plugin_loader.notify("on_mod_loaded", analysis=a)
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════════
    #  ACTIONS: RESLOT
    # ═════════════════════════════════════════════════════════════════════════
    @staticmethod
    def _build_output_name(folder_name: str, target_slot: str,
                           slot_count: int = 1) -> str:
        """Build the output folder name for a reslot operation.

        If 'smart_output_rename' is enabled AND the mod has only one slot,
        and the folder name already contains a slot pattern (cXX / CXX),
        that slot is replaced in-place. Otherwise the target slot is appended.
        Smart rename is disabled for multi-slot mods to avoid ambiguous replacements.
        """
        if settings.get("smart_output_rename", False) and slot_count <= 1:
            import re as _re
            m = _re.search(r'[Cc]\d{1,3}', folder_name)
            if m:
                return folder_name[:m.start()] + target_slot + folder_name[m.end():]
        return f"{folder_name} ({target_slot})"

    @staticmethod
    def _find_dir_info() -> str | None:
        """Return absolute path to dir_info_with_files_trimmed.json, or None."""
        fname = "dir_info_with_files_trimmed.json"
        # 1. User-specified in settings
        p = settings.get("dir_info_file", "")
        if p and os.path.isfile(p):
            return p
        # 2. Relative to this source file (works in dev)
        here = os.path.dirname(os.path.abspath(__file__))
        p = os.path.normpath(os.path.join(here, "..", fname))
        if os.path.isfile(p):
            return p
        # 3. PyInstaller bundle
        if getattr(sys, "frozen", False):
            p = os.path.join(sys._MEIPASS, fname)
            if os.path.isfile(p):
                return p
        # 4. Current working directory
        p = os.path.join(os.getcwd(), fname)
        if os.path.isfile(p):
            return p
        return None

    def _validate_reslot(self) -> bool:
        if not self.mod_path.get():
            messagebox.showerror("Error", "No mod folder selected.")
            return False
        if not self.fighter_var.get():
            messagebox.showerror("Error", "Fighter name is required.")
            return False
        hashes = self.hashes_var.get()
        if not hashes or not os.path.isfile(hashes):
            messagebox.showerror("Error",
                "Hashes_all.txt not found.\n"
                "Set the path in the Hashes File field or in Settings.")
            return False
        if not self._find_dir_info():
            messagebox.showerror("Error",
                "dir_info_with_files_trimmed.json not found.\n"
                "Set the path in Settings → Data Files.")
            return False
        return True

    def _handle_effects(self, src_mod: str, out_dir: str, fighter: str):
        """Apply effect settings after the reslotter has run."""
        import shutil, re as _re
        save_eff   = settings.get("save_effects",           True)
        reslot_eff = settings.get("reslot_slotted_effects", True)

        if not reslot_eff:
            # Remove slotted effects the reslotter may have copied
            eff_out = os.path.join(out_dir, "effect")
            if os.path.isdir(eff_out):
                shutil.rmtree(eff_out)

        if save_eff:
            # Copy unslotted effects (no _cXX in name) from source to output
            src_eff = os.path.join(src_mod, "effect", "fighter", fighter)
            if os.path.isdir(src_eff):
                for item in os.listdir(src_eff):
                    if _re.search(r'_c\d{2}', item):
                        continue  # slotted — handled by reslotter
                    src_item = os.path.join(src_eff, item)
                    dst_item = os.path.join(out_dir, "effect", "fighter", fighter, item)
                    os.makedirs(os.path.dirname(dst_item), exist_ok=True)
                    if os.path.isfile(src_item):
                        shutil.copy2(src_item, dst_item)
                    elif os.path.isdir(src_item):
                        shutil.copytree(src_item, dst_item, dirs_exist_ok=True)

    def _copy_extra_files(self, src_mod: str, out_dir: str):
        """Copy loose metadata files from the mod root to the output folder."""
        import shutil
        ext_map = {
            ".webp": "copy_webp",
            ".txt":  "copy_txt",
            ".png":  "copy_png",
            ".toml": "copy_toml",
        }
        copied = []
        for fname in os.listdir(src_mod):
            if not os.path.isfile(os.path.join(src_mod, fname)):
                continue
            ext = os.path.splitext(fname)[1].lower()
            key = ext_map.get(ext)
            if key and settings.get(key, True):
                shutil.copy(os.path.join(src_mod, fname),
                            os.path.join(out_dir, fname))
                copied.append(fname)
        if copied:
            logger.info(f"Kept: {', '.join(copied)}")

    # Combined-fighter groups for Aegis / Pokemon Trainer mode
    _COMBINED_FIGHTERS = {
        "eflame":       ["eflame", "elight", "element"],
        "elight":       ["eflame", "elight", "element"],
        "element":      ["eflame", "elight", "element"],
        "popo":         ["popo", "nana"],
        "nana":         ["popo", "nana"],
        "ptrainer":     ["ptrainer", "pzenigame", "pfushigisou", "plizardon"],
        "pzenigame":    ["ptrainer", "pzenigame", "pfushigisou", "plizardon"],
        "pfushigisou":  ["ptrainer", "pzenigame", "pfushigisou", "plizardon"],
        "plizardon":    ["ptrainer", "pzenigame", "pfushigisou", "plizardon"],
    }

    def _run_reslot(self):
        if not self._validate_reslot():
            return
        mod     = self.mod_path.get()
        hsh     = self.hashes_var.get()
        name    = self.fighter_var.get()
        new_cfg = self.new_config_var.get()
        aegis   = settings.get("special_cases", True)

        fighters = [name]
        if aegis and name in self._COMBINED_FIGHTERS:
            fighters = self._COMBINED_FIGHTERS[name]

        # ── Reslot All mode ───────────────────────────────────────────────────
        if (self.reslot_all_var.get()
                and self._analysis
                and len(self._analysis["slots"]) > 1):

            slots     = self._analysis["slots"]
            start_str = self.reslot_all_start_var.get()
            start_num = fighter_db.slot_num(start_str)
            first_num = fighter_db.slot_num(slots[0])
            pairs     = [
                (s, fighter_db.slot_str(start_num + fighter_db.slot_num(s) - first_num))
                for s in slots
            ]
            folder_name = os.path.basename(mod)
            out_dir = os.path.join(os.path.dirname(mod),
                                   f"{folder_name} ({start_str}+)")
            logger.info(
                f"{name} — {len(slots)} slots  "
                f"{slots[0]}–{slots[-1]} → starting at {start_str}"
            )

            do_split = self.split_slots_var.get()

            def _work_all():
                try:
                    import core.reslotter as reslotter
                    orig_dir = os.getcwd()
                    os.chdir(os.path.normpath(os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "..")))

                    if do_split:
                        # Each slot goes into its own output folder
                        for src_s, tgt_s in pairs:
                            logger.info(f"  {src_s} → {tgt_s}")
                            slot_out = os.path.join(
                                os.path.dirname(mod),
                                f"{folder_name} ({tgt_s})")
                            reslotter.init(hsh, mod, True)
                            for fighter in fighters:
                                reslotter.main(mod, hsh, fighter, src_s, tgt_s, tgt_s, slot_out)
                            cfg_path = os.path.join(slot_out, "config.json")
                            with open(cfg_path, "w", encoding="utf-8") as f:
                                json.dump(reslotter.resulting_config, f, indent=4)
                            self._handle_effects(mod, slot_out, name)
                            self._copy_extra_files(mod, slot_out)
                            logger.success(f"  → {slot_out}")
                    else:
                        reslotter.init(hsh, mod, new_cfg)
                        for src_s, tgt_s in pairs:
                            logger.info(f"  {src_s} → {tgt_s}")
                            for fighter in fighters:
                                reslotter.main(mod, hsh, fighter, src_s, tgt_s, tgt_s, out_dir)
                        cfg_path = os.path.join(out_dir, "config.json")
                        with open(cfg_path, "w", encoding="utf-8") as f:
                            json.dump(reslotter.resulting_config, f, indent=4)
                        self._handle_effects(mod, out_dir, name)
                        self._copy_extra_files(mod, out_dir)
                        logger.success(f"Saved to: {out_dir}")

                    os.chdir(orig_dir)
                except Exception as e:
                    logger.error(f"Reslot error: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            threading.Thread(target=_work_all, daemon=True).start()
            return

        # ── Single-slot mode ──────────────────────────────────────────────────
        src   = self.source_slot_var.get()
        tgt   = self.target_slot_var.get()
        share = self.share_slot_var.get()

        if src == tgt:
            messagebox.showerror("Error", "Source and target slots are the same.")
            return

        logger.info(f"{', '.join(fighters)}  {src} → {tgt}")

        def _work():
            try:
                import core.reslotter as reslotter
                folder_name = os.path.basename(mod)
                slot_count = len(self._analysis["slots"]) if self._analysis else 1
                out_dir = os.path.join(os.path.dirname(mod),
                                       self._build_output_name(folder_name, tgt, slot_count))
                orig_dir = os.getcwd()
                os.chdir(os.path.dirname(self._find_dir_info()))

                reslotter.init(hsh, mod, new_cfg)
                for fighter in fighters:
                    reslotter.main(mod, hsh, fighter, src, tgt, share, out_dir)

                cfg_path = os.path.join(out_dir, "config.json")
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(reslotter.resulting_config, f, indent=4)
                self._handle_effects(mod, out_dir, name)
                self._copy_extra_files(mod, out_dir)
                os.chdir(orig_dir)
                logger.success(f"Saved to: {out_dir}")

                try:
                    from core import plugin_loader
                    plugin_loader.notify("on_reslot",
                        mod_path=out_dir, fighter=name, src=src, tgt=tgt)
                except Exception:
                    pass

            except Exception as e:
                logger.error(f"Reslot error: {e}")
                import traceback
                logger.error(traceback.format_exc())

        threading.Thread(target=_work, daemon=True).start()

    def _run_reconfig(self):
        if not self._validate_reslot():
            return
        mod   = self.mod_path.get()
        hsh   = self.hashes_var.get()
        name  = self.fighter_var.get()
        src   = self.source_slot_var.get()
        tgt   = self.target_slot_var.get()
        share = self.share_slot_var.get()

        logger.info(f"Rewriting config — {name} {tgt}")

        def _work():
            try:
                import core.reslotter as reslotter
                orig_dir = os.getcwd()
                os.chdir(os.path.dirname(self._find_dir_info()))
                reslotter.init(hsh, mod, True)
                reslotter.main(mod, hsh, name, src, tgt, share, "")
                cfg_path = os.path.join(mod, "config.json")
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(reslotter.resulting_config, f, indent=4)
                os.chdir(orig_dir)
                logger.success(f"config.json → {cfg_path}")
            except Exception as e:
                logger.error(f"Reconfig failed: {e}")
                import traceback
                logger.error(traceback.format_exc())

        threading.Thread(target=_work, daemon=True).start()

    # ═════════════════════════════════════════════════════════════════════════
    #  ACTIONS: EFFECTS
    # ═════════════════════════════════════════════════════════════════════════
    def _run_eff_slotter(self):
        mod  = self.mod_path.get()
        name = self.eff_fighter_var.get()
        slot_str = self.eff_slot_var.get()

        if not mod or not os.path.isdir(mod):
            messagebox.showerror("Error", "No mod folder selected.")
            return
        if not name:
            messagebox.showerror("Error", "Fighter name required.")
            return

        slot_num = fighter_db.slot_num(slot_str)

        logger.info(f"Effects — {name}  → {slot_str}")

        def _work():
            try:
                from core import eff_slotter
                result = eff_slotter.run(mod, name, slot_num)
                if not result["errors"]:
                    logger.success("Effects done.")
                    # Reload mod to refresh UI
                    self.root.after(100, lambda: self._load_mod(mod))
            except Exception as e:
                logger.error(f"Effect slotter failed: {e}")
                import traceback
                logger.error(traceback.format_exc())

        threading.Thread(target=_work, daemon=True).start()

    # ═════════════════════════════════════════════════════════════════════════
    #  ACTIONS: BATCH
    # ═════════════════════════════════════════════════════════════════════════
    def _run_batch_validate(self):
        folder = self.batch_path_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Select a valid mods folder first.")
            return
        self._batch_checklist.clear()
        logger.info(f"Validating mods in: {folder}")

        def _work():
            from core import batch_validator

            def _progress(current, total, name):
                self.root.after(0, lambda c=current, t=total, n=name: None)

            results = batch_validator.validate_batch(folder, _progress)

            def _update():
                self._batch_checklist.clear()
                for r in results:
                    self._batch_checklist.add_item(r)
            self.root.after(0, _update)

        threading.Thread(target=_work, daemon=True).start()

    def _run_batch_fix(self):
        checked = self._batch_checklist.get_checked()
        if not checked:
            messagebox.showinfo("Nothing selected",
                "Check at least one fixable mod in the list first.")
            return

        if not messagebox.askyesno(
            "Confirm",
            f"Fix {len(checked)} selected mod(s)?\n\n"
            "• Single-slot mismatch → slot folder renamed in-place.\n"
            "• Multi-slot mod → each slot reslotted into its own output folder "
            "(requires Hashes file).\n\nProceed?"):
            return

        hsh = self.hashes_var.get()
        logger.info(f"Batch fix: {len(checked)} mod(s) selected…")

        def _work():
            from core import batch_validator
            import core.reslotter as reslotter

            fixed = 0
            for _var, r in checked:
                if not r.can_fix or not r.fighter:
                    continue

                folder_slot_match = re.search(r'c\d{2,3}', r.mod_name)
                if not folder_slot_match or not r.slots:
                    continue

                expected = folder_slot_match.group()  # slot from folder title

                # ── Case 1: single model slot → rename in-place ───────────────
                if len(r.slots) == 1:
                    actual = r.slots[0]
                    if expected != actual:
                        ok = batch_validator.fix_slot_mismatch(
                            r.mod_path, r.fighter, actual, expected)
                        if ok:
                            fixed += 1
                            logger.success(f"  Fixed {r.mod_name}: {actual} → {expected}")

                # ── Case 2: multiple model slots → reslot each as its own alt ─
                else:
                    if not hsh or not os.path.isfile(hsh):
                        logger.warn(
                            f"  Skipping {r.mod_name} (multi-slot): "
                            "Hashes file not set — cannot run reslotter.")
                        continue

                    dir_info = self._find_dir_info()
                    if not dir_info:
                        logger.warn(
                            f"  Skipping {r.mod_name} (multi-slot): "
                            "dir_info_with_files_trimmed.json not found.")
                        continue

                    expected_num = fighter_db.slot_num(expected)
                    first_num    = fighter_db.slot_num(r.slots[0])
                    parent_dir   = os.path.dirname(r.mod_path)
                    aegis        = settings.get("special_cases", True)
                    fighters     = [r.fighter]
                    if aegis and r.fighter in self._COMBINED_FIGHTERS:
                        fighters = self._COMBINED_FIGHTERS[r.fighter]

                    orig_dir = os.getcwd()
                    try:
                        os.chdir(os.path.dirname(dir_info))
                        for src_s in r.slots:
                            offset  = fighter_db.slot_num(src_s) - first_num
                            tgt_s   = fighter_db.slot_str(expected_num + offset)
                            out_dir = os.path.join(parent_dir,
                                                   f"{r.mod_name} ({tgt_s})")
                            logger.info(f"  {r.mod_name}: {src_s} → {tgt_s}")
                            reslotter.init(hsh, r.mod_path, True)
                            for fighter in fighters:
                                reslotter.main(r.mod_path, hsh, fighter,
                                               src_s, tgt_s, tgt_s, out_dir)
                            cfg_path = os.path.join(out_dir, "config.json")
                            with open(cfg_path, "w", encoding="utf-8") as f:
                                json.dump(reslotter.resulting_config, f, indent=4)
                            logger.success(f"    → {out_dir}")
                        fixed += 1
                    except Exception as e:
                        logger.error(f"  Reslot error for {r.mod_name}: {e}")
                    finally:
                        os.chdir(orig_dir)

            logger.success(f"Batch fix done: {fixed} mod(s) processed.")
            self.root.after(200, self._run_batch_validate)

        threading.Thread(target=_work, daemon=True).start()

    # ═════════════════════════════════════════════════════════════════════════
    #  ACTIONS: MISSING FILES
    # ═════════════════════════════════════════════════════════════════════════
    def _auto_detect_base(self):
        name = self.missing_fighter_var.get()
        slot = self.missing_slot_var.get()
        if not name:
            messagebox.showerror("Error", "Enter a fighter name first.")
            return
        from core import missing_files
        path = missing_files.auto_detect_base_folder(name, slot)
        if path:
            self.missing_base_var.set(path)
            logger.info(f"Base: {path}")
        else:
            logger.warn(f"No base folder saved for {name} / {slot}. "
                        f"Assign one in the Base Folders tab.")

    def _run_detect_missing(self):
        mod  = self.mod_path.get()
        name = self.missing_fighter_var.get()
        slot = self.missing_slot_var.get()
        base = self.missing_base_var.get()

        if not mod or not os.path.isdir(mod):
            messagebox.showerror("Error", "No mod folder loaded.")
            return

        from core import base_index as _bi
        if not _bi.is_loaded():
            _bi.load()
        base_ok = base and (os.path.isdir(base) or (base.lower().endswith(".zip") and os.path.isfile(base)))
        if not _bi.is_loaded() and not base_ok:
            messagebox.showerror("Error",
                "No base index loaded and no Base Folder set.\n"
                "Configure a source in the Base Files tab or set a Base Folder.")
            return

        self.missing_listbox.delete(0, "end")
        logger.info(f"Checking missing files — {name} {slot}")

        def _work():
            from core import missing_files, base_index as _bi
            special = settings.get("special_cases", True)

            use_index = _bi.is_loaded()

            # Build list of fighters to check (Aegis special case)
            fighters_to_check = [name]
            if special and name in ("eflame", "elight", "element"):
                fighters_to_check = ["eflame", "elight", "element"]

            all_results = []
            for f_name in fighters_to_check:
                if use_index:
                    m = missing_files.detect_missing_indexed(mod, f_name, slot)
                else:
                    f_base = base if f_name == name else missing_files.auto_detect_base_folder(f_name, slot)
                    if not f_base:
                        continue
                    m = missing_files.detect_missing(mod, f_name, slot, f_base)
                for part_name, files in sorted(m.items()):
                    all_results.append((f_name, part_name, files))

            def _update():
                if not all_results:
                    self.missing_listbox.insert("end", "  ✓  No missing files detected")
                    self.missing_listbox.itemconfig("end", fg=GREEN)
                    logger.success("All good, nothing missing.")
                else:
                    total = 0
                    multi = len(fighters_to_check) > 1
                    for f_name, part_name, files in all_results:
                        header = f"  ── {f_name} / {part_name} ──" if multi else f"  ── {part_name} ──"
                        self.missing_listbox.insert("end", header)
                        self.missing_listbox.itemconfig("end", fg=ACCENT3)
                        for f in files:
                            self.missing_listbox.insert("end", f"    {f}")
                            total += 1
                    logger.info(f"Found {total} missing files across {len(all_results)} parts.")
            self.root.after(0, _update)

        threading.Thread(target=_work, daemon=True).start()

    def _run_copy_missing(self):
        mod  = self.mod_path.get()
        name = self.missing_fighter_var.get()
        slot = self.missing_slot_var.get()
        base = self.missing_base_var.get()

        if not mod or not os.path.isdir(mod):
            messagebox.showerror("Error", "No mod folder loaded.")
            return

        if not messagebox.askyesno("Confirm",
            "Copy all missing files from base to mod?\n"
            "Existing files will NOT be overwritten."):
            return

        logger.info("Copying missing files...")

        def _work():
            from core import missing_files, base_index as _bi
            special = settings.get("special_cases", True)

            use_index = _bi.is_loaded()

            fighters_to_copy = [name]
            if special and name in ("eflame", "elight", "element"):
                fighters_to_copy = ["eflame", "elight", "element"]

            total_copied = 0
            total_skipped = 0
            for f_name in fighters_to_copy:
                if use_index:
                    m = missing_files.detect_missing_indexed(mod, f_name, slot)
                    if not m:
                        continue
                    if len(fighters_to_copy) > 1:
                        logger.info(f"  [{f_name}]")
                    result = missing_files.copy_missing_indexed(mod, f_name, slot, m)
                else:
                    f_base = base if f_name == name else missing_files.auto_detect_base_folder(f_name, slot)
                    if not f_base:
                        continue
                    m = missing_files.detect_missing(mod, f_name, slot, f_base)
                    if not m:
                        continue
                    if len(fighters_to_copy) > 1:
                        logger.info(f"  [{f_name}]")
                    result = missing_files.copy_missing(mod, f_name, slot, f_base, m)
                total_copied += result["copied"]
                total_skipped += result["skipped"]
                if result["errors"]:
                    for e in result["errors"]:
                        logger.warn(f"  {e}")

            if total_copied == 0 and total_skipped == 0:
                logger.success("Nothing to add, mod is already complete.")
            else:
                logger.success(f"Done: {total_copied} copied, {total_skipped} skipped")
            self.root.after(200, self._run_detect_missing)

        threading.Thread(target=_work, daemon=True).start()

    def _run_batch_missing(self):
        folder = self.batch_path_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error",
                "Set the Mods Folder path first (shared with the Batch tab).")
            return

        if not messagebox.askyesno("Confirm Batch Copy",
            f"Process ALL mods in:\n{folder}\n\n"
            "Missing files will be copied from saved base files.\n"
            "Mods with no base configured will be skipped.\n\n"
            "Continue?"):
            return

        logger.info(f"Batch fill — {folder}")

        def _work():
            from core import missing_files, mod_analyzer
            from core import base_index as _bi
            if not _bi.is_loaded():
                _bi.load()
            use_index = _bi.is_loaded()

            candidates = []
            for entry in sorted(os.scandir(folder), key=lambda e: e.name):
                if entry.is_dir():
                    candidates.append(entry.path)

            if not candidates:
                logger.warn("No subfolders found in the mods folder.")
                return

            total_copied = 0
            total_skipped_mods = 0
            total_mods = len(candidates)

            for i, mod_path in enumerate(candidates, 1):
                mod_name = os.path.basename(mod_path)
                logger.info(f"[{i}/{total_mods}] {mod_name}")

                try:
                    a = mod_analyzer.analyze(mod_path)
                except Exception as e:
                    logger.warn(f"  [SKIP] {mod_name} — analysis error: {e}")
                    total_skipped_mods += 1
                    continue

                fighter = a.get("fighter")
                slots = a.get("slots", [])

                if not fighter:
                    logger.warn(f"  [SKIP] {mod_name} — could not detect fighter")
                    total_skipped_mods += 1
                    continue

                if not slots:
                    logger.warn(f"  [SKIP] {mod_name} — no slots detected")
                    total_skipped_mods += 1
                    continue

                mod_copied = 0
                any_base_missing = False

                for slot in slots:
                    try:
                        if use_index:
                            missing = missing_files.detect_missing_indexed(mod_path, fighter, slot)
                            if not missing:
                                continue
                            result = missing_files.copy_missing_indexed(mod_path, fighter, slot, missing)
                        else:
                            base = missing_files.auto_detect_base_folder(fighter, slot)
                            if not base:
                                any_base_missing = True
                                logger.warn(
                                    f"  [SKIP] {mod_name} slot {slot} — no base configured.")
                                continue
                            missing = missing_files.detect_missing(mod_path, fighter, slot, base)
                            if not missing:
                                continue
                            result = missing_files.copy_missing(mod_path, fighter, slot, base, missing)
                        mod_copied += result["copied"]
                        total_copied += result["copied"]
                        if result["errors"]:
                            for e in result["errors"]:
                                logger.warn(f"    {e}")
                    except Exception as e:
                        logger.warn(f"  [ERROR] {mod_name} slot {slot}: {e}")

                if any_base_missing and mod_copied == 0:
                    total_skipped_mods += 1
                elif mod_copied > 0:
                    logger.success(f"  ✓ {mod_copied} files copied")

            logger.success(
                f"Batch complete — {total_copied} files copied, "
                f"{total_skipped_mods}/{total_mods} mods skipped (no base)"
            )

        threading.Thread(target=_work, daemon=True).start()

    # ═════════════════════════════════════════════════════════════════════════
    #  ACTIONS: BASE FOLDERS
    # ═════════════════════════════════════════════════════════════════════════
    def _add_base_folder(self):
        fighter = self.bf_fighter_var.get().strip()
        group_sel = self.bf_group_var.get().strip()
        path = self.bf_path_var.get().strip()

        if not fighter or not group_sel or not path:
            messagebox.showerror("Error", "Fighter, base group and path are all required.")
            return
        is_zip = path.lower().endswith(".zip")
        if not os.path.isdir(path) and not (is_zip and os.path.isfile(path)):
            messagebox.showerror("Error", "Path does not exist or is not a valid folder/ZIP.")
            return

        group_key = group_sel.split("  —")[0].strip()
        settings.set_base_folder(fighter, group_key, path)
        kind = "ZIP" if is_zip else "folder"
        logger.success(f"Base {kind} set for {fighter} ({group_key})")
        self._refresh_bf_list()

    def _remove_base_folder_by_key(self, key: str):
        """Remove a base folder entry and refresh the list."""
        settings.remove_base_folder(key)
        logger.info(f"Removed: {key}")
        self._refresh_bf_list()

    def _assign_path_for_key(self, key: str):
        """Open a folder browser and assign the path to a base folder entry."""
        p = filedialog.askdirectory(title=f"Select base folder for {key}")
        if p:
            settings.set_base_folder_by_key(key, p)
            logger.info(f"Folder set: {key}")
            if hasattr(self, "_bf_path_labels") and key in self._bf_path_labels:
                display_path = p if len(p) < 50 else "…" + p[-47:]
                self._bf_path_labels[key].config(
                    text=f"📁 {display_path}", fg=GREEN, cursor="hand2")
                self._bf_path_labels[key].bind(
                    "<Button-1>", lambda e, k=key: self._assign_path_for_key(k))
            else:
                self._refresh_bf_list()

    def _assign_zip_for_key(self, key: str):
        """Open a ZIP browser and assign the zip path to a base folder entry."""
        p = filedialog.askopenfilename(
            title=f"Select ZIP file for {key}",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        )
        if p:
            settings.set_base_folder_by_key(key, p)
            logger.info(f"ZIP set: {key}")
            if hasattr(self, "_bf_path_labels") and key in self._bf_path_labels:
                display_path = p if len(p) < 50 else "…" + p[-47:]
                self._bf_path_labels[key].config(
                    text=f"📦 {display_path}", fg=ACCENT2, cursor="hand2")
                self._bf_path_labels[key].bind(
                    "<Button-1>", lambda e, k=key: self._assign_path_for_key(k))
            else:
                self._refresh_bf_list()

    def _restore_default_base_folders(self):
        """Restore all default entries (doesn't remove user-added ones, doesn't overwrite paths)."""
        settings.restore_default_base_folders()
        logger.success("Base folder list reset to defaults.")
        self._refresh_bf_list()

    def _refresh_bf_list(self):
        """Rebuild the scrollable base folder list with per-row widgets."""
        if not hasattr(self, "bf_scroll_frame"):
            return

        # Temporarily unbind Configure to avoid scrollregion recalc per widget
        self.bf_scroll_frame.unbind("<Configure>")

        # Clear existing rows
        for w in self.bf_scroll_frame.winfo_children():
            w.destroy()

        self._bf_path_labels = {}   # key -> path_label widget (for in-place updates)

        base_folders = settings.get("base_folders", {})

        if not base_folders:
            tk.Label(self.bf_scroll_frame, text="  No base folders. Click 'Restore Defaults'.",
                     bg=BG3, fg=TEXT_DIM, font=FONT_SMALL, anchor="w",
                     pady=8).pack(fill="x")
            self._rebind_bf_configure()
            return

        # Build label lookup: {fighter: {group_key: label}}
        _label_cache = {}
        def _get_label(fighter, group_key):
            if fighter not in _label_cache:
                _label_cache[fighter] = {
                    g["key"]: g["label"]
                    for g in fighter_db.get_base_groups(fighter)
                }
            return _label_cache[fighter].get(group_key, group_key)

        # Group entries by fighter name — use longest-match to handle underscore names
        def _parse_bf_key(key):
            for fname in sorted(fighter_db.FIGHTER_NAMES, key=len, reverse=True):
                if key.startswith(fname + "_"):
                    return fname, key[len(fname) + 1:]
            parts = key.split("_", 1)
            return parts[0], (parts[1] if len(parts) > 1 else "")

        grouped = {}
        for key in base_folders.keys():
            fighter, group_part = _parse_bf_key(key)
            if fighter not in grouped:
                grouped[fighter] = []
            grouped[fighter].append((key, group_part, base_folders[key]))

        # Sort fighters by official ROSTER_ORDER, unknown fighters go at the end alphabetically
        roster_index = {name: i for i, name in enumerate(fighter_db.ROSTER_ORDER)}
        sorted_fighters = sorted(
            grouped.keys(),
            key=lambda f: (roster_index.get(f, 9999), f)
        )

        for fighter_name in sorted_fighters:
            entries = grouped[fighter_name]
            display_name = fighter_db.get_display_name(fighter_name)

            # Check if ALL entries for this fighter are missing a path
            all_missing = all(not path for _, _, path in entries)
            any_missing = any(not path for _, _, path in entries)

            # Fighter header row — red if all bases missing, orange if some missing
            if all_missing:
                header_fg = RED
                header_bg = BG4
                missing_badge = "  ⚠ no base"
                badge_fg = RED
            elif any_missing:
                header_fg = ORANGE
                header_bg = BG4
                missing_badge = "  ⚠ incomplete"
                badge_fg = ORANGE
            else:
                header_fg = ACCENT
                header_bg = BG4
                missing_badge = ""
                badge_fg = ORANGE

            header = tk.Frame(self.bf_scroll_frame, bg=header_bg)
            header.pack(fill="x", pady=(6, 0), padx=2)
            tk.Label(header, text=f"  {display_name}  ({fighter_name})",
                     bg=header_bg, fg=header_fg, font=FONT_SMALL, anchor="w",
                     pady=3).pack(side="left")
            if missing_badge:
                tk.Label(header, text=missing_badge,
                         bg=header_bg, fg=badge_fg, font=FONT_SMALL,
                         anchor="w").pack(side="left")

            # Entry rows
            for key, group_part, path in entries:
                row = tk.Frame(self.bf_scroll_frame, bg=BG3)
                row.pack(fill="x", padx=2, pady=1)

                # ✕ delete button
                _key = key  # closure capture
                del_btn = tk.Button(
                    row, text="✕", command=lambda k=_key: self._remove_base_folder_by_key(k),
                    bg=BG3, fg=RED, font=("Consolas", 9, "bold"),
                    relief="flat", bd=0, cursor="hand2", padx=4, pady=0,
                    activebackground=BG3, activeforeground=ACCENT2,
                )
                del_btn.pack(side="left", padx=(4, 2))

                # Group label
                display_label = _get_label(fighter_name, group_part)
                tk.Label(row, text=display_label, bg=BG3, fg=TEXT,
                         font=FONT_MONO, width=22, anchor="w").pack(side="left", padx=(0, 4))

                # Path display — clickable to assign folder
                is_zip_path = path.lower().endswith(".zip") if path else False
                if path:
                    display_path = path if len(path) < 50 else "…" + path[-47:]
                    icon = "📦" if is_zip_path else "📁"
                    path_label = tk.Label(
                        row, text=f"{icon} {display_path}", bg=BG3,
                        fg=ACCENT2 if is_zip_path else GREEN,
                        font=FONT_SMALL, anchor="w", cursor="hand2",
                    )
                    path_label.pack(side="left", fill="x", expand=True)
                    path_label.bind("<Button-1>", lambda e, k=_key: self._assign_path_for_key(k))
                else:
                    path_label = tk.Label(
                        row, text="(no path — click 📁 or 📦)",
                        bg=BG3, fg=TEXT_MUTED, font=FONT_SMALL,
                        anchor="w", cursor="hand2",
                    )
                    path_label.pack(side="left", fill="x", expand=True)
                    path_label.bind("<Button-1>", lambda e, k=_key: self._assign_path_for_key(k))

                self._bf_path_labels[_key] = path_label

                # ZIP browse button
                zip_btn = tk.Button(
                    row, text="📦",
                    command=lambda k=_key: self._assign_zip_for_key(k),
                    bg=BG3, fg=ACCENT2, font=FONT_SMALL,
                    relief="flat", bd=0, cursor="hand2", padx=4,
                    activebackground=BG4, activeforeground=ACCENT,
                )
                zip_btn.pack(side="right", padx=(0, 2))

                # Folder browse button
                browse_btn = tk.Button(
                    row, text="📁",
                    command=lambda k=_key: self._assign_path_for_key(k),
                    bg=BG3, fg=TEXT_DIM, font=FONT_SMALL,
                    relief="flat", bd=0, cursor="hand2", padx=4,
                    activebackground=BG4, activeforeground=ACCENT,
                )
                browse_btn.pack(side="right", padx=(2, 0))

        self._rebind_bf_configure()

    def _rebind_bf_configure(self):
        """Re-bind the Configure event and update the scroll region."""
        self.root.update_idletasks()
        self.bf_canvas.configure(scrollregion=self.bf_canvas.bbox("all"))
        self.bf_scroll_frame.bind(
            "<Configure>",
            lambda e: self.bf_canvas.configure(scrollregion=self.bf_canvas.bbox("all"))
        )

    # ═════════════════════════════════════════════════════════════════════════
    #  ACTIONS: PLUGINS
    # ═════════════════════════════════════════════════════════════════════════
    def _refresh_plugin_list(self):
        if not hasattr(self, "plugin_listbox"):
            return
        self.plugin_listbox.delete(0, "end")
        try:
            from core import plugin_loader
            plugins = plugin_loader.get_loaded_plugins()
            if not plugins:
                self.plugin_listbox.insert("end", "  No plugins loaded.")
                self.plugin_listbox.itemconfig("end", fg=TEXT_DIM)
            else:
                for p in plugins:
                    desc = f" — {p.description}" if p.description else ""
                    self.plugin_listbox.insert("end",
                        f"  {p.name} v{p.version}{desc}")
                    self.plugin_listbox.itemconfig("end", fg=GREEN)
        except Exception:
            self.plugin_listbox.insert("end", "  Plugin system not available.")
            self.plugin_listbox.itemconfig("end", fg=TEXT_DIM)

    def _reload_plugins(self):
        try:
            from core import plugin_loader
            plugin_loader.load_plugins(app=self)
            self._refresh_plugin_list()
            logger.success("Plugins reloaded.")
        except Exception as e:
            logger.error(f"Failed to reload plugins: {e}")

    def _open_plugins_folder(self):
        from core import plugin_loader
        plugins_dir = plugin_loader._plugin_dir
        os.makedirs(plugins_dir, exist_ok=True)
        # Cross-platform open
        try:
            if sys.platform == "win32":
                os.startfile(plugins_dir)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", plugins_dir])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", plugins_dir])
        except Exception:
            logger.info(f"Plugins folder: {os.path.abspath(plugins_dir)}")

    # ═════════════════════════════════════════════════════════════════════════
    #  SETTINGS / ABOUT
    # ═════════════════════════════════════════════════════════════════════════
    def _open_settings(self):
        import sys as _sys
        from gui.theme import THEME_NAMES
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.configure(bg=BG)
        win.geometry("560x660")
        win.grab_set()

        pad = dict(padx=16, pady=6)
        section_header(win, "DATA FILES").pack(anchor="w", **pad)

        # Hashes file
        row1 = tk.Frame(win, bg=BG)
        row1.pack(fill="x", **pad)
        styled_label(row1, "Hashes File", width=16, anchor="w").pack(side="left")
        h_var = tk.StringVar(value=settings.get("hashes_file", ""))
        styled_entry(row1, h_var, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=(0, 8))

        def _browse():
            p = filedialog.askopenfilename(
                filetypes=[("Text", "*.txt"), ("All", "*.*")])
            if p:
                h_var.set(p)
        styled_button(row1, "…", _browse).pack(side="left")

        # Dir info file
        row1b = tk.Frame(win, bg=BG)
        row1b.pack(fill="x", **pad)
        styled_label(row1b, "Dir Info File", width=16, anchor="w").pack(side="left")
        di_var = tk.StringVar(value=settings.get("dir_info_file", ""))
        styled_entry(row1b, di_var, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=(0, 8))

        def _browse_di():
            p = filedialog.askopenfilename(
                filetypes=[("JSON", "*.json"), ("All", "*.*")])
            if p:
                di_var.set(p)
        styled_button(row1b, "…", _browse_di).pack(side="left")

        # Max slots
        row2 = tk.Frame(win, bg=BG)
        row2.pack(fill="x", **pad)
        styled_label(row2, "Max Slots", width=14, anchor="w").pack(side="left")
        ms_var = tk.StringVar(value=str(settings.get("max_slots", 256)))
        styled_entry(row2, ms_var, width=6).pack(side="left")

        # Theme
        row3 = tk.Frame(win, bg=BG)
        row3.pack(fill="x", **pad)
        styled_label(row3, "Theme", width=14, anchor="w").pack(side="left")
        theme_var = tk.StringVar(value=settings.get("theme", "Dark"))
        theme_combo = styled_combo(row3, theme_var, THEME_NAMES, width=16)
        theme_combo.pack(side="left")
        restart_note = tk.Label(row3, text="", bg=BG, fg=ORANGE, font=FONT_SMALL)
        restart_note.pack(side="left", padx=(8, 0))

        def _on_theme_change(*_):
            if theme_var.get() != settings.get("theme", "Dark"):
                restart_note.config(text="↺ reopen to apply")
            else:
                restart_note.config(text="")
        theme_var.trace_add("write", _on_theme_change)

        # Font size
        row4 = tk.Frame(win, bg=BG)
        row4.pack(fill="x", **pad)
        styled_label(row4, "Font Size", width=14, anchor="w").pack(side="left")
        size_var = tk.StringVar(value=str(settings.get("font_size", 11)))
        size_combo = styled_combo(row4, size_var,
                                  ["10", "11", "12", "13", "14", "15", "16"], width=6)
        size_combo.pack(side="left")
        tk.Label(row4, text="  (applies after restart)", bg=BG, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left")

        # Special cases
        row5 = tk.Frame(win, bg=BG)
        row5.pack(fill="x", **pad)
        sc_var = tk.BooleanVar(value=settings.get("special_cases", True))
        sc_check = styled_check(row5, "Special cases mode", sc_var)
        sc_check.pack(side="left")
        Tooltip(sc_check,
            "Treats multi-part fighters as one when reslotting:\n"
            "  Aegis     — eflame + elight + element\n"
            "  Ice Climbers — popo + nana\n"
            "  Pokemon Trainer — ptrainer + the three Pokemon")

        separator(win).pack(fill="x", padx=16, pady=8)

        # Copy extra files to output
        section_header(win, "COPY TO OUTPUT FOLDER").pack(anchor="w", padx=16, pady=(4, 2))
        tk.Label(win, text="  Keep these loose files from the mod root when reslotting:",
                 bg=BG, fg=TEXT_DIM, font=FONT_SMALL).pack(anchor="w", padx=16)

        copy_row = tk.Frame(win, bg=BG)
        copy_row.pack(fill="x", padx=16, pady=4)
        webp_var  = tk.BooleanVar(value=settings.get("copy_webp",  True))
        txt_var   = tk.BooleanVar(value=settings.get("copy_txt",   True))
        png_var   = tk.BooleanVar(value=settings.get("copy_png",   True))
        toml_var  = tk.BooleanVar(value=settings.get("copy_toml",  True))
        chk_webp  = styled_check(copy_row, "Preview  (.webp)", webp_var)
        chk_webp.pack(side="left", padx=(0, 16))
        Tooltip(chk_webp, "preview.webp — thumbnail shown in mod managers")
        chk_txt   = styled_check(copy_row, "Readme/Credits  (.txt)", txt_var)
        chk_txt.pack(side="left", padx=(0, 16))
        Tooltip(chk_txt, "README.txt, credits.txt, etc.")
        chk_png   = styled_check(copy_row, "Images  (.png)", png_var)
        chk_png.pack(side="left", padx=(0, 16))
        Tooltip(chk_png, "Decorative PNGs placed at the mod root (e.g. [deleteme].png)")
        chk_toml  = styled_check(copy_row, "Mod info  (.toml)", toml_var)
        chk_toml.pack(side="left")
        Tooltip(chk_toml, "info.toml used by Arcadia and some mod managers")

        # Effects
        section_header(win, "EFFECTS").pack(anchor="w", padx=16, pady=(4, 2))
        tk.Label(win, text="  Controls how effect files are handled when reslotting:",
                 bg=BG, fg=TEXT_DIM, font=FONT_SMALL).pack(anchor="w", padx=16)

        eff_row = tk.Frame(win, bg=BG)
        eff_row.pack(fill="x", padx=16, pady=4)
        save_eff_var   = tk.BooleanVar(value=settings.get("save_effects",          True))
        reslot_eff_var = tk.BooleanVar(value=settings.get("reslot_slotted_effects", True))

        chk_save_eff = styled_check(eff_row, "Save effects", save_eff_var)
        chk_save_eff.pack(side="left", padx=(0, 16))
        Tooltip(chk_save_eff,
            "Copy unslotted effects (ef_fighter.eff, trail/) to the output folder as-is.\n"
            "Required when 'Reslot slotted effects' is on.")

        chk_reslot_eff = styled_check(eff_row, "Reslot slotted effects", reslot_eff_var)
        chk_reslot_eff.pack(side="left")
        Tooltip(chk_reslot_eff,
            "Rename and carry over slotted effects (ef_fighter_c00.eff, trail_c00/)\n"
            "when reslotting. Forces 'Save effects' on.\n"
            "Uncheck to ignore effect files entirely.")

        def _on_reslot_eff_toggle(*_):
            if reslot_eff_var.get():
                save_eff_var.set(True)
                chk_save_eff.config(state="disabled")
            else:
                chk_save_eff.config(state="normal")

        reslot_eff_var.trace_add("write", _on_reslot_eff_toggle)
        _on_reslot_eff_toggle()  # apply initial state

        # Reslot output naming
        section_header(win, "RESLOT OUTPUT").pack(anchor="w", padx=16, pady=(4, 2))
        tk.Label(win, text="  Controls how the output folder is named after reslotting:",
                 bg=BG, fg=TEXT_DIM, font=FONT_SMALL).pack(anchor="w", padx=16)

        rename_row = tk.Frame(win, bg=BG)
        rename_row.pack(fill="x", padx=16, pady=4)
        smart_rename_var = tk.BooleanVar(value=settings.get("smart_output_rename", False))
        chk_smart = styled_check(rename_row, "Smart rename (replace slot in folder name)", smart_rename_var)
        chk_smart.pack(side="left")
        Tooltip(chk_smart,
            "If the folder name already contains a slot like [c00] or (c00),\n"
            "replace it with the target slot instead of appending (cXX).\n"
            "Example: 'Skin [c00]' reslotted to c06 → 'Skin [c06]'\n"
            "Without this: 'Skin [c00] (c06)'")

        separator(win).pack(fill="x", padx=16, pady=8)

        def _save():
            settings.put("hashes_file", h_var.get())
            self.hashes_var.set(h_var.get())
            settings.put("dir_info_file", di_var.get())
            try:
                settings.put("max_slots", int(ms_var.get()))
            except ValueError:
                pass
            settings.put("special_cases", sc_var.get())
            settings.put("copy_webp",  webp_var.get())
            settings.put("copy_txt",   txt_var.get())
            settings.put("copy_png",   png_var.get())
            settings.put("copy_toml",  toml_var.get())
            settings.put("save_effects",           save_eff_var.get())
            settings.put("reslot_slotted_effects", reslot_eff_var.get())
            settings.put("smart_output_rename",    smart_rename_var.get())
            theme_changed = theme_var.get() != settings.get("theme", "Dark")
            size_changed  = size_var.get()  != str(settings.get("font_size", 11))
            settings.put("theme", theme_var.get())
            try:
                settings.put("font_size", int(size_var.get()))
            except ValueError:
                pass
            logger.info("Saved.")
            win.destroy()
            if theme_changed or size_changed:
                messagebox.showinfo(
                    "Restart required",
                    "Close and reopen SmashModManager to apply the new theme / font size.",
                )

        styled_button(win, "Save", _save, accent=True).pack(anchor="e", padx=16, pady=12)

    def _show_about(self):
        messagebox.showinfo(
            "About Smash Mod Manager",
            "Smash Mod Manager v4.0\n\n"
            "Modular tool for SSBU mod management.\n"
            "Reslot, effect slot, batch validate, missing file completion.\n\n"
            "Reslotter core by BluJay & Coolsonickirby\n"
            "Effect slotter integrated from community tools\n"
            "Missing file logic based on Fix.Cmd by zZJ0K3R",
        )
