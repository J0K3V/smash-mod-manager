"""
fighter_db.py — Fighter database for Smash Ultimate.

Contains:
- Internal fighter names used by the game engine
- Base model group definitions (which slots share which model base)
- Extra model parts per fighter (pipe, toad, sword, etc.)
- Kirby copy ability mappings
- Display name lookups
"""
import re

# ─── Slot pattern ─────────────────────────────────────────────────────────────
SLOT_PATTERN = re.compile(r'^c(\d{2,3})$')
SLOT_IN_PATH = re.compile(r'/c(\d{2,3})/')


def slot_str(n: int) -> str:
    """Return slot string like 'c00', 'c08', 'c100'."""
    return f"c{str(n).zfill(2)}"


def slot_num(s: str) -> int:
    """Parse 'c08' → 8, 'c100' → 100."""
    return int(s.lstrip("c"))


# ─── All internal fighter names ───────────────────────────────────────────────
FIGHTER_NAMES = sorted(set([
    "mario", "donkey", "link", "samus", "samusd", "yoshi", "kirby", "fox",
    "pikachu", "luigi", "ness", "captain", "purin", "peach", "daisy", "koopa",
    "ice_climber", "sheik", "zelda", "mariod", "pichu", "falco", "mewtwo",
    "marth", "lucina", "younglink", "ganon", "roy", "chrom", "gamewatch",
    "metaknight", "pit", "pitb", "szerosuit", "wario", "snake", "ike",
    "pokemontrainer", "popo", "nana", "squirtle", "ivysaur", "lizardon",
    "diddy", "lucas", "sonic", "dedede", "pikmin", "lucario", "rob",
    "toonlink", "wolf", "villager", "rockman", "wiifit", "rosetta",
    "littlemac", "gekkouga", "miifighter", "miiswordsman", "miigunner",
    "palutena", "pacman", "reflet", "shulk", "koopajr", "duckhunt",
    "ryu", "ken", "cloud", "kamui", "bayonetta", "inkling", "ridley",
    "simon", "richter", "krool", "shizue", "gaogaen", "packun",
    "jack", "brave", "buddy", "dolly", "master", "tantan", "pickel",
    "edge", "eflame", "elight", "demon", "trail",
    "eflame_first", "eflame_only", "elight_first", "elight_only", "element",
]))
# ─── Display names ────────────────────────────────────────────────────────────
DISPLAY_NAMES = {
    "mario": "Mario", "donkey": "Donkey Kong", "link": "Link",
    "samus": "Samus", "samusd": "Dark Samus", "yoshi": "Yoshi",
    "kirby": "Kirby", "fox": "Fox", "pikachu": "Pikachu",
    "luigi": "Luigi", "ness": "Ness", "captain": "Captain Falcon",
    "purin": "Jigglypuff", "peach": "Peach", "daisy": "Daisy",
    "koopa": "Bowser", "ice_climber": "Ice Climbers", "sheik": "Sheik",
    "zelda": "Zelda", "mewtwo": "Mewtwo", "marth": "Marth",
    "lucina": "Lucina", "younglink": "Young Link", "falco": "Falco",
    "ganon": "Ganondorf", "pichu": "Pichu", "gamewatch": "Mr. Game & Watch",
    "metaknight": "Meta Knight", "pit": "Pit", "pitb": "Dark Pit",
    "szerosuit": "Zero Suit Samus", "wario": "Wario", "snake": "Snake",
    "ike": "Ike", "pokemontrainer": "Pokemon Trainer",
    "popo": "Popo", "nana": "Nana",
    "squirtle": "Squirtle", "ivysaur": "Ivysaur", "lizardon": "Charizard",
    "diddy": "Diddy Kong", "lucas": "Lucas", "sonic": "Sonic",
    "dedede": "King Dedede", "pikmin": "Olimar", "lucario": "Lucario",
    "rob": "R.O.B.", "toonlink": "Toon Link", "wolf": "Wolf",
    "villager": "Villager", "rockman": "Mega Man", "wiifit": "Wii Fit Trainer",
    "rosetta": "Rosalina & Luma", "littlemac": "Little Mac",
    "gekkouga": "Greninja", "palutena": "Palutena", "pacman": "Pac-Man",
    "reflet": "Robin", "shulk": "Shulk", "koopajr": "Bowser Jr.",
    "duckhunt": "Duck Hunt", "ryu": "Ryu", "ken": "Ken",
    "cloud": "Cloud", "kamui": "Corrin", "bayonetta": "Bayonetta",
    "inkling": "Inkling", "ridley": "Ridley", "simon": "Simon",
    "richter": "Richter", "krool": "King K. Rool", "shizue": "Isabelle",
    "gaogaen": "Incineroar", "packun": "Piranha Plant", "jack": "Joker",
    "brave": "Hero", "buddy": "Banjo & Kazooie", "dolly": "Terry",
    "master": "Byleth", "tantan": "Min Min", "pickel": "Steve",
    "edge": "Sephiroth", "eflame": "Pyra", "elight": "Mythra",
    "demon": "Kazuya", "trail": "Sora",    
    "mariod": "Dr. Mario", "roy": "Roy", "chrom": "Chrom",
    "miifighter": "Mii Brawler", "miiswordsman": "Mii Swordfighter",
    "miigunner": "Mii Gunner",
}

