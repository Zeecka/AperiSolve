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
const { JSDOM, VirtualConsole } = require("jsdom");

const [repoRoot, htmlPath, resultsPath, infosPath] = process.argv.slice(2);
const KEY = "sk-live-test-key";

// jsdom has no canvas: getContext() returns null and logs "not implemented"
// to the virtual console. Keep that noise off stderr (the pytest wrapper
// prints stderr only when this script fails).
const virtualConsole = new VirtualConsole();
const dom = new JSDOM(fs.readFileSync(htmlPath, "utf8"), {
  runScripts: "outside-only",
  url: "http://localhost/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  virtualConsole,
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

function streamResponse(frames) {
  const queue = frames.slice();
  const encoder = new TextEncoder();
  return Promise.resolve({
    ok: true,
    status: 200,
    headers: { get: () => "text/event-stream" },
    body: {
      getReader: () => ({
        read: () =>
          Promise.resolve(
            queue.length ? { done: false, value: encoder.encode(queue.shift()) } : { done: true },
          ),
      }),
    },
  });
}

function tokenFrames(texts) {
  return texts
    .map((text) => `data: ${JSON.stringify({ choices: [{ delta: { content: text } }] })}\n\n`)
    .concat(["data: [DONE]\n\n"]);
}

let sent = null;
window.fetch = (url, options) => {
  sent = { url, options };
  return streamResponse(
    tokenFrames(["Likely: LSB in the blue channel.\n", "Evidence: zsteg b1,rgb,lsb,xy"]),
  );
};

for (const script of ["aperisolve.js", "ai_panel.js"]) {
  window.eval(
    fs.readFileSync(path.join(repoRoot, "aperisolve", "static", "js", script), "utf8"),
  );
}

const byId = (id) => doc.getElementById(id);
const settle = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
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
  keyLinkPointsToProvider: byId("ai-key-link").href,
  jumpLinkTargetsPanel: (() => {
    const jump = doc.querySelector(".ai-jump");
    return Boolean(
      jump &&
        jump.getAttribute("href") === "#result-ai" &&
        jump.compareDocumentPosition(byId("result-analyzers")) &
          window.Node.DOCUMENT_POSITION_FOLLOWING,
    );
  })(),
};

byId("ai-ask").click();
facts.statusWithoutKey = byId("ai-status").textContent;
facts.noRequestWithoutKey = sent === null;

(async () => {
  const results = JSON.parse(fs.readFileSync(resultsPath, "utf8"));
  window.parseResult(results);
  window.APERISOLVE_INFO = JSON.parse(fs.readFileSync(infosPath, "utf8"));
  facts.toolsPublishedToThePanel = Object.keys(window.APERISOLVE_RESULTS || {}).length;

  byId("ai-key").value = KEY;
  byId("ai-ask").click();
  await settle(200);

  const body = JSON.parse(sent.options.body);
  const digest = body.messages[1].content;
  facts.request = {
    url: String(sent.url),
    method: sent.options.method,
    authHeader: sent.options.headers.Authorization.replace(KEY, "<KEY>"),
    keyIsHeaderOnly: !sent.options.body.includes(KEY) && !String(sent.url).includes(KEY),
    credentialsOmitted: sent.options.credentials === "omit",
    systemPromptFirst: body.messages[0].role === "system",
    // No canvas in jsdom: nothing is attached, the digest says so, and the
    // turn stays a plain string exactly as before images existed.
    digestIsPlainString: typeof digest === "string",
    digestSaysUntrusted: digest.includes("UNTRUSTED"),
    digestSaysNoImageAttached: digest.includes("## IMAGES ATTACHED (0)"),
    digestCarriesInjectionAttemptAsData: digest.includes("Ignore previous instructions"),
    digestBytes: digest.length,
  };
  facts.answerRendered = byId("ai-answer").textContent;
  facts.answerBoxVisible = !byId("ai-answer-box").hidden;
  facts.answerIsOneParagraph =
    byId("ai-answer").children.length === 1 && byId("ai-answer").children[0].tagName === "P";
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

  // Stop: one token arrives, then the stream hangs until the signal aborts it,
  // the way a browser rejects a pending read on abort.
  let signal = null;
  window.fetch = (url, options) => {
    signal = options.signal;
    let first = true;
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: { get: () => "text/event-stream" },
      body: {
        getReader: () => ({
          read: () => {
            if (first) {
              first = false;
              return Promise.resolve({
                done: false,
                value: new TextEncoder().encode(
                  'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n',
                ),
              });
            }
            return new Promise((resolve, reject) => {
              signal.addEventListener("abort", () => {
                const error = new Error("aborted");
                error.name = "AbortError";
                reject(error);
              });
            });
          },
        }),
      },
    });
  };
  byId("ai-question").value = "And the red channel?";
  byId("ai-ask").click();
  await settle(100);
  facts.stop = { buttonWhileStreaming: byId("ai-ask").textContent };
  byId("ai-ask").click();
  await settle(100);
  facts.stop.signalAborted = Boolean(signal && signal.aborted);
  facts.stop.status = byId("ai-status").textContent;
  facts.stop.partialKept = byId("ai-answer").textContent.endsWith("partial");
  facts.stop.buttonAfter = byId("ai-ask").textContent;

  // Remembering a key also remembers which provider it belongs to.
  byId("ai-provider").value = "anthropic";
  byId("ai-provider").dispatchEvent(new window.Event("change"));
  byId("ai-model").value = "claude-haiku-4-5";
  byId("ai-remember").checked = true;
  byId("ai-remember").dispatchEvent(new window.Event("change"));
  facts.prefsStoredWithKey = JSON.parse(window.localStorage.getItem("aperisolve.ai_prefs"));
  window.AperiSolveAI.init(); // what a reload does
  facts.reloaded = {
    provider: byId("ai-provider").value,
    model: byId("ai-model").value,
    key: byId("ai-key").value,
    remember: byId("ai-remember").checked,
  };
  byId("ai-remember").checked = false;
  byId("ai-remember").dispatchEvent(new window.Event("change"));
  facts.prefsForgottenWithKey = window.localStorage.getItem("aperisolve.ai_prefs");

  // Markdown from the model becomes headings, lists, bold and code — and
  // nothing else. A tag or a link in the model text stays literal text.
  byId("ai-provider").value = "openrouter";
  byId("ai-provider").dispatchEvent(new window.Event("change"));
  const hostile = '<script>alert(1)</script> and [a link](https://evil.example/) <img src=x onerror=alert(2)>';
  window.fetch = () =>
    streamResponse(
      tokenFrames([
        "## Verdict\nSomething is **hidden** in `blue`.\n\n## Evi",
        "dence\n- zsteg: `b1,rgb,lsb,xy`\n- image 3 shows text\n\n## Next steps\n1. run zsteg\n2. try `aperisolve`\n\n",
        `## Suspicious strings\n${hostile}\n\n\`\`\`\nflag{x}\n\`\`\`\n`,
      ]),
    );
  byId("ai-ask").click();
  await settle(200);
  const answer = byId("ai-answer");
  facts.markdown = {
    headings: [...answer.querySelectorAll("h3")].map((node) => node.textContent),
    bulletCount: answer.querySelectorAll("ul li").length,
    numberedCount: answer.querySelectorAll("ol li").length,
    strongText: [...answer.querySelectorAll("strong")].map((node) => node.textContent),
    inlineCode: [...answer.querySelectorAll("p code, li code")].map((node) => node.textContent),
    fencedCode: [...answer.querySelectorAll("pre code")].map((node) => node.textContent),
    forbiddenElements: [...answer.querySelectorAll("script, a, img, iframe, svg, style")].length,
    hostileKeptAsText: answer.textContent.includes(hostile),
    eventHandlerAttributes: [...answer.querySelectorAll("*")].filter((node) =>
      [...node.attributes].some((attribute) => attribute.name.startsWith("on")),
    ).length,
  };

  // Images: with a canvas (stubbed here, real in a browser) the first turn
  // carries the original and the derived images as image parts; a model that
  // rejects them with a 400 gets the same turn again as text, once.
  byId("ai-reset").click();
  window.HTMLCanvasElement.prototype.getContext = () => ({ drawImage() {} });
  window.HTMLCanvasElement.prototype.toDataURL = (type) =>
    `data:${type || "image/png"};base64,QUJD`;
  window.Image = class FakeImage {
    set src(value) {
      this.naturalWidth = value.includes("original") ? 1600 : 64;
      this.naturalHeight = value.includes("original") ? 1200 : 64;
      setTimeout(() => this.onload && this.onload(), 0);
    }
  };
  window.parseResult({
    ...results,
    decomposer: {
      status: "ok",
      images: { Red: ["/image/h/Red_bit_0.png", "/image/h/Red_bit_1.png"] },
    },
  });
  window.APERISOLVE_INFO = {
    ...window.APERISOLVE_INFO,
    kind: "image",
    image_path: "image/original.png",
    names: ["secret.png"],
  };
  const bodies = [];
  window.fetch = (url, options) => {
    bodies.push(JSON.parse(options.body));
    if (bodies.length === 1) {
      return Promise.resolve({
        ok: false,
        status: 400,
        headers: { get: () => "application/json" },
        text: () => Promise.resolve('{"error":"image input is not supported"}'),
      });
    }
    return streamResponse(tokenFrames(["text-only answer"]));
  };
  byId("ai-ask").click();
  await settle(300);
  const withImages = bodies[0] && bodies[0].messages[1].content;
  const retried = bodies[1] && bodies[1].messages[1].content;
  facts.images = {
    requests: bodies.length,
    firstTurnIsArray: Array.isArray(withImages),
    imageParts: Array.isArray(withImages)
      ? withImages.filter((part) => part.type === "image_url").map((part) => part.image_url)
      : [],
    labels: Array.isArray(withImages)
      ? withImages
          .filter((part) => part.type === "text" && part.text.startsWith("Image "))
          .map((part) => part.text)
      : [],
    digestListsThree: Array.isArray(withImages) && withImages[0].text.includes("## IMAGES ATTACHED (3)"),
    originalDownscaled:
      Array.isArray(withImages) && withImages[0].text.includes("(1600x1200, sent at 1024x768)"),
    keyNeverInBody: !bodies.some((sentBody) => JSON.stringify(sentBody).includes(KEY)),
    retryIsPlainText: typeof retried === "string",
    retrySaysWhy: typeof retried === "string" && retried.includes("[images were not attached: the model rejected them]"),
    retryKeepsDigest: typeof retried === "string" && retried.includes("## ANALYZER OUTPUT"),
    answerAfterRetry: byId("ai-answer").textContent,
  };
  // A follow-up must not resend the rejected images.
  byId("ai-question").value = "More?";
  byId("ai-ask").click();
  await settle(100);
  facts.images.requests = bodies.length;
  facts.images.historyStaysTextOnlyForFollowUps =
    bodies.length === 3 && typeof bodies[2].messages[1].content === "string";

  process.stdout.write(JSON.stringify(facts, null, 1));
})().catch((error) => {
  process.stderr.write(`${error && error.stack}\n`);
  process.exit(1);
});
