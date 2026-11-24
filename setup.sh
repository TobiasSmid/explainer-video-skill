#!/usr/bin/env bash
# Installs what the explainer-video skill needs in Claude's cloud workspace. Safe to run again.
set -e
cd "$(dirname "$0")"

if ! python3 -c "import manim, manim_voiceover, kokoro_onnx, misaki, spacy" 2>/dev/null || ! command -v dvisvgm >/dev/null; then
  apt-get update -q
  apt-get install -y -q libpango1.0-dev pkg-config dvisvgm texlive-latex-extra texlive-fonts-recommended sox espeak-ng
  pip install --break-system-packages -q manim manim-voiceover "kokoro-onnx>=0.6" soundfile num2words
  # plain misaki + a prebuilt spacy: "misaki[en]" tries to build spacy from source and fails
  pip install --break-system-packages -q --only-binary=:all: spacy
  pip install --break-system-packages -q misaki https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
fi

# Kokoro model that reports timings (release model-files-v1.1). The older v1.0 file and the int8 file do not work.
REL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1
mkdir -p models
[ -f models/kokoro-timed.onnx ] || { curl -sSL -o models/kokoro-timed.part $REL/kokoro-v1.0.onnx && mv models/kokoro-timed.part models/kokoro-timed.onnx; }
[ -f models/voices.bin ] || { curl -sSL -o models/voices.part $REL/voices-v1.0.bin && mv models/voices.part models/voices.bin; }

python3 -c "import manim, manim_voiceover, kokoro_onnx, misaki, spacy; print('SETUP OK')"
