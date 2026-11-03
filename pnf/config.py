"""Layout, tuning and difficulty constants."""

W, H = 1280, 720
FPS = 60

LEVELS = 10
WORDS_PER_LEVEL = 3
LEVEL_TIME = 120.0          # seconds per level
START_LIVES = 3
MAX_AMMO = 3
PICK_TIME = 3.0             # seconds of holding SPACE to pick the nose

# Shooting gallery window
GAL_X0, GAL_X1 = 50, 1120
GAL_TOP, GAL_BOTTOM = 100, 470
GAL_CX = (GAL_X0 + GAL_X1) // 2
BELT_Y = [190, 298, 406]            # tile centre for top / middle / bottom belts
TILE = 62
AIM_MIN, AIM_MAX = GAL_X0 + 40, GAL_X1 - 40
AIM_SPEED = 620.0

# Word board (the counter under the gallery window)
BOARD_TOP, BOARD_BOTTOM = 475, 578

# Player hand
REST_TIP_Y = 604
FINGER_LEN = 92

# Nose refill panel
PANEL = (1130, 100, 140, 370)
NOSE_CX, NOSE_CY = 1200, 238

# Belt behaviour: base speed (px/s), direction (+1 = left-to-right), mode, spacing
BELTS = [
    {"speed": 240.0, "dir": 1, "mode": "loop", "spacing": 168, "points": 50},
    {"speed": 150.0, "dir": -1, "mode": "loop", "spacing": 186, "points": 30},
    {"speed": 82.0, "dir": 1, "mode": "pingpong", "spacing": 200, "points": 20},
]
BELT_COLORS = [(255, 183, 3), (110, 210, 240), (255, 143, 171)]

DIFFICULTIES = ["easy", "medium", "hard"]

DIFF = {
    "easy": {
        "speed": 0.60, "needed": 0.45, "tissue": 0.030, "tissue_step": 0.006,
        "starve": 2.0, "penalty": 0, "mult": 1.0, "guide": True,
    },
    "medium": {
        "speed": 0.85, "needed": 0.35, "tissue": 0.050, "tissue_step": 0.010,
        "starve": 3.0, "penalty": 5, "mult": 1.5, "guide": True,
    },
    "hard": {
        "speed": 1.10, "needed": 0.28, "tissue": 0.070, "tissue_step": 0.013,
        "starve": 4.0, "penalty": 10, "mult": 2.0, "guide": False,
    },
}
LEVEL_SPEEDUP = 0.08        # +8% belt speed per level
EMPTY_CHANCE = 0.12

# Colours
INK = (34, 24, 48)
WHITE = (255, 255, 255)
CREAM = (255, 246, 222)
YELLOW = (255, 214, 10)
GREEN = (120, 200, 60)
BOOGER = (138, 190, 52)
BOOGER_DARK = (82, 128, 30)
RED = (230, 57, 70)
SKIN = (246, 196, 160)
SKIN_DARK = (214, 150, 118)
SLEEVE = (66, 110, 220)
BG_TOP = (44, 22, 70)
BG_BOTTOM = (18, 10, 32)
