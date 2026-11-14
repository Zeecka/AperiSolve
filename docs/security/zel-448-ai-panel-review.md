# Security review — "Ask AI" BYOK panel (ZEL-448 / A2)

Independent review of the Track A panel delivered by A1, against the checklist in
`docs/improvement-plan.md` ("Post-audit feature work") and ZEL-441 plan §2.5.

- Target: branch `ZEL-447-zel-441-a1-track-a-byok-ai-panel-build`, head `b77ffce`.
- Reviewed: `aperisolve/static/js/ai_panel.js`, `templates/result.html`,
  `templates/base.html`, `config.py`, `app.py`, `i18n.py`, the new CSS and i18n
  entries, `tests/test_ai_panel.py` and its two node fixtures.
- Verdict: **ship with fixes**. Every key-handling, escaping and server-surface
  invariant holds under independent measurement. Three hardening items below, one
  of which (F1) is what keeps those invariants true after the next edit.

## Method

A1 wrote both the panel and `tests/fixtures/ai_panel_dom_check.js`, so the
invariants were re-measured from scratch rather than read off that fixture:
`docs/security/ai_panel_review_probe.js` builds the panel in a fresh jsdom, feeds
it a hostile model stream and a hostile EXIF comment, and records every `fetch`.

```
npm install jsdom --prefix /tmp/jsdomroot
NODE_PATH=/tmp/jsdomroot/node_modules node docs/security/ai_panel_review_probe.js .
```

## Findings

### F1 — medium — the only guard for the key and XSS invariants never runs in CI

`tests/test_ai_panel.py:308-310` skips the whole `dom_facts` fixture when jsdom is
absent, and neither `.github/workflows/lint.yml:44` nor `release.yml:37` installs
node or jsdom. The six tests that assert the security properties — key field
starts empty, box starts unchecked, storage only on opt-in, answer has no child
nodes, key is header-only, one request only — therefore skip on every CI run, and
`--cov-fail-under=55` does not notice.

Measured: without jsdom `16 passed, 6 skipped`; with jsdom `22 passed`.

Consequence: a later edit that swaps `textContent` for `innerHTML` at
`ai_panel.js:529`, or drops the `rememberBox.checked` guard at `:480`, merges
green. The invariants are correct today and unguarded tomorrow.

Fix: add a jsdom install step to `lint.yml`, or turn the skip into a failure when
`CI` is set.

### F2 — medium-low — a typed base URL can send the key, with cookies, to aperisolve.com

`ai_panel.js:204-210` (`endpointFor`) trims trailing slashes and appends
`/chat/completions`. It validates no scheme, no host, and nothing rejects a
relative path; `fetch` at `:513` passes no `credentials` option, so the default
`same-origin` applies.

Measured with base URL `/v1`:

```
resolvedUrl: "/v1/chat/completions"   sameOriginKeyPost: true
cookiesWouldBeSent: true
endpointFor("custom","javascript:alert(1)") -> "javascript:alert(1)/chat/completions"
endpointFor("custom","http://evil.tld")     -> "http://evil.tld/chat/completions"
```

That is a POST to aperisolve.com carrying `Authorization: Bearer <key>` and the
visitor's cookies — the one path that contradicts the file's own invariant #1 at
`ai_panel.js:11` ("never reaches ... any aperisolve.com request"). The key does
not reach a server log (it is a header, access logs record the request line), and
the field is not prefilled from any attacker-controlled source — no URL
parameter, no localStorage — so this needs the visitor to type it, e.g. from a
bad tutorial or a social-engineered instruction. It is a documented-guarantee
break, not a remote exploit.

Fix, three lines: parse with `new URL(base)` and accept only `https:`, or `http:`
when the host is a loopback name; pass `credentials: "omit"` on every provider
fetch.

### F3 — low — the digest ships passwords the visitor typed, which the consent note does not name

`ai_panel.js:159-161` emits `passwords already tried: ...` into the first user
turn. The disclosure at `:356` says only "Analyzer outputs (which may include
content extracted from your file) are sent to the provider you selected" — a
password the visitor typed is neither an analyzer output nor extracted from the
file.

Measured: `digestLeaksTriedPasswords: true`, digest header line
`passwords already tried: hunter2, correct-horse-battery-staple`.

Mitigant: those passwords are already rendered publicly on the result page
(`aperisolve.js:288` → `displayPasswordsWithRemoval`, `:320`), so anyone with the
hash already sees them. This is a consent-wording gap, not a new disclosure.

Fix: name them in the note, or drop the line from `fileHeader`.

### F4 — low — no timeout or abort on the provider request

`ai_panel.js:513` has no `AbortController`, and `readAnswer` accumulates `answer`
without a cap. A wedged provider leaves the panel on "Waiting for the model…"
with `ai-ask` disabled until reload; an unbounded stream grows one string without
limit. Self-inflicted — the visitor chose the endpoint and pays for it.

### F5 — informational — the result globals are published even when the panel is off

`aperisolve.js:261` (`window.APERISOLVE_INFO`) and `:550`
(`window.APERISOLVE_RESULTS`) are set unconditionally, with no
`AI_PANEL_ENABLED` check. No new disclosure — the same data is already rendered
into the DOM, which the third-party script can read either way — but it hands
that script a parsed object instead of making it scrape. Gate both on
`window.AI_PANEL_ENABLED` for a zero delta when the panel is off.

## Checklist results (plan §2.5) — all confirmed

| Check | Result | Evidence |
|---|---|---|
| Key default in-memory | pass | field empty, box unchecked, `defaultWhileUnchecked: null` |
| localStorage only on explicit opt-in, warning shown | pass | `storedAfterOptIn: true`, `forgottenAfterOptOut: true`, warning never `hidden` (`ai_panel.js:376`) |
| Key never in a URL / a log / an aperisolve.com request | pass | `urlContainsKey: false`, `bodyContainsKey: false`, no `console.*` in the file, `noAperisolveRequest: true` — only counter-example is F2 |
| Model output not rendered as markup | pass, stronger than specified | `textContent` at `:529`, not `escapeHtml`; `<img src=x onerror>` + `<script>` payload gave `childElementCount: 0`, `scriptExecuted: false`; no markdown renderer |
| Prompt injection advisory only | pass | system prompt frames tool output as hostile data (`:28-32`); injection string travels as data (`injectionTravelsAsData: true`); no `eval`, no `Function`, nothing executed |
| CSP exposure documented and tied to the CSP task | pass | `docs/improvement-plan.md:98-102`, naming `base.html:41`; verified that `CUSTOM_EXTERNAL_SCRIPT` is the **only** third-party script on the result page (three.js is self-hosted, the CDN references are CSS), and that it reads the stored key (`readableByAnyPageScript: true`) |
| Zero new route / proxy / key transit | pass | `git diff main...b77ffce \| grep -E 'route\(\|add_url_rule'` → empty; only a config flag |
| Security headers unchanged | pass | `app.py:722-733` untouched; A1's `test_security_headers_are_untouched` passes |

One residual accepted by design: `anthropic-dangerous-direct-browser-access: true`
at `ai_panel.js:223` disables the guard Anthropic ships precisely to discourage
browser-side keys. It is the only way to make that provider work BYOK, the panel
names it in a visible warning (`:379-381`), and it is the visitor's own key.

## Next action

Le Forgeron: F1 (CI jsdom step) first — it is what keeps the rest true — then F2
(`new URL` scheme check plus `credentials: "omit"`). F3 is a one-clause string
change. F4 and F5 are optional.
