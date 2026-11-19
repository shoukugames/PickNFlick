#!/usr/bin/env python3
"""Pick 'n' Flick launcher: the desktop game, or the browser version when run by pygbag.

Web build:  python3 tools/build_web.py     (writes build/web/)
"""
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame  # noqa: E402,F401  (imported here so pygbag loads pygame for the web build)

# Browser audio: the page mixes sound on its main thread, between the game's frames, so a small
# mixer buffer runs dry whenever a frame takes a little longer, and the sound crackles and drops
# out. 2048 samples (43 ms at the browser's 48 kHz) rides over slow frames. Browser only.
if sys.platform == "emscripten":
    WEB_AUDIO_BUFFER = 2048

    def _web_audio_buffer(fn):
        def call(*args, **kwargs):
            if len(args) >= 4:
                args = args[:3] + (WEB_AUDIO_BUFFER,) + args[4:]
            else:
                kwargs["buffer"] = WEB_AUDIO_BUFFER
            return fn(*args, **kwargs)
        return call

    pygame.mixer.pre_init = _web_audio_buffer(pygame.mixer.pre_init)
    pygame.mixer.init = _web_audio_buffer(pygame.mixer.init)
    pygame.mixer.pre_init()

from pnf import __version__  # noqa: E402


def main():
    if any(a in ("--version", "-V") for a in sys.argv[1:]):
        print("Pick 'n' Flick v" + __version__)
        return
    from pnf.app import App
    App().run()


if sys.platform == "emscripten":
    import asyncio

    from pnf.app import App

    async def web_main():
        await App().run_web()

    asyncio.run(web_main())
elif __name__ == "__main__":
    main()
