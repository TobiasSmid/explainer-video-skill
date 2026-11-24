---
name: "explainer-video"
description: "Make 3b1b-style animated explainer videos (manim + local Kokoro voiceover) about course topics from material the user names; splits big topics into a series automatically. Use instead of generic video skills."
---

# 3b1b-style explainer videos with voiceover

The user says something like "make a video about X" (optionally "use lecture 4 / my notes / this PDF").
You deliver finished 720p MP4s with animations in the style of 3Blue1Brown and a narrated voiceover
in the user's chosen voice. There is NO length limit: a video is as long as its material needs.
Cover everything in the material the user points to; never cut content to hit a length.
Every video is self-contained: it makes complete sense on its own, without the slides and without other videos.
When the material holds several topics, split it into a series of smaller videos (section 2) and make all of
them. Never ask the user questions: decide, tell them the plan, and start working right away.

Set up a task list: find material, plan the split, set up tools, then one task per video (script, scene,
draft + check, final render, deliver). Tell the user roughly how long it takes so they are not left waiting
blindly: per minute of finished video, about 30 seconds of narration, 10 seconds of draft and 15 seconds of
final render, plus the time to write the script and the scene.
When making more than one video, ALWAYS follow the pipeline in section 10: the user wants to start watching
video 1 while the next ones are still being made, not get the whole batch at the end.

Keeping videos cheap and fast (all of this was measured; do not drop it):
- Never retype code that exists as a file. The code comes from the user's GitHub repo (section 3), and
  files go to the project with `local_path` (section 9).
- Start the narration in the background as soon as the script exists, and write the scene meanwhile (section 5).
- Never poll with `sleep`. Wait for a job in one command that returns the moment the job ends (section 8).
- One draft, one look at its sheets, one final render: fix everything the draft reports before the final.

## 1. Find the material

- If the user names material (a lecture, slides, exercise sheet, uploaded file, project doc), use exactly that.
- If they only name a topic or a course, search Google Drive (Google_Drive search_files, fullText contains
  the topic keywords) and read the matching slides/handouts with read_file_content. Prefer the newest
  handout version (e.g. "-v2"). Also check attached project docs.
- Extract: the theorems/definitions, the course's exact notation (e.g. D_A = (Q_A, Σ, δ_A, q_A, F_A)),
  the constructions, the proof structures, and any examples the course uses.
- The videos must match the course notation and be mathematically correct. Re-verify any example you invent
  (e.g. trace the word through the automaton by hand).

## 2. Detect topics and plan the split (no questions)

After reading the material, list its topics in the material's order: every definition cluster, theorem,
construction, proof technique and worked example. (Track internally where each topic comes from so nothing
is missed, but never show slide numbers or page ranges to the user or in the videos.)

- If the request is one narrow topic that fits a single video (roughly up to 12 minutes), skip this step
  and make that one video.
- If the user asks for one big video ("one video", "one long video", "in a single video"), make one video with
  a chapter per topic instead of a series, still in the material's order.
- Otherwise, group the topics into a series of self-contained videos of roughly 5-15 minutes each:
  - one central idea per video, with a title that says what it answers ("Why is A ∪ B regular?");
  - keep a construction together with its correctness proof and its worked example;
  - each video briefly (re)introduces every definition and notation it uses, so it can be watched on its own,
    in any order;
  - keep the course's order for the numbering;
  - estimate each video's length (about 140 spoken words per minute plus animation pauses).
- The order of the videos is always the order of the topics in the material. Never reorder videos, and never
  shorten or cut a video to make it arrive sooner.
- Do NOT ask anything (no AskUserQuestion, no "which videos should I make?", no format question). Send the plan
  with SendUserMessage and immediately start making ALL videos. The plan message has:
  - a numbered list: **title** (the question it answers), then one line on what it covers, then "~N min";
  - the total length;
  - how delivery works: "I'm making all N now, in this order, in a pipeline: while one video renders, I write
    the next. Video 1 arrives in about X min and you can watch it while the rest are made; after that, a new
    video roughly every Y min. Each one is sent the moment it's done."
    (X = setup + script + draft + render of video 1; Y = the longer of scripting one video and rendering one.)
- If the user interrupts to change the plan ("merge 2 and 3", "skip 5"), adjust and keep going.

Each selected video then goes through sections 5-9. Separate videos share one workspace folder ($EX, section 3), one scene file
per video (`01_union.py`, `02_concatenation.py`, ...) and numbered outputs (`01_union_construction.mp4`),
keep the same colors and notation across the series, and are produced with the pipeline in section 10.
For one big video, each topic becomes a chapter (same pipeline, chapter by chapter, joined at the end).

