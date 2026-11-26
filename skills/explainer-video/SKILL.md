---
name: explainer-video
description: Make narrated, animated explainer videos in the style of 3Blue1Brown (3b1b) with Manim and a Kokoro text-to-speech voice that runs locally. Use when the user asks for an explainer or explanation video of a math, computer-science or other course topic, optionally from material they name (slides, notes, a PDF). Big topics are split into a series of videos automatically. Use instead of generic video skills for such requests.
---

# 3b1b-style explainer videos with voiceover

The user says something like "make a video about X" (optionally "use lecture 4 / my notes / this PDF").
You deliver finished 720p MP4s with 3Blue1Brown-style animation, a narrated voiceover, subtitles and chapters.
- No length limit: a video is as long as its material needs. Cover everything; never cut content to hit a length.
- Every video is self-contained: it makes sense without the slides and without the other videos.
- Several topics become a series of smaller videos (section 2), and you make all of them.
- Do not stop to ask questions: decide, tell the user the plan, start right away. They can redirect any time.

Set up a task list if the session has one: find material, plan the split, set up tools, then one task per
video (script, scene, draft + check, final render, deliver). Give a time estimate: per minute of finished
video about 30 s of narration, 10 s of draft and 15 s of final render (2 cores), plus writing time.
When making more than one video, ALWAYS use the pipeline of section 9: the user starts watching video 1
while the next ones are still being made.

Cheap and fast (measured; keep it): never retype code that exists as a file (setup copies it, project
uploads use `local_path`); start narration in the background as soon as a beats file exists; never poll with
`sleep`, wait with one command that returns when the job ends; one draft, one look, one final render.

Reference files, read only when needed (they sit in `references/` next to this file):
- `references/helpers.md`: every scene helper with examples. Read it before writing the first scene.
- `references/voice.md`: how the voice works; fixing a flagged word; LISTEN flags; changing the voice.
- `references/publishing.md`: making a change to the skill permanent (GitHub).

## 1. Find the material
- If the user names material (lecture, slides, exercise sheet, attached file, working-folder file, project
  doc), use exactly that.
- If they only name a topic or course, look for their material first: attached files, project docs, the
  working folder, any connected file store (e.g. Google Drive: search the topic keywords). Prefer the newest
  version of a handout ("-v2").
- No material anywhere: use your own knowledge in standard textbook notation, and say so in the plan.
- Extract the definitions, theorems, the course's exact notation (e.g. D_A = (Q_A, Σ, δ_A, q_A, F_A)),
  constructions, proof structures and the course's examples. Be mathematically correct; re-verify every
  example you invent (trace the word through the automaton by hand).

## 2. Detect topics and plan the split (no questions)
List the material's topics in its order: every definition cluster, theorem, construction, proof technique and
worked example (track internally where each comes from; never show slide numbers or page ranges).
- One narrow topic (up to roughly 12 minutes): one video.
- The user asks for one big video: one video with a chapter per topic, in the material's order.
- Otherwise a series of self-contained videos of roughly 5-15 minutes: one central idea each, titled by the
  question it answers ("Why is A ∪ B regular?"); a construction stays with its proof and worked example;
  each video briefly (re)introduces every definition and notation it uses; ~140 spoken words per minute.
- The order is always the material's order. Never reorder, never shorten a video to make it arrive sooner.
- Send the plan (with SendUserMessage where the session has it) and start ALL videos immediately: a numbered
  list (**title**, one line on what it covers, ~N min), the total length, and how delivery works: "I'm making
  all N now, in this order, in a pipeline: while one video renders, I write the next. Video 1 arrives in about
  X min; after that a new one roughly every Y min, each sent the moment it's done."
- If the user changes the plan ("merge 2 and 3", "skip 5"), adjust and keep going.

A series shares one working folder ($EX), one scene file per video (`01_union.py`, ...), numbered outputs
(`01_union_construction.mp4`), the same colors and notation throughout.

