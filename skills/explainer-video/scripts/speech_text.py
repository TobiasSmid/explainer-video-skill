"""Narration: plain Kokoro, fed the right text.

Kokoro makes all the audio itself, in ONE reading per narration block, with its own pause and speed
settings. Nothing is cut, re-rendered or post-processed: every attempt to do that (fixed or averaged
voice styles, per-sentence pace matching, pauses cut into the audio, sentence-by-sentence synthesis,
EQ) caused audible artifacts ("trick-eeh" tails, creaking, pitch jumps, nasal moments). The skill only
decides what TEXT goes in:
  - the math reading rules (normalize): A ∪ B -> "A union B", aⁿbⁿ -> "a to the n b to the n", ...
  - pronunciation from misaki, Kokoro's own dictionary, with letter names forced where needed
  - a dash after every sentence. Inside one reading Kokoro leaves almost no silence at a full stop
    (it was trained on single sentences); after ". —" it leaves a small gap, which Kokoro's own pause
    setting (sentence_pause) stretches into a real pause. Without the dash some sentence ends got none.

Script conventions:
  - Write math as you would on a slide: A ∪ B, ε-transition, q₀, δ(q, a), Σ*, aⁿbⁿ, |w|.
  - A standalone capital letter (A, B, D, L, N...) is read as a letter name ("ay", "bee").
  - Avoid starting a sentence with the article "A"; `abba` in backticks is spelled letter by letter.
  - "[pause 0.8]" marks an extra pause; it becomes one more Kokoro sentence pause (the number is ignored).
  - Force a pronunciation with misaki's inline syntax: [Kleene](/klˈAni/), or add the word to CUSTOM.
Needs the Kokoro export that reports timings (release "model-files-v1.1") and kokoro-onnx >= 0.6.
"""
import hashlib
import re
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")

# ---- The narration voice (all of it is Kokoro's own settings) ----
VOICE = "narrator"       # the skill's one voice (models/narrator.npz): Kokoro's am_puck with every one of its
                         # 510 tones shifted a little deeper (about 107 -> 95 Hz). Kokoro still picks the tone
                         # by input length, as with any stock voice. Tested: 0 creaky endings in 40 readings,
                         # against 6 for plain am_puck. Chosen by ear (2026-11-27).
BRITISH = False          # the narrator is an American voice
SPEED = 0.85             # Kokoro's speed setting, chosen by ear: ~17 sounds/s in block-sized readings,
                         # about 130 words per minute with the pauses. Kokoro speaks faster the longer its
                         # input, so this value is for blocks of 2-5 sentences, not for one long text.
SENTENCE_PAUSE = 0.5     # Kokoro's own pause after . ? ! (it only lengthens a gap Kokoro left itself)
CLAUSE_PAUSE = 0.15      # Kokoro's own pause after , ; : where it left a gap
END_PAUSE = 0.5          # silence after every narration block, so blocks are spaced like sentences

SR = 24000
_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_NUM = "zero one two three four five six seven eight nine".split()

SYMBOLS = [
    (r"<=>|⟺|⇔|↔", " if and only if "), (r"=>|⟹|⇒", " implies "), (r"⟸|⇐", " is implied by "),
    (r":=|≔", " is defined as "), (r"->|⟶", " goes to "), (r"<=", " is at most "), (r">=", " is at least "),
    (r"⊇", " is a superset of "), (r"⊃", " is a proper superset of "), (r"⊈|⊄", " is not a subset of "),
    (r"∖", " minus "), (r"↦", " maps to "), (r"←", " gets "), (r"⊢\*", " yields, in any number of steps, "),
    (r"⊢", " yields "), (r"⊨", " models "), (r"≡", " is equivalent to "), (r"≈", " is approximately "),
    (r"∞", " infinity "), (r"ℕ", " the natural numbers "), (r"ℤ", " the integers "), (r"ℚ", " the rationals "),
    (r"ℝ", " the reals "), (r"∑", " the sum of "), (r"∏", " the product of "), (r"√", " the square root of "),
    (r"∫", " the integral of "), (r"[⟨⟩⌈⌉⌊⌋]", " "), (r"\+", " plus "),
    (r"Γ", " capital gamma "), (r"Λ", " capital lambda "), (r"Π", " capital pi "), (r"Ω", " capital omega "),
    (r"Δ", " capital delta "), (r"Φ", " capital phi "), (r"α", " alpha "), (r"β", " beta "), (r"γ", " gamma "),
    (r"λ", " lambda "), (r"π", " pi "), (r"θ", " theta "), (r"σ", " sigma "), (r"μ", " mu "), (r"[φϕ]", " phi "),
    (r"ω", " omega "), (r"τ", " tau "), (r"ρ", " rho "), (r"ψ", " psi "), (r"η", " eta "), (r"κ", " kappa "),
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
    "pushdown": "pˈʊʃdˌWn",
}


