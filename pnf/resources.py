import os
import sys


def resource_path(*parts):
    """Locate bundled assets both from source and from a PyInstaller build."""
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def data_dir():
    """Per-user writable folder for saves, scores and progress."""
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        root = os.path.expanduser("~/Library/Application Support")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(root, "PickNFlick")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = os.path.abspath(".")
    return path
