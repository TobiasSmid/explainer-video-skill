# kokoro_service.py

Connects the voice in `speech_text.py` to manim-voiceover and caches the audio. It expects the Kokoro model files in a `models` folder next to it.

This page is the source of the module. The skill copies the code block below, unchanged, into `kokoro_service.py` in the working folder (section 3 of SKILL.md).

```python
"""manim-voiceover speech service using the local Kokoro voice (settings live in speech_text.py)."""
import os
from pathlib import Path

import onnxruntime as rt
import soundfile as sf
from kokoro_onnx import Kokoro
from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import SpeechService, initialize_speech_service

import speech_text

MODELS = Path(__file__).resolve().parent / "models"  # the model files sit next to this module
_KOKORO = None


def _engine():
    global _KOKORO
    if _KOKORO is None:
        opts = rt.SessionOptions()
        # onnxruntime's default can end up on one thread (it does in Claude's cloud workspace);
        # using all cores makes narration 1.6x faster
        cores = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
        opts.intra_op_num_threads = cores or 1
        session = rt.InferenceSession(str(MODELS / "kokoro-timed.onnx"), opts, providers=["CPUExecutionProvider"])
        _KOKORO = Kokoro.from_session(session, str(MODELS / "voices.bin"))
    return _KOKORO


class KokoroService(SpeechService):
    def __init__(self, **kwargs):
        initialize_speech_service(self, kwargs)

    def input_data(self, text):
        """The cache key: the spoken text plus every setting that changes the audio."""
        return {"input_text": remove_bookmarks(text), "service": "kokoro", "settings": speech_text.settings()}

    def generate_from_text(self, text, cache_dir=None, path=None, **kwargs):
        cache_dir = cache_dir or self.cache_dir
        input_data = self.input_data(text)
        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            return cached
        audio_path = path or (self.get_audio_basename(input_data) + ".wav")
        samples, sr = speech_text.narrate(_engine(), input_data["input_text"])
        sf.write(str(Path(cache_dir) / audio_path), samples, sr)
        return {"input_text": text, "input_data": input_data, "original_audio": str(audio_path)}
```
