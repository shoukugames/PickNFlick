#!/usr/bin/env python3
"""Pick 'n' Flick launcher: the desktop game, or the browser version when run by pygbag.

Web build:  python3 tools/build_web.py     (writes build/web/)
"""
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame  # noqa: E402,F401  (imported here so pygbag loads pygame for the web build)

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
