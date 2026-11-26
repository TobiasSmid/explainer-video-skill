# explainer_lib.py: what scenes can use

Everything comes in with `from explainer_lib import *` (which also imports all of manim).

## Base class and timing
```python
from explainer_lib import *
from beats_01_union import BEATS as B

class UnionConstruction(Explainer):
    def construct(self):
        title_card(self, r"Is $A \cup B$ regular?")          # also a chapter in the final MP4
        q = ctex(r"A \cup B \text{ regular?}", {"A": A_COL, "B": B_COL}, font_size=56)
        with self.say(B["question"]) as tr:                  # one narration block; waits for the audio to end
            self.play(Write(q), run_time=1.5)
            self.wait_until_bookmark("u")                    # the beat says: "... the <bookmark mark='u'/>union ..."
            self.play(Indicate(q), run_time=1)
            self.wait_to(tr, 0.9)                            # or: until 90% of the block has played
```
- `self.say(text)`: one narration block. Subtitles are made from it automatically, timed to the words.
- Bookmarks: put `<bookmark mark='name'/>` right before a word in the beat; `self.wait_until_bookmark("name")`
  waits until that word is spoken; `tr.time_until_bookmark("name")` gives the seconds left, e.g. as a
  run_time so an animation ENDS on the word. prenarrate prints every bookmark's time (`@name 3.4s`).
- `self.wait_to(tr, fraction)`: wait until that fraction of the block has played.
- `tr.duration` includes the block's closing pause; consecutive blocks are already spaced like sentences.
- Camera (every Explainer can move it): `zoom_to(self, mob, margin=1.6)`, `zoom_reset(self)`.

## Colors (one per object family, the same in every video of a series)
A_COL, B_COL (the two main objects), KEY_COL (ε / the key idea), OK_COL (success), BAD_COL (failure),
NOTE_COL (caveats).

## Text and formulas
- `title_card(scene, text, sub=None)`: chapter title; marks a chapter for finish.py.
- `para(*lines, font_size=34)`: left-aligned multi-line prose (one Tex per line).
- `rows([(left_tex, right_tex or None), ...], font_size=40)`: two-column formulas with a shared right
  column; returns a VGroup with one VGroup per row; position it as a whole.
- `ctex(tex, colors, font_size=44)`: MathTex with colors on pieces, `ctex(r"A \cup B", {"A": A_COL})`.
  Every occurrence of a key is colored (also inside \mathcal{A}).
- `eq = morph(self, eq, new_tex, colors)`: one derivation step with TransformMatchingTex (the matching
  pieces glide into place); returns the new formula. Keep the same colors dict for every step.

## Strings, tapes, stacks
- `cells("aaabbb")` or `cells([r"q_0", "a"])`: a row of boxes, one symbol each. Each cell is VGroup(square, symbol).
- `segments(row, [(0, 1, "x", A_COL), (1, 3, "y", KEY_COL), (3, 6, "z", B_COL)])`: braces with labels
  under parts of a row (end exclusive) and colors those cells: the pumping-lemma split.
- `tape = Tape("0110", blanks=2)`: Turing-machine tape with a head; `self.play(tape.head_to(i))`,
  `self.play(tape.write(i, "1", color=KEY_COL))` (i counts from the first symbol, not the blanks).
- `st = Stack([r"\$"])`: PDA stack, top at the top; `self.play(st.push("a"))`, `self.play(st.pop())`.

## Tables, sets, number lines
- `grid(rows, col_labels=[...], row_labels=[...])`: a MathTable (transition table, truth table, DP table);
  `t.get_cell((r, c))` / `t.get_entries((r, c))` are 1-based and include the label row/column.
- `v = venn(("A", "B"))`, `venn_region(v, "A&B" | "A|B" | "A-B" | "B-A", color, opacity)`: two sets and a
  shaded region (FadeIn the region).
- `numline(lo, hi, step=1, length=10)`: NumberLine with numbers; `.n2p(x)` is the point for x.

## Automata (any DFA/NFA/PDA-style topic)
- `state(label, accepting=False, color=WHITE)`; `start_arrow(s)`; `token(color)` (a Dot to run along paths).
- `edge(s1, s2, angle=0.0, color=GREY_B)` and `loop(s, color=GREY_B)` return `(path, arrow)`: draw the
  arrow, and use the path for `MoveAlongPath` (angle > 0 bends to the left of travel). Two opposite
  transitions: two edges with angle=0.5, labels UP and DOWN.
- `elabel(path, text, direction=UP, buff=0.12, color=WHITE)`.
- Place machines in SurroundingRectangles with their name (D_A) and a one-line description to the right.

## Anything else
Build small helpers in the scene file in the same style (trees, graphs with manim's `Graph`, code with
`Code`), keep the same beat structure and colors.

## Layout lessons
- Keep every mobject you add in a group you later FadeOut (labels left on screen were a real bug).
- Frame is about 14.2 x 8 units; keep content within x in [-6.5, 6.5], y in [-3.7, 3.7] (below y = -2.6 is where
  subtitles appear); put input/status text in a free corner, never on a box border.
- Multi-line prose: `para()` (a multi-line Tex centers its lines). Two-column formulas: `rows()` (`&&`
  alignment does not work across separate MathTex objects). Don't Write an empty VMobject.
- Keep animations short (1 to 2 seconds) and hold the still picture in between: a still renders twice as
  fast as animation, and it is easier to follow than a slow Write stretched over a whole sentence.
