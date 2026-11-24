"""Shared building blocks for explainer scenes: narration, colors, text layout, layout check, automata."""
from contextlib import contextmanager
from pathlib import Path

from manim import *
from manim_voiceover import VoiceoverScene
from PIL import Image, ImageDraw, ImageFont

from kokoro_service import KokoroService

# One color per object family, the same in every video of a series.
A_COL, B_COL, KEY_COL, OK_COL, BAD_COL, NOTE_COL = BLUE_C, TEAL_C, YELLOW, GREEN_C, RED_C, ORANGE


class Explainer(VoiceoverScene):
    """Base class for every scene.

        with self.say(B["hook"]) as tr:     # one narration block; it waits for the audio to finish
            self.play(Write(title), run_time=1.5)
            self.wait_to(tr, 0.6)           # hold until 60% of the narration has played
            self.play(Indicate(title))

    A still picture renders about twice as fast as an animated one, so hold stills between short
    animations. In the 5 fps draft every block ends with a layout check (log lines starting with
    LAYOUT) and a snapshot; the snapshots are saved as numbered contact sheets (lines starting with
    SHEET), and a TIMING line says how many seconds are animated.
    """

    def setup(self):
        super().setup()
        self.set_speech_service(KokoroService())
        self.animated, self._seen, self._shots = 0.0, set(), []

    @contextmanager
    def say(self, text):
        with self.voiceover(text=text) as tr:
            yield tr
        if config.frame_rate <= 10:
            layout_check(self)
            self._shots.append((" ".join(text.split()[:4]), Image.fromarray(self.renderer.get_frame()).convert("RGB")))

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
    fw, fh = config.frame_width / 2, config.frame_height / 2
    name = lambda m: repr((getattr(m, "tex_string", None) or getattr(m, "text", ""))[:32])
    box = lambda m: (m.get_left()[0], m.get_right()[0], m.get_bottom()[1], m.get_top()[1])
    texts = [(m, box(m)) for m in _texts(scene.mobjects)]
    found = []
    for i, (m, (l, r, b, t)) in enumerate(texts):
        if l < -fw or r > fw or b < -fh or t > fh:
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
def title_card(scene, text, sub=None, hold=1.0):
    """Chapter title: fade in, hold, fade out."""
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
