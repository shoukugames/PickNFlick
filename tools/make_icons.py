#!/usr/bin/env python3
"""Render the game icon to assets/icon.png and assets/icon.ico (PNG-in-ICO)."""
import io
import os
import struct
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))
from pnf.gfx import make_icon  # noqa: E402

out = os.path.join(ROOT, "assets")
pygame.image.save(make_icon(256), os.path.join(out, "icon.png"))

sizes = [16, 32, 48, 64, 128, 256]
blobs = []
for s in sizes:
    path = os.path.join(out, "_tmp_%d.png" % s)
    pygame.image.save(make_icon(s), path)
    with open(path, "rb") as f:
        blobs.append(f.read())
    os.remove(path)

ico = io.BytesIO()
ico.write(struct.pack("<HHH", 0, 1, len(sizes)))
offset = 6 + 16 * len(sizes)
for s, data in zip(sizes, blobs):
    dim = 0 if s >= 256 else s
    ico.write(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset))
    offset += len(data)
for data in blobs:
    ico.write(data)
with open(os.path.join(out, "icon.ico"), "wb") as f:
    f.write(ico.getvalue())
print("wrote assets/icon.png and assets/icon.ico")
