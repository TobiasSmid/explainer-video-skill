"""Listen-back check: transcribe narration with a local speech recognizer and report words that
came out wrong. Claude cannot hear the audio; this is how it finds "automatar" or "uh" for "A".

    import listen
    for said, heard in listen.check(text, "media/voiceovers/xyz.wav"):
        print(said, "->", heard)

Differences that only differ in spelling ("their"/"there", "two"/"too", "Q0"/"q zero") are ignored:
both sides are turned into sounds with the same dictionary the voice uses, and only differences
that also SOUND different are reported. The recognizer is Moonshine (sherpa-onnx), from
models/asr, downloaded by setup.sh.
"""
import difflib
import re
from pathlib import Path

import numpy as np
import soundfile as sf

import speech_text

ASR = Path(__file__).resolve().parent / "models" / "asr"
_REC = [None]
SIMILAR = 0.72        # sound similarity at or above which a difference is ignored
CHUNK = 20.0          # seconds of audio per recognizer call (it handles up to about 30)
# small words a recognizer often drops even when they were spoken fine (case matters: "A" is a letter)
_SMALL = set("a the of and to is in it that this we you are be an as at on or for so then but its by with".split())


def _recognizer():
    if _REC[0] is None:
        import sherpa_onnx as so
        d = next(p for p in ASR.iterdir() if p.is_dir()) if ASR.is_dir() else None
        if d is None:
            raise FileNotFoundError(f"no speech recognizer in {ASR}; run setup.sh")
        _REC[0] = so.OfflineRecognizer.from_moonshine(
            preprocessor=str(d / "preprocess.onnx"), encoder=str(d / "encode.int8.onnx"),
            uncached_decoder=str(d / "uncached_decode.int8.onnx"), cached_decoder=str(d / "cached_decode.int8.onnx"),
            tokens=str(d / "tokens.txt"), num_threads=2)
    return _REC[0]


def _chunks(x: np.ndarray, sr: int):
    """Cut the audio into pieces of at most CHUNK seconds, at the quietest moment near each cut."""
    hop = sr // 100
    start = 0
    while len(x) - start > CHUNK * sr:
        lo, hi = start + int((CHUNK - 6) * sr), start + int(CHUNK * sr)
        frames = x[lo:hi][: (hi - lo) // hop * hop].reshape(-1, hop)
        cut = lo + int(np.argmin((frames ** 2).mean(1))) * hop
        yield x[start:cut]
        start = cut
    yield x[start:]


def transcribe(path) -> str:
    x, sr = sf.read(str(path), dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    rec, out = _recognizer(), []
    for piece in _chunks(x, sr):
        s = rec.create_stream()
        s.accept_waveform(sr, piece)
        rec.decode_stream(s)
        out.append(s.result.text)
    return " ".join(out)


def spoken(text: str) -> str:
    """What the narration is meant to say, in plain words (no bookmarks, pauses or markup)."""
    text = re.sub(r"<bookmark[^>]*>", "", text)
    text = speech_text.PAUSE.sub(" ", text)
    text = re.sub(r"\[([^\]]+)\]\(/[^)]*/\)", r"\1", speech_text.normalize(text))
    return text


def _words(text: str, heard: bool = False) -> list:
    out = []
    for w in re.findall(r"[A-Za-z0-9']+", text):
        if heard:  # "Q0" -> "Q zero", "42" -> "forty-two": compare like with like
            w = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", w)
            w = re.sub(r"\d+", lambda m: " " + _num(m.group()) + " ", w)
        out += w.split()
    return out


def _num(d: str) -> str:
    try:
        from num2words import num2words
        return num2words(int(d)).replace("-", " ")
    except Exception:
        return d


def _sounds(words: list) -> str:
    if not words:
        return ""
    text = " ".join(words)
    try:
        ps = speech_text._g2p()(speech_text._mark_up(text))[0]
    except Exception:
        ps = text.lower()
    return re.sub(r"[ˈˌ\s,.?!;:—]", "", ps).replace("ɾ", "T").replace("ɐ", "ə")


def check(text: str, audio_path) -> list:
    """[(said, heard), ...] for every stretch that sounds different from the script."""
    said, heard = _words(spoken(text)), _words(transcribe(audio_path), heard=True)
    low = lambda ws: [w.lower() for w in ws]
    out = []
    for op, a, b, c, d in difflib.SequenceMatcher(None, low(said), low(heard), autojunk=False).get_opcodes():
        if op == "equal":
            continue
        if any(w in speech_text.CUSTOM for w in said[a:b]):
            continue  # its pronunciation was already set by hand; the recognizer just doesn't know the word
        if c == d and any(w not in _SMALL for w in said[a:b]):
            out.append((" ".join(said[a:b]), ""))  # a word that was never heard: "A" read as "uh", a dropped symbol
            continue
        if a == b or c == d:  # a word only on one side: compare with a neighbour attached on both sides
            a, b, c, d = max(a - 1, 0), min(b + 1, len(said)), max(c - 1, 0), min(d + 1, len(heard))
        s, h = _sounds(said[a:b]), _sounds(heard[c:d])
        if difflib.SequenceMatcher(None, s, h).ratio() >= SIMILAR:
            continue
        out.append((" ".join(said[a:b]), " ".join(heard[c:d])))
    return out
