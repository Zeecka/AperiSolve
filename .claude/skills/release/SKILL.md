---
name: release
description: Cut a new AperiSolve release — bump the version, commit "chore(release): X.Y.Z", tag it, push, and publish a GitHub Release whose notes are computed from the commits since the last tag. Use when the user says "release", "cut a release", "ship a release", "publish X.Y.Z", or "/release". Pushing the tag triggers the production deploy workflow, so this always confirms first.
argument-hint: "[version | patch | minor | major]"
allowed-tools: [Bash, Read, Edit, Write]
---

# release — bump, commit, tag, push, publish GitHub Release

Cut a release of AperiSolve. The steps are: bump the version, commit the bump as
`chore(release): X.Y.Z`, push `main`, create and push an annotated tag `X.Y.Z`,
then publish a GitHub Release whose body is **computed from the commits since the
last tag**.

The user's version request (if any) is: **$ARGUMENTS** — an explicit version
(`3.3.3`), a bump level (`patch` / `minor` / `major`), or empty (infer + confirm).

> ⚠️ **Pushing the `X.Y.Z` tag triggers `.github/workflows/release.yml`, which
> builds the Docker image AND deploys to production.** Treat this as a
> hard-to-reverse, outward-facing action: you MUST show the computed plan and get
> an explicit go-ahead (step 4) before executing step 5 onward.

## How this repo versions (facts, don't re-derive)
- Version lives in **`pyproject.toml`** (`[project] version = "X.Y.Z"`) and in
  **`uv.lock`** (under `[[package]] name = "aperisolve"`).
- ⚠️ **Never blind-`sed` `uv.lock`.** Unrelated packages can share the version
  string (e.g. `greenlet` has sat at the same `3.3.x`), so a global replace
  corrupts them. Bump the lockfile with **`uv lock`**, or, if offline, edit only
  the `version = "…"` line that sits directly under `name = "aperisolve"`.
- Tags are **bare `X.Y.Z`** (no `v` prefix), **annotated**, message
  `Release X.Y.Z — <one-line summary>`.
- The release commit contains **only the version bump** (2 files). Feature code is
  expected to already be merged to `main` (via `/commit`).
- Repo slug for compare/release URLs: **`Zeecka/AperiSolve`**.

## Workflow

Run in order. **Stop and report** on any problem instead of forcing anything.
Combine independent Bash calls where you can.

### 1. Preflight
- `git rev-parse --is-inside-work-tree`; confirm `origin` exists (`git remote`).
- `gh auth status` — must be logged in (needed for the GitHub Release).
- Branch: `git branch --show-current`. Releases deploy from `main`, so require
  `main`. If you're **not** on `main`, stop and tell the user to land the code on
  `main` first (e.g. `/commit`) then re-run — do **not** tag a feature branch.
- Sync: `git fetch --tags origin`, then ensure local `main` matches
  `origin/main` (`git pull --ff-only origin main`). If it can't fast-forward,
  stop and report.
- Clean tree: `git status --porcelain` must be empty (the only diff will be the
  bump this skill creates). If dirty, stop — tell the user to commit/stash first.

### 2. Compute the version and the release text
- **Previous version** = `pyproject.toml` `[project] version` (call it `$PREV`).
  Sanity-check a tag `$PREV` exists: `git rev-parse -q --verify "refs/tags/$PREV"`.
- **Commits to release** = `git log "$PREV"..HEAD --no-merges --format='%h %s'`
  (also skim bodies for `BREAKING CHANGE`). If **empty**, stop: "nothing to
  release since $PREV".
- **Next version `$NEXT`**:
  - If `$ARGUMENTS` is an explicit `X.Y.Z`, use it.
  - If it's `patch`/`minor`/`major`, apply that bump to `$PREV`.
  - If empty, **infer** and propose (confirm in step 4): any `feat` → **minor**;
    only `fix`/`perf`/`refactor`/`chore`/`docs`/`test` → **patch**; any `!` or
    `BREAKING CHANGE` → **major**. This is a suggestion, not a rule — the
    maintainer decides (past `feat` releases have shipped as patches).
  - `$NEXT` must be strictly greater than `$PREV` and not already a tag.
