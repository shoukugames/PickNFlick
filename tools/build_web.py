#!/usr/bin/env python3
"""Build the browser version into build/web/ with pygbag (https://pygame-web.github.io).

1. Composes every music track once into web_music/*.ogg (composing takes over a second per
   track even on a PC, too slow for a browser, which also can't compose in the background).
2. Runs pygbag, which packs the game folder into build/web/.

Needs: pygame, pygbag (python3 -m pip install pygbag) and ffmpeg on PATH (or FFMPEG=/path).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from pnf import music  # noqa: E402

RATE = 22050


def compose_tracks(ffmpeg):
    out = os.path.join(ROOT, "web_music")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    composer = music.Composer(RATE)
    with tempfile.TemporaryDirectory() as tmp:
        for name in music.TRACKS:
            data = composer.render(name, 2)
            composer.note_cache.clear()
            wav = os.path.join(tmp, name + ".wav")
            with wave.open(wav, "wb") as handle:
                handle.setnchannels(2)
                handle.setsampwidth(2)
                handle.setframerate(RATE)
                handle.writeframes(data)
            subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "4",
                            os.path.join(out, name + ".ogg")], check=True)
    size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
    print(f"web_music: {len(music.TRACKS)} tracks, {size // 1024} KB")


if __name__ == "__main__":
    ffmpeg = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found (set FFMPEG=/path/to/ffmpeg)")
    compose_tracks(ffmpeg)
    env = dict(os.environ, PATH=os.path.dirname(os.path.abspath(ffmpeg)) + os.pathsep + os.environ.get("PATH", ""))
    icon = [a for a in ("assets/icon.png", "assets/icons/icon-256.png") if os.path.exists(os.path.join(ROOT, a))]
    subprocess.run([sys.executable, "-m", "pygbag", "--build", "--title", "Pick 'n' Flick", "--app_name", "picknflick"]
                   + (["--icon", icon[0]] if icon else []) + ["."], cwd=ROOT, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(os.path.join(ROOT, "build", "web", "index.html")):
        sys.exit("pygbag did not write build/web/index.html")
    print("build/web ready: upload the folder as-is")

# pygbag sometimes sizes the canvas before the game has opened its window, squeezing the game
# into a square: add a small script that keeps it the game's shape (tools/web_canvas_fix.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import web_canvas_fix  # noqa: E402

web_canvas_fix.apply(os.path.join(ROOT, "build", "web", "index.html"))