# ─── Extra model parts besides "body" ────────────────────────────────────────
# Key = internal fighter name → list of extra model folder names
EXTRA_MODEL_PARTS = {
    "koopajr":     ["clown"],          # Koopa Clown Car
    "rosetta":     ["tico"],           # Luma
    "pikmin":      ["pikmin"],
    "duckhunt":    ["dog", "duck"],
    "ice_climber": ["nana"],           # Nana controlled separately
    "pokemontrainer": [],              # uses squirtle/ivysaur/lizardon
    "mario":       [],                 # no extra (FLUDD is effect)
    "peach":       ["kinopio"],        # Toad
    "daisy":       ["kinopio"],        # Toad
    "diddy":       [],
    "pacman":      [],
    "rockman":     [],
    "master":      [],                 # Byleth weapons are effect/model
    "jack":        ["arsene"],         # Arsene
    "buddy":       ["kazooie"],        # Kazooie
    "brave":       [],
    "edge":        ["wing"],           # One-Winged Angel wing
    "eflame":      ["esword"],         # Aegis sword
    "elight":      ["esword"],
    "pickel":      [],                 # Steve tools are effect
    "tantan":      ["arm_l", "arm_r", "dragon", "megawatt", "ramram"],
}

# ─── Base model groups ────────────────────────────────────────────────────────
# Each fighter can have multiple base model groups.
# group: { key, label, slots (display), slot_range (list/range for detection) }
_DEFAULT_GROUP = [
    {"key": "c00", "label": "default", "slots": "c00–c07+", "slot_range": range(0, 256)},
]

