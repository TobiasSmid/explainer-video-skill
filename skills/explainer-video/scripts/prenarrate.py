"""Generate and cache the narration of a beats file, before or while the scene is written.

Usage (from the explainer folder):  python3 prenarrate.py beats_01_union [--no-listen | --listen-all]
Prints the length of every beat and the time of every bookmark in it, so the scene can be timed
while it is written. Beats that are already cached are skipped, so re-running after an edit only
makes the changed ones. Then it listens back to every new beat with a speech recognizer and prints
a LISTEN line for each stretch that came out wrong (see listen.py).
"""
import importlib
import re
import sys
import time
from pathlib import Path

import soundfile as sf
from manim_voiceover.tracker import TimeInterpolator

import speech_text
from kokoro_service import KokoroService, one_line

BOOKMARK = re.compile(r"<bookmark\s*mark\s*=['\"](\w*)['\"]\s*/>")


def bookmark_times(data) -> dict:
    """{mark: seconds into the beat}, computed the way manim-voiceover does it."""
    if not data.get("word_boundaries"):
        return {}
    f = TimeInterpolator(data["word_boundaries"])
    out, content = {}, ""
    for part in re.split(r"(<bookmark\s*mark\s*=['\"]\w*['\"]\s*/>)", data["input_text"]):
        m = BOOKMARK.fullmatch(part)
        if m:
            out[m.group(1)] = f.interpolate(len(content))
        else:
            content += part
    return out


beats = importlib.import_module(sys.argv[1].removesuffix(".py")).BEATS
listen_back = "--no-listen" not in sys.argv
service = KokoroService()
start, total, made, new = time.time(), 0.0, 0, []
for key, text in beats.items():
    text = one_line(text)
    data = service.get_cached_result(service.input_data(text), service.cache_dir)
    if data is None:
        data = service._wrap_generate_from_text(text)
        made += 1
        new.append((key, text, data))
    elif "--listen-all" in sys.argv:
        new.append((key, text, data))
    secs = sf.info(str(Path(service.cache_dir) / data["final_audio"])).duration
    total += secs
    marks = "  ".join(f"@{m} {t:.1f}s" for m, t in bookmark_times(data).items())
    print(f"{key:28} {secs:5.1f}s  {marks}".rstrip(), flush=True)
readings, sentences = speech_text.PASSES
print(f"TOTAL {total:.0f}s of narration; {made} new beats made in {time.time() - start:.0f}s "
      f"({sentences} sentences in {readings} Kokoro readings)", flush=True)

if listen_back and new:
    import listen
    start, flagged = time.time(), 0
    try:
        for key, text, data in new:
            for said, heard in listen.check(text, Path(service.cache_dir) / data["final_audio"]):
                print(f"LISTEN {key}: said {said!r}, heard {heard!r}", flush=True)
                flagged += 1
        print(f"LISTEN checked {len(new)} new beats in {time.time() - start:.0f}s: {flagged} to look at", flush=True)
    except FileNotFoundError as e:
        print(f"LISTEN skipped: {e}", flush=True)
