#!/usr/bin/env python3
"""Pick 'n' Flick launcher."""
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pnf import __version__  # noqa: E402


def main():
    if any(a in ("--version", "-V") for a in sys.argv[1:]):
        print("Pick 'n' Flick v" + __version__)
        return
    from pnf.app import App
    App().run()


if __name__ == "__main__":
    main()
