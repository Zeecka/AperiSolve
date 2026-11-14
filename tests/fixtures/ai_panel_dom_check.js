/**
 * End-to-end check of the AI panel in a real DOM.
 *
 * Loads the result page exactly as the server rendered it, runs the real
 * aperisolve.js and ai_panel.js, stubs only the provider's fetch, drives the
 * panel, and prints one JSON object of facts for tests/test_ai_panel.py.
 *
 * Needs jsdom, which is not a dependency of this repo. Install it anywhere and
 * point NODE_PATH at it:
 *
 *   npm install jsdom                       # e.g. in /tmp/jd
 *   NODE_PATH=/tmp/jd/node_modules node tests/fixtures/ai_panel_dom_check.js \
 *       . page.html results.json infos.json
 *
 * The pytest wrapper does that automatically and skips when jsdom is absent.
 */
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const [repoRoot, htmlPath, resultsPath, infosPath] = process.argv.slice(2);
const KEY = "sk-live-test-key";

const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"), {
  runScripts: "outside-only",
  url: "http://localhost/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
});
const { window } = dom;
const doc = window.document;

/* The page's inline block is what injects TOOL_ORDER / I18N / AI_PANEL_ENABLED;
   run the real one rather than hand-stubbing those globals. */
window.eval(
  [...doc.querySelectorAll("script:not([src])")]
    .map((node) => node.textContent)
    .find((text) => text.includes("window.TOOL_ORDER")),
);

let sent = null;
window.fetch = (url, options) => {
  sent = { url, options };
  const frames = [
    'data: {"choices":[{"delta":{"content":"Likely: LSB in the blue channel.\\n"}}]}\n\n',
    'data: {"choices":[{"delta":{"content":"Evidence: zsteg b1,rgb,lsb,xy"}}]}\n\ndata: [DONE]\n\n',
  ];
  const encoder = new TextEncoder();
  return Promise.resolve({
    ok: true,
    status: 200,
    headers: { get: () => "text/event-stream" },
    body: {
      getReader: () => ({
        read: () =>
          Promise.resolve(
            frames.length
              ? { done: false, value: encoder.encode(frames.shift()) }
              : { done: true },
          ),
      }),
    },
  });
};

for (const script of ["aperisolve.js", "ai_panel.js"]) {
  window.eval(
    fs.readFileSync(path.join(repoRoot, "aperisolve", "static", "js", script), "utf8"),
  );
}

const byId = (id) => doc.getElementById(id);
const facts = {
  panelRendered: Boolean(doc.querySelector(".ai-panel")),
  missingControls: [
    "ai-provider",
    "ai-model",
    "ai-key",
    "ai-remember",
    "ai-ask",
    "ai-reset",
    "ai-question",
    "ai-answer",
    "ai-status",
  ].filter((id) => !byId(id)),
  providerOptions: [...doc.querySelectorAll("#ai-provider option")].map((o) => o.value),
  keyFieldIsPassword: byId("ai-key").type === "password",
  keyFieldStartsEmpty: byId("ai-key").value === "",
  rememberStartsUnchecked: byId("ai-remember").checked === false,
  storageWarningVisible:
    [...doc.querySelectorAll(".ai-panel .ai-warning")].filter((p) => !p.hidden).length === 1,
  anthropicWarningHiddenForOpenRouter: byId("ai-anthropic-warning").hidden,
};

byId("ai-ask").click();
facts.statusWithoutKey = byId("ai-status").textContent;
facts.noRequestWithoutKey = sent === null;

(async () => {
  window.parseResult(JSON.parse(fs.readFileSync(resultsPath, "utf8")));
  window.APERISOLVE_INFO = JSON.parse(fs.readFileSync(infosPath, "utf8"));
  facts.toolsPublishedToThePanel = Object.keys(window.APERISOLVE_RESULTS || {}).length;

  byId("ai-key").value = KEY;
  byId("ai-ask").click();
  await new Promise((resolve) => setTimeout(resolve, 200));

  const body = JSON.parse(sent.options.body);
  facts.request = {
    url: String(sent.url),
    method: sent.options.method,
    authHeader: sent.options.headers.Authorization.replace(KEY, "<KEY>"),
    keyIsHeaderOnly: !sent.options.body.includes(KEY) && !String(sent.url).includes(KEY),
    systemPromptFirst: body.messages[0].role === "system",
    digestSaysUntrusted: body.messages[1].content.includes("UNTRUSTED"),
    digestCarriesInjectionAttemptAsData:
      body.messages[1].content.includes("Ignore previous instructions"),
    digestBytes: body.messages[1].content.length,
  };
  facts.answerRendered = byId("ai-answer").textContent;
  facts.answerBoxVisible = !byId("ai-answer-box").hidden;
  facts.answerHasNoChildNodes = byId("ai-answer").children.length === 0;
  facts.resetOfferedAfterAnswer = !byId("ai-reset").hidden;

  const storageKey = "aperisolve.ai_key";
  facts.storedWhileUnchecked = window.localStorage.getItem(storageKey);
  byId("ai-remember").checked = true;
  byId("ai-remember").dispatchEvent(new window.Event("change"));
  facts.storedAfterTicking = window.localStorage.getItem(storageKey) === KEY;
  byId("ai-remember").checked = false;
  byId("ai-remember").dispatchEvent(new window.Event("change"));
  facts.storedAfterUnticking = window.localStorage.getItem(storageKey);

  const bodyBefore = sent.options.body;
  byId("ai-ask").click();
  facts.statusOnEmptyFollowUp = byId("ai-status").textContent;
  facts.emptyFollowUpSentNothing = sent.options.body === bodyBefore;

  process.stdout.write(JSON.stringify(facts, null, 1));
})().catch((error) => {
  process.stderr.write(`${error && error.stack}\n`);
  process.exit(1);
});