BASE_GROUPS = {
    # ── Link (hat / special alts) ──
    "link": [
        {"key": "c00_nohat",  "label": "No Hat",       "slots": "c00,c02,c04,c06", "slot_range": [0, 2, 4, 6]},
        {"key": "c01_hat",    "label": "With Hat",     "slots": "c01,c05",         "slot_range": [1, 5]},
        {"key": "c03_fierce", "label": "Fierce Deity", "slots": "c03",             "slot_range": [3]},
        {"key": "c07_dark",   "label": "Dark Link",    "slots": "c07",             "slot_range": [7]},
    ],
    # ── Two-outfit bases ──
    "cloud": [
        {"key": "c00_ff7",  "label": "FF7 (Buster Sword)",              "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_ac",   "label": "Advent Children (Fusion Sword)",   "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    "ike": [
        {"key": "c00_por",  "label": "Path of Radiance (Ranger)",  "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_rd",   "label": "Radiant Dawn (Hero)",        "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    "wario": [
        {"key": "c00_biker",    "label": "Biker (WarioWare)",     "slots": "c00,c02,c04,c06", "slot_range": [0, 2, 4, 6]},
        {"key": "c01_overalls", "label": "Overalls (Wario Land)", "slots": "c01,c03,c05,c07", "slot_range": [1, 3, 5, 7]},
    ],
    "bayonetta": [
        {"key": "c00_bayo2", "label": "Bayonetta 2 (Love is Blue)",       "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_bayo1", "label": "Bayonetta 1 (Scarborough Fair)",    "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    "edge": [  # Sephiroth
        {"key": "c00_shirt",     "label": "Shirted",   "slots": "c00–c05", "slot_range": [0, 1, 2, 3, 4, 5]},
        {"key": "c06_shirtless", "label": "Shirtless", "slots": "c06–c07", "slot_range": [6, 7]},
    ],
    # ── Male / Female ──
    "kamui": [  # Corrin
        {"key": "c00_male",   "label": "Male Corrin",   "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_female", "label": "Female Corrin", "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    "reflet": [  # Robin
        {"key": "c00_male",   "label": "Male Robin",   "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_female", "label": "Female Robin", "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    "master": [  # Byleth
        {"key": "c00_male",   "label": "Male Byleth",   "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_female", "label": "Female Byleth", "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    "wiifit": [
        {"key": "c00_female", "label": "Female Trainer", "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_male",   "label": "Male Trainer",   "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    "inkling": [
        {"key": "c00_female", "label": "Female Inkling", "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_male",   "label": "Male Inkling",   "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    # ── Aegis ──
    "eflame": [
        {"key": "c00_pyra",   "label": "Pyra",   "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_mythra", "label": "Mythra", "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    "elight": [
        {"key": "c00_pyra",   "label": "Pyra",   "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_mythra", "label": "Mythra", "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    # ── Hero (4 protagonists) ──
    "brave": [
        {"key": "c00_xi",      "label": "Eleven (DQ XI)",   "slots": "c00–c01", "slot_range": [0, 1]},
        {"key": "c02_erdrick", "label": "Erdrick (DQ III)", "slots": "c02–c03", "slot_range": [2, 3]},
        {"key": "c04_solo",    "label": "Solo (DQ IV)",     "slots": "c04–c05", "slot_range": [4, 5]},
        {"key": "c06_eight",   "label": "Eight (DQ VIII)",  "slots": "c06–c07", "slot_range": [6, 7]},
    ],
    # ── Joker ──
    "jack": [
        {"key": "c00_uniform", "label": "School Uniform",       "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_casual",  "label": "Phantom Thief Casual", "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    # ── Mario special outfits ──
    "mario": [
        {"key": "c00_normal",  "label": "Normal",            "slots": "c00–c05", "slot_range": [0, 1, 2, 3, 4, 5]},
        {"key": "c06_wedding", "label": "Wedding (Odyssey)", "slots": "c06",     "slot_range": [6]},
        {"key": "c07_builder", "label": "Builder (Maker)",   "slots": "c07",     "slot_range": [7]},
    ],
    # ── Isabelle ──
    "shizue": [
        {"key": "c00_summer", "label": "Summer Outfit", "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_winter", "label": "Winter Outfit", "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    # ── Sora ──
    "trail": [
        {"key": "c00_kh1",      "label": "KH1",                 "slots": "c00–c01", "slot_range": [0, 1]},
        {"key": "c02_kh2",      "label": "KH2",                 "slots": "c02–c03", "slot_range": [2, 3]},
        {"key": "c04_kh3d",     "label": "Dream Drop Distance", "slots": "c04–c05", "slot_range": [4, 5]},
        {"key": "c06_timeless", "label": "Timeless River",      "slots": "c06–c07", "slot_range": [6, 7]},
    ],
    # ── Shulk ──
    "shulk": [
        {"key": "c00_classic",  "label": "Classic Outfit", "slots": "c00–c06", "slot_range": [0, 1, 2, 3, 4, 5, 6]},
        {"key": "c07_swimsuit", "label": "Swimsuit",       "slots": "c07",     "slot_range": [7]},
    ],
    # ── Zero Suit Samus ──
    "szerosuit": [
        {"key": "c00_zerosuit",   "label": "Zero Suit",  "slots": "c00–c05", "slot_range": [0, 1, 2, 3, 4, 5]},
        {"key": "c06_sportswear", "label": "Sportswear", "slots": "c06–c07", "slot_range": [6, 7]},
    ],
    # ── Olimar / Alph ──
    "pikmin": [
        {"key": "c00_olimar", "label": "Olimar", "slots": "c00–c03", "slot_range": [0, 1, 2, 3]},
        {"key": "c04_alph",   "label": "Alph",   "slots": "c04–c07", "slot_range": [4, 5, 6, 7]},
    ],
    # ── Pokemon Trainer ──
    "pokemontrainer": [
        {"key": "c00_male",   "label": "Male Trainer (Red)",    "slots": "c00,c02,c04,c06", "slot_range": [0, 2, 4, 6]},
        {"key": "c01_female", "label": "Female Trainer (Leaf)", "slots": "c01,c03,c05,c07", "slot_range": [1, 3, 5, 7]},
    ],
    # ── Meta Knight ──
    "metaknight": [
        {"key": "c00_base",    "label": "Meta Knight",           "slots": "c00–c05", "slot_range": [0, 1, 2, 3, 4, 5]},
        {"key": "c06_galacta", "label": "Galacta Knight Mask",   "slots": "c06",     "slot_range": [6]},
        {"key": "c07_dark",    "label": "Dark Meta Knight Mask", "slots": "c07",     "slot_range": [7]},
    ],
    # ── Snake ──
    "snake": [
        {"key": "c00_camo1", "label": "Sneaking Suit (Camo 1)", "slots": "c00–c01", "slot_range": [0, 1]},
        {"key": "c02_camo2", "label": "Sneaking Suit (Camo 2)", "slots": "c02–c07", "slot_range": [2, 3, 4, 5, 6, 7]},
    ],
    # ── Ridley ──
    "ridley": [
        {"key": "c00_organic", "label": "Ridley (Organic)",         "slots": "c00,c02–c06", "slot_range": [0, 2, 3, 4, 5, 6]},
        {"key": "c01_meta",    "label": "Meta Ridley (Cybernetic)", "slots": "c01,c07",     "slot_range": [1, 7]},
    ],
    # ── Kazuya ──
    "demon": [
        {"key": "c00_gi",   "label": "Gi Outfit",     "slots": "c00,c02,c04,c06", "slot_range": [0, 2, 4, 6]},
        {"key": "c01_suit", "label": "Suit (Blazer)",  "slots": "c01,c03,c05,c07", "slot_range": [1, 3, 5, 7]},
    ],
    # ── Little Mac ──
    "littlemac": [
        {"key": "c00_boxing",    "label": "Boxing Outfit",      "slots": "c00–c04", "slot_range": [0, 1, 2, 3, 4]},
        {"key": "c05_hoodie",    "label": "Pink Hoodie",        "slots": "c05",     "slot_range": [5]},
        {"key": "c06_wireframe", "label": "Wireframe",          "slots": "c06",     "slot_range": [6]},
        {"key": "c07_wf_hoodie", "label": "Wireframe + Hoodie", "slots": "c07",     "slot_range": [7]},
    ],
    # ── Pac-Man ──
    "pacman": [
        {"key": "c00",       "label": "Classic",      "slots": "c00",     "slot_range": [0,7]},
        {"key": "c01_wings", "label": "Winged Shoes", "slots": "c01–c05", "slot_range": [1, 2, 3, 4, 5]},
        {"key": "c06",       "label": "Alt",          "slots": "c06–c07", "slot_range": [6]},
    ],
    # ── Pikachu (each slot is a unique model) ──
    "pikachu": [
        {"key": "c00",          "label": "No Hat",           "slots": "c00", "slot_range": [0]},
        {"key": "c01_origcap",  "label": "Original Cap",     "slots": "c01", "slot_range": [1]},
        {"key": "c02_honeycap", "label": "Hoenn Cap",        "slots": "c02", "slot_range": [2]},
        {"key": "c03_sinncap",  "label": "Sinnoh Cap",       "slots": "c03", "slot_range": [3]},
        {"key": "c04_unovacap", "label": "Unova Cap",        "slots": "c04", "slot_range": [4]},
        {"key": "c05_kalosscap","label": "Kalos Cap",        "slots": "c05", "slot_range": [5]},
        {"key": "c06_alolahat", "label": "Alola Cap",        "slots": "c06", "slot_range": [6]},
        {"key": "c07_libre",    "label": "Pikachu Libre",    "slots": "c07", "slot_range": [7]},
    ],
    # ── Jigglypuff (each slot is a unique model) ──
    "purin": [
        {"key": "c00",         "label": "Default",     "slots": "c00", "slot_range": [0]},
        {"key": "c01_flower",  "label": "Flower",      "slots": "c01", "slot_range": [1]},
        {"key": "c02_bow",     "label": "Bow",         "slots": "c02", "slot_range": [2]},
        {"key": "c03_ribbon",  "label": "Ribbon",      "slots": "c03", "slot_range": [3]},
        {"key": "c04_crown",   "label": "Crown",       "slots": "c04", "slot_range": [4]},
        {"key": "c05_tophat",  "label": "Top Hat",     "slots": "c05", "slot_range": [5]},
        {"key": "c06_hairclip","label": "Hair Clip",   "slots": "c06", "slot_range": [6]},
        {"key": "c07_headband","label": "Headband",    "slots": "c07", "slot_range": [7]},
    ],
    # ── Pichu (each slot is a unique model) ──
    "pichu": [
        {"key": "c00",          "label": "Default",    "slots": "c00", "slot_range": [0]},
        {"key": "c01_goggles",  "label": "Goggles",    "slots": "c01", "slot_range": [1]},
        {"key": "c02_scarf",    "label": "Scarf",      "slots": "c02", "slot_range": [2]},
        {"key": "c03_hat",      "label": "Party Hat",  "slots": "c03", "slot_range": [3]},
        {"key": "c04_bow",      "label": "Bow",        "slots": "c04", "slot_range": [4]},
        {"key": "c05_flower",   "label": "Flower",     "slots": "c05", "slot_range": [5]},
        {"key": "c06_necklace", "label": "Necklace",   "slots": "c06", "slot_range": [6]},
        {"key": "c07_leaf",     "label": "Leaf",       "slots": "c07", "slot_range": [7]},
    ],
    # ── Villager (each slot is a unique model) ──
    "villager": [
        {"key": "c00", "label": "Villager Boy 1",  "slots": "c00", "slot_range": [0]},
        {"key": "c01", "label": "Villager Girl 1", "slots": "c01", "slot_range": [1]},
        {"key": "c02", "label": "Villager Boy 2",  "slots": "c02", "slot_range": [2]},
        {"key": "c03", "label": "Villager Girl 2", "slots": "c03", "slot_range": [3]},
        {"key": "c04", "label": "Villager Boy 3",  "slots": "c04", "slot_range": [4]},
        {"key": "c05", "label": "Villager Girl 3", "slots": "c05", "slot_range": [5]},
        {"key": "c06", "label": "Villager Boy 4",  "slots": "c06", "slot_range": [6]},
        {"key": "c07", "label": "Villager Girl 4", "slots": "c07", "slot_range": [7]},
    ],
    # ── Bowser Jr. / Koopalings (each slot is a different character) ──
    "koopajr": [
        {"key": "c00_bowserjr", "label": "Bowser Jr.",       "slots": "c00", "slot_range": [0]},
        {"key": "c01_larry",    "label": "Larry Koopa",      "slots": "c01", "slot_range": [1]},
        {"key": "c02_roy",      "label": "Roy Koopa",        "slots": "c02", "slot_range": [2]},
        {"key": "c03_wendy",    "label": "Wendy O. Koopa",   "slots": "c03", "slot_range": [3]},
        {"key": "c04_iggy",     "label": "Iggy Koopa",       "slots": "c04", "slot_range": [4]},
        {"key": "c05_morton",   "label": "Morton Koopa Jr.", "slots": "c05", "slot_range": [5]},
        {"key": "c06_lemmy",    "label": "Lemmy Koopa",      "slots": "c06", "slot_range": [6]},
        {"key": "c07_ludwig",   "label": "Ludwig von Koopa", "slots": "c07", "slot_range": [7]},
    ],
    # ── Steve (each slot is a different character) ──
    "pickel": [
        {"key": "c00_steve",      "label": "Steve",     "slots": "c00", "slot_range": [0]},
        {"key": "c01_alex",       "label": "Alex",      "slots": "c01", "slot_range": [1]},
        {"key": "c02_zombie",     "label": "Zombie",    "slots": "c02", "slot_range": [2]},
        {"key": "c03_enderman",   "label": "Enderman",  "slots": "c03", "slot_range": [3]},
        {"key": "c04_steve2",     "label": "Steve 2",   "slots": "c04", "slot_range": [4]},
        {"key": "c05_alex2",      "label": "Alex 2",    "slots": "c05", "slot_range": [5]},
        {"key": "c06_zombie2",    "label": "Zombie 2",  "slots": "c06", "slot_range": [6]},
        {"key": "c07_enderman2",  "label": "Enderman 2","slots": "c07", "slot_range": [7]},
    ],
}


def get_base_groups(fighter_name: str) -> list:
    """Return the base model groups for a given fighter internal name."""
    return BASE_GROUPS.get(fighter_name.lower().strip(), _DEFAULT_GROUP)


def get_group_for_slot(fighter_name: str, slot_number: int) -> dict:
    """Return the base group dict that covers the given slot number."""
    groups = get_base_groups(fighter_name)
    for g in groups:
        if slot_number in g["slot_range"]:
            return g
    return groups[0]


def get_extra_parts(fighter_name: str) -> list[str]:
    """Return list of extra model part folder names for a fighter (besides body)."""
    return EXTRA_MODEL_PARTS.get(fighter_name.lower().strip(), [])


def get_display_name(fighter_name: str) -> str:
    """Return the display name for a fighter internal name."""
    return DISPLAY_NAMES.get(fighter_name.lower().strip(), fighter_name.title())


# ─── Ice Climber / Aegis aliases for UI paths ────────────────────────────────
UI_FIGHTER_ALIASES = {
    "popo":   ["ice_climber"],
    "nana":   ["ice_climber"],
    "eflame": ["eflame_first", "eflame_only"],
    "elight": ["elight_first", "elight_only"],
}


# ─── Roster order (official Smash Ultimate number order) ──────────────────────
ROSTER_ORDER = [
    "mario", "donkey", "link", "samus", "samusd", "yoshi", "kirby", "fox",
    "pikachu", "luigi", "ness", "captain", "purin", "peach", "daisy", "koopa",
    "popo", "nana", "sheik", "zelda", "mariod", "pichu", "falco",
    "marth", "lucina", "younglink", "ganon", "mewtwo", "roy", "chrom",
    "gamewatch", "metaknight", "pit", "pitb", "szerosuit", "wario", "snake",
    "ike", "pokemontrainer", "squirtle", "ivysaur", "lizardon",
    "diddy", "lucas", "sonic", "dedede", "pikmin", "lucario", "rob",
    "toonlink", "wolf", "villager", "rockman", "wiifit", "rosetta",
    "littlemac", "gekkouga", "miifighter", "miiswordsman", "miigunner",
    "palutena", "pacman", "reflet", "shulk", "koopajr", "duckhunt",
    "ryu", "ken", "cloud", "kamui", "bayonetta", "inkling", "ridley",
    "simon", "richter", "krool", "shizue", "gaogaen", "packun",
    "jack", "brave", "buddy", "dolly", "master", "tantan", "pickel",
    "edge", "eflame", "element", "elight", "demon", "trail",
]


def get_default_base_folder_entries() -> dict[str, str]:
    """
    Generate default base folder entries for ALL fighters in roster order.
    - Fighters with multiple base groups get one entry per group.
    - All others get a single c00 entry.
    """
    entries = {}
    for fighter_name in ROSTER_ORDER:
        if fighter_name in BASE_GROUPS:
            for g in BASE_GROUPS[fighter_name]:
                key = f"{fighter_name}_{g['key']}"
                entries[key] = ""
        else:
            entries[f"{fighter_name}_c00"] = ""
    return entries


def get_default_base_folder_keys() -> set[str]:
    """Return the set of keys that are considered 'default' entries."""
    return set(get_default_base_folder_entries().keys())