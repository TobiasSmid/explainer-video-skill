# explainer-video-skill

Code behind the `explainer-video` skill: narrated, animated explainer videos of course topics in the style of
3Blue1Brown, made by Claude with [Manim](https://www.manim.community/) and a local
[Kokoro](https://github.com/thewh1teagle/kokoro-onnx) voice. The skill's instructions live in Claude; this repo
holds the code, so Claude clones it instead of retyping it every session.

| File | What it does |
|---|---|
| `setup.sh` | Installs manim, the voice packages and LaTeX, and downloads the Kokoro model (checked against SHA-256 checksums). Safe to run again. |
| `speech_text.py` | The narration voice: pronunciation of math notation, one fixed voice, an even pace, pauses by rule, a warmer sound. All settings are at the top. |
| `kokoro_service.py` | Connects that voice to manim-voiceover and caches the audio. |
| `prenarrate.py` | Generates the narration of a beats file ahead of the render and prints each beat's length. |
| `explainer_lib.py` | Scene base class (`Explainer`), layout check, draft contact sheets, text and automata helpers. |

## Use

```bash
git clone --depth 1 https://github.com/TobiasSmid/explainer-video-skill explainer && cd explainer
bash setup.sh
python3 prenarrate.py beats_01_union          # narration for a beats file
manim -ql --frame_rate 5 --progress_bar none 01_union.py UnionConstruction      # draft
manim -r 1280,720 --frame_rate 24 --encoder-option preset=veryfast --max-inflight-encoders 4 --progress_bar none 01_union.py UnionConstruction
```

The cloned folder is also the working folder: scenes, beats files, models and rendered media sit next to the
code and are ignored by git.

`setup.sh` is made for Claude's cloud workspace, where it runs as root and installs everything by itself. As a
normal user it puts the Python packages in a virtualenv (`.venv`), never uses sudo, and reports missing system
packages instead of installing them.

## Changing the voice

Edit the settings at the top of `speech_text.py` (`VOICE`, `PACE`, the pauses, `WARM`). Add a mispronounced
word to `CUSTOM`. Cached audio is made again automatically when a setting changes.

## License

MIT, see [LICENSE](LICENSE). Not affiliated with or endorsed by 3Blue1Brown.

An earlier version of this repo packaged the code as a Claude plugin. It is in the history (commit `606fe9a`).
