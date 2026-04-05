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