## 3. Set up the workspace (cloud Linux workspace)

Network notes: Hugging Face and cloud TTS APIs (OpenAI, ElevenLabs, Google, Edge) are BLOCKED from the
workspace. GitHub release downloads, pip and apt work. So the voice is Kokoro, run locally.

All code lives in the user's public GitHub repo TobiasSmid/explainer-video-skill: speech_text.py (the voice),
kokoro_service.py (the manim-voiceover service), prenarrate.py, explainer_lib.py (scene helpers) and setup.sh.
Never retype these files. Clone the repo as the working folder `explainer` inside the session's working
directory (what `pwd` shows at the start, so usually /home/claude/explainer). The folder is called $EX below:
write the absolute path out in every command, because shell variables do not persist between commands. Do not
work in the home directory (~): it is outside the working directory, so files there cannot be uploaded to the
project without retyping them.

Right after reading the material, clone the repo and start the setup as a background job, so it finishes
while you write the split plan and the first script:
```bash
git clone --depth 1 https://github.com/TobiasSmid/explainer-video-skill $EX; cd $EX && bash setup.sh > setup.log 2>&1; echo "EXIT $?" >> setup.log
```
setup.sh installs manim, the voice packages and LaTeX and downloads the Kokoro model (a few minutes the first
time in a session, seconds when run again); setup.log ends with SETUP OK. The cloned folder is also the working
folder: scenes, beats files, models and media sit next to the code and are ignored by git.
No separate smoke test is needed: the first prenarrate run tests the voice, and the first draft tests manim.

If the clone is refused, call add_repo (owner TobiasSmid, repo explainer-video-skill, access "read") and clone
again. If the repo still cannot be reached, say so in one line and fall back to the copies in the project docs
(`claude/speech_text.py`, `claude/kokoro_service.py`, `claude/prenarrate.py`, `claude/explainer_lib.py`,
`claude/setup.sh`): read each with project_read and write it into $EX with the Write tool. That is slow, so
it is the last resort.

Changing the code (a voice setting, a CUSTOM word, a helper): edit the file in $EX and test it, then call
add_repo with access "push", commit and push that file, and update its project copy with project_write and
`local_path`. Code changes do not need a change to this skill. The repo is public: never commit course
material, scenes, or anything personal to it.

## 4. The voice (already chosen by the user, do not change unless asked)

Kokoro, the single voice am_puck (never a blend of voices), at a slightly lively pace (PACE 19.5, about 140
words per minute including pauses), with the warmer sound on (WARM = True). The user picked this by ear from
four versions: calm or livelier, each with and without the warmer sound. Pauses follow rules: about 0.2 s at a
comma, 0.5 s after a sentence, 0.7 s after a question, and the same pause at the end of every voiceover block.
All settings are at the top of speech_text.py.
Why each piece exists (the user heard every one of these problems; do not undo the fixes):
- Pronunciation comes from misaki, Kokoro's own G2P. Raw espeak phonemes (kokoro-onnx's default) stress
  words wrongly ("automata") and sound more artificial.
- misaki writes the soft American t as "ɾ"; Kokoro v1.0 needs "T". With "ɾ" it rolls an r, and "automata"
  comes out as "automatar" with a foreign accent.
- Kokoro picks a different voice style for every input length, so pitch and tone jumped from one sentence
  to the next ("nasal, then normal again"). narrator() uses one fixed style for everything.
- Kokoro talks faster the longer its input, so long sentences sounded rushed and short ones slow. render()
  measures every unit with the model's timings and re-renders it until it hits PACE.
- Pauses are spliced into the gaps the model already left, so sentences stay whole. Do not go back to
  synthesizing sentences in pieces cut at commas.
