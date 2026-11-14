#!/usr/bin/env bash
# Build ColorSight debug APK with Buildozer and copy it to dist/.
# Intended for WSL2 Ubuntu / Linux — not native Windows.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p dist

echo "==> ColorSight Android debug build"
echo "    project: $ROOT"

if ! command -v buildozer >/dev/null 2>&1; then
  echo "ERROR: buildozer not found. Install with: pip3 install --user buildozer cython"
  exit 1
fi

buildozer android debug

APK="$(ls -1t bin/colorsight-*-debug.apk 2>/dev/null | head -n1 || true)"
if [[ -z "${APK}" ]]; then
  echo "ERROR: no debug APK found under bin/"
  exit 1
fi

cp -f "$APK" dist/
echo "==> Copied $(basename "$APK") → dist/"
ls -lh dist/
echo "==> Done. Install with: adb install -r dist/$(basename "$APK")"
