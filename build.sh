#!/usr/bin/env bash
# Build everything: Linux .deb and Windows .exe (via Wine). Results land in builds/.
set -euo pipefail
cd "$(dirname "$0")"
./build_linux.sh
./build_windows.sh
ls -lh builds/*.deb builds/*.exe
