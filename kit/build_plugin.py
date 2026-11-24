"""Write the plugin's reference pages from the code in this folder.

The plugin directory takes no script files from this repository, so the plugin carries the four
modules as Markdown pages with one python code block each, and the skill copies the blocks out.
Run this after changing a module:  python3 kit/build_plugin.py
It also checks that copying the block out of each page gives back the module, byte for byte.
"""
from pathlib import Path

KIT = Path(__file__).resolve().parent
REFS = KIT.parent / "plugin" / "skills" / "explainer-video" / "references"
FENCE = "```"

PAGES = {
    "speech_text": "The narration voice: how math notation is pronounced, one fixed Kokoro voice, an even pace, "
                   "pauses by rule and a warmer sound. All settings are at the top.",
    "kokoro_service": "Connects the voice in `speech_text.py` to manim-voiceover and caches the audio. It expects "
                      "the Kokoro model files in a `models` folder next to it.",
    "prenarrate": "Makes the narration of a beats file ahead of the render and prints the length of every beat.",
    "explainer_lib": "What scenes build on: the `Explainer` base class, the automatic layout check, the contact "
                     "sheets of the draft, and text and automata helpers.",
}


def page(name: str, about: str, code: str) -> str:
    return (f"# {name}.py\n\n{about}\n\n"
            f"This page is the source of the module. The skill copies the code block below, unchanged, into "
            f"`{name}.py` in the working folder (section 3 of SKILL.md).\n\n"
            f"{FENCE}python\n{code}{FENCE}\n")


def copy_out(text: str) -> str:
    """What the skill's awk command gives: the lines between the python fence and the closing fence."""
    out, inside = [], False
    for line in text.split("\n"):
        if line == FENCE + "python":
            inside = True
        elif line == FENCE:
            inside = False
        elif inside:
            out.append(line + "\n")
    return "".join(out)


REFS.mkdir(parents=True, exist_ok=True)
for name, about in PAGES.items():
    code = (KIT / f"{name}.py").read_text(encoding="utf-8")
    assert code.endswith("\n") and not any(line.startswith(FENCE) for line in code.split("\n")), name
    text = page(name, about, code)
    assert copy_out(text) == code, f"{name}: the code block does not copy out unchanged"
    (REFS / f"{name}.md").write_text(text, encoding="utf-8")
    print(f"{name}.md  {len(text.encode()):6d} bytes")
