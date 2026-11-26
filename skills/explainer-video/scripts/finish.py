"""Turn rendered scenes into the finished video: joined in order, with subtitles and chapters.

Usage (from the explainer folder):
    python3 finish.py 01_union_construction.mp4 media/videos/01_union/720p24/Intro.mp4 [more scene mp4s ...]

- The scenes are joined in the order given (no re-encoding).
- Their subtitle files (.srt, written by manim next to each scene) are merged and added as a
  subtitle track that players can switch on (VLC, QuickTime, most phones); a copy is also written
  next to the video as <name>.srt, for players that want a separate file.
- Chapters: every title_card() is a chapter; when a scene has none, the scene itself is one
  (named after its class: ChapterTwoUnion -> "Chapter Two Union"). A video with one scene and no
  title cards gets no chapters.
- --burn also draws the subtitles into the picture (re-encodes; about 5 s per minute of video).
Prints one FINISHED line with what the file holds.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def duration(p) -> float:
    return float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)))


def srt_entries(p: Path):
    if not p.exists():
        return []
    out = []
    for block in re.split(r"\n\s*\n", p.read_text(encoding="utf-8").strip()):
        lines = block.strip().splitlines()
        if len(lines) >= 3 and "-->" in lines[1]:
            a, b = [_secs(x) for x in lines[1].split("-->")]
            out.append((a, b, "\n".join(lines[2:])))
    return out


def _secs(t: str) -> float:
    h, m, s = t.strip().replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _stamp(x: float) -> str:
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def words(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Za-z])(?=\d)", " ", name)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    burn = "--burn" in sys.argv
    out, parts = Path(args[0]), [Path(p) for p in args[1:]]
    if not parts:
        sys.exit(__doc__)
    tmp = Path(tempfile.mkdtemp())
    subs, chapters, t = [], [], 0.0
    for p in parts:
        d = duration(p)
        subs += [(a + t, b + t, text) for a, b, text in srt_entries(p.with_suffix(".srt"))]
        marks = p.with_suffix(".chapters.json")
        cards = json.loads(marks.read_text()) if marks.exists() else []
        if cards:
            if cards[0][1] > 1.0 and (not chapters or len(parts) > 1):  # the part before the first card
                chapters.append((t, words(p.stem) if len(parts) > 1 else "Introduction"))
            chapters += [(t + s, title) for title, s in cards]
        elif len(parts) > 1:
            chapters.append((t, words(p.stem)))
        t += d
    total = t

    lst = tmp / "parts.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    joined = tmp / "joined.mp4"
    run("ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined))

    srt = out.with_suffix(".srt")
    srt.write_text("".join(f"{i}\n{_stamp(a)} --> {_stamp(b)}\n{text}\n\n" for i, (a, b, text) in enumerate(subs, 1)),
                   encoding="utf-8")
    meta = tmp / "meta.txt"
    lines = [";FFMETADATA1"]
    for i, (s, title) in enumerate(chapters):
        e = chapters[i + 1][0] if i + 1 < len(chapters) else total
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(s * 1000)}", f"END={int(e * 1000)}",
                  "title=" + title.replace("=", r"\=").replace(";", r"\;").replace("#", r"\#")]
    meta.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(joined)]
    if subs:
        cmd += ["-i", str(srt)]
    cmd += ["-i", str(meta), "-map", "0:v", "-map", "0:a"]
    if subs:
        cmd += ["-map", "1:s", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-disposition:s:0", "default"]
    cmd += ["-map_metadata", str(2 if subs else 1), "-map_chapters", str(2 if subs else 1)]
    if burn and subs:
        style = "FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=1.5,MarginV=18"
        cmd += ["-vf", f"subtitles={srt}:force_style='{style}'", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "20", "-c:a", "copy"]
    else:
        cmd += ["-c:v", "copy", "-c:a", "copy"]
    run(*cmd, "-movflags", "+faststart", str(out))
    info = run("ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "csv=p=0", str(out))
    streams = ", ".join(x for x in info.split() if x)
    print(f"FINISHED {out}: {total:.0f}s, streams [{streams}], {len(subs)} subtitle lines"
          f"{' (burned in)' if burn and subs else ''}, {len(chapters)} chapters"
          + (": " + "; ".join(f"{s:.0f}s {c}" for s, c in chapters) if chapters else ""), flush=True)


if __name__ == "__main__":
    main()
