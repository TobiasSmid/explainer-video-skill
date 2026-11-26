# The voice: how it works, and how to fix or change it

Read this when the user flags a word, asks about the voice, or wants it changed. Everything below lives in
`speech_text.py` (settings at the top); cached audio is re-made automatically after any change to that file.

## The setup (do not change it unless asked)
Kokoro, the single voice am_puck (never a blend of voices), at a slightly lively pace (PACE 19.5, about 140
words per minute including pauses), with the warmer sound on (WARM = True). Pauses follow rules: about 0.2 s at
a comma, 0.5 s after a sentence, 0.7 s after a question, and the same pause at the end of every voiceover
block.

Why each piece exists (each one fixes a problem that listeners noticed; do not undo the fixes):
- Pronunciation comes from misaki, Kokoro's own G2P. Raw espeak phonemes (kokoro-onnx's default) stress
  words wrongly ("automata") and sound more artificial.
- misaki writes the soft American t as "ɾ"; Kokoro v1.0 needs "T". With "ɾ" it rolls an r, and "automata"
  comes out as "automatar" with a foreign accent.
- Kokoro picks a different voice style for every input length, so pitch and tone jump from one sentence
  to the next ("nasal, then normal again"). narrator() uses one fixed style for everything.
- Kokoro talks faster the longer its input, so long sentences sound rushed and short ones slow. render()
  measures every unit with the model's timings and re-renders it until it hits PACE.
- Pauses are spliced into the gaps the model already left, so sentences stay whole. Do not go back to
  synthesizing sentences in pieces cut at commas.
- Blended voices and the low-rated voices (am_liam, am_eric: grade D) sound unstable.
- A lone "a" is read as the article "uh" and misaki drops a lone lowercase "x" entirely; normalize() forces
  the letter names where the article is impossible ("an a", "every a it reads", "a b c", formulas).
- Symbols like ∪ are silently dropped unless normalize() turns them into words (SYMBOLS).
- The model reports when every sound is spoken; speak() turns that into word start times, which
  kokoro_service.py hands to manim-voiceover for bookmarks and word-timed subtitles.

Speed: narration takes about half a minute per minute of audio (Kokoro on all cores; render() learns the
voice's natural rate as it goes, so most sentences need one synthesis pass).

## Checking audio you cannot hear
- prenarrate.py listens back to every new beat (listen.py: a local Moonshine recognizer) and prints
  `LISTEN key: said 'X', heard 'Y'` for stretches that sound different from the script. Spelling-only
  differences (their/there, Q0/q zero) are already filtered out. A flag is a hint, not proof: the recognizer
  also stumbles on rare words. Words in CUSTOM are never flagged.
- For a flagged stretch: print its phonemes,
  `python3 -c "import speech_text as s; from kokoro_service import _engine; print(s.to_phonemes(_engine(), 'the phrase'))"`.
  Empty or odd phonemes mean a normalizer or dictionary problem: add a SYMBOLS rule (a symbol), a CUSTOM
  entry (a mangled word), or reword the beat. Fine phonemes usually mean the recognizer misheard: move on.
- Pass `log=[]` to speak() for the pace of every unit; measure silences in the output with numpy.
- Ask the user to name the second where something sounds off.

## Fixing a word the user flags
Add it to CUSTOM in speech_text.py (misaki phonemes, e.g. `"Kleene": "klˈAni"`), re-run prenarrate (only the
affected beats are re-made), and publish the change (references/publishing.md) so it stays fixed.
Inline alternatives in a beat: `[Kleene](/klˈAni/)`; backticks spell a token letter by letter: `0110`.

## A different voice (only when the user asks)
Render a short comparison MP3 of SINGLE voices through this same pipeline (`narrator(k, "am_michael")`; each
voice says its own name, then the same passage) and let them pick; then set VOICE. Kokoro's best-rated male
voices are am_michael, am_fenrir and am_puck (C+), then bm_george and bm_fable (C); the best overall is
af_heart (A). Community voice packs (.pt, 510x1x256 float32) can be loaded without torch: the tensor is the
raw file `*/data/0` inside the .pt zip. The pronunciation pipeline is English only: narrate in English, also
when the material is in another language.
