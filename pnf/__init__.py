"""Pick 'n' Flick - a booger-flicking spelling shooting gallery."""
__version__ = "0.2.0"

# True when running in a web browser (pygbag / WebAssembly).
import sys as _sys
WEB = _sys.platform == "emscripten"
