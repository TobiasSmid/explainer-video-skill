# speech_text.py

The narration voice: how math notation is pronounced, one fixed Kokoro voice, an even pace, pauses by rule and a warmer sound. All settings are at the top.

This page is the source of the module. The skill copies the code block below, unchanged, into `speech_text.py` in the working folder (section 3 of SKILL.md).

```python
"""Turn narration with math notation into calm, even, natural Kokoro speech.

Script conventions:
  - Write math as you would on a slide: A ∪ B, ε-transition, q₀, δ(q, a), Σ*.
  - A standalone capital letter (A, B, D, L, N...) is read as a letter name ("ay", "bee").
  - Use lowercase "a" for the article; avoid starting a sentence with the article "A".
  - "[pause 0.8]" adds 0.8 seconds of extra silence between beats.
  - Force a pronunciation with misaki's inline syntax: [Kleene](/klˈAni/), or add the word to CUSTOM.

How it gets an even, human delivery (each point fixes a problem you can hear without it):
  - Pronunciation: misaki's G2P (dictionary + part of speech), the phonemes Kokoro was trained on,
    with the soft American t written as "T". ("ɾ" makes Kokoro roll an r: a foreign accent.)
  - One voice: Kokoro picks a different voice style for every input length, which shifts pitch and
    tone from one sentence to the next. narrator() uses one fixed style for everything.
  - One pace: Kokoro talks faster the longer its input (a 3-word and a 30-word sentence differ by 40%).
    Every unit is measured with the model's own timings and re-rendered at the speed that hits PACE.
  - Pauses by rule: commas, sentence ends, questions and the end of every clip get a set silence,
    spliced into the gap the model already left, so sentences stay in one piece.
Needs the Kokoro export that reports timings (release "model-files-v1.1") and kokoro-onnx >= 0.6.
"""
import re
import subprocess
import warnings

import numpy as np

warnings.filterwarnings("ignore")

# ---- The narration voice ----
VOICE = "am_puck"        # ONE Kokoro voice. Never blend voices: blends sound unstable.
BRITISH = VOICE[0] == "b"  # a British voice (bm_/bf_) needs British sounds instead of American ones
PACE = 19.5              # speaking rate in sounds per second (about 140 words/min with pauses). Lower = calmer.
CLAUSE_PAUSE = 0.20      # after , ; :
SENTENCE_PAUSE = 0.50    # after . !
QUESTION_PAUSE = 0.70    # after ?  (a question gets a moment to land)
WARM = True              # warmer, softer sound (EQ + gentle compression); False = Kokoro's plain output
STYLE_ROWS = (100, 160)  # the voice style Kokoro uses for a normal-length sentence, used for everything

SR = 24000
_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_NUM = "zero one two three four five six seven eight nine".split()

SYMBOLS = [
    (r"Σ\*", " sigma star "), (r"Σ", " sigma "), (r"∪", " union "), (r"∩", " intersect "),
    (r"ε", " epsilon "), (r"δ", " delta "), (r"∈", " is in "), (r"∉", " is not in "),
    (r"→", " goes to "), (r"⊆", " is a subset of "), (r"⊂", " is a proper subset of "),
    (r"∅", " the empty set "), (r"×", " times "), (r"∘", " composed with "), (r"≤", " is at most "),
    (r"≥", " is at least "), (r"≠", " is not equal to "), (r"¬", " not "), (r"∧", " and "),
    (r"∨", " or "), (r"⇒", " implies "), (r"⇔", " if and only if "), (r"∀", " for all "),
    (r"∃", " there exists "), (r"-transition", " transition"), (r"\.\.\.|…", ","), (r"[(){}]", " "),
    (r"\s*=\s*", " equals "), (r"\*", " star "),
]
LETTER = re.compile(r"(?<![\w'\[/])([A-HJ-Z])(?![\w'\]])")  # every capital except the pronoun I
LETTER_PH = {"A": "ˈA", "B": "bˈi", "C": "sˈi", "D": "dˈi", "E": "ˈi", "F": "ˈɛf", "G": "ʤˈi", "H": "ˈAʧ",
             "J": "ʤˈA", "K": "kˈA", "L": "ˈɛl", "M": "ˈɛm", "N": "ˈɛn", "O": "ˈO", "P": "pˈi", "Q": "kjˈu",
             "R": "ˈɑɹ", "S": "ˈɛs", "T": "tˈi", "U": "jˈu", "V": "vˈi", "W": "dˈʌbᵊlju", "X": "ˈɛks",
             "Y": "wˈI", "Z": "zˈi"}
# Words misaki gets wrong for course material; add one here whenever the user flags a word.
CUSTOM = {
    "Kleene": "klˈAni",
}


# ---- Pronunciation ----
def normalize(text: str) -> str:
    # subscripts: q₀ -> "q zero"; D_A -> "D A" (then read as letter names)
    text = re.sub(r"([A-Za-z])([₀-₉]+)", lambda m: f"{m.group(1)} " + " ".join(
        _NUM[int(d)] for d in m.group(2).translate(_SUB)), text)
    text = re.sub(r"\b([a-z])(\d)\b", lambda m: f"{m.group(1)} {_NUM[int(m.group(2))]}", text)
    text = text.replace("_", " ")
    for pat, rep in SYMBOLS:
        text = re.sub(pat, rep, text)
    text = re.sub(r"\s+([,.?!;:])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


_G2P, _LETTERS = {}, {}


def _g2p():
    if BRITISH not in _G2P:
        from misaki import en, espeak
        _G2P[BRITISH] = en.G2P(trf=False, british=BRITISH, fallback=espeak.EspeakFallback(british=BRITISH))
    return _G2P[BRITISH]


def _letters() -> dict:
    """Letter names in the current accent (British: "zed", and no r in "ar")."""
    if BRITISH not in _LETTERS:
        _LETTERS[BRITISH] = dict(LETTER_PH) if not BRITISH else {
            L: _g2p()(f"the letter {L}.")[0].split()[-1].rstrip(".") for L in LETTER_PH} | {"Z": "zˈɛd"}
    return _LETTERS[BRITISH]


def _mark_up(text: str) -> str:
    """Force letter names and custom words via misaki's [word](/phonemes/) syntax."""
    for word, ph in CUSTOM.items():
        text = re.sub(rf"(?<!\[)\b{word}\b", f"[{word}](/{ph}/)", text)
    names = _letters()
    return LETTER.sub(lambda m: f"[{m.group(1)}](/{names[m.group(1)]}/)", text)


def to_phonemes(k, text: str) -> str:
    text = normalize(text)
    ps = _g2p()(_mark_up(text))[0]
    if not BRITISH:
        # Kokoro v1.0 was trained with "T" for the American soft t ("automata", "better"). misaki writes
        # it as "ɾ", which Kokoro reads as a rolled r from its other languages: a foreign-sounding accent.
        ps = ps.replace("ɾ", "T").replace("ʔ", "t")
    ps = "".join(c for c in ps if c in k.tokenizer.vocab)
    ps = re.sub(r"\s+([,.?!])", r"\1", ps).strip()
    # misaki drops the final mark after an inline [X](/../) word; Kokoro needs it for the ending tone
    if text and text[-1] in ".?!" and not ps.endswith(text[-1]):
        ps = ps.rstrip(",;: ") + text[-1]
    return ps


# ---- Pacing ----
PACE_TOLERANCE = 0.05  # a unit within 5% of PACE is accepted
PASSES = [0, 0]        # units rendered, synthesis passes made (for timing reports)
GAMMA = 0.8            # Kokoro's speaking rate grows roughly like speed ** 0.8
_CAL = [None]          # learned ratio between this voice's real rate and _model_rate()
LONG_SENTENCE = 20     # words; a sentence at least this long gets LONG_BONUS extra silence after it
LONG_BONUS = 0.10
MIN_UNIT_WORDS = 5     # a shorter sentence is spoken together with its neighbour
MAX_UNIT_WORDS = 32    # a longer sentence is split at a comma
BREATH_RUN = 16        # words without punctuation before a breath comma is added
BREATH_WORDS = {"and", "but", "because", "which", "when", "whenever", "while", "where",
                "without", "if", "then", "until", "since", "whereas", "unless"}
_SILENT = set(" ,.;:!?—ˈˌ")
_MARKS = ",;:—.!?"


def _breathe(sentence: str) -> str:
    """Add a comma before a conjunction in a long run with no punctuation, so the narrator can breathe."""
    out = []
    for piece in re.split(r"(?<=[,;:—])\s+", sentence):
        words = piece.split()
        while len(words) > BREATH_RUN:
            cands = [i for i in range(6, len(words) - 4) if words[i].lower() in BREATH_WORDS]
            if not cands:
                break
            i = min(cands, key=lambda c: abs(c - len(words) / 2))
            out.append(" ".join(words[:i]) + ",")
            words = words[i:]
        out.append(" ".join(words))
    return " ".join(out)


def units(part: str):
    """Split a beat into the pieces that are synthesized in one go: whole sentences."""
    sents = [_breathe(x) for x in re.split(r"(?<=[.?!])\s+", part.strip()) if x.strip()]
    out = []
    for sent in sents:
        words = sent.split()
        while len(words) > MAX_UNIT_WORDS:  # split an overlong sentence at the comma nearest the middle
            cands = [i for i in range(6, len(words) - 5) if words[i - 1][-1] in ",;:"]
            if not cands:
                break
            i = min(cands, key=lambda c: abs(c - len(words) / 2))
            out.append(" ".join(words[:i]))
            words = words[i:]
        out.append(" ".join(words))
    i = 0
    while i < len(out) and len(out) > 1:  # glue short sentences: alone they come out slow and odd
        if len(out[i].split()) < MIN_UNIT_WORDS:
            j = i + 1 if i + 1 < len(out) else i - 1
            lo, hi = min(i, j), max(i, j)
            if len(out[lo].split()) + len(out[hi].split()) <= MAX_UNIT_WORDS:
                out[lo:hi + 1] = [out[lo] + " " + out[hi]]
                i = lo
                continue
        i += 1
    return out


def end_pause(unit: str) -> float:
    """Silence after a unit, from how it ends and how long its last sentence was."""
    last = re.split(r"(?<=[.?!])\s+", unit.strip())[-1]
    mark = unit.strip()[-1]
    p = QUESTION_PAUSE if mark == "?" else SENTENCE_PAUSE if mark in ".!" else CLAUSE_PAUSE
    return p + (LONG_BONUS if mark in ".?!" and len(last.split()) >= LONG_SENTENCE else 0.0)


def _rate(timings) -> float:
    """Sounds per second. The sound right before a mark is left out: it carries the model's own pause."""
    keep = []
    for i, t in enumerate(timings):
        if t.phoneme in _SILENT:
            continue
        nxt = next((u.phoneme for u in timings[i + 1:] if u.phoneme not in "ˈˌ"), ".")
        if nxt not in _MARKS:
            keep.append(t.end - t.start)
    return len(keep) / max(sum(keep), 0.05)


def _model_rate(n: int, speed: float) -> float:
    """Kokoro's natural rate for n input tokens: it talks faster the longer the input."""
    return (4.6 * np.log(max(n, 8)) - 1.0) * (speed / 0.9) ** GAMMA


def _frames(audio: np.ndarray):
    hop = SR // 100
    n = len(audio) // hop
    return hop, n, np.sqrt((audio[: n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)


def _pauses(audio: np.ndarray, timings) -> np.ndarray:
    """Set the silence after every comma and inner sentence end, using the model's timings.

    Where the model left a gap, silence is added in the middle of that gap up to the target.
    Where it ran straight through a sentence end, the audio is cut at the quietest point near
    the mark (with short fades) so the sentence still gets its pause. The final mark is left
    to the caller, which adds the end-of-unit pause.
    """
    hop, n, rms = _frames(audio)
    quiet = rms <= rms.max() * 0.01
    marks = [t for t in timings if t.phoneme in _MARKS]
    last = max((i for i, t in enumerate(timings) if t.phoneme not in " ˈˌ"), default=-1)
    if last >= 0 and timings[last].phoneme in _MARKS:
        marks = [t for t in marks if t is not timings[last]]
    parts, cut = [], 0
    fade = int(SR * 0.008)
    for t in marks:
        want = SENTENCE_PAUSE if t.phoneme in ".!?" else CLAUSE_PAUSE
        at = int(t.end * 100)
        lo, hi = max(at - 15, 0), min(at + 15, n - 1)
        if hi <= lo:
            continue
        q = lo + int(np.argmin(rms[lo:hi + 1]))            # quietest 10 ms near the mark
        if quiet[q]:                                       # the model paused here: lengthen its gap
            i, j = q, q
            while i > 0 and quiet[i - 1]:
                i -= 1
            while j + 1 < n and quiet[j + 1]:
                j += 1
            missing, where = want - (j - i + 1) * 0.01, (i + j + 1) // 2 * hop
            if missing <= 0 or where <= cut:
                continue
            parts += [audio[cut:where], np.zeros(int(missing * SR), dtype=np.float32)]
        elif t.phoneme in ".!?" or rms[q] <= rms.max() * 0.05:
            # no real gap: a sentence end always gets its pause, a comma only where the voice dips
            where = q * hop + hop // 2
            if where - fade <= cut or where + fade >= len(audio):
                continue
            head = audio[cut:where].copy()
            head[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
            audio = audio.copy()
            audio[where:where + fade] *= np.linspace(0, 1, fade, dtype=np.float32)
            parts += [head, np.zeros(int(want * SR), dtype=np.float32)]
        else:
            continue
        cut = where
    return np.concatenate(parts + [audio[cut:]]) if parts else audio


def _strip(audio: np.ndarray) -> np.ndarray:
    """Cut the silence the model leaves before and after a unit, so pauses are exactly the ones we add."""
    hop, n, rms = _frames(audio)
    loud = np.flatnonzero(rms > rms.max() * 0.01)
    if not len(loud):
        return audio
    return audio[max(loud[0] - 2, 0) * hop: min(loud[-1] + 4, n) * hop]


def render(k, text: str, style, pace: float = None, log: list = None) -> np.ndarray:
    """Synthesize one unit at the target pace, with the comma and inner sentence pauses in place."""
    if not k.has_timings:
        raise RuntimeError("This Kokoro model file reports no timings; use the one from release model-files-v1.1")
    pace = pace or PACE
    ps = to_phonemes(k, text)
    # First guess from the length model, corrected by what earlier units of this voice measured.
    speed = float(np.clip(0.9 * (pace / ((_CAL[0] or 1.0) * _model_rate(len(ps), 0.9))) ** (1 / GAMMA), 0.55, 1.05))
    kw = dict(voice=style, is_phonemes=True, sentence_pause=0, clause_pause=0)  # pauses: see _pauses
    tried = []
    for _ in range(4):
        audio, _, timings = k.create_timed(ps, speed=speed, **kw)
        rate = _rate(timings)
        tried.append((speed, rate, audio, timings))
        seen = rate / _model_rate(len(ps), speed)
        _CAL[0] = seen if _CAL[0] is None else 0.6 * _CAL[0] + 0.4 * seen
        if abs(rate / pace - 1) <= PACE_TOLERANCE:
            break
        lo = max((t for t in tried if t[1] < pace), key=lambda t: t[1], default=None)
        hi = min((t for t in tried if t[1] > pace), key=lambda t: t[1], default=None)
        if lo and hi:   # the pace we want lies between two tries: aim in between
            speed = lo[0] + (hi[0] - lo[0]) * (pace - lo[1]) / (hi[1] - lo[1])
        else:
            speed = speed * (pace / rate) ** (1 / GAMMA)
        speed = float(np.clip(speed, 0.55, 1.05))
        if any(abs(speed - t[0]) < 0.012 for t in tried):
            break
    speed, rate, audio, timings = min(tried, key=lambda t: abs(t[1] / pace - 1))
    audio = _strip(_pauses(audio.astype(np.float32), timings))
    PASSES[0] += 1
    PASSES[1] += len(tried)
    if log is not None:
        log.append({"text": text, "speed": round(speed, 2), "rate": round(rate, 1),
                    "seconds": round(len(audio) / SR, 2), "tries": len(tried)})
    return audio


def speak(k, script: str, style, pace: float = None, tail: bool = True, log: list = None):
    """Render a script with [pause X] markers. Returns (samples, sample_rate).

    tail=True ends the clip with the pause its last mark calls for, so consecutive
    voiceover blocks in a video are spaced like sentences instead of running into each other.
    """
    silence = lambda t: np.zeros(int(SR * t), dtype=np.float32)
    parts = re.split(r"\[pause\s+([\d.]+)\]", script)
    audio = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            audio.append(silence(float(part)))
        elif part.strip():
            us = units(part)
            for j, unit in enumerate(us):
                audio.append(render(k, unit, style, pace, log))
                last = j == len(us) - 1 and not any(p.strip() for p in parts[i + 1:])
                if tail or not last:
                    audio.append(silence(end_pause(unit)))
    return np.concatenate(audio), SR


# ---- Sound ----
WARM_CHAIN = ",".join([
    "highpass=f=60",
    "equalizer=f=150:t=q:w=0.9:g=2.5",     # body / warmth
    "equalizer=f=3300:t=q:w=1.3:g=-2.5",   # soften the hard "digital" presence peak
    "deesser=i=0.35",
    "lowpass=f=10500",                     # hide vocoder fizz
    "acompressor=threshold=-24dB:ratio=2:attack=15:release=200:makeup=1.5",
    "aecho=0.9:0.9:23|41:0.06|0.04",       # a hint of room, not a hall
])


def warm(samples: np.ndarray) -> np.ndarray:
    out = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
         "-af", WARM_CHAIN, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"],
        input=samples.astype(np.float32).tobytes(), capture_output=True, check=True)
    y = np.frombuffer(out.stdout, dtype=np.float32).copy()
    return y[:len(samples)] if len(y) >= len(samples) else np.pad(y, (0, len(samples) - len(y)))


def level(y: np.ndarray, target_db: float = -19.0) -> np.ndarray:
    """Same loudness for every clip: speech RMS to target_db, peaks kept under -1 dBFS."""
    frames = y[: len(y) // 480 * 480].reshape(-1, 480)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    voiced = rms[rms > rms.max() * 0.05]
    if not len(voiced):
        return y
    y = y * (10 ** (target_db / 20) / np.sqrt((voiced ** 2).mean()))
    peak = np.abs(y).max()
    return y * (0.89 / peak) if peak > 0.89 else y


# ---- Entry points ----
def settings() -> str:
    """Everything that changes the audio; part of the cache key, so a changed setting re-renders."""
    return repr((VOICE, STYLE_ROWS, PACE, CLAUSE_PAUSE, SENTENCE_PAUSE, QUESTION_PAUSE, WARM, sorted(CUSTOM.items())))


def narrator(k, voice: str = None):
    """One fixed voice style (510 identical rows), so pitch and tone don't change with sentence length."""
    pack = k.get_voice_style(voice or VOICE)
    row = pack[STYLE_ROWS[0]:STYLE_ROWS[1]].mean(axis=0, keepdims=True)
    return np.repeat(row, len(pack), axis=0).astype(np.float32)


def narrate(k, script: str):
    """Render a script in the chosen voice. Returns (samples, sample_rate)."""
    y, sr = speak(k, script, narrator(k))
    return level(warm(y) if WARM else y), sr
```