- Blended voices and the low-rated voices (am_liam, am_eric: grade D) sounded unstable to the user.
- Without the letter rule, a standalone "A" is read as the article "uh" ("if uh is regular").
- Symbols like ∪ are silently dropped unless normalize() turns them into words.
Speed: narration takes about half a minute per minute of audio. Two things keep it that fast: kokoro_service.py
runs Kokoro on all cores (onnxruntime's default uses one core here, 1.6x slower), and render() learns the
voice's natural rate as it goes, so most sentences need one synthesis pass instead of two.
You cannot hear the audio, so check it with numbers: pass `log=[]` to speak() for the pace of every unit, and
measure the silences in the output. Ask the user to name the second where something sounds off.
When the user flags a mispronounced word, add it to CUSTOM in speech_text.py, re-render, and push the change
to the repo (section 3).
If the user wants a different voice: render a short comparison MP3 of SINGLE voices through this same
pipeline (`narrator(k, "am_michael")`; each voice says its own name, then the same passage) and let them
pick; then set VOICE. Kokoro's best-rated male voices are am_michael, am_fenrir and am_puck (C+), then
bm_george and bm_fable (C). The best overall is af_heart (A). Kokoro has no Dutch voice; narrate in English.
Never clone or imitate a real person's voice; offer generic qualities (calm, warm, slower) instead.

## 5. Write the script (3b1b style)

One script per video, written as a beats file `beats_01_union.py` that holds one dictionary:
`BEATS = {"setup": "Suppose A and B are regular languages. ...", "question": "Is A ∪ B regular too?", ...}`
with one entry per narration block, in order, under a short descriptive key. The scene refers to beats by
key, so narration text is typed once.

As soon as the beats file is written, start the narration with run_in_background and go on to the scene:
```bash
cd $EX && python3 prenarrate.py beats_01_union > narr_01.log 2>&1; echo "EXIT $?" >> narr_01.log
```
It takes about half a minute per minute of narration and prints the length of every beat in narr_01.log;
read that log before you time the animations, so you know how long each block lasts. Run only one prenarrate
at a time. After changing some beats, run it again: it only makes the changed ones.

A video that covers several topics (one big video, or a planned video with two
ideas) is split into chapters, each starting with a title card. Do not skip proofs, examples or side conditions
that are in the material for that video.

Exercises: when the material includes exercise sheets, only work out exercises that have official solutions
(so the video never teaches a wrong answer), and follow the official solution's approach. Before each answer,
add a "pause and try it yourself" moment: show the exercise, say "pause the video and try it", and hold the
screen for about 3 seconds. Tell the user (not in the video) which exercises were left out because they have
no published solution, so they can do those themselves.

Self-contained: never mention slides, slide numbers, "the lecture", "as we saw last time" or "in the previous
video". Introduce every definition and piece of notation the video uses (briefly if it is basic), so a viewer
who only watches this video can follow it.

Structure of each video or chapter (roughly 10-25 voiceover beats):
1. Hook: state the question plainly ("Is A ∪ B regular too?"), after a short setup of the definitions it needs.
2. A concrete, small example (e.g. two 2-state DFAs over {0,1}). Name what each does in one sentence.
3. The obstacle (why it is not obvious).
4. The key idea, revealed in steps ("Here's the trick. We don't choose. We let the machine guess.").
5. Run the example: trace a word / compute a case step by step, with success and failure visible.
6. The formal definition, in the course's exact notation, built up line by line ("the way you'd write it on the exam").
7. Important side conditions (e.g. disjoint state sets, rename if needed).
8. Why it works: proof idea for each direction (⊆ and ⊇, or each case).
9. Conclusion tied back to the question; optionally one line on a related idea worth exploring next.

Voice: calm, curious, second person ("let's", "you"), question before answer, short sentences,
`[pause 0.3]` before the key reveal. No walls of text on screen; narration carries the explanation,
the screen shows the objects and formulas.

TTS rules for narration text (learned the hard way):
- Write math with symbols as on slides: "A ∪ B", "ε-transition", "q₀", "Σ*". The normalizer handles them.
- Capital letters are read as letter names. Subscripts: say "D sub A", "q A", "F A ∪ F B".
- Never start a sentence with the article "A"; use "One ...", "This ...", "Every ..." instead.
- The lowercase symbol "a" is read as the article ("uh"). Prefer alphabets like {0,1} ("a one", "one zero"),
  or force the letter name with `[a](/ˈA/)`. Other lowercase letters (b, w, q) and plural acronyms (NFAs)
  are read correctly.
- Punctuation sets the pauses, so punctuate the way it should be spoken: a comma where the narrator should
  breathe, a question mark on real questions. Every sentence already gets its pause, so do not put
  `[pause X]` after every sentence; keep it for the extra beat before a reveal.
- No ellipses for pauses; use `[pause X]` between beats.
- Check unusual terms first:
  `python3 -c "import speech_text as s; from kokoro_onnx import Kokoro; k=Kokoro('models/kokoro-timed.onnx','models/voices.bin'); print(s.to_phonemes(k,'your phrase'))"`
  and add a rule to SYMBOLS if a symbol is dropped, or an entry to CUSTOM if a word is mangled.

## 6. Build the manim scene

One file per video in $EX (`01_union.py`, ...). One scene class per chapter (a single class for a
one-chapter video); this keeps renders restartable. Every scene class extends `Explainer` from
explainer_lib.py, which sets up the narration:

```python
from explainer_lib import *
from beats_01_union import BEATS as B

class UnionConstruction(Explainer):
    def construct(self):
        title = MathTex(r"A \cup B \text{ regular?}", font_size=56)
        with self.say(B["question"]) as tr:      # one narration block; it waits for the audio to finish
            self.play(Write(title), run_time=1.5)
            self.wait_to(tr, 0.7)                # hold the still until 70% of the narration has played
            self.play(Indicate(title), run_time=1)
```

Use what explainer_lib.py provides instead of writing your own; its functions are listed at the end of this
section.

Timing: everything inside a block must fit in `tr.duration` (read the beat lengths in narr_01.log).
`tr.duration` already includes the block's closing pause (0.5-0.7 s of silence), so consecutive blocks are
spaced like sentences; do not add `self.wait()` between blocks just for breathing room. Use
`self.wait_to(tr, fraction)` so a visual lands when the narration mentions it.
Keep animations short (1 to 2 seconds) and hold the still picture in between. A still renders twice as fast
as animation, and it is easier to follow than a slow `Write` stretched over a whole sentence.

Visual style: default black background; one consistent color per object family across the whole series
(e.g. A = BLUE_C, B = TEAL_C, ε / key idea = YELLOW, success = GREEN_C, failure = RED_C, caveats = ORANGE).
MathTex for formulas, Tex for prose, font_size 34-56. Use Write/Create/GrowArrow to build things up,
Indicate to point at things being discussed, MoveAlongPath with Dots for "running" computations,
SurroundingRectangle for grouping and highlighting, FadeOut between sections. No slide references on screen.

Layout lessons:
- Keep every mobject you add in a group you later FadeOut (labels left on screen were a real bug).
- Frame is about 14.2 x 8 units; keep content within x in [-6.5, 6.5], y in [-3.7, 3.7]; put input/status text
  in a free corner, never on top of a box border.
- Multi-line prose: use `para()` (a multi-line Tex centers its lines). Two-column formulas
  ("δ(q, a) = ...   for all ..."): use `rows()` (`&&` alignment does not work across separate MathTex objects).
- Don't Write an empty VMobject.

What explainer_lib.py provides:
- `Explainer`: the base class. `self.say(text)` is one narration block; `self.wait_to(tr, fraction)` waits
  until that fraction of the block's narration has played. In the 5 fps draft it also checks the layout after
  every block and saves the contact sheets (section 7).
- Colors, one per object family for the whole series: A_COL, B_COL, KEY_COL (ε / key idea), OK_COL (success),
  BAD_COL (failure), NOTE_COL (caveats).
- Text: `title_card(scene, text, sub=None)` for chapter titles; `para(*lines, font_size=34)` for left-aligned
  multi-line prose; `rows([(left_tex, right_tex or None), ...], font_size=40)` for two-column formulas (it
  returns a VGroup with one VGroup per row; position it as a whole).
- Automata (any DFA/NFA/PDA-style topic): `state(label, accepting=False, color=WHITE)`;
  `edge(s1, s2, angle=0.0, color=GREY_B)` and `loop(s, color=GREY_B)` return `(path, arrow)`: draw the arrow,
  and use the path for `MoveAlongPath` (angle > 0 bends to the left of travel);
  `elabel(path, text, direction=UP, buff=0.12, color=WHITE)`; `start_arrow(s)`; `token(color)`.
Use two edges with angle=0.5 for a pair of opposite transitions (labels UP and DOWN). Place machines in
SurroundingRectangles with their name (D_A) and a one-line description to the right of the box.
For non-automata topics, build analogous small helpers (number lines, sets as ellipses, trees, tables, graphs
with `Graph`), and keep the same beat structure.

## 7. Draft render and visual check

```bash
cd $EX && until grep -q "^EXIT" narr_01.log; do sleep 3; done; timeout 900 manim -ql --frame_rate 5 --progress_bar none 01_union.py UnionConstruction > draft_01.log 2>&1; grep -E "^(LAYOUT|TIMING|SHEET)|Traceback|Error" draft_01.log
```
The draft runs at 480p and 5 fps and takes about 10 seconds per minute of video (the `until` waits for the
narration; without it the draft would generate the missing audio itself, slowly). It prints:
- LAYOUT lines: text that overlaps other text or runs off the screen, with the time it happens. Fix every one.
- SHEET lines: contact sheets in sheets/, with one numbered snapshot per narration block, taken at the end
  of the block (16 per sheet). Open every sheet with Read and look for what the automatic check cannot see:
  labels left behind after a section, boxes cutting through content, misaligned columns, crowded or lopsided
  layouts, wrong colors. The number and first words on a snapshot tell you which block to fix.
- TIMING: animated seconds out of the total. If more than half the video is animated, shorten long animations.
Fix and re-run the draft until it is clean (re-runs take seconds: narration and formulas are cached).
Draft-render every chapter/video and check each.

## 8. Final render

```bash
cd $EX && manim -r 1280,720 --frame_rate 24 --encoder-option preset=veryfast --max-inflight-encoders 4 --progress_bar none 01_union.py UnionConstruction > final_01.log 2>&1; echo "EXIT $?" >> final_01.log
```
The user chose 720p at 24 fps to make videos faster; do not raise them unless asked. It takes about
15 seconds per minute of video, or about twice that when a second render or prenarrate runs at the same
time. The two encoder flags make it a third faster at the same picture quality and file size (measured);
keep them. Never pass `--disable_caching`: with caching on, re-rendering after a small fix only redoes the
changed animations. Never run more heavy jobs at once (manim renders and prenarrate together) than `nproc`
(usually 2): extra jobs only slow every job down.

A single video: run the final in the foreground with a timeout of 600000 ms when the estimate is under
8 minutes. Longer videos, and every video of a series: start it with run_in_background and keep working.
When there is nothing left to do but wait, wait in ONE command that returns the moment the render ends
(timeout 600000 ms; repeat it if the render is still going), instead of polling with `sleep 300`:
```bash
cd $EX && until grep -q "^EXIT" final_01.log; do sleep 5; done; tail -3 final_01.log
```
If the user asks how long is left, answer from the log: it lists every finished animation.

Verify each output: `ffprobe -v error -show_entries stream=codec_type,width,height,duration -of csv=p=0 <mp4>`
(video 1280x720 + audio of nearly the same length). Grab one full-res frame from the middle and look at it.

Join chapters of one video in order:
```bash
cd $EX/media/videos/01_union/720p24
printf "file '%s'\n" Chapter01Intro.mp4 Chapter02Union.mp4 > chapters.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i chapters.txt -c copy $EX/01_union_construction.mp4
```

## 9. Deliver

- Give each video a clear numbered name (e.g. $EX/01_union_construction.mp4) and send it with SendUserFile
  (display: render) as soon as it is finished; don't hold finished videos back until the whole series is done.
- If the session is attached to a claude.ai Project, save each scene file and beats file to the project with
  project_write and `local_path` (path `claude/<name>.py`). Never paste a file's content into the call: that
  retypes the whole file. Keep a short series plan there too (`claude/<course>-video-plan.md`: titles, topics
  covered, status), so later sessions can continue the series. The code files live in the repo and need
  no saving.
- Reply briefly: what each video covers (one line each), that you checked frames but cannot hear the audio
  (ask them to flag odd words), and which exercises were left for them to do.

## 10. Making several videos: the pipeline (watch one while the next is made)

Goal: the user starts watching video 1 as early as possible, and every next video follows as soon as it is done,
always in the material's order. Never script everything first and render everything at the end.

1. Right after sending the plan: attach and clone the repo and start setup.sh in the background (section 3).
2. Work strictly in the material's order (video 1, 2, 3, ...). Video 1: beats file -> prenarrate in the
   background -> scene -> draft -> check sheets -> fix -> start its final render as a background job. Get
   video 1 out first; don't start video 2's beats before video 1's final render is running.
3. While video N's final render runs, write video N+1's beats, start its prenarrate, write its scene and draft
   it. As soon as that draft is clean, start its final render.
4. Keep at most `nproc` heavy jobs running at once (drafts, finals and prenarrate together). If both slots are
   busy, keep writing instead of waiting idle.
5. Every time a final render finishes: verify it (ffprobe + one frame), send it right away with SendUserFile,
   post a one-line SendUserMessage ("Video 2 of 5 is ready: <title>. Video 3 in about N min."), tick its task,
   and start the next queued final render. Deliver in order: if a later video finishes before an earlier one,
   hold it and send it right after the earlier one.
6. Do not end your turn while renders are still running or videos are still queued: background jobs are
   stopped a few minutes after the reply ends. When you have nothing to write, wait with the `until grep`
   command of section 8 (not with `sleep`), and keep going until every video is delivered. Never stop halfway to ask whether to continue.
7. If the user writes in between (e.g. "how long left"), answer from the logs with a concrete estimate and
   keep the pipeline going.
8. For one big video: run the same pipeline per chapter, send finished chapters as previews in order, and
   join them (section 8) once the last one is done.
9. After all videos are delivered, update the series plan in the project (status: done) and make sure every
   scene and beats file is saved there (with `local_path`).