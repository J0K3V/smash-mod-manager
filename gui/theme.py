"""
theme.py — Visual theme constants for Smash Mod Manager.
Call apply_theme() before building the GUI to set the active theme.
"""
import sys

# ─── Defaults (Dark) ──────────────────────────────────────────────────────────
BG          = "#0c0c0e"
BG2         = "#141418"
BG3         = "#1c1c24"
BG4         = "#24242e"

ACCENT      = "#e8ff47"
ACCENT2     = "#ff6b35"
ACCENT3     = "#47c8ff"

TEXT        = "#e4e4ee"
TEXT_DIM    = "#6b6b80"
TEXT_MUTED  = "#44445a"

GREEN       = "#4ade80"
RED         = "#f87171"
ORANGE      = "#fb923c"
BORDER      = "#2a2a38"

FONT_MONO   = ("Consolas", 9)
FONT_UI     = ("Segoe UI", 10)
FONT_TITLE  = ("Segoe UI", 11, "bold")
FONT_SMALL  = ("Segoe UI", 9)
FONT_HEADER = ("Segoe UI", 13, "bold")

SLOT_OPTIONS = [f"c{str(i).zfill(2)}" for i in range(0, 64)]

# ─── Theme definitions ────────────────────────────────────────────────────────
THEMES = {
    "Dark": {
        "BG": "#0c0c0e", "BG2": "#141418", "BG3": "#1c1c24", "BG4": "#24242e",
        "ACCENT": "#e8ff47", "ACCENT2": "#ff6b35", "ACCENT3": "#47c8ff",
        "TEXT": "#e4e4ee", "TEXT_DIM": "#6b6b80", "TEXT_MUTED": "#44445a",
        "GREEN": "#4ade80", "RED": "#f87171", "ORANGE": "#fb923c", "BORDER": "#2a2a38",
    },
    "Slate": {
        "BG": "#0d1117", "BG2": "#161b22", "BG3": "#1f2937", "BG4": "#374151",
        "ACCENT": "#58d6ff", "ACCENT2": "#f97316", "ACCENT3": "#a78bfa",
        "TEXT": "#e2e8f0", "TEXT_DIM": "#64748b", "TEXT_MUTED": "#334155",
        "GREEN": "#34d399", "RED": "#f87171", "ORANGE": "#fb923c", "BORDER": "#1e293b",
    },
    "Crimson": {
        "BG": "#070709", "BG2": "#0e0709", "BG3": "#160b0d", "BG4": "#1e1012",
        "ACCENT": "#ff1a3d", "ACCENT2": "#ff9e00", "ACCENT3": "#c084fc",
        "TEXT": "#f0f0f4", "TEXT_DIM": "#bf5060", "TEXT_MUTED": "#5a2830",
        "GREEN": "#4ade80", "RED": "#f87171", "ORANGE": "#fb923c", "BORDER": "#2e1018",
    },
    "Light": {
        "BG": "#f4f4f8", "BG2": "#e8e8f0", "BG3": "#d8d8e4", "BG4": "#c8c8d8",
        "ACCENT": "#1a56db", "ACCENT2": "#e3470b", "ACCENT3": "#0891b2",
        "TEXT": "#1a1a2e", "TEXT_DIM": "#555568", "TEXT_MUTED": "#8888a0",
        "GREEN": "#15803d", "RED": "#dc2626", "ORANGE": "#d97706", "BORDER": "#a0a0b8",
    },
}

THEME_NAMES = list(THEMES.keys())


def apply_theme(theme_name: str, font_size: int = 11):
    """
    Update module-level constants to the selected theme and font size.
    Must be called before the GUI is built (i.e. before importing app.py).
    """
    theme = THEMES.get(theme_name, THEMES["Dark"])
    mod = sys.modules[__name__]
    for key, val in theme.items():
        setattr(mod, key, val)

    b = max(9, min(16, font_size))
    setattr(mod, "FONT_MONO",   ("Consolas",  b - 1))
    setattr(mod, "FONT_UI",     ("Segoe UI",  b))
    setattr(mod, "FONT_TITLE",  ("Segoe UI",  b + 1, "bold"))
    setattr(mod, "FONT_SMALL",  ("Segoe UI",  b - 1))
    setattr(mod, "FONT_HEADER", ("Segoe UI",  b + 3, "bold"))
