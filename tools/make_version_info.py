#!/usr/bin/env python3
"""Write a PyInstaller Windows version-resource file (shown in the .exe's Properties > Details)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from pnf import __version__  # noqa: E402

nums = tuple(int(x) for x in __version__.split(".")) + (0,)
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "builds", "windows", "version_info.txt")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write("""VSVersionInfo(
  ffi=FixedFileInfo(filevers=%(n)r, prodvers=%(n)r, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Shouku Games'),
      StringStruct('FileDescription', "Pick 'n' Flick v%(v)s"),
      StringStruct('FileVersion', 'v%(v)s'),
      StringStruct('InternalName', 'PickNFlick'),
      StringStruct('LegalCopyright', 'Shawn Rapaz and Claude Code - GPLv3'),
      StringStruct('OriginalFilename', 'PickNFlick-v%(v)s-windows.exe'),
      StringStruct('ProductName', "Pick 'n' Flick"),
      StringStruct('ProductVersion', 'v%(v)s')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""" % {"n": nums, "v": __version__})
print(out)
