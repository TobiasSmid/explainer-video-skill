# Explainer Video

A Claude plugin that turns course material into narrated, animated explainer videos in the style of 3Blue1Brown.
Claude writes the script, animates it with [Manim](https://www.manim.community/) and narrates it with
[Kokoro](https://github.com/thewh1teagle/kokoro-onnx), a text-to-speech voice that runs locally. You get
finished 720p MP4 files.

It is made for studying. Point it at a lecture, a set of slides or just a topic, and it explains the
definitions, constructions and proofs in the notation of your course. A big topic becomes a series of short
videos, and each one is delivered as soon as it is done, while the next is being made.

## Using it

Ask Claude for a video, for example:

- "Make an explainer video about the union construction for regular languages."
- "Make videos of lecture 4, use the attached slides."
- `/explainer-video:explainer-video the pumping lemma, from my notes`

Claude reads the material, tells you the plan (which videos, and how long each one is) and starts right away.
You can change the plan at any time ("merge 2 and 3", "skip 5", "one long video instead").

The computing part takes about one minute per minute of video, measured on the 2 cores of Claude's cloud
workspace. The time Claude needs to write the script and the animation comes on top of that. The first video
of a session takes a few minutes longer, because the tools are set up first.

Claude cannot hear the narration. If a word sounds wrong, tell Claude which word, and it fixes the
pronunciation.

## What is in the plugin

The plugin holds one skill. It contains no scripts or programs, only text:

- `skills/explainer-video/SKILL.md`: the instructions Claude follows for finding the material, planning the
  series, writing the script, and building, checking and rendering each video.
- `skills/explainer-video/references/`: four Markdown pages with the Python source of the helper modules the
  skill uses. They are the narration voice (pronunciation of math notation, one fixed voice, an even pace,
  pauses by rule), its link to manim-voiceover, a tool that makes the narration ahead of the render, and a
  library for scenes (layout check, contact sheets of the draft, text and automata helpers). Claude copies
  that code into its working folder and runs it there. Everything it runs can be read on those pages.

## What Claude sets up for it

The skill needs tools that are not part of the plugin. Where they are missing, the skill tells Claude to
install them from their own projects, following each project's installation instructions:

- Manim Community, with LaTeX, dvisvgm, ffmpeg and pango
- manim-voiceover, with sox
- kokoro-onnx, misaki, spaCy with its small English model, soundfile and num2words
- the Kokoro v1.0 voice model and voices (about 350 MB), from the releases of the kokoro-onnx project on
  GitHub, checked against SHA-256 checksums that are written in the skill

In Claude's cloud workspace all of this goes into the session's temporary container. On your own computer the
skill tells Claude to keep the Python packages in a virtualenv inside the working folder, and to ask you to
install missing system packages yourself.

## Requirements

The plugin is built for Claude's cloud workspace (Linux, Python 3.13). Its code was tested there, and also as
a normal user without root on Linux, which is how Claude Code runs on your own machine. macOS and Windows are
untested.

Tested with manim 0.22.1, manim-voiceover 0.4.0, kokoro-onnx 0.6.1, misaki 0.7.4 and spaCy 3.8.

## Data and privacy

- The narration is made on the machine where Claude runs the skill. The plugin does not send your material,
  scripts, audio or video to any service. It has no telemetry, and it needs no account or sign-in.
- The network is used only during setup, for the tools and the voice model listed above. The skill also
  turns off Manim's own check for a newer version, so making a video needs no network.
- Claude reads the material you point it to. If you only name a topic, the skill tells Claude to look for your
  material in attached files, the working folder, the Claude Project and file connectors you have connected,
  such as Google Drive.
- If the session is attached to a Claude Project, the skill tells Claude to save the scripts and scene files of
  your videos to that Project, so that a later session can continue the series. The videos themselves are
  given to you in the conversation, or as files in the working folder.
- The voice is a stock Kokoro voice. The skill tells Claude never to clone or imitate a real person's voice.

## Changing the voice

Ask Claude ("make the voice calmer", "let me hear a few other voices"). The settings are at the top of
`speech_text.py` in the working folder: the voice, the pace, the pauses and the warmer sound. Mispronounced
words go into its list of custom pronunciations. The narration is in English.

## Credits and license

MIT, see [LICENSE](LICENSE).

This project is not affiliated with or endorsed by 3Blue1Brown. It builds on
[Manim Community](https://www.manim.community/) (MIT), [manim-voiceover](https://github.com/ManimCommunity/manim-voiceover) (MIT),
[kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (MIT) with the Kokoro-82M model (Apache 2.0),
[misaki](https://github.com/hexgrad/misaki) (Apache 2.0) and [spaCy](https://spacy.io/) (MIT). None of them is
included in the plugin.
