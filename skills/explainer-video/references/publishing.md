# Changing the skill permanently

Read this when the user asks to change the skill itself (a voice setting, a CUSTOM word, a helper, these
instructions), or after fixing a pronunciation they flagged.

Edit the copy in $EX and test it there. That copy lasts as long as the folder; in a cloud session it is gone
when the session ends. A change becomes permanent, for everyone who has this plugin, only in the skill's
GitHub repository TobiasSmid/explainer-video-skill, and only its owner can push there:
1. Get push access: where the session has an add_repo tool, call it with owner TobiasSmid, repo
   explainer-video-skill and access "push". If access is refused, the user is not the owner: say that the
   change holds for this session only, and stop here.
2. Clone the repository into a folder next to $EX, never into $EX
   (`git clone --depth 1 https://github.com/TobiasSmid/explainer-video-skill <folder>`), copy each changed file
   over its original under the clone's `skills/explainer-video/` (code in `scripts/`, these notes in
   `references/`), then commit and push to main.
3. There is no version number to raise: every push is a new version. People who turned on automatic sync for
   the repository get it by themselves, others when they check for updates on their Plugins page. A session
   that is already running keeps the version it started with.
The repository is public: never commit course material, scenes, or anything personal to it.

Package versions are pinned in scripts/setup.sh (PINS and the pip lines). To move to newer versions: change
both, run setup in a fresh folder, make a short test video (draft, final, finish.py, listen-back), then publish.
