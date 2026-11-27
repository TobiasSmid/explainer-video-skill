# The voice: how it works, and how to fix or change it

Read this when the user flags a word, asks about the voice, or wants it changed. Everything lives in
`speech_text.py` (settings at the top); cached audio is re-made automatically after any change to that file.

## The setup: plain Kokoro, fed the right text (do not add audio processing)
Each narration block is ONE Kokoro reading: the skill's one voice (models/narrator.npz, see below), Kokoro's
speed setting (SPEED 0.85,
about 130 words per minute with pauses) and Kokoro's own pause setting (0.5 s at a sentence end, 0.15 s at
a comma, only where Kokoro left a gap itself), plus 0.5 s of silence after the block. Nothing is cut,
re-rendered or post-processed. The skill only decides the TEXT that goes in:
- normalize(): math as words (A ∪ B -> "A union B", aⁿbⁿ -> "a to the n b to the n", |w|, q₀, δ(q, a), ...),
  letter names where an article is impossible ("an a", "a b c"), a lone "x" kept (misaki drops it).
- misaki, Kokoro's own pronunciation dictionary, with the soft American t written "T" ("ɾ" makes Kokoro
  roll an r: "automatar").
- a dash after every sentence (". —"): inside one reading Kokoro leaves almost no silence at a full stop,
  but after a dash it leaves a small gap that its pause setting stretches into a real pause.

What was tried before and must not come back (each one was audible, the user rejected all of them):
- fixed or averaged voice styles, steering the style vector: creaking "trick-eeh" tails at sentence ends;
- synthesizing sentence by sentence: Kokoro picks its tone by input length, so pitch jumps and nasal moments;
- per-sentence pace matching (re-rendering at different speeds), pauses cut into the audio ("tri... ck"),
  a sentence plus the next word cut off, EQ/compression/echo: warping and an unnatural sound.
Kokoro was trained on single utterances: it does not pause mid-reading, it ends an utterance with a
drawn-out tail, and it rushes a very short input (one short sentence reads about 40% faster). Work with that (one reading per block, Kokoro's own pause and speed settings), not against it.

## Checking audio you cannot hear
- prenarrate.py listens back to every new beat (listen.py: a local Moonshine recognizer) and prints
  `LISTEN key: said 'X', heard 'Y'` for stretches that sound different from the script. Spelling-only
  differences (their/there, Q0/q zero) are filtered out. A flag is a hint: the recognizer also stumbles on
  rare words. Words in CUSTOM are never flagged. It checks WORDS only, not how smooth the voice sounds.
- For a flagged stretch, print what Kokoro is given:
  `python3 -c "import speech_text as s; from kokoro_service import _engine; print(s.to_kokoro(_engine(), 'the phrase'))"`.
  Missing or odd phonemes mean a text problem: add a SYMBOLS rule (a symbol), a CUSTOM entry (a mangled
  word), or reword the beat. Fine phonemes usually mean the recognizer misheard: move on.
- Ask the user to name the second where something sounds off.

## Fixing a word the user flags
Add it to CUSTOM in speech_text.py (misaki phonemes, e.g. `"Kleene": "klˈAni"`), re-run prenarrate (only the
affected beats are re-made), and publish the change (references/publishing.md) so it stays fixed.
Inline alternatives in a beat: `[Kleene](/klˈAni/)`; backticks spell a token letter by letter: `0110`.

## The voice file
`narrator.npz` (ships in scripts/, copied to models/ by setup) holds one Kokoro voice pack (510 tones, one per
input length): am_puck + (-18) x a pitch direction, the same shift added to every tone, so Kokoro still picks
the tone by length. The direction came from a regression of 24 male Kokoro voices' tone vectors on their
measured pitch, brightness, melody and tempo. Tested on 8 blocks x 5 runs: 0 creaky endings (plain am_puck: 6),
same pitch steadiness, same listen-back result. Kokoro adds a little randomness to every reading, so judge any
voice change over several runs, never one. Shifting toward "darker" (brightness) or "calmer" (melody) brought
the creaky endings back in every run: only the pitch shift is safe. A new voice file means: make it the same
way, test it the same way, let the user judge it by ear, then publish it (references/publishing.md).

## Speed, pauses, voice
Only through Kokoro's own settings at the top of speech_text.py: SPEED (lower = slower; 0.85 was chosen by
ear; Kokoro speaks faster the longer its input, so judge a speed on block-sized samples, never on one long
text: the same 0.72 that sounded right on a long sample was 25% too slow in real blocks), SENTENCE_PAUSE, CLAUSE_PAUSE, END_PAUSE. Change one
at a time, make a short sample, and let the user judge it by ear before using it in a video.
The pronunciation pipeline is English only: narrate in English, also when the material is in another language.
