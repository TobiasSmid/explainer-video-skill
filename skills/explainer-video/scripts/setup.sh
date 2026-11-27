#!/usr/bin/env bash
# Sets up the CURRENT folder as the working folder for explainer videos. Safe to run again.
#   1. copies the code files that sit next to this script into the folder (copies already there are kept)
#   2. installs what is missing: LaTeX, ffmpeg and sox (apt), manim and the voice packages (pip)
#   3. puts the narration voice (narrator.npz, part of this skill) and the Kokoro model into ./models, plus the
#      speech recognizer for the listen-back check, and checks their checksums
# Python packages are pinned to the versions this skill was tested with, so an upstream release cannot
# break it; a folder with other versions is brought to the pinned ones.
# It never uses sudo. As root (a disposable container such as Claude's cloud workspace) it installs
# system-wide. Otherwise Python packages go into the active virtualenv, or into a new ./.venv, and
# missing system packages are only reported.
set -e
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
have() { command -v "$1" >/dev/null 2>&1; }
have python3 || { echo "MISSING python3"; exit 1; }

for f in speech_text.py kokoro_service.py explainer_lib.py prenarrate.py listen.py finish.py; do
  if [ ! -f "$f" ]; then
    cp "$SRC/$f" "$f"
  elif ! cmp -s "$SRC/$f" "$f"; then
    echo "KEPT $f (it differs from the skill's copy; delete it to get the skill's version)"
  fi
done
# manim asks PyPI for its newest version on every run; switch that off, so rendering needs no network
[ -f manim.cfg ] || printf '[CLI]\nnotify_outdated_version = False\n' > manim.cfg

VENV=""
if [ -z "$VIRTUAL_ENV" ] && [ -x .venv/bin/python3 ]; then
  VENV="$PWD/.venv/bin"; export PATH="$VENV:$PATH"
fi
MODS="manim, manim_voiceover, kokoro_onnx, misaki, spacy, en_core_web_sm, num2words, soundfile, sherpa_onnx"
# Tested versions. To move to newer ones: change them here, make a test video, then publish.
PINS="manim==0.22.1 manim-voiceover==0.4.0 kokoro-onnx==0.6.1 onnxruntime==1.29.0 misaki==0.7.4 spacy==3.8.18
      en-core-web-sm==3.8.0 num2words==0.5.14 soundfile==0.14.0 sherpa-onnx==2.0.3"
py_ok() {
  python3 - $PINS <<'EOF' 2>/dev/null
import sys
from importlib.metadata import version
sys.exit(any(version(p.split("==")[0]) != p.split("==")[1] for p in sys.argv[1:]))
EOF
}
sys_ok() { have latex && have dvisvgm && have ffmpeg; }
APT="libpango1.0-dev pkg-config dvisvgm texlive-latex-extra texlive-fonts-recommended sox espeak-ng ffmpeg"

if have apt-get && [ "$(id -u)" = 0 ]; then
  if ! sys_ok || ! py_ok; then
    apt-get update -q
    apt-get install -y -q $APT
  fi
elif ! sys_ok; then
  echo "MISSING system packages: LaTeX (with latex-extra and dvisvgm), ffmpeg, sox and the pango development"
  echo "files. Install them and run this script again. On Debian or Ubuntu:"
  echo "  sudo apt-get install $APT"
  echo "Other systems: https://docs.manim.community/en/stable/installation.html"
  exit 1
fi

if ! py_ok; then
  if [ -n "$VIRTUAL_ENV" ] || [ -n "$VENV" ]; then
    :                                    # install into the virtualenv that is in use
  elif [ "$(id -u)" = 0 ]; then
    export PIP_BREAK_SYSTEM_PACKAGES=1   # disposable container: install system-wide
  else
    python3 -m venv .venv
    VENV="$PWD/.venv/bin"; export PATH="$VENV:$PATH"
  fi
  python3 -m pip install -q manim==0.22.1 manim-voiceover==0.4.0 kokoro-onnx==0.6.1 onnxruntime==1.29.0 \
    soundfile==0.14.0 num2words==0.5.14 sherpa-onnx==2.0.3
  # plain misaki + a prebuilt spacy: "misaki[en]" tries to build spacy from source and fails
  python3 -m pip install -q --only-binary=:all: spacy==3.8.18
  python3 -m pip install -q misaki==0.7.4 https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
  py_ok || echo "WARNING: some Python packages are not at the tested versions (pip kept others); it may still work"
fi

sha() { python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())" "$1"; }
fetch() {  # fetch <file> <sha256> <url> [fallback url ...]: download once; refuse a file that is not the expected one
  local file="$1" want="$2"; shift 2
  [ -f "models/$file" ] && return 0
  for url in "$@"; do
    if curl -fsSL -o "models/$file.part" "$url" && [ "$(sha "models/$file.part")" = "$want" ]; then
      mv "models/$file.part" "models/$file"
      return 0
    fi
    rm -f "models/$file.part"
  done
  echo "DOWNLOAD FAILED or CHECKSUM MISMATCH for $file"
  exit 1
}
mkdir -p models
# The narration voice: Kokoro's am_puck, every tone shifted a little deeper (it ships with this skill).
cp "$SRC/narrator.npz" models/narrator.npz
# Kokoro model that reports timings. From this skill's own GitHub release, so it keeps working if the original
# goes away; the original kokoro-onnx release (model-files-v1.1) is the fallback. Same file, same checksum.
fetch kokoro-timed.onnx beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a \
  https://github.com/TobiasSmid/explainer-video-skill/releases/download/kokoro-model/kokoro-timed.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx

# Speech recognizer for the listen-back check (Moonshine base, from the sherpa-onnx release on GitHub).
# Without it everything else still works; prenarrate then skips the check.
ASR=sherpa-onnx-moonshine-base-en-int8
if [ ! -f "models/asr/$ASR/tokens.txt" ]; then
  if (fetch asr.tar.bz2 21870cecaa2e44e4e2bf63e02d1072bed183ccd10284871353bd9d24dad14e5e \
        https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/$ASR.tar.bz2); then
    mkdir -p models/asr && tar xjf models/asr.tar.bz2 -C models/asr --exclude='*/test_wavs*' && rm -f models/asr.tar.bz2
  else
    echo "NO LISTEN: the speech recognizer could not be downloaded; the listen-back check is skipped"
  fi
fi

if [ -n "$VENV" ]; then echo "VENV $VENV"; fi
python3 -c "import $MODS; print('SETUP OK')"
