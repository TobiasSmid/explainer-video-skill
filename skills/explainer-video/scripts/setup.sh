#!/usr/bin/env bash
# Sets up the CURRENT folder as the working folder for explainer videos. Safe to run again.
#   1. copies the code files that sit next to this script into the folder (copies already there are kept)
#   2. installs what is missing: LaTeX, ffmpeg and sox (apt), manim and the voice packages (pip)
#   3. downloads the Kokoro voice model into ./models and checks its checksum
# It never uses sudo. As root (a disposable container such as Claude's cloud workspace) it installs
# system-wide. Otherwise Python packages go into the active virtualenv, or into a new ./.venv, and
# missing system packages are only reported.
set -e
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
have() { command -v "$1" >/dev/null 2>&1; }
have python3 || { echo "MISSING python3"; exit 1; }

for f in speech_text.py kokoro_service.py explainer_lib.py prenarrate.py; do
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
MODS="manim, manim_voiceover, kokoro_onnx, misaki, spacy, en_core_web_sm, num2words, soundfile"
py_ok() { python3 -c "import $MODS" 2>/dev/null; }
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
  python3 -m pip install -q manim manim-voiceover "kokoro-onnx>=0.6" soundfile num2words
  # plain misaki + a prebuilt spacy: "misaki[en]" tries to build spacy from source and fails
  python3 -m pip install -q --only-binary=:all: spacy
  python3 -m pip install -q misaki https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
fi

# Kokoro model that reports timings (release model-files-v1.1). The older v1.0 file and the int8 file do not work.
REL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1
fetch() {  # fetch <file> <url> <sha256>: download once, and refuse a file that is not the expected one
  [ -f "models/$1" ] && return 0
  curl -fsSL -o "models/$1.part" "$2"
  local got
  got=$(python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())" "models/$1.part")
  if [ "$got" != "$3" ]; then
    rm -f "models/$1.part"
    echo "CHECKSUM MISMATCH for $1: got $got"
    exit 1
  fi
  mv "models/$1.part" "models/$1"
}
mkdir -p models
fetch kokoro-timed.onnx $REL/kokoro-v1.0.onnx beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a
fetch voices.bin $REL/voices-v1.0.bin bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d

if [ -n "$VENV" ]; then echo "VENV $VENV"; fi
python3 -c "import $MODS; print('SETUP OK')"
