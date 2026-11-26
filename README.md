# Explainer Video

A Claude plugin that turns course material into narrated, animated explainer videos in the style of 3Blue1Brown.
Claude writes the script, animates it with [Manim](https://www.manim.community/) and narrates it with
[Kokoro](https://github.com/thewh1teagle/kokoro-onnx), a text-to-speech voice that runs locally. You get
finished 720p MP4 files.

It is made for studying. Point it at a lecture, a set of slides or just a topic, and it explains the
definitions, constructions and proofs in the notation of your course. A big topic becomes a series of short
videos, and each one is delivered as soon as it is done, while the next is being made.

## Install

In the Claude app or on claude.ai:

1. Open **Customize > Plugins**.
2. Choose **Add > Add marketplace** and enter `TobiasSmid/explainer-video-skill`.
3. Add the **Explainer Video** plugin that now appears.
4. Turn on **Sync automatically** for this marketplace. You then get every update by yourself. Without it,
   use **Check for updates** now and then.

In Claude Code (2.1.275 or later):

```
/plugin install explainer-video --marketplace TobiasSmid/explainer-video-skill
```

The plugin has no version number: every change that is pushed to this repository is a new version.

## Using it

Ask Claude for a video, for example:

- "Make an explainer video about the union construction for regular languages."
- "Make videos of lecture 4, use the attached slides."
- `/explainer-video:explainer-video the pumping lemma, from my notes`

Claude reads the material, tells you the plan (which videos, and how long each one is) and starts right away.
You can change the plan at any time ("merge 2 and 3", "skip 5", "one long video instead").

The computing part takes about one minute per minute of video, measured on the 2 cores of Claude's cloud
workspace. The time Claude needs to write the script and the animation comes on top of that. The first video
of a session takes a few minutes longer, because the tools are installed first.

Claude cannot hear the narration. If a word sounds wrong, tell Claude which word, and it fixes the
pronunciation.

## What is in the plugin

| Path | What it is |
|---|---|
| `skills/explainer-video/SKILL.md` | The instructions Claude follows: finding the material, planning the series, writing the script, building, checking and rendering the video. |
| `skills/explainer-video/scripts/setup.sh` | Sets up a working folder: copies the code below into it, installs the tools and downloads the voice model. Safe to run again. |
| `skills/explainer-video/scripts/speech_text.py` | The narration voice: pronunciation of math notation, one fixed voice, an even pace, pauses by rule, a warmer sound. All settings are at the top. |
| `skills/explainer-video/scripts/kokoro_service.py` | Connects that voice to manim-voiceover and caches the audio. |
| `skills/explainer-video/scripts/prenarrate.py` | Generates the narration of a script ahead of the render and prints the length of each part. |
| `skills/explainer-video/scripts/explainer_lib.py` | Scene base class, an automatic layout check, contact sheets of the draft, and text and automata helpers. |
| `setup.sh` | Sets up a clone of this repository in place, for use without the plugin system. |

## Requirements

The plugin needs a Claude session that can run code and install packages. It is built for and tested in
Claude's cloud workspace (Linux, Python 3.13), where setup installs everything by itself. It was also tested
as a normal user, without root, on Linux, which is how Claude Code runs on your own machine. There, setup puts
the Python packages into a virtualenv in the working folder. If LaTeX or ffmpeg is missing, it tells you what
to install yourself, because it never uses sudo. macOS and Windows are untested.

Tested with manim 0.22.1, manim-voiceover 0.4.0, kokoro-onnx 0.6.1, misaki 0.7.4 and spaCy 3.8.

## What setup installs and downloads

`setup.sh` runs once per working folder. It fetches the following, and nothing else:

- With apt, only when it runs as root on Debian or Ubuntu (as in Claude's cloud workspace):
  `libpango1.0-dev pkg-config dvisvgm texlive-latex-extra texlive-fonts-recommended sox espeak-ng ffmpeg`.
- With pip, from PyPI: `manim`, `manim-voiceover`, `kokoro-onnx`, `soundfile`, `num2words`, `spacy`, `misaki`.
- The spaCy English model `en_core_web_sm` 3.8.0, from the
  [spacy-models release](https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0) on GitHub.
- The Kokoro v1.0 voice model and voices (about 350 MB), from the
  [kokoro-onnx release](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1) on GitHub.
  Both files are checked against SHA-256 checksums that are written in the script.

Where the Python packages go: system-wide when setup runs as root (that is meant for a disposable container),
otherwise into the virtualenv that is active, or into a new `.venv` in the working folder.

## Data and privacy

- The narration is made on the machine where Claude runs the skill. The plugin does not send your material,
  scripts, audio or video to any service. It has no telemetry, no account and no API key.
- Only setup uses the network, for the downloads listed above. Setup also turns off Manim's own check for a
  newer version on PyPI, so making a video needs no network.
- Claude reads the material you point it to. If you only name a topic, the skill tells Claude to look for your
  material in attached files, the working folder, the Claude Project and file connectors you have connected,
  such as Google Drive.
- If the session is attached to a Claude Project, the skill tells Claude to save the scripts and scene files of
  your videos to that Project, so that a later session can continue the series. The videos themselves are
  given to you in the conversation, or as files in the working folder.
- The default voice is a stock Kokoro voice.

## Changing the voice

Ask Claude ("make the voice calmer", "let me hear a few other voices"). The settings are at the top of
`speech_text.py`: `VOICE`, `PACE`, the pauses and `WARM`, and mispronounced words go into `CUSTOM`. A change
holds for the session you make it in. Only the owner of this repository can make a change permanent, by
pushing it here; everyone who installed the plugin then gets it at their next sync.

## Credits and license

MIT, see [LICENSE](LICENSE).

This project is not affiliated with or endorsed by 3Blue1Brown. It builds on
[Manim Community](https://www.manim.community/) (MIT), [manim-voiceover](https://github.com/ManimCommunity/manim-voiceover) (MIT),
[kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (MIT) with the Kokoro-82M model (Apache 2.0),
[misaki](https://github.com/hexgrad/misaki) (Apache 2.0) and [spaCy](https://spacy.io/) (MIT). None of them is
included in this repository; setup downloads them.
