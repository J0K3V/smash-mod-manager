"""Shared fighter special-case grouping used by app and plugins."""

from __future__ import annotations


# Keep one authoritative mapping so app and plugins stay in sync.
COMBINED_FIGHTERS = {
    "eflame": ["eflame", "elight", "element"],
    "elight": ["eflame", "elight", "element"],
    "element": ["eflame", "elight", "element"],
    "popo": ["popo", "nana"],
    "nana": ["popo", "nana"],
    "ptrainer": ["ptrainer", "pzenigame", "pfushigisou", "plizardon"],
    "pzenigame": ["ptrainer", "pzenigame", "pfushigisou", "plizardon"],
    "pfushigisou": ["ptrainer", "pzenigame", "pfushigisou", "plizardon"],
    "plizardon": ["ptrainer", "pzenigame", "pfushigisou", "plizardon"],
}


def expand_fighter_group(fighter: str, enabled: bool = True) -> list[str]:
    """Return fighter group members for special-cases mode, or just [fighter]."""
    name = (fighter or "").strip().lower()
    if not name:
        return []
    if not enabled:
        return [name]
    return list(COMBINED_FIGHTERS.get(name, [name]))


def suggest_share_base_slot(fighter: str, source_slot: str) -> str | None:
    """Return a CSharp-like base share slot for all fighters.

    The rule set mirrors the common reslotter heuristics used by the community.
    """
    name = (fighter or "").strip().lower()
    token = (source_slot or "").strip().lower()
    if token.startswith("c"):
        token = token[1:]
    if not token.isdigit():
        return None

    base_num = int(token) % 8
    alts_last2 = {
        "edge", "szerosuit", "littlemac", "mario", "metaknight", "jack",
    }
    alts_odd = {
        "bayonetta", "master", "cloud", "kamui", "ike", "shizue", "demon",
        "link", "packun", "reflet", "wario", "wiifit",
        "ptrainer", "ptrainer_low", "pzenigame", "pfushigisou", "plizardon",
        # Keep cohesion with modules that may still emit these ids.
        "pokemontrainer", "squirtle", "ivysaur", "lizardon",
    }
    alts_all = {
        "koopajr", "murabito", "purin", "pikachu", "pichu", "sonic",
    }

    if name in {"brave", "trail"}:
        share = base_num % 4
    elif name in {"pikmin", "popo", "nana"}:
        share = 0 if base_num < 4 else 4
    elif name == "pacman":
        share = 0 if base_num in {0, 7} else base_num
    elif name == "ridley":
        share = 0 if base_num in {1, 7} else base_num
    elif name in {"inkling", "pickel"}:
        share = (base_num % 2) if base_num < 6 else base_num
    elif name == "shulk":
        share = 0 if base_num < 7 else 7
    elif name in alts_last2:
        share = 0 if base_num < 6 else base_num
    elif name in alts_all:
        share = base_num
    elif name in alts_odd:
        share = base_num % 2
    else:
        share = 0

    return f"c0{share}"