# ---- Pronunciation ----
_SUP_CHARS = "⁰¹²³⁴⁵⁶⁷⁸⁹ⁿⁱʲᵏᵐˣʸᴿ⁺⁻*"
_SUP = str.maketrans(_SUP_CHARS[:-1], "0123456789nijkmxyR+-")
_SUBL = str.maketrans("ₐₑₒₓₕₖₗₘₙₚₛₜᵢⱼ", "aeoxhklmnpstij")
_EXP_WORDS = {"*": "star", "+": "plus", "R": "reversed", "2": "squared"}


_A = ""  # stands for the letter "a" until normalize() ends (SYMBOLS would break the [a](/ˈA/) markup)
_X = ""  # the same for "x", which misaki drops when it stands alone


def _letter(c: str) -> str:
    # a lone lowercase "a" is read as the article ("uh"); in a formula it is the letter
    return _A if c == "a" else _X if c == "x" else c


def _spell(m) -> str:
    """`abba` or `0110`: read character by character."""
    return " ".join(_NUM[int(c)] if c.isdigit() else _letter(c) for c in m.group(1) if not c.isspace())


def _math_token(tok: str) -> str:
    """Speak a formula token like aⁿbⁿ, 0^n1^n, xy^iz, (ab)*, w^R, a^{n+1}, Σ*.
    Letters are spoken one by one ("x y z", not the word "xyz"), exponents as "to the n"."""
    tok = re.sub(f"[{_SUP_CHARS[:-1]}]+", lambda m: "^{" + m.group().translate(_SUP) + "}", tok)
    out, i = [], 0
    while i < len(tok):
        c = tok[i]
        if c == "^" and i + 1 < len(tok):
            if tok[i + 1] == "{" and "}" in tok[i:]:
                j = tok.index("}", i)
                exp, i = tok[i + 2:j], j + 1
            else:
                exp, i = tok[i + 1], i + 2
            out.append(_EXP_WORDS.get(exp, "to the " + " ".join(_letter(x) if x.isalpha() else x for x in exp)))
            continue
        if c == "*":
            out.append("star")
        elif c.isalpha() and c.isascii():
            out.append(_letter(c))
        elif c.isdigit():
            j = i
            while j < len(tok) and tok[j].isdigit():
                j += 1
            out.append(tok[i:j])
            i = j
            continue
        elif c not in "()":
            out.append(c)
        i += 1
    return " ".join(out)


def _bars(m) -> str:
    inner = m.group(1).strip()
    if re.fullmatch(r"[a-z]\w?", inner):
        return f" the length of {inner} "
    if re.fullmatch(r"[A-Z]\w?", inner):
        return f" the size of {inner} "
    return f" the absolute value of {inner} "