## 3. Set up the workspace
Everything runs locally: Claude's cloud workspace (Linux; Hugging Face is blocked there, GitHub and pip work)
or the user's computer in Claude Code. No account or API key. The code ships in `${CLAUDE_SKILL_DIR}/scripts`
(if that still shows a placeholder, use the `scripts` folder in this skill's base directory). Never retype it.

Work in a folder `explainer` inside the session's working directory (cloud: usually /home/claude/explainer),
called $EX here: write the absolute path in every command (shell variables do not persist). Not in ~ in the
cloud: files there cannot be uploaded to a project by path.

Right after reading the material, start setup in the background:
```bash
mkdir -p $EX && cd $EX && bash "${CLAUDE_SKILL_DIR}/scripts/setup.sh" > setup.log 2>&1; echo "EXIT $?" >> setup.log
```
It copies the code into $EX, installs what is missing at the tested versions (LaTeX, ffmpeg, sox by apt;
Python packages by pip) and downloads the Kokoro model and the listen-back recognizer into $EX/models
(~600 MB; minutes the first time, seconds after). setup.log ends with SETUP OK and EXIT 0. Also look for:
- `VENV <path>`: start every later command with `export PATH=<path>:$PATH;`.
- `MISSING ...`: system packages it may not install (it never uses sudo); show the user the command, rerun later.
- `KEPT <file>`: $EX holds a changed copy of a code file, left alone.
- `NO LISTEN`: the recognizer could not be downloaded; everything else works.

## 4. Write the script (3b1b style)
One beats file per video, `beats_01_union.py`, holding one dictionary, one entry per narration block in order:
`BEATS = {"setup": "Suppose A and B are regular languages. ...", "question": "Is A ∪ B regular too?", ...}`.
As soon as it is written, start the narration in the background and go on to the scene:
```bash
cd $EX && python3 prenarrate.py beats_01_union > narr_01.log 2>&1; echo "EXIT $?" >> narr_01.log
```
narr_01.log lists every beat's length and bookmark times (`@u 3.4s`), then `LISTEN` lines: stretches the
recognizer heard differently from the script (`said 'xyz', heard 'size'`). Fix each one before the final
render: reword the beat or follow references/voice.md, then run prenarrate again (it only re-makes changed
beats). Run one prenarrate at a time.

Structure of each video or chapter (roughly 10-25 beats):
1. Hook: the question, plainly ("Is A ∪ B regular too?"), after a short setup of what it needs.
2. A small concrete example (two 2-state DFAs over {0,1}); say what each does in one sentence.
3. The obstacle (why it is not obvious).
4. The key idea, in steps ("Here's the trick. We don't choose. We let the machine guess.").
5. Run the example step by step, with success and failure visible.
6. The formal definition in the course's exact notation, built up line by line.
7. Side conditions (disjoint state sets, rename if needed).
8. Why it works: proof idea for each direction (⊆ and ⊇, or each case).
9. Conclusion tied back to the question; optionally one related idea worth exploring next.
Never skip proofs, examples or side conditions the material has for that video. Several ideas in one video:
chapters, each starting with `title_card`.

Exercises: only work out exercises with official solutions, following them. Before each answer: show it,
say "pause the video and try it", hold ~3 s. Tell the user (not the video) which exercises were left out.

Self-contained: never mention slides, "the lecture", "last time" or "the previous video"; introduce every
definition and notation the video uses.

Voice: calm, curious, second person ("let's", "you"), question before answer, short sentences. The narration
carries the explanation; the screen shows objects and formulas, no walls of text.

Writing for the voice (it reads exactly what you write):
- Math as on slides: "A ∪ B", "ε-transition", "q₀", "Σ*", "aⁿbⁿ", "a^{n+1}", "|w| ≥ p", "w^R", "δ(q, a)",
  "q′", "⊇", "Γ". The normalizer turns them into words.
- Capital letters are read as letter names; "D sub A" or "D_A" both work. Letter strings: "xyz" and "xy^iz"
  are spelled; for anything else use backticks: `abba`, `0110`.
- The lowercase letter a: write it where the article is impossible ("an a", "every a it reads", "a b c",
  formulas) or in backticks. Never start a sentence with the article "A"; use "One ...", "This ...".
- Punctuation sets the pauses: a comma where the narrator breathes, a question mark on real questions. Every
  sentence already gets its pause; use `[pause 0.3]` only for the extra beat before a reveal. No ellipses.
- Bookmarks for exact timing: `... we take the <bookmark mark='u'/>union ...` (section 5).

## 5. Build the manim scene
Read references/helpers.md first. One file per video in $EX, one scene class per chapter (renders stay
restartable), every class extends `Explainer`:
```python
from explainer_lib import *
from beats_01_union import BEATS as B

class UnionConstruction(Explainer):
    def construct(self):
        q = ctex(r"A \cup B \text{ regular?}", {"A": A_COL, "B": B_COL}, font_size=56)
        with self.say(B["question"]) as tr:      # one narration block; waits for the audio to finish
            self.play(Write(q), run_time=1.5)
            self.wait_until_bookmark("u")        # lands exactly on the bookmarked word
            self.play(Indicate(q), run_time=1)
```
Timing: everything inside a block must fit in `tr.duration` (see narr log); it includes the block's closing
pause, so do not add `self.wait()` between blocks. Prefer bookmarks over guessing; `self.wait_to(tr, 0.7)`
waits for a fraction of the block. Animations 1-2 s, then hold the still picture.
Visual style: black background; one color per object family across the series (A_COL, B_COL, KEY_COL for
ε / the key idea, OK_COL success, BAD_COL failure, NOTE_COL caveats); MathTex/ctex for formulas, Tex for prose,
font_size 34-56; Write/Create/GrowArrow to build up, Indicate to point, MoveAlongPath with a token for running
computations, SurroundingRectangle to group, morph() for derivation steps, zoom_to() for detail, FadeOut
between sections. Subtitles are added automatically; keep important content above y = -2.6 (two subtitle lines fit below).

## 6. Draft render and check
```bash
cd $EX && until grep -q "^EXIT" narr_01.log; do sleep 3; done; timeout 900 manim -ql --frame_rate 5 --progress_bar none 01_union.py UnionConstruction > draft_01.log 2>&1; grep -E "^(LAYOUT|TIMING|SHEET)|Traceback|Error" draft_01.log
```
About 10 s per minute of video. It prints:
- LAYOUT: text overlapping text or running off the screen, with the time. Fix every one.
- SHEET: contact sheets in sheets/ with one numbered snapshot per narration block. Open every sheet with Read:
  look for leftover labels, boxes cutting through content, misaligned columns, crowded layouts, wrong colors.
- TIMING: animated seconds of the total. More than half animated: shorten long animations.
Also fix every LISTEN line from the narr log. Re-run until clean (seconds: audio and formulas are cached).

## 7. Final render and finishing
```bash
cd $EX && manim -r 1280,720 --frame_rate 24 --encoder-option preset=veryfast --max-inflight-encoders 4 --progress_bar none 01_union.py UnionConstruction > final_01.log 2>&1; echo "EXIT $?" >> final_01.log
```
About 15 s per minute of video (twice that while another heavy job runs). 1080p (`-r 1920,1080 --frame_rate
30`, nearly twice as slow) only when asked. Keep the encoder flags; never pass `--disable_caching`. Never run
more heavy jobs (renders, prenarrate) at once than `nproc` (2 in the cloud).
A single video under ~8 minutes: final in the foreground (timeout 600000 ms). Longer videos and every video of
a series: in the background; when there is nothing else to do, wait in one command (repeat if needed):
```bash
cd $EX && until grep -q "^EXIT" final_01.log; do sleep 5; done; tail -3 final_01.log
```
Then finish it: join the chapter scenes in order (or pass the single scene), with subtitles and chapters:
```bash
cd $EX && python3 finish.py 01_union_construction.mp4 media/videos/01_union/720p24/Intro.mp4 media/videos/01_union/720p24/Union.mp4
```
It prints `FINISHED ...` with the streams, subtitle lines and chapters, and writes `01_union_construction.srt`
next to it. Subtitles are a track players can switch on; `--burn` draws them into the picture (about 5 s per minute of
video; use it when the user wants to see subtitles in a player without a subtitle switch, like the chat preview). Grab one full-res frame from the middle and look at it.

## 8. Deliver
- Hand each finished video over at once (SendUserFile, display: render, where available; else the full path).
  Send the .srt along only if the user wants subtitles in a player that needs a separate file.
- In a claude.ai Project: save each scene and beats file with project_write and `local_path`
  (`claude/<name>.py`), never pasted content, plus a short series plan `claude/<course>-video-plan.md`
  (titles, topics, status) so later sessions can continue.
- Reply briefly: one line per video, that the listen-back check passed (or what it could not settle), and
  which exercises were left for them. They can flag any odd word by its second in the video.

## 9. Several videos: the pipeline (watch one while the next is made)
1. Right after the plan: setup in the background.
2. Strictly in the material's order. Video 1: beats -> prenarrate (background) -> scene -> draft -> check ->
   fix -> final render in the background. Don't start video 2's beats before video 1's final is running.
3. While video N renders, write video N+1's beats, start its prenarrate, write its scene and draft it; start
   its final as soon as the draft is clean.
4. At most `nproc` heavy jobs at once; if all slots are busy, keep writing instead of waiting.
5. Each time a final finishes: finish.py, check, deliver at once, one line to the user ("Video 2 of 5 is
   ready: <title>. Video 3 in about N min."), tick the task, start the next queued final. Deliver in order.
6. Do not end your turn while renders run or videos are queued (cloud background jobs stop a few minutes
   after a reply ends). Wait with the `until grep` command, not `sleep`. Never stop halfway to ask.
7. If the user writes in between ("how long left"), answer from the logs and keep going.
8. One big video: the same per chapter; send finished chapters as previews; finish.py joins them at the end.
9. Afterwards: update the series plan in the project (status: done); every scene and beats file saved there.