- **Compose two texts from the commits** (this is the "computed content"):
  1. **`$SUMMARY`** — one line (≤ ~120 chars), plain, what changed. Used in the
     tag message and as the commit-body lead.
  2. **`$NOTES`** — the GitHub Release body, markdown, in this repo's house style:
     a themed `##`/`###` heading, grouped bullets that describe user-visible
     changes (not raw commit subjects), and end with the compare link:
     ```
     **Full changelog:** https://github.com/Zeecka/AperiSolve/compare/$PREV...$NEXT
     ```
     Keep it faithful to the actual commits — summarize, don't invent.

### 3. Bump the version
- Edit `pyproject.toml`: `[project] version = "$PREV"` → `"$NEXT"` (the version
  line under `[project]`, **not** `target-version`).
- Update the lockfile: run `uv lock` (regenerates `uv.lock`, touching only the
  `aperisolve` version). If `uv` is unavailable/offline, edit **only** the
  `version` line directly beneath `name = "aperisolve"` in `uv.lock`.
- Verify the diff is exactly those two files and just the version:
  `git diff --stat` (expect `pyproject.toml`, `uv.lock`) and eyeball
  `git diff -- pyproject.toml uv.lock`. If anything else changed, stop and report.

### 4. Confirm (mandatory gate — this deploys to prod)
Show the user, and get an explicit go-ahead before proceeding:
- `$PREV` → `$NEXT` and how it was chosen,
- the commit subject `chore(release): $NEXT` + `$SUMMARY` body,
- the tag message `Release $NEXT — $SUMMARY`,
- the full `$NOTES` release body,
- a reminder that pushing the tag builds the image and deploys production.

If the user asked to proceed non-interactively in this turn, that go-ahead counts.

### 5. Commit the bump
Use a heredoc so the body + trailer stay intact:
```sh
git commit -aF - <<'EOF'
chore(release): $NEXT

$SUMMARY

<session-required trailer lines>
EOF
```
- **Append the trailer this harness session requires** — the `Co-Authored-By:`
  and `Claude-Session:` lines from your current environment's git/commit
  instructions. Read them from the live session; **never hardcode** them (the
  session URL changes each session). If the session specifies none, omit them.

### 6. Push `main`
- `git push origin main`.
- If **rejected** (non-fast-forward): stop, suggest `git pull --rebase origin
  main` and re-run. **Never** force-push.

### 7. Tag and push the tag (⇒ triggers build + deploy)
- `git tag -a "$NEXT" -m "Release $NEXT — $SUMMARY"`.
- `git push origin "$NEXT"`.

### 8. Publish the GitHub Release
- Write `$NOTES` to a temp file (use the session scratchpad dir) and run:
  ```sh
  gh release create "$NEXT" --title "$NEXT" --notes-file <notes-file> --latest
  ```
- The tag already exists on the remote, so `gh` attaches the release to it
  (it won't move or overwrite your annotated tag).

### 9. Report
- New commit sha + subject, the pushed tag, and the release URL
  (`gh release view "$NEXT" --json url -q .url`).
- Note that the tag push kicked off the Docker build + production deploy, and
  point at Actions to watch it: `gh run list --workflow release.yml --limit 3`.

## Safety rules (non-negotiable)
- **Confirm before step 5** — the tag push deploys production. No silent releases.
- **Never blind-replace in `uv.lock`** — `uv lock` or the anchored `aperisolve`
  line only.
- Release only from `main`, with a clean, up-to-date tree.
- `$NEXT` must be > `$PREV` and not an existing tag; tags are bare `X.Y.Z`.
- Never force-push; never delete or move an existing tag/branch/release.
- If any step fails, **stop and report** — don't improvise around a failure.

## Example usage
```
/release            # infer the bump from commits since the last tag, then confirm
/release patch      # 3.3.2 -> 3.3.3
/release minor      # 3.3.2 -> 3.4.0
/release 3.4.0      # explicit version
```
