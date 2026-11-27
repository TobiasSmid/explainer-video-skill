"""manim-voiceover speech service using the local Kokoro voice (settings live in speech_text.py).

It also reports when every word starts, so scenes can time animations to a word with bookmarks:
    with self.say("We take the <bookmark mark='u'/>union of both.") as tr:
        self.wait_until_bookmark("u")
"""
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
RES = 10_000_000  # manim-voiceover's audio_offset unit (100 ns)


def _engine():
    global _KOKORO
    if _KOKORO is None:
        opts = rt.SessionOptions()
        # onnxruntime's default can end up on one thread (it does in Claude's cloud workspace);
        # using all cores makes narration 1.6x faster
        cores = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
        opts.intra_op_num_threads = cores or 1
        session = rt.InferenceSession(str(MODELS / "kokoro-timed.onnx"), opts, providers=["CPUExecutionProvider"])
        _KOKORO = Kokoro.from_session(session, str(MODELS / "narrator.npz"))  # the skill's one voice
    return _KOKORO


def one_line(text: str) -> str:
    """The form of a beat that is spoken and cached: whitespace collapsed (a beat may span lines)."""
    return " ".join(text.split())


def word_boundaries(script: str, bounds) -> list:
    """speech_text bounds -> manim-voiceover word boundaries (strictly increasing text offsets)."""
    out, last = [], -1
    for at, t in bounds:
        if at <= last:
            continue
        end = script.find(" ", at)
        word = script[at:end if end > 0 else len(script)]
        out.append({"audio_offset": int(t * RES), "text_offset": at, "word_length": len(word),
                    "text": word, "boundary_type": "Word"})
        last = at
    if out and out[0]["text_offset"] > 0:
        out.insert(0, {"audio_offset": 0, "text_offset": 0, "word_length": 0, "text": "", "boundary_type": "Word"})
    return out


class KokoroService(SpeechService):
    def __init__(self, **kwargs):
        initialize_speech_service(self, kwargs)

    def input_data(self, text):
        """The cache key: the spoken text plus every setting that changes the audio."""
        return {"input_text": remove_bookmarks(one_line(text)), "service": "kokoro", "settings": speech_text.settings()}

    def generate_from_text(self, text, cache_dir=None, path=None, **kwargs):
        cache_dir = cache_dir or self.cache_dir
        text = one_line(text)
        input_data = self.input_data(text)
        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            return cached
        audio_path = path or (self.get_audio_basename(input_data) + ".wav")
        script, bounds = input_data["input_text"], []
        samples, sr = speech_text.narrate(_engine(), script, bounds)
        sf.write(str(Path(cache_dir) / audio_path), samples, sr)
        return {"input_text": text, "input_data": input_data, "original_audio": str(audio_path),
                "word_boundaries": word_boundaries(script, bounds)}
