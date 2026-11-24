"""Generate and cache the narration of a beats file, before or while the scene is written.

Usage (from the explainer folder):  python3 prenarrate.py beats_01_union
Prints the length of every beat, so the scene can be timed while it is written. Beats that are
already cached are skipped, so re-running after an edit only makes the changed ones.
"""
import importlib
import sys
import time
from pathlib import Path

import soundfile as sf

import speech_text
from kokoro_service import KokoroService

beats = importlib.import_module(sys.argv[1].removesuffix(".py")).BEATS
service = KokoroService()
start, total, made = time.time(), 0.0, 0
for key, text in beats.items():
    text = " ".join(text.split())
    data = service.get_cached_result(service.input_data(text), service.cache_dir)
    if data is None:
        data = service._wrap_generate_from_text(text)
        made += 1
    secs = sf.info(str(Path(service.cache_dir) / data["final_audio"])).duration
    total += secs
    print(f"{key:28} {secs:5.1f}s", flush=True)
units, passes = speech_text.PASSES
print(f"TOTAL {total:.0f}s of narration; {made} new beats made in {time.time() - start:.0f}s "
      f"({units} sentences, {passes} synthesis passes)")
