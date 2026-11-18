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
    "ai-send-images",
    "ai-send-pixels",
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
  // Images go by default, the pixel matrix only when asked for.
  optionDefaults: { images: byId("ai-send-images").checked, pixels: byId("ai-send-pixels").checked },
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
    digestHasNoPixelValues: !digest.includes("PIXEL VALUES"),
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
  byId("ai-send-images").checked = false;
  byId("ai-send-pixels").checked = true;
  byId("ai-remember").checked = true;
  byId("ai-remember").dispatchEvent(new window.Event("change"));
  facts.prefsStoredWithKey = JSON.parse(window.localStorage.getItem("aperisolve.ai_prefs"));
  window.AperiSolveAI.init(); // what a reload does
  facts.reloaded = {
    provider: byId("ai-provider").value,
    model: byId("ai-model").value,
    key: byId("ai-key").value,
    remember: byId("ai-remember").checked,
    sendImages: byId("ai-send-images").checked,
    sendPixels: byId("ai-send-pixels").checked,
  };
  byId("ai-remember").checked = false;
  byId("ai-remember").dispatchEvent(new window.Event("change"));
  facts.prefsForgottenWithKey = window.localStorage.getItem("aperisolve.ai_prefs");
  byId("ai-send-images").checked = true;
  byId("ai-send-pixels").checked = false;

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

  // Both boxes are locked once a conversation exists, and Reset frees them.
  const optionsLocked = () => byId("ai-send-images").disabled && byId("ai-send-pixels").disabled;
  facts.options = { lockedAfterAnswer: optionsLocked() };
  byId("ai-reset").click();
  facts.options.freeAfterReset = !byId("ai-send-images").disabled && !byId("ai-send-pixels").disabled;

  // Images: with a canvas (stubbed here, real in a browser) the first turn
  // carries the original and the derived images as image parts; a model that
  // rejects them with a 400 gets the same turn again as text, once.
  let encodes = 0;
  let drawn = null;
  window.HTMLCanvasElement.prototype.getContext = () => ({
    drawImage(source) {
      drawn = source;
    },
    // Synthetic pixels: the original is an RGB ramp, everything else a
    // checkerboard bit plane. Rows come back at native width, as in a browser.
    getImageData(x, y, width, height) {
      const data = new Uint8ClampedArray(width * height * 4);
      for (let row = 0; row < height; row++) {
        for (let col = 0; col < width; col++) {
          const at = 4 * (row * width + col);
          const rgb = drawn.url.includes("original") || drawn.url.includes("big_rgb")
            ? [(col * 7 + row) & 255, (col * 3) & 255, row & 255]
            : [((col ^ row) & 1) * 255, ((col ^ row) & 1) * 255, ((col ^ row) & 1) * 255];
          data.set([...rgb, 255], at);
        }
      }
      return { data };
    },
  });
  window.HTMLCanvasElement.prototype.toDataURL = (type) => {
    encodes += 1;
    return `data:${type || "image/png"};base64,QUJD`;
  };
  window.Image = class FakeImage {
    set src(value) {
      this.url = value;
      const side = value.includes("big") ? 512 : value.includes("original") ? 1600 : 64;
      this.naturalWidth = side;
      this.naturalHeight = value.includes("big") ? 512 : value.includes("original") ? 1200 : 64;
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
  facts.images.digestHasNoPixelValues = !JSON.stringify(withImages).includes("PIXEL VALUES");

  // One conversation per call: the boxes as given, the provider's first answer
  // as given, every later one a plain stream.
  async function converse({ images, pixels, first }) {
    byId("ai-reset").click();
    byId("ai-send-images").checked = images;
    byId("ai-send-pixels").checked = pixels;
    const seen = [];
    window.fetch = (url, options) => {
      seen.push(JSON.parse(options.body));
      return first && seen.length === 1 ? first() : streamResponse(tokenFrames(["ok"]));
    };
    byId("ai-ask").click();
    await settle(300);
    return seen;
  }
  const firstTurn = (seen) => seen[0].messages[1].content;
  const digestOf = (content) =>
    typeof content === "string"
      ? content
      : content.filter((part) => part.type === "text").map((part) => part.text).join("\n");
  const sectionOf = (digest) => {
    const start = digest.indexOf("## PIXEL VALUES");
    return start === -1 ? "" : digest.slice(start, digest.indexOf("\n## ANALYZER OUTPUT"));
  };

  // #287: OpenRouter answers 404 to image parts for a text-only model.
  const notFound = () =>
    Promise.resolve({
      ok: false,
      status: 404,
      headers: { get: () => "application/json" },
      text: () => Promise.resolve('{"error":{"message":"No endpoints found that support image input"}}'),
    });
  const refused = await converse({ images: true, pixels: false, first: notFound });
  facts.notFound = {
    requests: refused.length,
    firstHadImages: Array.isArray(firstTurn(refused)),
    retryIsPlainText: typeof refused[1].messages[1].content === "string",
    retrySaysWhy: refused[1].messages[1].content.includes("[images were not attached: the model rejected them]"),
    answer: byId("ai-answer").textContent,
  };

  // Images off: no image part, no canvas encoding, a plain string.
  const encodesBefore = encodes;
  const imagesOff = await converse({ images: false, pixels: false });
  const offTurn = firstTurn(imagesOff);
  facts.imagesOff = {
    requests: imagesOff.length,
    isPlainString: typeof offTurn === "string",
    hasNoImagePart: !JSON.stringify(imagesOff).includes("image_url"),
    saysZeroAttached: digestOf(offTurn).includes("## IMAGES ATTACHED (0)"),
    saysWhy: digestOf(offTurn).includes("- none: disabled in the panel"),
    toolsStillNameTheirImages: digestOf(offTurn).includes("images (not attached): Red_bit_0.png, Red_bit_1.png"),
    canvasEncodes: encodes - encodesBefore,
    noPixelValues: !digestOf(offTurn).includes("PIXEL VALUES"),
  };

  // Matrix on, images on: the section sits between IMAGES and ANALYZER OUTPUT.
  const both = await converse({ images: true, pixels: true });
  const bothDigest = digestOf(firstTurn(both));
  const bothSection = sectionOf(bothDigest);
  const blocks = bothSection.split("\n### ").slice(1);
  facts.pixelValues = {
    hasImageParts: firstTurn(both).some((part) => part.type === "image_url"),
    sections: (bothDigest.match(/^## .*$/gm) || []).map((line) => line.replace(/\s*\(.*\)$/, "")),
    headers: blocks.map((block) => block.split("\n")[0]),
    planeFirstRow: blocks[1].split("\n")[2],
    originalFirstRow: blocks[0].split("\n")[2].slice(0, 28),
    originalMarker: blocks[0].match(/\[\.\.\. \d+ pixels omitted \.\.\.\]/)?.[0],
    planeMarker: blocks[1].match(/\[\.\.\. \d+ pixels omitted \.\.\.\]/)?.[0],
    sectionChars: bothSection.length,
    isFenced: blocks.every((block) => block.includes("```text\n")),
  };

  // Matrix only: the text-only use case, a plain string that still has pixels.
  const only = await converse({ images: false, pixels: true });
  facts.pixelsOnly = {
    isPlainString: typeof firstTurn(only) === "string",
    hasSection: firstTurn(only).includes("## PIXEL VALUES (UNTRUSTED DATA)"),
    saysImagesDisabled: firstTurn(only).includes("- none: disabled in the panel"),
    status: byId("ai-status").textContent,
  };

  // The browser path: bytes re-read same-origin, decoded without premultiplying
  // alpha or converting colours. jsdom has no createImageBitmap; stub it.
  const decodes = [];
  window.createImageBitmap = (blob, options) => {
    decodes.push({ blob, options });
    return Promise.resolve({ width: 64, height: 64, url: blob.url, close() {} });
  };
  const reread = [];
  byId("ai-reset").click();
  byId("ai-send-images").checked = false;
  byId("ai-send-pixels").checked = true;
  window.fetch = (url, options) => {
    if (!String(url).startsWith("https://")) {
      reread.push({ url: String(url), credentials: options && options.credentials });
      return Promise.resolve({ blob: () => Promise.resolve({ url: String(url) }) });
    }
    return streamResponse(tokenFrames(["ok"]));
  };
  byId("ai-ask").click();
  await settle(300);
  delete window.createImageBitmap;
  facts.bitmapPath = {
    decodedWithoutPremultiply: decodes.length > 0 && decodes.every(
      (call) => call.options.premultiplyAlpha === "none" && call.options.colorSpaceConversion === "none",
    ),
    rereadsAreRelative: reread.length > 0 && reread.every((call) => !/^[a-z]+:/.test(call.url)),
    stillAnswers: byId("ai-answer").textContent.endsWith("ok"),
  };

  // Size: a 512x512 RGB original alone, then a 512x512 bit plane alone.
  async function sizeOf(url, kind) {
    window.parseResult({
      ...results,
      decomposer: { status: "ok", images: kind === "audio" ? { Red: [url] } : {} },
    });
    window.APERISOLVE_INFO = { ...window.APERISOLVE_INFO, kind, image_path: url, names: ["big.png"] };
    const seen = await converse({ images: false, pixels: true });
    return sectionOf(digestOf(firstTurn(seen)));
  }
  const rgbSection = await sizeOf("image/big_rgb.png", "image");
  const planeSection = await sizeOf("/image/h/big_plane.png", "audio");
  facts.size = {
    rgbChars: rgbSection.length,
    rgbHeader: rgbSection.split("\n")[1],
    planeChars: planeSection.length,
    planeHeader: planeSection.split("\n")[1],
  };

  // Many images: the whole matrix stays under 64 KiB and names what it drops.
  window.parseResult({
    ...results,
    decomposer: {
      status: "ok",
      images: { Red: Array.from({ length: 20 }, (_, i) => `/image/h/Red_bit_${i}.png`) },
    },
  });
  window.APERISOLVE_INFO = {
    ...window.APERISOLVE_INFO,
    kind: "image",
    image_path: "image/original.png",
    names: ["secret.png"],
  };
  const crowded = sectionOf(digestOf(firstTurn(await converse({ images: false, pixels: true }))));
  const crowdedBlocks = crowded.split("\n### ").slice(1);
  facts.crowded = {
    sectionChars: crowded.length,
    blocks: crowdedBlocks.length,
    omittedMarker: crowded.match(/\[\.\.\. \d+ images omitted for size: [^\]]*\.\.\.\]/)?.[0] || "",
  };

  process.stdout.write(JSON.stringify(facts, null, 1));
})().catch((error) => {
  process.stderr.write(`${error && error.stack}\n`);
  process.exit(1);
});
