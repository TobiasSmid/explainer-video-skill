"""Shared building blocks for explainer scenes: narration, subtitles, chapters, colors, text layout,
layout check, camera, and helpers for automata, formulas, tapes, stacks, strings, tables and sets."""
import json
import re
from contextlib import contextmanager
from pathlib import Path

from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.helper import remove_bookmarks
from PIL import Image, ImageDraw, ImageFont

from kokoro_service import KokoroService
from speech_text import PAUSE

# One color per object family, the same in every video of a series.
A_COL, B_COL, KEY_COL, OK_COL, BAD_COL, NOTE_COL = BLUE_C, TEAL_C, YELLOW, GREEN_C, RED_C, ORANGE

CAPTION_CHARS = 64  # longest subtitle line


def caption_text(text: str) -> str:
    """What a viewer reads: no bookmarks, pause markers, pronunciation markup or spelling backticks."""
    text = PAUSE.sub(" ", remove_bookmarks(text))
    text = re.sub(r"\[([^\]]+)\]\(/[^)]*/\)", r"\1", text).replace("`", "")
    return " ".join(text.split())


class Explainer(VoiceoverScene, MovingCameraScene):
    """Base class for every scene.

        with self.say(B["hook"]) as tr:     # one narration block; it waits for the audio to finish
            self.play(Write(title), run_time=1.5)
            self.wait_until_bookmark("u")   # hold until the word after <bookmark mark='u'/> is spoken
            self.play(Indicate(title))
            self.wait_to(tr, 0.8)           # or: hold until 80% of the block has played

    A still picture renders about twice as fast as an animated one, so hold stills between short
    animations. In the 5 fps draft every block ends with a layout check (log lines starting with
    LAYOUT) and a snapshot; the snapshots are saved as numbered contact sheets (lines starting with
    SHEET), and a TIMING line says how many seconds are animated. Subtitles follow the words
    exactly, and title_card() marks a chapter; finish.py puts both into the final MP4.
    """

    def setup(self):
        super().setup()
        self.set_speech_service(KokoroService(), create_subcaption=False)  # say() makes word-timed ones
        self.animated, self._seen, self._shots, self.chapters = 0.0, set(), [], []

    @contextmanager
    def say(self, text):
        with self.voiceover(text=text) as tr:
            self._captions(tr)
            yield tr
        if config.frame_rate <= 10:
            layout_check(self)
            self._shots.append((" ".join(caption_text(text).split()[:4]),
                                Image.fromarray(self.renderer.get_frame()).convert("RGB")))

    def _captions(self, tr):
        """Subtitles for one block, cut at sentence and comma ends, each shown while it is spoken."""
        if config.save_last_frame:
            return
        script = remove_bookmarks(tr.data["input_text"])
        bounds = sorted((b["text_offset"], b["audio_offset"] / 10_000_000) for b in tr.data.get("word_boundaries") or [])
        if len(bounds) < 2:
            self.add_subcaption(caption_text(script), duration=tr.duration)
            return
        at = dict(bounds)
        words = [(m.start(), m.group()) for m in re.finditer(r"\S+", PAUSE.sub(lambda m: " " * len(m.group()), script))]
        lines, cur = [], []
        for off, w in words:
            cur.append((off, w))
            text = caption_text(" ".join(x for _, x in cur))
            if w[-1] in ".?!" or (w[-1] in ",;:" and len(text) > CAPTION_CHARS * 0.6) or len(text) >= CAPTION_CHARS:
                lines.append(cur)
                cur = []
        if cur:
            lines.append(cur)
        merged = []  # a short tail ("either one.") goes back onto the line before it
        for line in lines:
            short = len(caption_text(" ".join(w for _, w in line))) < 16
            prev_open = merged and merged[-1][-1][1][-1] not in ".?!"
            if short and prev_open and len(caption_text(" ".join(w for _, w in merged[-1] + line))) <= CAPTION_CHARS + 20:
                merged[-1] = merged[-1] + line
            else:
                merged.append(line)
        lines = merged
        speech_end = bounds[-1][1]
        starts = [at.get(line[0][0], None) for line in lines]
        for i, line in enumerate(lines):
            t0 = starts[i] if starts[i] is not None else (starts[i - 1] if i else 0.0)
            t1 = next((s for s in starts[i + 1:] if s is not None), speech_end)
            if t1 - t0 > 0.05:
                self.add_subcaption(caption_text(" ".join(w for _, w in line)), duration=t1 - t0 - 0.02, offset=t0)

    def wait_to(self, tr, frac):
        """Wait until `frac` (0-1) of the current narration block has played."""
        self.wait(max(tr.start_t + tr.duration * frac - self.renderer.time, 1 / config.frame_rate))

    def play(self, *args, **kwargs):
        before = self.renderer.time
        super().play(*args, **kwargs)
        if not all(isinstance(a, Wait) for a in args):
            self.animated += self.renderer.time - before

    def tear_down(self):
        print(f"TIMING {type(self).__name__}: animated {self.animated:.0f}s of {self.renderer.time:.0f}s", flush=True)
        for n in range(0, len(self._shots), 16):       # contact sheets: 4 x 4 snapshots, one per block
            sheet = Image.new("RGB", (1920, 1080))
            for i, (label, shot) in enumerate(self._shots[n:n + 16]):
                tile = shot.resize((480, 270))
                ImageDraw.Draw(tile).text((6, 4), f"{n + i + 1}: {label}", fill=(255, 220, 0), font=ImageFont.load_default(18))
                sheet.paste(tile, (i % 4 * 480, i // 4 * 270))
            path = Path("sheets") / f"{type(self).__name__}_{n // 16 + 1:02d}.png"
            path.parent.mkdir(exist_ok=True)
            sheet.save(path)
            print(f"SHEET {path}", flush=True)
        if self.chapters and not config.save_last_frame:  # read by finish.py
            movie = Path(self.renderer.file_writer.movie_file_path)
            movie.parent.mkdir(parents=True, exist_ok=True)
            movie.with_suffix(".chapters.json").write_text(json.dumps(self.chapters))
        super().tear_down()


def _texts(mobs):
    out = []
    for m in mobs:
        if isinstance(m, (SingleStringMathTex, Text)):
            if m.family_members_with_points():
                out.append(m)
        else:
            out += _texts(m.submobjects)
    return out


def layout_check(scene):
    """Print text that is partly off-screen or that overlaps other text (each problem once)."""
    frame = scene.camera.frame if hasattr(scene.camera, "frame") else None
    cx, cy = (frame.get_center()[:2] if frame is not None else (0, 0))
    fw = (frame.width if frame is not None else config.frame_width) / 2
    fh = (frame.height if frame is not None else config.frame_height) / 2
    name = lambda m: repr((getattr(m, "tex_string", None) or getattr(m, "text", ""))[:32])
    box = lambda m: (m.get_left()[0], m.get_right()[0], m.get_bottom()[1], m.get_top()[1])
    texts = [(m, box(m)) for m in _texts(scene.mobjects)]
    found = []
    for i, (m, (l, r, b, t)) in enumerate(texts):
        if l < cx - fw or r > cx + fw or b < cy - fh or t > cy + fh:
            found.append(f"off-screen: {name(m)}")
        for n, (l2, r2, b2, t2) in texts[i + 1:]:
            w, h = min(r, r2) - max(l, l2), min(t, t2) - max(b, b2)
            if w > 0 and h > 0 and w * h > 0.2 * min((r - l) * (t - b), (r2 - l2) * (t2 - b2)):
                found.append(f"overlap: {name(m)} and {name(n)}")
    for msg in found:
        if msg not in scene._seen:
            scene._seen.add(msg)
            print(f"LAYOUT t={scene.renderer.time:.0f}s {msg}", flush=True)


# ---- Text layout ----
_TEX_PLAIN = {r"\cup": "∪", r"\cap": "∩", r"\Sigma": "Σ", r"\varepsilon": "ε", r"\epsilon": "ε",
              r"\delta": "δ", r"\subseteq": "⊆", r"\supseteq": "⊇", r"\in": "∈", r"\to": "→",
              r"\emptyset": "∅", r"\times": "×", r"\circ": "∘", r"\leq": "≤", r"\geq": "≥", r"\neq": "≠",
              r"\Gamma": "Γ", r"\lambda": "λ", r"\vdash": "⊢", r"\mathbb{N}": "ℕ", r"\setminus": "∖"}


def plain(tex: str) -> str:
    """TeX -> readable text for chapter names: $A \\cup B$ -> A ∪ B."""
    for k, v in sorted(_TEX_PLAIN.items(), key=lambda kv: -len(kv[0])):
        tex = tex.replace(k, v)
    tex = re.sub(r"\\[A-Za-z]+\{([^{}]*)\}", r"\1", tex)  # \text{x}, \mathcal{A} -> x, A
    tex = re.sub(r"\\[A-Za-z]+|[${}]", "", tex).replace("_", "")
    return " ".join(tex.split())


def title_card(scene, text, sub=None, hold=1.0):
    """Chapter title: fade in, hold, fade out. Also marks a chapter for the final MP4."""
    if hasattr(scene, "chapters"):
        scene.chapters.append([plain(text), float(scene.renderer.time)])
    g = VGroup(Tex(text, font_size=56))
    if sub:
        g.add(Tex(sub, font_size=34, color=GREY_B))
    g.arrange(DOWN, buff=0.4)
    scene.play(FadeIn(g, shift=UP * 0.3), run_time=0.8)
    scene.wait(hold)
    scene.play(FadeOut(g), run_time=0.6)


def para(*lines, font_size=34, color=WHITE, buff=0.12):
    """Left-aligned multi-line prose: one Tex per line (a multi-line Tex would center its lines)."""
    return VGroup(*[Tex(x, font_size=font_size, color=color) for x in lines]).arrange(DOWN, aligned_edge=LEFT, buff=buff)


def rows(pairs, font_size=40, gap=0.8, buff=0.32, note_color=GREY_B):
    """Two-column formulas. pairs = [(left_tex, right_tex or None), ...] -> VGroup with one row each;
    the right column is left-aligned at a shared x. Position the returned group as a whole."""
    lefts = [MathTex(left, font_size=font_size) for left, _ in pairs]
    VGroup(*lefts).arrange(DOWN, aligned_edge=LEFT, buff=buff)
    x = max(m.get_right()[0] for m in lefts) + gap
    out = VGroup()
    for left, (_, right) in zip(lefts, pairs):
        row = VGroup(left)
        if right:
            r = MathTex(right, font_size=font_size, color=note_color)
            row.add(r.move_to([x + r.width / 2, left.get_center()[1], 0]))
        out.add(row)
    return out


# ---- Formulas ----
def ctex(tex, colors=None, font_size=44, **kwargs):
    """MathTex with the series colors on pieces: ctex(r"A \\cup B", {"A": A_COL, "B": B_COL}).
    Every occurrence of a key is colored, also inside commands (\\mathcal{A}); lowercase keys are
    separate from uppercase ones. Use the same colors in morph() so a derivation keeps them."""
    return MathTex(tex, tex_to_color_map=dict(colors or {}), font_size=font_size, **kwargs)


def morph(scene, eq, tex, colors=None, run_time=1.2, **kwargs):
    """One step of a derivation: the pieces that stay the same glide into place, the rest fades.
    eq = morph(self, eq, r"...")  -> returns the new formula (already on screen, where eq was)."""
    new = ctex(tex, colors, font_size=kwargs.pop("font_size", eq.font_size if hasattr(eq, "font_size") else 44),
               **kwargs).move_to(eq)
    scene.play(TransformMatchingTex(eq, new), run_time=run_time)
    return new


# ---- Camera ----
def zoom_to(scene, mob, margin=1.6, run_time=1.2):
    """Move the camera onto `mob` (it then fills about 1/margin of the frame width)."""
    frame = scene.camera.frame
    scene.play(frame.animate.move_to(mob).set(width=max(mob.width * margin, mob.height * margin * 16 / 9)),
               run_time=run_time)


def zoom_reset(scene, run_time=1.0):
    scene.play(scene.camera.frame.animate.move_to(ORIGIN).set(width=config.frame_width), run_time=run_time)


# ---- Strings, tapes, stacks ----
def cells(symbols, size=0.7, color=GREY_B, font_size=40):
    """A row of boxes with one symbol each (a word, a tape). symbols: a string or a list of TeX strings.
    Returns a VGroup of cells; each cell is VGroup(square, symbol)."""
    syms = list(symbols)
    row = VGroup(*[VGroup(Square(size, color=color, stroke_width=2),
                          MathTex(s, font_size=font_size) if s.strip() else VMobject()) for s in syms])
    for c in row:
        c[1].move_to(c[0])
    return row.arrange(RIGHT, buff=0)


def segments(row, parts, direction=DOWN, buff=0.12):
    """Braces under parts of a cells() row, e.g. the pumping-lemma split w = xyz:
    segments(row, [(0, 2, "x", A_COL), (2, 4, "y", KEY_COL), (4, 7, "z", B_COL)])  (end exclusive).
    Colors the cells too. Returns a VGroup of (brace, label) pairs."""
    out = VGroup()
    for lo, hi, label, color in parts:
        part = VGroup(*row[lo:hi])
        for c in part:
            c[0].set_stroke(color, width=3)
            c[1].set_color(color)
        brace = Brace(part, direction, buff=buff, color=color)
        out.add(VGroup(brace, brace.get_tex(label).set_color(color)))
    return out


class Tape(VGroup):
    """Turing-machine tape with a head. tape = Tape("0110", blanks=2); tape.head_to(3) and
    tape.write(3, "1") return animations; tape.head is the head marker."""

    def __init__(self, symbols, blanks=1, size=0.7, head_color=KEY_COL, **kwargs):
        syms = [r"\sqcup"] * blanks + list(symbols) + [r"\sqcup"] * blanks
        self.row = cells(syms, size=size, **kwargs)
        self.offset, self.pos = blanks, 0
        self.head = Triangle(color=head_color, fill_opacity=1).scale(0.14).rotate(PI)
        super().__init__(self.row, self.head)
        self.head.next_to(self.row[self.offset], UP, buff=0.08)

    def head_to(self, i):
        self.pos = i
        return self.head.animate.next_to(self.row[self.offset + i], UP, buff=0.08)

    def write(self, i, sym, color=WHITE):
        cell = self.row[self.offset + i]
        return Transform(cell[1], MathTex(sym, font_size=40, color=color).move_to(cell[0]))


class Stack(VGroup):
    """PDA stack, top at the top. st = Stack(["\\$"]); self.play(st.push("a")); self.play(st.pop())."""

    def __init__(self, items=(), width=1.4, height=0.65, color=GREY_B, font_size=40):
        super().__init__()
        self.w, self.h, self.color, self.fs = width, height, color, font_size
        self.base = Line(LEFT * width / 2, RIGHT * width / 2, color=color)
        self.add(self.base)
        self.items = []
        for s in items:
            self._place(self._box(s))

    def _box(self, s):
        return VGroup(Rectangle(width=self.w, height=self.h, color=self.color, stroke_width=2),
                      MathTex(s, font_size=self.fs))

    def _place(self, box):
        top = self.items[-1] if self.items else self.base
        box.next_to(top, UP, buff=0)
        self.items.append(box)
        self.add(box)
        return box

    def push(self, s, color=WHITE):
        box = self._box(s)
        box[1].set_color(color)
        self._place(box)
        return FadeIn(box, shift=DOWN * 0.4)

    def pop(self):
        box = self.items.pop()
        self.remove(box)
        return FadeOut(box, shift=UP * 0.4)


# ---- Tables, sets, number lines ----
def grid(data, col_labels=None, row_labels=None, font_size=44, **kwargs):
    """A table of TeX entries (a transition table, a truth table, a DP table). data: list of rows.
    Returns a manim MathTable: grid.get_cell((r, c)) and grid.get_entries((r, c)) are 1-based."""
    t = MathTable([[str(x) for x in row] for row in data],
                  col_labels=[MathTex(c) for c in col_labels] if col_labels else None,
                  row_labels=[MathTex(r) for r in row_labels] if row_labels else None,
                  include_outer_lines=True, line_config={"stroke_width": 1.5, "color": GREY_B},
                  element_to_mobject_config={"font_size": font_size}, **kwargs)
    return t.scale_to_fit_height(min(t.height, 6.4))


def venn(labels=("A", "B"), colors=(A_COL, B_COL), radius=1.5, gap=1.6):
    """Two overlapping sets. Returns VGroup(a, b, label_a, label_b); use venn_region() to shade."""
    a = Circle(radius, color=colors[0]).shift(LEFT * gap / 2)
    b = Circle(radius, color=colors[1]).shift(RIGHT * gap / 2)
    la = MathTex(labels[0], color=colors[0]).next_to(a, UL, buff=-0.3)
    lb = MathTex(labels[1], color=colors[1]).next_to(b, UR, buff=-0.3)
    return VGroup(a, b, la, lb)


def venn_region(v, which="A&B", color=KEY_COL, opacity=0.45):
    """Shaded region of a venn(): "A&B", "A|B", "A-B" or "B-A"."""
    a, b = v[0], v[1]
    op = {"A&B": lambda: Intersection(a, b), "A|B": lambda: Union(a, b),
          "A-B": lambda: Difference(a, b), "B-A": lambda: Difference(b, a)}[which]()
    return op.set_fill(color, opacity).set_stroke(width=0)


def numline(lo, hi, step=1, length=10, **kwargs):
    """A number line with numbers; numline(0, 10).n2p(3) is the point for 3."""
    return NumberLine(x_range=[lo, hi, step], length=length, include_numbers=True,
                      font_size=28, color=GREY_B, **kwargs)


# ---- Automata (DFA / NFA / PDA-style diagrams) ----
R = 0.42  # state radius

def state(label, accepting=False, color=WHITE):
    g = VGroup(Circle(radius=R, color=color, stroke_width=3))
    if accepting:
        g.add(Circle(radius=R - 0.08, color=color, stroke_width=3))
    g.add(MathTex(label, font_size=36))
    return g

def edge(s1, s2, angle=0.0, color=GREY_B):
    """Returns (path, arrow). angle>0 bends to the left of travel (s1->s2 rightward = arc on top).
    Use `path` for MoveAlongPath (the arrow has a tip, which distorts movement)."""
    d = normalize(s2.get_center() - s1.get_center())
    p1 = s1.get_center() + R * rotate_vector(d, angle / 2)
    p2 = s2.get_center() + R * rotate_vector(-d, -angle / 2)
    path = ArcBetweenPoints(p1, p2, angle=-angle) if angle else Line(p1, p2)
    arrow = path.copy().set_color(color).set_stroke(width=3)
    arrow.add_tip(tip_length=0.2, tip_width=0.2)
    return path, arrow

def loop(s, color=GREY_B):
    c = s.get_center()
    p1 = c + R * np.array([np.cos(125 * DEGREES), np.sin(125 * DEGREES), 0])
    p2 = c + R * np.array([np.cos(55 * DEGREES), np.sin(55 * DEGREES), 0])
    path = ArcBetweenPoints(p1, p2, angle=-1.5 * PI)
    arrow = path.copy().set_color(color).set_stroke(width=3)
    arrow.add_tip(tip_length=0.18, tip_width=0.18)
    return path, arrow

def elabel(path, text, direction=UP, buff=0.12, color=WHITE):
    return MathTex(text, font_size=30, color=color).next_to(path.point_from_proportion(0.5), direction, buff=buff)

def start_arrow(s, length=0.8):
    end = s.get_left()
    return Arrow(end + LEFT * length, end, buff=0, stroke_width=3, max_tip_length_to_length_ratio=0.3)

def token(color):
    return Dot(radius=0.11, color=color).set_z_index(5)
