---
name: deps-bump
description: Sweep Dependabot for AperiSolve — land every open Dependabot PR (and any open security alert) in one combined PR, cut a patch release, watch the deploy and smoke-test production, rolling back if it breaks. Use when the user says "deps-bump", "land the dependabot PRs", "bump dependencies and release", or when a scheduled sweep runs.
argument-hint: "(no arguments)"
allowed-tools: [Bash, Read, Edit, Write]
---

# deps-bump — Dependabot sweep → patch release → verified prod

Built for an unattended 12-hourly run. Running this skill **is** the go-ahead
for the release in step 6 (the `release` skill's confirmation gate is
satisfied by the invocation). Most runs find nothing and stop at step 1.

## Facts (don't re-derive)
- Repo `Zeecka/AperiSolve`. `gh` may be missing: every GitHub call below is
  plain REST with `curl`, token from `$GITHUB_TOKEN`. **Never put the token on a
  command line**: write the headers into a mode-600 curl config once and use
  `curl -K <cfg>`:
  ```sh
  CFG=$(mktemp); chmod 600 "$CFG"
  printf 'header = "Authorization: Bearer %s"\nheader = "Accept: application/vnd.github+json"\nuser-agent = "curl/8.5.0"\n' "$GITHUB_TOKEN" >"$CFG"
  api() { p=$1; shift; curl -sS -K "$CFG" "https://api.github.com/repos/Zeecka/AperiSolve$p" "$@"; }
  ```
- Merging to `main` does **not** deploy. Pushing a tag does:
  `release.yml` → `tests` → `docker-releases` → `deploy`, about 10 minutes.
- The PR gate is `lint.yml` (3.12 + 3.15 matrix, ruff, ty, pytest, pip-audit,
  Docker build). Don't build the image locally; let CI do it.
- `uv.lock` is never hand-edited. On conflict: take `main`'s lock and re-run
  `uv lock --upgrade-package <pkg>==<version>`.
- Never move or delete a published tag. Failures are fixed forward.

## 1. Check — stop here if nothing is pending
```sh
api '/pulls?state=open&per_page=100' | python3 -c 'import json,sys; [print(p["number"], p["head"]["ref"], p["head"]["sha"]) for p in json.load(sys.stdin) if p["user"]["login"]=="dependabot[bot]"]'
api '/dependabot/alerts?state=open&per_page=100' | python3 -c 'import json,sys; [print(a["number"], a["dependency"]["package"]["name"], a["security_vulnerability"]["first_patched_version"]) for a in json.load(sys.stdin)]'
```
Both empty → report "nothing pending" and stop.

## 2. Select
- For each Dependabot PR, read its head commit's check runs
  (`api /commits/<sha>/check-runs`). Keep it if every run concluded `success`
  or `skipped`. A red or pending PR is left out; note the reason.
- An open alert whose package already has a selected PR is covered. An alert
  with no PR but a `first_patched_version`: add
  `uv lock --upgrade-package <pkg>` in step 3. An alert with no patched version
  is reported only; it does not by itself cause a release.

## 3. Consolidate on one branch
```sh
git fetch origin main '+refs/heads/dependabot/*:refs/remotes/origin/dependabot/*'
git switch -c "deps/$(date -u +%F)" origin/main
git cherry-pick origin/main..origin/<dependabot-ref>   # once per selected PR
```
On a `uv.lock` conflict: `git checkout origin/main -- uv.lock`,
`uv lock --upgrade-package <pkg>==<ver>` (plus the PR's `pyproject.toml` side if
it conflicts too), `git add`, `git cherry-pick --continue`. Then run the same
install CI runs, to prove the lock resolves: `uv sync --frozen --extra mcp --extra dev`.

## 4. Gate in CI
Push the branch and open one PR (`POST /pulls`, base `main`) titled
`build(deps): Dependabot sweep <date>`, body listing each bump and the PR it
supersedes. Poll the PR head's check runs every 60 s until all complete.
- All green → step 5.
- Red while each part was green on its own → drop bumps one at a time,
  **majors first**, force-push the branch, re-gate. Report every drop and its
  failing log line.

## 5. Merge
`PUT /pulls/<n>/merge` with `merge_method: merge`. Then close each superseded
Dependabot PR with a comment `Landed in #<n>.` (`POST /issues/<pr>/comments`,
then `PATCH /pulls/<pr>` `{"state":"closed"}`).

## 6. Release (patch)
Follow the `release` skill with argument `patch`, from an up-to-date `main`,
with these substitutions:
- Its step 4 confirmation is already given (see top).
- Commit trailers: follow the rules of your environment, not the skill's
  default.
- If `gh` is missing, create the Release with
  `api /releases -X POST --data-binary @<json>` where the JSON is
  `{"tag_name": X, "name": X, "body": <notes>, "make_latest": "true"}` built with
  `json.dumps`.

Release notes: a `## Dependency updates` heading, one bullet per bump
(`gunicorn 26.2.0 → 27.0.1`), flagged **(security)** when it closes an alert,
then the compare link.

## 7. Watch the deploy — in this same run
```sh
api "/actions/workflows/release.yml/runs?branch=<X.Y.Z>&event=push"   # take the newest run id
api "/actions/runs/<id>/jobs"                                          # poll every 60 s
```
Do not end the run while `deploy` is queued or running. A tag run takes about
10 minutes.

## 8. Verify production
```sh
scripts/prod-smoke.sh <X.Y.Z>
```
It checks the home page version, MCP `initialize` (`serverInfo.version`), and a
real upload → analysis → `/result`, with 3 attempts 60 s apart. Exit 0 = done.

## 9. On failure
- **`tests` or `docker-releases` red on the tag**: no image was pushed, prod is
  untouched. Fix forward with the next patch; do not retag.
- **`deploy` red, or the smoke test fails after deploy**: roll back by
  re-running the previous tag's `release.yml` run, which checks out and deploys
  that older tag:
  ```sh
  api "/actions/workflows/release.yml/runs?branch=<previous X.Y.Z>&event=push"   # its run id
  api "/actions/runs/<old id>/rerun" -X POST
  ```
  Watch it as in step 7, then `scripts/prod-smoke.sh <previous X.Y.Z>`. GitHub
  refuses reruns of runs older than 30 days; if that happens, say so — prod
  needs a manual redeploy.
- In every failure case: report what broke, with the failing job URL and log
  line, and hand the fix to a human or a follow-up task. Do not leave it silent.

## 10. Report
One block: bumps landed (old → new, PR numbers), bumps left out and why, the
version, the `release.yml` run id with the `deploy` conclusion, and the full
`prod-smoke.sh` output.