def normalize(text: str) -> str:
    # `0110` or `abba`: spell it out; a string of digits that starts with 0 is spelled too ("01")
    text = re.sub(r"`([^`]+)`", _spell, text)
    text = re.sub(r"(?<![\w.])(0\d+)(?![\w.])", _spell, text)
    # variable strings like xyz, uvw, uvxyz are spelled ("x y z", not "size")
    text = re.sub(r"(?<![\w\[`/'])([u-z]{2,5})(?![\w\]`'])", lambda m: " ".join(m.group(1)), text)
    # "a" where the article is impossible is the letter: "an a", "every a it reads", "a and b", "reads a."
    text = re.sub(r"\ban a\b", "an " + _A, text)
    text = re.sub(r"(?<![\w\[`'])a(?=\s*(?:[,.;:?!)]|$)|\s+(?:it|is|and|or|in|on|to|then|by|from|are|was|"
                  r"but|we|you|has|gets|goes|followed|itself)\b"
                  r"|\s+[b-z](?=\s*(?:[,.;:?!)]|$)|\s+[a-z](?![\w'])))", _A, text)
    # misaki drops a lone lowercase x entirely ("the word x" -> "the word"): force the letter name
    text = re.sub(r"(?<![\w\[`/'])x(?![\w\]`'])", _X, text)
    # δ(q, a): a short item in a tuple is a symbol, so "a" there is the letter
    text = re.sub(r"\(([^()]{1,40})\)", lambda m: "(" + ", ".join(
        _letter(x.strip()) if len(x.strip()) == 1 else x.strip() for x in m.group(1).split(",")) + ")"
        if "," in m.group(1) else m.group(0), text)
    # |w| -> "the length of w", |Q| -> "the size of Q"; a lone | (set builder) -> "such that"
    text = re.sub(r"\|([^|\s][^|]{0,5}?)\|", _bars, text)
    text = re.sub(r"\s\|\s", " such that ", text)
    # formulas with exponents or a Kleene star: aⁿbⁿ, a^n, (ab)*, w^R
    text = " ".join(_math_token(t) if re.search(rf"[\^{_SUP_CHARS}]", t) and not t.startswith("[") else t
                    for t in text.split(" "))
    # primes: q′ or q' -> "q prime"
    text = re.sub(r"(?<![\w'])([A-Za-z])(″|'')(?!\w)", r"\1 double prime", text)
    text = re.sub(r"(?<![\w'])([A-Za-z])(′|'(?!\w))", r"\1 prime", text)
    # subscripts: q₀ -> "q zero"; qᵢ -> "q i"; D_A -> "D A" (then read as letter names)
    text = re.sub(r"([A-Za-z])([₀-₉]+)", lambda m: f"{m.group(1)} " + " ".join(
        _NUM[int(d)] for d in m.group(2).translate(_SUB)), text)
    text = re.sub(r"([A-Za-z])([ₐₑₒₓₕₖₗₘₙₚₛₜᵢⱼ]+)", lambda m: f"{m.group(1)} " + " ".join(
        m.group(2).translate(_SUBL)), text)
    text = re.sub(r"\b([a-z])(\d)\b", lambda m: f"{m.group(1)} {_NUM[int(m.group(2))]}", text)
    text = text.replace("_", " ")
    for pat, rep in SYMBOLS:
        text = re.sub(pat, rep, text)
    text = re.sub(r"\s+([,.?!;:])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip().replace(_A, "[a](/ˈA/)").replace(_X, "[x](/ˈɛks/)")


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
    try:
        ps = _g2p()(_mark_up(text))[0]
    except Exception:  # misaki can crash on stray symbols: drop them and try again
        text = re.sub(r"[^\w\s,.?!;:'\-\[\]()/ˈ]", " ", text)
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


# ---- Speech ----
PASSES = [0, 0]          # readings made, sentences in them (for timing reports)
_MARKS = ",;:—.!?…"
PAUSE = re.compile(r"\[pause\s+([\d.]+)\]")


def to_kokoro(k, script: str) -> str:
    """The phonemes Kokoro reads for one block: every sentence through the text rules, joined with
    a dash after each sentence end, so Kokoro leaves a gap its pause setting can lengthen."""
    script = PAUSE.sub(" — ", script)
    pieces = [x.strip(" —") for x in re.split(r"(?<=[.?!])\s+|\s+—\s+", script.strip()) if x.strip(" —")]
    PASSES[1] += len(pieces)
    return " — ".join(to_phonemes(k, x) for x in pieces)


def _word_starts(timings) -> list:
    """Start time (s) of every spoken word in Kokoro's timings: a word starts after a space."""
    starts, new = [], True
    for t in timings:
        if t.phoneme == " ":
            new = True
        elif new and t.phoneme not in _MARKS:
            starts.append(t.start)
            new = False
    return starts


def narrate(k, script: str, bounds: list = None):
    """One narration block in one Kokoro reading. Returns (samples, sample_rate).
    `bounds`, if given, receives (character offset in `script`, seconds) for the start of every
    word, plus the end of the script: what manim-voiceover needs for bookmarks and subtitles."""
    samples, sr, timings = k.create_timed(to_kokoro(k, script), voice=VOICE, speed=SPEED, is_phonemes=True,
                                          sentence_pause=SENTENCE_PAUSE, clause_pause=CLAUSE_PAUSE)
    PASSES[0] += 1
    samples = np.concatenate([samples.astype(np.float32), np.zeros(int(sr * END_PAUSE), np.float32)])
    if bounds is not None:
        # written words -> spoken words: "q₀" is two spoken words, a [pause] marker none
        spans = [(m.start(), m.group()) for m in re.finditer(r"\S+", PAUSE.sub(lambda m: " " * len(m.group()), script))]
        counts = [len(normalize(w).split()) for _, w in spans]
        spoken, total, done = _word_starts(timings), sum(counts) or 1, 0
        for (at, _), c in zip(spans, counts):
            i = min(int(round(done * len(spoken) / total)), len(spoken) - 1) if spoken else -1
            bounds.append((at, spoken[i] if i >= 0 else 0.0))
            done += c
        bounds.append((len(script), len(samples) / sr))
    return samples, sr


def settings() -> str:
    """Everything that changes the audio; part of the cache key, so a change re-makes the audio.
    The fingerprint of this file covers every rule; the rest covers the settings above."""
    code = hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:12]
    voice = Path(__file__).resolve().parent / "models" / "narrator.npz"
    voice = hashlib.sha1(voice.read_bytes()).hexdigest()[:12] if voice.exists() else ""
    return repr((VOICE, SPEED, SENTENCE_PAUSE, CLAUSE_PAUSE, END_PAUSE, sorted(CUSTOM.items()), code, voice))
