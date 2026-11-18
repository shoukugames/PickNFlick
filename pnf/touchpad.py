"""On-screen buttons for phones and tablets (shown during play on touch screens).

Pick 'n' Flick is played with held keys: Left/Right aim, Up/Down choose a belt, holding Space
picks and pressing it flicks. These buttons stand in for those keys, including holding them.
"""
import pygame

from . import config as C
from . import gfx

# name -> (rect, label); the labels "<", ">", "^", "v" and "II" are drawn as shapes
BUTTONS = {
    "left": (pygame.Rect(56, 600, 112, 100), "<"),
    "right": (pygame.Rect(180, 600, 112, 100), ">"),
    "up": (pygame.Rect(310, 600, 104, 46), "^"),
    "down": (pygame.Rect(310, 654, 104, 46), "v"),
    "flick": (pygame.Rect(740, 600, 330, 100), "flick"),
    "pause": (pygame.Rect(1090, 612, 84, 84), "II"),
}


class TouchPad:
    def __init__(self):
        self.held = {}          # finger/mouse id -> button name

    def hit(self, pos):
        for name, (rect, _) in BUTTONS.items():
            if rect.inflate(10, 10).collidepoint(pos):
                return name
        return None

    def holding(self, name):
        return name in self.held.values()

    def draw(self, surf, flick_label):
        for name, (rect, label) in BUTTONS.items():
            down = self.holding(name)
            gfx.panel(surf, rect, (255, 214, 92) if down else (255, 246, 222), C.INK, 18, 4, shadow=not down)
            cx, cy = rect.center
            ink = C.INK
            if label == "<" or label == ">":
                d = -1 if label == "<" else 1
                pygame.draw.polygon(surf, ink, [(cx + d * 26, cy), (cx - d * 18, cy - 28), (cx - d * 18, cy + 28)])
            elif label == "^" or label == "v":
                d = -1 if label == "^" else 1
                pygame.draw.polygon(surf, ink, [(cx, cy + d * 14), (cx - 20, cy - d * 10), (cx + 20, cy - d * 10)])
            elif label == "II":
                pygame.draw.rect(surf, ink, (cx - 16, cy - 20, 11, 40), border_radius=3)
                pygame.draw.rect(surf, ink, (cx + 5, cy - 20, 11, 40), border_radius=3)
            else:
                gfx.text(surf, flick_label, 34, ink, (cx, cy))
