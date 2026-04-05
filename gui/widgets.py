"""
widgets.py — Reusable styled widget factories for the dark theme.
"""
import tkinter as tk
from tkinter import ttk

from gui.theme import *


def styled_button(parent, text, command, accent=False, width=None, small=False):
    """Create a themed flat button."""
    bg = ACCENT if accent else BG3
    fg = BG if accent else TEXT
    font = FONT_SMALL if small else FONT_UI
    kw = dict(
        text=text, command=command, bg=bg, fg=fg, font=font,
        relief="flat", bd=0, cursor="hand2", padx=10, pady=4,
        activebackground=ACCENT2, activeforeground=BG,
    )
    if width:
        kw["width"] = width
    return tk.Button(parent, **kw)


def styled_entry(parent, textvariable, font=None, **kwargs):
    """Create a themed text entry."""
    return tk.Entry(
        parent, textvariable=textvariable, bg=BG3, fg=TEXT,
        insertbackground=ACCENT, relief="flat", font=font or FONT_UI,
        bd=0, highlightthickness=1, highlightcolor=ACCENT,
        highlightbackground=BORDER, **kwargs,
    )


def styled_combo(parent, textvariable, values, width=6):
    """Create a themed Combobox."""
    style = ttk.Style()
    style.configure(
        "Dark.TCombobox",
        fieldbackground=BG3, background=BG3,
        foreground=TEXT, selectbackground=BG3,
        selectforeground=ACCENT, arrowcolor=TEXT_DIM,
    )
    return ttk.Combobox(
        parent, textvariable=textvariable, values=values,
        width=width, style="Dark.TCombobox", state="normal",
    )


def styled_check(parent, text, variable):
    """Create a themed Checkbutton."""
    return tk.Checkbutton(
        parent, text=text, variable=variable,
        bg=BG, fg=TEXT, selectcolor=BG3,
        activebackground=BG, activeforeground=ACCENT,
        font=FONT_SMALL, relief="flat", bd=0,
    )


def styled_label(parent, text, font=None, fg=None, **kwargs):
    """Create a themed label."""
    return tk.Label(
        parent, text=text, bg=kwargs.pop("bg", BG),
        fg=fg or TEXT_DIM, font=font or FONT_SMALL,
        **kwargs,
    )


def styled_listbox(parent) -> tuple[tk.Listbox, tk.Scrollbar]:
    """Create a themed Listbox with scrollbar. Returns (listbox, scrollbar)."""
    frame = tk.Frame(parent, bg=BG3)
    lb = tk.Listbox(
        frame, bg=BG3, fg=TEXT, font=FONT_MONO,
        relief="flat", bd=0, selectbackground=BG,
        selectforeground=ACCENT, highlightthickness=0,
    )
    lb.pack(side="left", fill="both", expand=True)
    sb = tk.Scrollbar(
        frame, command=lb.yview, bg=BG3, troughcolor=BG,
        relief="flat", bd=0, width=10,
    )
    sb.pack(side="right", fill="y")
    lb.config(yscrollcommand=sb.set)
    return frame, lb


class CheckList:
    """Scrollable list of rows with checkboxes and colored status indicators.

    Each row shows a color bar, a checkbox (enabled only if the item is fixable),
    and a text label.  Use add_item(result) where result is a ValidationResult.
    """

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG3, relief="flat", bd=0,
                              highlightthickness=1, highlightbackground=BORDER)
        self._canvas = tk.Canvas(self.frame, bg=BG3, highlightthickness=0)
        self._scrollbar = tk.Scrollbar(
            self.frame, command=self._canvas.yview,
            bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10,
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._inner = tk.Frame(self._canvas, bg=BG3)
        self._win_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)

        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

        self._items = []  # list of (BooleanVar, result)

    # ── internal callbacks ────────────────────────────────────────────────────

    def _on_inner_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._win_id, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── public API ────────────────────────────────────────────────────────────

    def clear(self):
        for w in self._inner.winfo_children():
            w.destroy()
        self._items.clear()

    def add_item(self, result, checked: bool = True):
        """Add one validation result row."""
        from core.batch_validator import ValidationResult
        var = tk.BooleanVar(value=checked and result.can_fix)

        if result.status == ValidationResult.STATUS_OK:
            color = GREEN
        elif result.status == ValidationResult.STATUS_WARN:
            color = ORANGE
        else:
            color = RED

        row = tk.Frame(self._inner, bg=BG3)
        row.pack(fill="x", pady=1)

        # left color stripe
        tk.Frame(row, bg=color, width=3).pack(side="left", fill="y", padx=(2, 4))

        # checkbox – enabled only when the item has a fixable issue
        state = "normal" if result.can_fix else "disabled"
        tk.Checkbutton(
            row, variable=var, bg=BG3, fg=TEXT,
            selectcolor=BG4, activebackground=BG3, activeforeground=ACCENT,
            disabledforeground=TEXT_MUTED, relief="flat", bd=0, state=state,
        ).pack(side="left")

        # summary text
        tk.Label(
            row, text=result.summary(), bg=BG3, fg=color,
            font=FONT_MONO, anchor="w",
        ).pack(side="left", fill="x", expand=True)

        self._items.append((var, result))

    def get_checked(self):
        """Return list of (BooleanVar, result) for all checked fixable items."""
        return [(var, r) for var, r in self._items if var.get()]

    def select_all(self, state: bool = True):
        """Check or uncheck all fixable items."""
        for var, r in self._items:
            if r.can_fix:
                var.set(state)


class Tooltip:
    """Simple hover tooltip for any widget."""
    def __init__(self, widget, text: str):
        self._tip = None
        widget.bind("<Enter>", lambda e: self._show(widget, text))
        widget.bind("<Leave>", lambda e: self._hide())

    def _show(self, widget, text):
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + widget.winfo_height() + 4
        self._tip = tk.Toplevel(widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self._tip, text=text, bg=BG4, fg=TEXT,
            font=FONT_SMALL, relief="flat", padx=10, pady=5,
            justify="left",
        ).pack()

    def _hide(self):
        if self._tip:
            self._tip.destroy()
            self._tip = None


def separator(parent, padx=20, pady=4):
    """Horizontal line separator."""
    return tk.Frame(parent, bg=BORDER, height=1)


def section_header(parent, text):
    """Section title with accent color."""
    return tk.Label(
        parent, text=text, bg=BG, fg=ACCENT,
        font=FONT_TITLE, anchor="w",
    )
