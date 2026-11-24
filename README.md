# explainer-video-skill

Code behind the `explainer-video` skill: 3b1b-style explainer videos made with manim and a local Kokoro voiceover.
The skill's instructions live in Claude; this repo holds the code, so Claude clones it instead of retyping it every session.

| File | What it does |
|---|---|
| `setup.sh` | Installs manim, the voice packages and LaTeX, and downloads the Kokoro model. Safe to run again. |
| `speech_text.py` | The narration voice: pronunciation, one fixed voice, even pace, pauses by rule, warmer sound. All settings are at the top. |
| `kokoro_service.py` | Connects that voice to manim-voiceover and caches the audio. |
| `prenarrate.py` | Generates the narration of a beats file ahead of the render and prints each beat's length. |
| `explainer_lib.py` | Scene base class (`Explainer`), layout check, draft contact sheets, text and automata helpers. |
| `SKILL.md` | A copy of the skill's instructions, kept for history. The live version is the one saved in Claude. |

## Use

```bash
git clone --depth 1 https://github.com/TobiasSmid/explainer-video-skill explainer && cd explainer
bash setup.sh
python3 prenarrate.py beats_01_union          # narration for a beats file
manim -ql --frame_rate 5 --progress_bar none 01_union.py UnionConstruction      # draft
manim -r 1280,720 --frame_rate 24 --encoder-option preset=veryfast --max-inflight-encoders 4 --progress_bar none 01_union.py UnionConstruction
```

The cloned folder is also the working folder: scenes, beats files, models and rendered media sit next to the code and are ignored by git.

## Changing the voice

Edit the settings at the top of `speech_text.py` (`VOICE`, `PACE`, the pauses, `WARM`). Add a mispronounced word to `CUSTOM`. Cached audio is re-made automatically when a setting changes.
