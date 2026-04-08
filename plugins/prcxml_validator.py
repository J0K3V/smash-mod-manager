"""
prcxml_validator.py — Validate and update PRCXML against actual mod slots.

Scans a folder of mods to detect fighter slots, compares against the PRCXML,
and updates the PRCXML if discrepancies are found.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import re
import threading
import xml.etree.ElementTree as ET
import unicodedata

PLUGIN_NAME = "PRCXML Validator"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Validate and update PRCXML against actual mod slots"

_app = None

try:
    from core import settings as app_settings
except Exception:
    app_settings = None

try:
    from gui import theme as app_theme
except Exception:
    app_theme = None

try:
    from core import fighter_db
except Exception:
    fighter_db = None


def register(app):
    """Called when plugin is loaded. Receives the app instance."""
    global _app
    _app = app


class PRCXMLManager:
    """Handles reading and writing ui_chara_db.prcxml files."""

    def __init__(self, prcxml_path: str):
        self.prcxml_path = prcxml_path
        self.tree = None
        self.root = None
        self.fighter_slots = {}
        self._fighter_nodes = {}
        self._db_root_mode = False

    def read(self) -> bool:
        """Parse the PRCXML file and extract fighter slot state."""
        try:
            self.tree = ET.parse(self.prcxml_path)
            self.root = self.tree.getroot()
            self._extract_slots()
            return True
        except Exception as e:
            print(f"Failed to read PRCXML: {e}")
            return False

    def _extract_slots(self):
        """Extract fighter -> slots mapping from the XML tree."""
        self.fighter_slots = {}
        self._fighter_nodes = {}
        self._db_root_mode = False

        char_nodes = list(self.root.findall(".//character"))
        if char_nodes:
            for char_node in char_nodes:
                fighter_key = self._detect_fighter_key(char_node)
                if not fighter_key:
                    continue

                self._fighter_nodes[fighter_key] = char_node

                slots = self._get_slots_for_char(char_node)
                if slots:
                    self.fighter_slots[fighter_key] = slots
            return

        self._db_root_mode = True
        for struct_node in self.root.findall('.//list[@hash="db_root"]/struct'):
            fighter_key = self._detect_fighter_key_from_struct(struct_node)
            if not fighter_key:
                continue

            self._fighter_nodes[fighter_key] = struct_node
            slots = self._get_slots_for_struct(struct_node)
            if slots:
                self.fighter_slots[fighter_key] = slots

    @staticmethod
    def _normalize_fighter_token(token: str) -> str:
        val = (token or "").strip().lower()
        if not val:
            return ""

        # Trim common narrator suffixes first so explicit names (e.g. roy_append)
        # resolve correctly before alias conversion.
        val = re.sub(r"(?:_append|_article|_c\d{1,3})+$", "", val)

        # Normalize common narrator labels to internal fighter ids.
        alias = {
            "dsamus": "samusd",
            "iceclimber": "ice_climber",
            "poketrainer": "pokemontrainer",
            "robot": "rob",
            "murabito": "villager",
            "miisword": "miiswordsman",
            "wii": "wiifit",
            "roy": "koopajr",  # koopa jr alt announcer labels (larry/roy/etc.)
            "larry": "koopajr",
            "wendy": "koopajr",
            "iggy": "koopajr",
            "morton": "koopajr",
            "lemmy": "koopajr",
            "ludwig": "koopajr",
        }
        if val in alias:
            val = alias[val]

        if fighter_db is not None:
            known = set(getattr(fighter_db, "FIGHTER_NAMES", []))
            if val in known:
                return val
            return ""
        return val

    def _detect_fighter_key_from_struct(self, struct_node) -> str:
        """Detect fighter key from db_root struct using characall labels."""
        for h40 in struct_node.findall("./hash40"):
            txt = (h40.text or "").strip().lower()
            if not txt:
                continue
            # Clean up whitespace (tabs, spaces, newlines) that might be embedded
            txt = re.sub(r'\s+', '', txt)
            m = re.search(r"vc_narration_characall_([a-z0-9_]+)", txt)
            if not m:
                continue
            token = m.group(1)
            token = re.sub(r"(?:_append|_article|_c\d{1,3})+$", "", token)
            fighter = self._normalize_fighter_token(token)
            if fighter:
                return fighter
        return ""

    @staticmethod
    def _parse_int_text(value: str, default: int = -1) -> int:
        try:
            return int((value or "").strip())
        except Exception:
            return default

    def _get_slots_for_struct(self, struct_node) -> list[str]:
        """Extract slots from db_root struct (nXX_index, characall_label_cXX, color_num)."""
        slots = set()
        color_num = -1

        for b in struct_node.findall("./byte"):
            h = (b.get("hash") or "").strip().lower()
            m = re.match(r"n(\d{2,3})_index$", h)
            if m:
                num = int(m.group(1))
                if 0 <= num <= 255:
                    slots.add(f"c{num:02d}")
                continue
            if h == "color_num":
                color_num = self._parse_int_text(b.text, -1)

        for h40 in struct_node.findall("./hash40"):
            h = (h40.get("hash") or "").strip().lower()
            m = re.search(r"_c(\d{2,3})$", h)
            if not m:
                continue
            num = int(m.group(1))
            if 0 <= num <= 255:
                slots.add(f"c{num:02d}")

        if color_num > 0:
            for n in range(min(color_num, 256)):
                slots.add(f"c{n:02d}")

        return sorted(slots, key=lambda s: int(s[1:]))

    @staticmethod
    def _detect_fighter_key(char_node) -> str:
        """Best-effort mapping from PRCXML character node to fighter id."""
        known_names = set(getattr(fighter_db, "FIGHTER_NAMES", [])) if fighter_db is not None else set()
        display_to_internal = {}
        if fighter_db is not None:
            for internal, disp in getattr(fighter_db, "DISPLAY_NAMES", {}).items():
                key = unicodedata.normalize("NFKD", str(disp)).encode("ascii", "ignore").decode("ascii").lower()
                key = re.sub(r"[^a-z0-9]+", "", key)
                if key:
                    display_to_internal[key] = internal

        def _normalize_candidate(raw: str) -> str:
            value = (raw or "").strip().lower()
            if not value:
                return ""
            if value.startswith("ui_chara_"):
                value = value[len("ui_chara_"):]
            if "/" in value:
                value = value.rsplit("/", 1)[-1]

            # Direct match first.
            if value in known_names or not known_names:
                return value

            # Match display name forms, e.g. "mr game watch" -> gamewatch.
            compact = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
            compact = re.sub(r"[^a-z0-9]+", "", compact)
            if compact in display_to_internal:
                return display_to_internal[compact]

            # Try trimming common suffixes like _00, _01, _c08.
            trimmed = re.sub(r"(?:_c?\d{1,3})+$", "", value)
            if trimmed in known_names:
                return trimmed

            # Fallback: longest known fighter prefix match at underscore boundary.
            for name in sorted(known_names, key=len, reverse=True):
                if value == name or value.startswith(name + "_"):
                    return name

            return value

        for attr in ("id", "name", "chara_id", "fighter"):
            value = _normalize_candidate(char_node.get(attr) or "")
            if not value:
                continue
            return value

        # Fallback: inspect all attributes and text within the node.
        for _, raw in char_node.attrib.items():
            value = _normalize_candidate(raw)
            if value in known_names:
                return value

        for raw in char_node.itertext():
            value = _normalize_candidate(raw)
            if value in known_names:
                return value
        return ""

    def _get_slots_for_char(self, char_node) -> list[str]:
        """Extract slot numbers for a character node."""
        slots = []

        slots_attr = char_node.get("slots")
        if slots_attr:
            try:
                # Accept formats like "0,1,2", "c00,c01", or mixed tokens.
                slot_nums = []
                for token in re.split(r"[,\s]+", slots_attr.strip()):
                    if not token:
                        continue
                    m = re.search(r"(\d{1,3})", token)
                    if not m:
                        continue
                    num = int(m.group(1))
                    if 0 <= num <= 255:
                        slot_nums.append(num)
                slots = [f"c{num:02d}" for num in sorted(set(slot_nums))]
                if slots:
                    return slots
            except Exception:
                pass

        for slot_elem in char_node.findall(".//slot"):
            slot_id = slot_elem.get("id")
            if slot_id:
                try:
                    m = re.search(r"(\d{1,3})", str(slot_id))
                    if not m:
                        continue
                    num = int(m.group(1))
                    if 0 <= num <= 255:
                        slots.append(f"c{num:02d}")
                except Exception:
                    pass

        return sorted(set(slots))

    def add_slot(self, fighter: str, slot: str):
        """Register a new slot assignment for a fighter."""
        fighter = (fighter or "").strip().lower()
        if not fighter:
            return
        if fighter not in self.fighter_slots:
            self.fighter_slots[fighter] = []
        if slot not in self.fighter_slots[fighter]:
            self.fighter_slots[fighter].append(slot)
            self.fighter_slots[fighter] = sorted(self.fighter_slots[fighter])

    def write(self) -> bool:
        """Update the PRCXML file with new slot assignments."""
        if not self.tree or not self.root:
            return False
        try:
            if self._db_root_mode:
                for fighter, slots in self.fighter_slots.items():
                    struct_node = self._fighter_nodes.get(fighter)
                    if struct_node is None or not slots:
                        continue

                    max_slot = max(int(s[1:]) for s in slots)
                    desired_color_num = max_slot + 1

                    color_node = None
                    for b in struct_node.findall("./byte"):
                        if (b.get("hash") or "").strip().lower() == "color_num":
                            color_node = b
                            break
                    if color_node is None:
                        color_node = ET.SubElement(struct_node, "byte", {"hash": "color_num"})
                    color_node.text = str(desired_color_num)

                self.tree.write(self.prcxml_path, encoding="utf-8", xml_declaration=True)
                return True

            for fighter, slots in self.fighter_slots.items():
                char_node = self._fighter_nodes.get(fighter)
                if char_node is None:
                    continue
                if slots:
                    slot_nums = [int(s[1:]) for s in slots]
                    slots_str = ",".join(str(n) for n in sorted(slot_nums))
                    char_node.set("slots", slots_str)

            self.tree.write(self.prcxml_path, encoding="utf-8", xml_declaration=True)
            return True
        except Exception as e:
            print(f"Failed to write PRCXML: {e}")
            return False


def show_validator_dialog():
    """Show the PRCXML Validator UI."""
    if not _app:
        print("Error: App instance not available")
        return

    dialog = tk.Toplevel(_app.root)
    dialog.title("Validador PRCXML")
    dialog.geometry("760x600")
    dialog.configure(bg=(app_theme.BG if app_theme else "#1a1a1a"))
    dialog.minsize(700, 500)
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
        dialog, text="Validador PRCXML", bg=BG, fg=ACCENT,
        font=FONT_HEADER
    ).pack(pady=10)

    scroll_wrap = tk.Frame(dialog, bg=BG)
    scroll_wrap.pack(fill="both", expand=True)

    scroll_canvas = tk.Canvas(scroll_wrap, bg=BG, highlightthickness=0, bd=0)
    scroll_bar = tk.Scrollbar(scroll_wrap, orient="vertical", command=scroll_canvas.yview)
    scroll_canvas.configure(yscrollcommand=scroll_bar.set)
    scroll_canvas.pack(side="left", fill="both", expand=True)
    scroll_bar.pack(side="right", fill="y")

    body = tk.Frame(scroll_canvas, bg=BG)
    body_window = scroll_canvas.create_window((0, 0), window=body, anchor="nw")

    def _sync_scroll_region(_event=None):
        scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

    def _sync_body_width(event):
        scroll_canvas.itemconfigure(body_window, width=event.width)

    body.bind("<Configure>", _sync_scroll_region)
    scroll_canvas.bind("<Configure>", _sync_body_width)

    prcxml_path = tk.StringVar(value=(app_settings.get("prcxml_validator_last_prcxml", "") if app_settings else ""))
    mods_folder = tk.StringVar(value=(app_settings.get("prcxml_validator_last_mods", "") if app_settings else ""))
    detect_from_names_var = tk.BooleanVar(
        value=(app_settings.get("prcxml_validator_detect_from_names", True) if app_settings else True)
    )
    ignore_moveset_name_var = tk.BooleanVar(
        value=(app_settings.get("prcxml_validator_ignore_moveset_name", True) if app_settings else True)
    )
    ignore_moveset_pattern_var = tk.BooleanVar(
        value=(app_settings.get("prcxml_validator_ignore_moveset_pattern", True) if app_settings else True)
    )

    def _persist_setting(key: str, value: str):
        if app_settings is not None:
            app_settings.put(key, value)

    def _persist_bool(key: str, value: bool):
        if app_settings is not None:
            app_settings.put(key, value)

    def _ensure_dialog_front():
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()

    def _label_text(path: str) -> str:
        if not path:
            return "(not selected)"
        base = os.path.basename(path)
        return base if base else path

    def select_prcxml():
        path = filedialog.askopenfilename(
            parent=dialog,
            title="Select ui_chara_db.prcxml",
            filetypes=[("PRCXML files", "*.prcxml"), ("All files", "*.*")]
        )
        _ensure_dialog_front()
        if path:
            prcxml_path.set(path)
            _persist_setting("prcxml_validator_last_prcxml", path)
            prcxml_label.config(text=_label_text(path))

    def select_mods():
        path = filedialog.askdirectory(parent=dialog, title="Select folder with mods to validate")
        _ensure_dialog_front()
        if path:
            mods_folder.set(path)
            _persist_setting("prcxml_validator_last_mods", path)
            mods_label.config(text=_label_text(path))

    frame1 = tk.Frame(body, bg=BG)
    frame1.pack(fill="x", padx=15, pady=10)
    tk.Label(frame1, text="Archivo PRCXML:", bg=BG, fg=TEXT, font=FONT_UI).pack(anchor="w")
    prcxml_label = tk.Label(frame1, text=_label_text(prcxml_path.get()), bg=BG, fg=TEXT_DIM, font=FONT_SMALL)
    prcxml_label.pack(anchor="w", padx=(0, 5))
    tk.Button(
        frame1, text="Examinar...", command=select_prcxml, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=10, pady=4, cursor="hand2"
    ).pack(anchor="w", pady=(5, 0))

    frame2 = tk.Frame(body, bg=BG)
    frame2.pack(fill="x", padx=15, pady=10)
    tk.Label(frame2, text="Carpeta de Mods:", bg=BG, fg=TEXT, font=FONT_UI).pack(anchor="w")
    mods_label = tk.Label(frame2, text=_label_text(mods_folder.get()), bg=BG, fg=TEXT_DIM, font=FONT_SMALL)
    mods_label.pack(anchor="w", padx=(0, 5))
    tk.Button(
        frame2, text="Examinar...", command=select_mods, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=10, pady=4, cursor="hand2"
    ).pack(anchor="w", pady=(5, 0))

    options_frame = tk.Frame(body, bg=BG)
    options_frame.pack(fill="x", padx=15, pady=(0, 8))
    tk.Checkbutton(
        options_frame,
        text="Detectar slots desde nombres de carpetas de mods (ej: c00, c08, etc.)",
        variable=detect_from_names_var,
        bg=BG,
        fg=TEXT,
        selectcolor=BG3,
        activebackground=BG,
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        command=lambda: _persist_bool("prcxml_validator_detect_from_names", detect_from_names_var.get()),
    ).pack(anchor="w")

    tk.Checkbutton(
        options_frame,
        text="Ignorar mods con 'moveset' en el nombre",
        variable=ignore_moveset_name_var,
        bg=BG,
        fg=TEXT,
        selectcolor=BG3,
        activebackground=BG,
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        command=lambda: _persist_bool("prcxml_validator_ignore_moveset_name", ignore_moveset_name_var.get()),
    ).pack(anchor="w")

    tk.Checkbutton(
        options_frame,
        text="Ignore mods with suspicious slot patterns (gaps, high slot numbers)",
        variable=ignore_moveset_pattern_var,
        bg=BG,
        fg=TEXT,
        selectcolor=BG3,
        activebackground=BG,
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        command=lambda: _persist_bool("prcxml_validator_ignore_moveset_pattern", ignore_moveset_pattern_var.get()),
    ).pack(anchor="w")

    info_frame = tk.Frame(body, bg=BG)
    info_frame.pack(fill="x", padx=15, pady=10)
    tk.Label(
        info_frame,
        text=(
            "Scans the mods folder to detect fighter slots and compares them "
            "against PRCXML. Shows discrepancies and can validate/update the PRCXML."
        ),
        bg=BG, fg=TEXT_DIM, font=FONT_SMALL, justify="left", anchor="w"
    ).pack(fill="x")

    def _open_results_window(title: str, content: list[str]):
        """Open a window showing validation results."""
        res_win = tk.Toplevel(dialog)
        res_win.title(title)
        res_win.geometry("700x400")
        res_win.configure(bg=BG)
        res_win.resizable(True, True)
        res_win.transient(dialog)
        res_win.grab_set()

        title_label = tk.Label(res_win, text=title, bg=BG, fg=ACCENT, font=FONT_HEADER)
        title_label.pack(anchor="w", padx=12, pady=(10, 2))

        text_widget = tk.Text(
            res_win,
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
        )
        text_widget.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        for line in content:
            text_widget.config(state="normal")
            text_widget.insert("end", line + "\n")
            text_widget.config(state="disabled")

        btn_frame = tk.Frame(res_win, bg=BG)
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        tk.Button(
            btn_frame,
            text="Close",
            command=res_win.destroy,
            bg=BG3,
            fg=TEXT,
            relief="flat",
            bd=0,
            padx=18,
            pady=6,
            cursor="hand2",
            font=FONT_UI,
        ).pack(side="left")

        return res_win

    def _normalize_slot(value: str) -> str | None:
        token = (value or "").strip().lower()
        if not token:
            return None
        if token.startswith("c"):
            token = token[1:]
        if not token.isdigit():
            return None
        num = int(token)
        if num < 0 or num > 255:
            return None
        return f"c{num:02d}"

    def _extract_slot_from_name(folder_name: str) -> str | None:
        m = re.search(r"(?i)(?:^|[^a-z0-9])c(\d{1,3})(?:[^a-z0-9]|$)", folder_name)
        if m:
            return _normalize_slot(m.group(1))
        m = re.search(r"(?:^|[^a-z0-9])(\d{1,3})(?:[^a-z0-9]|$)", folder_name)
        if m:
            return _normalize_slot(m.group(1))
        return None

    def _is_probable_moveset(slots: list[str], mod_name: str, check_name: bool, check_pattern: bool) -> bool:
        """Detect if slots are likely from a moveset mod (false positives).

        Args:
            slots: List of detected slot codes (e.g., ['c00', 'c06', 'c120'])
            mod_name: The mod folder name
            check_name: If True, check for "moveset" in the folder name
            check_pattern: If True, check for suspicious slot patterns (gaps, high numbers)
        """
        if not slots:
            return False

        # Check name if enabled
        if check_name and "moveset" in mod_name.lower():
            return True

        # Check patterns if enabled
        if check_pattern:
            slot_nums = []
            for s in slots:
                try:
                    num = int(s[1:])
                    slot_nums.append(num)
                except (ValueError, IndexError):
                    pass

            if slot_nums:
                # Any slot >= 100 is suspicious (costume slots rarely go past c99)
                if any(num >= 100 for num in slot_nums):
                    return True

                # Check for suspicious large gaps between slots
                # Large gaps indicate separate resource structures, not costume slots
                if len(slot_nums) >= 2:
                    sorted_nums = sorted(slot_nums)
                    for i in range(len(sorted_nums) - 1):
                        gap = sorted_nums[i + 1] - sorted_nums[i]
                        # Gap > 25 is very suspicious
                        if gap > 25:
                            return True

        return False

    def validate():
        if not prcxml_path.get():
            messagebox.showerror("Error", "Por favor selecciona un archivo PRCXML", parent=dialog)
            return
        if not mods_folder.get():
            messagebox.showerror("Error", "Por favor selecciona una carpeta de mods", parent=dialog)
            return

        progress_win = tk.Toplevel(dialog)
        progress_win.title("PRCXML Validator")
        progress_win.geometry("560x210")
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
        progress_text = tk.StringVar(value="0/0 mods")
        status_text = tk.StringVar(value="Starting validation...")

        tk.Label(progress_win, text="Validando PRCXML", bg=BG, fg=ACCENT, font=FONT_HEADER).pack(
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

        log_text = tk.Text(
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
            height=16,
        )

        action_row = tk.Frame(progress_win, bg=BG)

        def _set_log(lines: list[str]):
            log_text.config(state="normal")
            log_text.delete("1.0", "end")
            for line in lines:
                log_text.insert("end", line + "\n")
            log_text.see("1.0")
            log_text.config(state="disabled")

        def _cancel():
            if state["done"]:
                return
            state["cancel"].set()
            status_text.set("Cancelling... finishing current mod")

        cancel_btn = tk.Button(
            progress_win,
            text="Cancel",
            command=_cancel,
            bg=BG3,
            fg=TEXT,
            relief="flat",
            bd=0,
            padx=18,
            pady=6,
            cursor="hand2",
            font=FONT_UI,
        )
        cancel_btn.pack(anchor="w", padx=12, pady=(10, 0))

        def _close_window():
            if state["done"]:
                try:
                    progress_win.grab_release()
                except Exception:
                    pass
                progress_win.destroy()
                return
            _cancel()

        progress_win.protocol("WM_DELETE_WINDOW", _close_window)

        def _push_event(event):
            with state["events_lock"]:
                state["events"].append(event)

        def _apply_missing_slots_to_prcxml(results: dict) -> tuple[bool, str]:
            try:
                prcxml_file = prcxml_path.get()
                manager = PRCXMLManager(prcxml_file)
                if not manager.read():
                    return False, f"Failed to read PRCXML: {prcxml_file}"

                VANILLA = {f"c{n:02d}" for n in range(8)}
                fighters_to_fix = set()

                # Collect fighters from both discrepancies and over_provisioned
                for disc in results.get("discrepancies", []):
                    fighter = disc.get("fighter", "")
                    detected = disc.get("detected", [])
                    if fighter and detected:
                        manager.fighter_slots[fighter] = sorted(
                            detected, key=lambda s: int(s[1:])
                        )
                        fighters_to_fix.add(fighter)

                for entry in results.get("over_provisioned", []):
                    fighter = entry.get("fighter", "")
                    if not fighter:
                        continue

                    detected = entry.get("detected", [])
                    extra = entry.get("extra", [])
                    prcxml = entry.get("prcxml", [])

                    # If detected is empty but we have extra slots, calculate it
                    # as "prcxml minus non-vanilla extra plus vanilla only"
                    if not detected and extra and prcxml:
                        # Fallback: use only vanilla slots (safest assumption)
                        # Next validation will detect if mods need more
                        detected = sorted([s for s in prcxml if s in VANILLA])

                    if detected:
                        manager.fighter_slots[fighter] = sorted(
                            detected, key=lambda s: int(s[1:])
                        )
                        fighters_to_fix.add(fighter)

                # Only write if we actually have fighters to fix
                if not fighters_to_fix:
                    return False, "No fighters to fix"

                # Check if the fighters are in _fighter_nodes
                unfound = [f for f in fighters_to_fix if f not in manager._fighter_nodes]
                if unfound:
                    return False, f"Not found in PRCXML: {', '.join(unfound)}"

                if manager.write():
                    return True, ""
                return False, "Failed to write PRCXML"
            except Exception as e:
                return False, f"Exception: {str(e)[:150]}"

        def _worker():
            results = {
                "prcxml_slots": {},
                "detected_slots": {},
                "discrepancies": [],
                "over_provisioned": [],
                "errors": [],
                "log_lines": [],
                "total_mods": 0,
                "processed_mods": 0,
                "canceled": False,
            }

            try:
                manager = PRCXMLManager(prcxml_path.get())
                if not manager.read():
                    results["errors"].append("Failed to read PRCXML file")
                    return results

                results["prcxml_slots"] = {
                    k: list(v) for k, v in manager.fighter_slots.items()
                }
                results["log_lines"].append("PRCXML cargado exitosamente.")

                try:
                    from core import mod_analyzer
                except Exception:
                    results["errors"].append("Failed to import mod_analyzer")
                    return results

                mods_path = mods_folder.get()
                mod_entries = [
                    name for name in sorted(os.listdir(mods_path))
                    if os.path.isdir(os.path.join(mods_path, name))
                ]

                results["total_mods"] = len(mod_entries)
                if not mod_entries:
                    results["errors"].append("No se encontraron carpetas de mods en la ruta seleccionada")
                    return results

                for idx, mod_name in enumerate(mod_entries, start=1):
                    if state["cancel"].is_set():
                        results["canceled"] = True
                        results["log_lines"].append("Validation cancelled by user.")
                        break

                    _push_event(("progress", idx, len(mod_entries), mod_name))
                    mod_path = os.path.join(mods_path, mod_name)

                    try:
                        analysis = mod_analyzer.analyze(mod_path)
                        fighter = (analysis.get("fighter", "") or "").strip().lower()
                        # Normalize fighter name using same alias rules as PRCXML detection
                        fighter = PRCXMLManager._normalize_fighter_token(fighter)
                        slots = list(analysis.get("slots", []))

                        # Fallback: extract slot from folder name when detection fails.
                        # This is important for mods with non-standard folder structures.
                        # Always try this fallback, don't wait for the checkbox.
                        if not slots:
                            name_slot = _extract_slot_from_name(mod_name)
                            if name_slot:
                                slots.append(name_slot)

                        # Skip probable moveset mods based on detection settings
                        check_name = ignore_moveset_name_var.get()
                        check_pattern = ignore_moveset_pattern_var.get()

                        if (check_name or check_pattern) and _is_probable_moveset(slots, mod_name, check_name, check_pattern):
                            reason = "moveset mod"
                            reasons = []
                            if check_name and "moveset" in mod_name.lower():
                                reasons.append("name")
                            if check_pattern:
                                reasons.append("pattern")
                            if reasons:
                                reason += f" ({', '.join(reasons)})"
                            results["log_lines"].append(f"IGNORAR {mod_name}: {reason}")
                            continue

                        if not fighter:
                            results["log_lines"].append(f"IGNORAR {mod_name}: luchador no detectado")
                            continue

                        # Check if fighter exists in PRCXML
                        if fighter not in results["prcxml_slots"]:
                            results["log_lines"].append(f"IGNORAR {mod_name}: luchador '{fighter}' no encontrado en PRCXML")
                            continue

                        if not slots:
                            results["log_lines"].append(f"IGNORAR {mod_name}: slots no detectados")
                            continue

                        detected_slots = sorted(
                            slots,
                            key=lambda s: int((s or "c00")[1:]) if len(s) > 1 else 0,
                        )

                        if fighter not in results["detected_slots"]:
                            results["detected_slots"][fighter] = set()
                        for slot in detected_slots:
                            results["detected_slots"][fighter].add(slot)

                        results["processed_mods"] += 1
                    except Exception as e:
                        results["errors"].append(f"Error analizando {mod_name}: {e}")

                VANILLA_SLOTS = {f"c{n:02d}" for n in range(8)}

                for fighter in sorted(results["detected_slots"].keys()):
                    detected = sorted(results["detected_slots"][fighter], key=lambda s: int(s[1:]))
                    prcxml_data = sorted(results["prcxml_slots"].get(fighter, []), key=lambda s: int(s[1:]))

                    # Detect missing slots, but exclude vanilla (c00-c07) since those are always valid
                    missing_in_prcxml = sorted(
                        [s for s in (set(detected) - set(prcxml_data)) if s not in VANILLA_SLOTS],
                        key=lambda s: int(s[1:])
                    )
                    extra_in_prcxml = sorted(set(prcxml_data) - set(detected), key=lambda s: int(s[1:]))

                    # Vanilla slots (c00-c07) are always present in the PRCXML even without
                    # mods on top — suppress INFO noise for those.
                    non_vanilla_extra = [s for s in extra_in_prcxml if s not in VANILLA_SLOTS]

                    # IMPORTANT: Only report as over_provisioned if there are ALSO missing slots.
                    # If there are no missing slots, it means the PRCXML already matches the detected mods perfectly,
                    # so extra slots are just pre-allocated and fine (they might be used in future mods).
                    if non_vanilla_extra and missing_in_prcxml:
                        results["over_provisioned"].append({
                            "fighter": fighter,
                            "detected": detected,
                            "prcxml": prcxml_data,
                            "extra": non_vanilla_extra,
                        })

                    if missing_in_prcxml:
                        msg = f"Luchador: {fighter} | Faltante en PRCXML: {', '.join(missing_in_prcxml)}"
                        results["discrepancies"].append({
                            "fighter": fighter,
                            "detected": detected,
                            "prcxml": prcxml_data,
                            "missing_in_prcxml": missing_in_prcxml,
                            "extra_in_prcxml": extra_in_prcxml,
                            "message": msg,
                        })

                if results["discrepancies"]:
                    results["log_lines"].append(
                        f"Slots faltantes encontrados en {len(results['discrepancies'])} luchador(es)."
                    )
                else:
                    results["log_lines"].append("No hay slots faltantes en el PRCXML.")

                if results["over_provisioned"]:
                    results["log_lines"].append(
                        f"Over-provisioned color_num in {len(results['over_provisioned'])} fighter(s) "
                        f"(will be corrected on apply)."
                    )

                return results
            except Exception as e:
                results["errors"].append(f"Fatal error: {e}")
                return results

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

                kind = item[0]
                if kind == "progress":
                    _, current, total, name = item
                    pct = (current / total) * 100.0 if total else 0.0
                    progress_var.set(pct)
                    progress_text.set(f"{current}/{total} mods")
                    status_text.set(f"Analizando: {name}")
                elif kind == "done":
                    state["done"] = True
                    state["result"] = item[1]
                    cancel_btn.config(state="disabled", text="Listo")

            if not state["done"]:
                progress_win.after(80, _pump_queue)
                return

            result = state["result"] or {}
            progress_win.geometry("760x540")

            log_content = [
                f"Escaneados {result.get('total_mods', 0)} mod(s)",
                f"Procesados {result.get('processed_mods', 0)} mod(s)",
                "",
            ]

            if result.get("errors"):
                log_content.append("Errores:")
                for line in result["errors"]:
                    log_content.append(f"- {line}")
                log_content.append("")

            if result.get("discrepancies"):
                log_content.append("Slots Faltantes:")
                for disc in result["discrepancies"]:
                    log_content.append(disc["message"])
                log_content.append("")
            else:
                log_content.append("No hay slots faltantes detectados.")
                log_content.append("")

            if result.get("log_lines"):
                log_content.append("Validation Log:")
                for line in result["log_lines"]:
                    log_content.append(f"- {line}")

            _set_log(log_content)
            log_text.pack(fill="both", expand=True, padx=12, pady=(10, 6))

            for w in action_row.winfo_children():
                w.destroy()
            action_row.pack(fill="x", padx=12, pady=(0, 10))

            def _close_done():
                try:
                    progress_win.grab_release()
                except Exception:
                    pass
                progress_win.destroy()

            if result.get("errors"):
                status_text.set("Validation completed with errors.")
                tk.Button(
                    action_row,
                    text="Cerrar",
                    command=_close_done,
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

            if result.get("canceled"):
                status_text.set("Validation cancelled.")
                tk.Button(
                    action_row,
                    text="Cerrar",
                    command=_close_done,
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

            needs_fix = result.get("discrepancies") or result.get("over_provisioned")
            if needs_fix:
                disc_count = len(result.get("discrepancies", []))
                over_count = len(result.get("over_provisioned", []))
                parts = []
                if disc_count:
                    parts.append(f"{disc_count} luchador(es) con slots faltantes")
                if over_count:
                    parts.append(f"{over_count} luchador(es) con color_num sobre-asignado")
                status_text.set("Problemas encontrados: " + "; ".join(parts) + ".")

                def _apply_missing(apply_btn_ref):
                    ok, err = _apply_missing_slots_to_prcxml(result)
                    if ok:
                        apply_btn_ref.config(
                            state="disabled",
                            text="Already applied",
                            bg=BG3,
                            fg=TEXT_DIM,
                            cursor="",
                        )
                        _close_done()
                        validate()
                    else:
                        status_text.set(f"Update failed: {err}")

                apply_btn = tk.Button(
                    action_row,
                    text="Aplicar Reparaciones al PRCXML",
                    bg=ACCENT,
                    fg="#000000",
                    relief="flat",
                    bd=0,
                    padx=18,
                    pady=6,
                    cursor="hand2",
                    font=FONT_UI,
                )
                apply_btn.config(command=lambda b=apply_btn: _apply_missing(b))
                apply_btn.pack(side="left", padx=(0, 8))
                tk.Button(
                    action_row,
                    text="Cerrar",
                    command=_close_done,
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

            status_text.set("PRCXML is already correct. No update needed.")
            messagebox.showinfo(
                "PRCXML OK",
                "PRCXML is already correct. No update needed.",
                parent=progress_win,
            )
            tk.Button(
                action_row,
                text="Close",
                command=_close_done,
                bg=BG3,
                fg=TEXT,
                relief="flat",
                bd=0,
                padx=18,
                pady=6,
                cursor="hand2",
                font=FONT_UI,
            ).pack(side="left")

        progress_win.after(80, _pump_queue)

    button_frame = tk.Frame(dialog, bg=BG)
    button_frame.pack(fill="x", padx=15, pady=10)
    tk.Button(
        button_frame, text="Cancel", command=dialog.destroy, bg=BG3, fg=TEXT,
        relief="flat", bd=0, padx=20, pady=6, cursor="hand2", font=FONT_UI
    ).pack(side="left", padx=(0, 10))
    tk.Button(
        button_frame, text="Validar", command=validate, bg=ACCENT, fg="#000000",
        relief="flat", bd=0, padx=20, pady=6, cursor="hand2", font=FONT_UI
    ).pack(side="left")


def show_prcxml_dialog():
    """Compatibility alias for older plugin button discovery in the EXE."""
    show_validator_dialog()
