# explainer-video-skill

Narrated, animated explainer videos of course topics, made by Claude with [Manim](https://www.manim.community/)
and a local [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) voice.

| Path | What it is |
|---|---|
| `plugin/` | The Claude plugin "Explainer Video": one skill, text only. This is the folder that is submitted to Anthropic's plugin directory. What it does and what it sets up is in [plugin/README.md](plugin/README.md). |
| `kit/` | The same code as real files: the four Python modules, `setup.sh` (installs the tools and gets the voice model in one go) and `build_plugin.py` (writes the plugin's reference pages from the modules). |
| `setup.sh` | Sets up a clone of this repository as a working folder, by running `kit/setup.sh` in it. |
| `.claude-plugin/marketplace.json` | Lets Claude Code install the plugin straight from this repository. |

## Install the plugin from this repository

In Claude Code (2.1.275 or later):

```
/plugin install explainer-video --marketplace TobiasSmid/explainer-video-skill
```

## Use the kit without the plugin

```bash
git clone --depth 1 https://github.com/TobiasSmid/explainer-video-skill explainer && cd explainer
bash setup.sh
python3 prenarrate.py beats_01_union          # narration for a beats file
manim -ql --frame_rate 5 --progress_bar none 01_union.py UnionConstruction      # draft
manim -r 1280,720 --frame_rate 24 --encoder-option preset=veryfast --max-inflight-encoders 4 --progress_bar none 01_union.py UnionConstruction
```

`setup.sh` copies the modules to the top of the clone, which is then the working folder: scenes, beats files,
models and rendered media sit there and are ignored by git. As root in a container it installs system-wide.
Otherwise it uses a virtualenv, never uses sudo, and reports missing system packages instead of installing
them. The voice model is checked against SHA-256 checksums.

## Changing the code

Edit the module in `kit/`, then run `python3 kit/build_plugin.py` so the plugin's reference pages match, and
raise `version` in `plugin/.claude-plugin/plugin.json`. Commit the module and the page together.

The plugin directory does not take script files from this repository, which is why the plugin carries the code
as Markdown pages and describes the setup in words, while `kit/` keeps the scripts.

## License

MIT, see [LICENSE](LICENSE). Not affiliated with or endorsed by 3Blue1Brown.
