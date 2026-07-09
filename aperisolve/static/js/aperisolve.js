// Injected by base.html from the backend analyzer registry; the literal
// list is only a fallback for pages served without the injection.
const TOOL_ORDER = window.TOOL_ORDER || [
  "decomposer",
  "spectrogram",
  "color_remapping",
  "file",
  "pdfinfo",
  "pdfid",
  "exiftool",
  "binwalk",
  "foremost",
  "outguess",
  "pngcheck",
  "pcrt",
  "identify",
  "steghide",
  "jpseek",
  "jsteg",
  "openstego",
  "zsteg",
  "strings"
];

function escapeHtml(text) {
  if (typeof text !== "string") return text;
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Translation lookup: window.I18N is injected by base.html; the English
// string doubles as the key and the fallback.
function t(text) {
  return (window.I18N && window.I18N[text]) || text;
}

function capitalize(str) {
  if (typeof str !== "string" || str.length === 0) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function slideUp(element, duration = 400) {
  element.style.height = element.offsetHeight + "px";
  element.offsetHeight; // force reflow
  element.style.transitionProperty = "height, margin, padding";
  element.style.transitionDuration = duration + "ms";
  element.style.boxSizing = "border-box";
  element.style.overflow = "hidden";
  element.style.height = 0;
  element.style.paddingTop = 0;
  element.style.paddingBottom = 0;
  element.style.marginTop = 0;
  element.style.marginBottom = 0;

  window.setTimeout(() => {
    element.style.display = "none";
    // Optional: reset styles
    element.style.removeProperty("height");
    element.style.removeProperty("padding-top");
    element.style.removeProperty("padding-bottom");
    element.style.removeProperty("margin-top");
    element.style.removeProperty("margin-bottom");
    element.style.removeProperty("overflow");
    element.style.removeProperty("transition-duration");
    element.style.removeProperty("transition-property");
  }, duration);
}

function formatBytes(bytes) {
  if (typeof bytes !== "number" || isNaN(bytes)) return bytes;
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return `${bytes % 1 === 0 ? bytes : bytes.toFixed(2)} ${units[i]}`;
}

/**
 * Alert functions
 */

function showAlert(message, alertType, reset) {
  const resultDiv = document.getElementById("result-analyzers");
  if (reset) {
    resultDiv.innerHTML = "";
  }
  resultDiv.innerHTML += `<div class="alert alert-${escapeHtml(
    alertType
  )}" role="alert">${escapeHtml(message)}</div>`;
}

function showSuccess(message, reset) {
  showAlert(message, "success", reset);
}
function showDanger(message, reset) {
  showAlert(message, "danger", reset);
}
function showWarning(message, reset) {
  showAlert(message, "warning", reset);
}
function showInfo(message, reset) {
  showAlert(message, "info", reset);
}

/**
 * Copy to clipboard
 */

document.addEventListener('click', function (event) {
  // Check if the clicked element is a copy icon
  if (event.target.classList.contains('copy-icon')) {
    const icon = event.target;
    const codeContainer = icon.closest('.code-container');
    const codeBlock = codeContainer ? codeContainer.querySelector('code') : null;

    if (codeBlock) {
      const textToCopy = codeBlock.textContent;
      navigator.clipboard.writeText(textToCopy).then(() => {
        icon.classList.remove('fa-copy');
        icon.classList.add('fa-check');
        setTimeout(() => {
          icon.classList.remove('fa-check');
          icon.classList.add('fa-copy');
        }, 1500);
      });
    }
  }
});

/**
 * Image preview functions
 */

// Reference the modal elements
const modal = document.getElementById("image-modal-container");
const modalImage = document.getElementById("modal-image");

let currentImages = [];
let currentIndex = -1;

function updateCurrentImages() {
  currentImages = Array.from(document.querySelectorAll(".results_img img"));
}

// Function to handle image click (open modal)
function openImageModal(src) {
  updateCurrentImages();
  currentIndex = currentImages.findIndex((img) => img.src === src);
  if (currentIndex !== -1) {
    modalImage.src = currentImages[currentIndex].src;
    modalImage.alt = currentImages[currentIndex].alt || "";
    modal.classList.add("modal-visible");
    modal.classList.remove("modal-hidden");
  }
}

function closeImageModal() {
  modal.classList.remove("modal-visible");
  modal.classList.add("modal-hidden");
  currentIndex = -1;
}

// Handle dynamic images added with innerHTML
document.addEventListener("click", function (e) {
  const img = e.target.closest(".results_img img");
  if (img) {
    openImageModal(img.src);
  }
});

// Click on modal image to download and close
modalImage.addEventListener("click", function () {
  const link = document.createElement("a");
  link.href = modalImage.src;
  link.download = modalImage.src.split("/").pop();
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  closeImageModal();
});

// Optional: Close modal if user clicks outside the image
modal.addEventListener("click", function (e) {
  if (e.target === modal) {
    closeImageModal();
  }
});

// Keyboard support
document.addEventListener("keydown", function (e) {
  if (!modal.classList.contains("modal-visible")) return;

  if (e.key === "Escape") {
    closeImageModal();
  } else if (e.key === "ArrowLeft") {
    // Show previous image
    if (currentIndex > 0) {
      currentIndex--;
      modalImage.src = currentImages[currentIndex].src;
    }
  } else if (e.key === "ArrowRight") {
    // Show next image
    if (currentIndex < currentImages.length - 1) {
      currentIndex++;
      modalImage.src = currentImages[currentIndex].src;
    }
  }
});

// Build the type-appropriate original-file preview shown in the info panel.
// The upload can now be any file, so branch on the backend-detected kind:
// image -> <img>, audio -> player, everything else -> a download file card.
// The default is ALWAYS the file card, never a bare <img>, so an unknown or
// non-image upload cannot render a broken image.
function renderMainPreview(infoData) {
  const src = escapeHtml(infoData.image_path);
  const rawName =
    (Array.isArray(infoData.names) && infoData.names[0]) ||
    String(infoData.image_path || "").split("/").pop();
  const fileName = escapeHtml(rawName);

  if (infoData.kind === "image") {
    return `<img src="${src}" alt="${t("Analyzed file")}"/>`;
  }
  if (infoData.kind === "audio") {
    return `<audio controls preload="metadata" src="${src}"></audio>`;
  }
  const icon = infoData.kind === "pdf" ? "fa-file-pdf" : "fa-file";
  return (
    `<div class="file-card">` +
    `<i class="fa ${icon} file-card-icon"></i>` +
    `<span class="file-card-name"><code>${fileName}</code></span>` +
    `<a href="${src}" class="btn btn-primary mt-2" download>` +
    `<i class="fa fa-download"></i> ${t("Download file")}</a>` +
    `</div>`
  );
}

async function fetchImageInfo(submission_hash) {
  let infoData;
  try {
    const infoResp = await fetch(`/infos/${submission_hash}`);
    if (!infoResp.ok) throw new Error(`HTTP ${infoResp.status}`);
    infoData = await infoResp.json();
  } catch (error) {
    // The info panel is auxiliary: a transient failure must not break the page.
    console.error("Failed to load image info:", error);
    return;
  }

  const resultInfosDiv = document.getElementById("result-infos");
  resultInfosDiv.innerHTML = ""; // Clear previous info

  const mainImgLeft = document.createElement("div");
  const mainImgRight = document.createElement("div");
  const tableInfos = document.createElement("table");
  mainImgLeft.id = "main-img-left";
  mainImgRight.id = "main-img-right";
  resultInfosDiv.appendChild(mainImgLeft);
  resultInfosDiv.appendChild(mainImgRight);
  mainImgRight.appendChild(tableInfos);

  mainImgLeft.innerHTML += `<div id="main_image">${renderMainPreview(infoData)}</div>`;
  tableInfos.innerHTML += `<tr><td><i class="fa fa-backward-step"></i> ${t("First upload:")}</td><td>${infoData.first_submission_date}</td></tr>`;
  tableInfos.innerHTML += `<tr><td><i class="fa fa-history"></i> ${t("Last upload:")}</td><td>${infoData.last_submission_date}</td></tr>`;
  if (Array.isArray(infoData.names)) {
    const nameList = infoData.names
      .map((name) => `<code>${escapeHtml(name)}</code>`)
      .join(", ");
    tableInfos.innerHTML += `<tr><td><i class="fa fa-list"></i> ${t("Name(s):")}</td><td>${nameList}</td></tr>`;
  }
  tableInfos.innerHTML += `<tr><td><i class="fa fa-balance-scale"></i> ${t("Size:")}</td><td>${formatBytes(
    infoData.size
  )}</td></tr>`;
  tableInfos.innerHTML += `<tr><td><i class="fa fa-upload"></i> ${t("Upload count:")}</td><td>${infoData.upload_count}</td></tr>`;
  if (Array.isArray(infoData.passwords) && infoData.passwords.length > 0) {
    await displayPasswordsWithRemoval(tableInfos, infoData.passwords, submission_hash, infoData);
  }

  // Fetch removal status and update removal UI
  await updateRemovalUI(submission_hash, infoData);
}

async function displayPasswordsWithRemoval(tableInfos, passwords, submission_hash, infoData) {
  const tr = document.createElement("tr");
  const tdLabel = document.createElement("td");
  const tdContent = document.createElement("td");

  tdLabel.innerHTML = `<i class="fa fa-key"></i> ${t("Common password(s):")}`;
  tr.appendChild(tdLabel);
  tr.appendChild(tdContent);
  tableInfos.appendChild(tr);

  // Clear existing password timer if any
  if (passwordTimerIntervals[submission_hash]) {
    clearInterval(passwordTimerIntervals[submission_hash]);
    delete passwordTimerIntervals[submission_hash];
  }

  const uploadTime = infoData.submission_date * 1000;
  const currentTime = new Date().getTime();
  const ageSeconds = Math.floor((currentTime - uploadTime) / 1000);
  const REMOVAL_MIN_AGE_SECONDS = infoData.removal_min_age_seconds || 300;

  for (const pwd of passwords) {
    const passwordSpan = document.createElement("span");
    passwordSpan.className = "password-item";
    passwordSpan.innerHTML = `<code>${escapeHtml(pwd)}</code>`;

    // Check if this password can be removed
    const canRemove = ageSeconds >= REMOVAL_MIN_AGE_SECONDS;

    if (canRemove) {
      const deleteIcon = document.createElement("i");
      deleteIcon.className = "fas fa-times password-delete-icon";
      deleteIcon.title = t("Remove password");
      deleteIcon.dataset.submissionHash = submission_hash;
      deleteIcon.dataset.password = pwd;
      deleteIcon.style.cursor = "pointer";
      deleteIcon.style.marginLeft = "5px";
      deleteIcon.style.color = "#ff4d4d";

      deleteIcon.addEventListener("click", async function() {
        await handlePasswordRemoval(submission_hash, deleteIcon);
      });

      passwordSpan.appendChild(deleteIcon);
    }

    tdContent.appendChild(passwordSpan);
    tdContent.appendChild(document.createTextNode(" "));
  }

  // Set up timer to refresh when passwords become eligible for removal
  if (ageSeconds < REMOVAL_MIN_AGE_SECONDS) {
    const remainingSeconds = REMOVAL_MIN_AGE_SECONDS - ageSeconds;
    passwordTimerIntervals[submission_hash] = setInterval(async () => {
      const newUploadTime = infoData.submission_date * 1000;
      const newCurrentTime = new Date().getTime();
      const newAgeSeconds = Math.floor((newCurrentTime - newUploadTime) / 1000);

      if (newAgeSeconds >= REMOVAL_MIN_AGE_SECONDS) {
        // Time has elapsed, refresh the password display
        clearInterval(passwordTimerIntervals[submission_hash]);
        delete passwordTimerIntervals[submission_hash];

        // Re-fetch info and refresh display
        const infoResp = await fetch(`/infos/${submission_hash}`);
        const newInfoData = await infoResp.json();

        // Clear and rebuild password row
        tr.remove();
        await displayPasswordsWithRemoval(tableInfos, newInfoData.passwords, submission_hash, newInfoData);
      }
    }, Math.min(remainingSeconds * 1000, 1000)); // Check every second or at the exact time
  }
}

async function checkPasswordRemovalEligibility(submission_hash, password, infoData) {
  try {
    // Check age constraint using submission date, not first_submission_date
    const uploadTime = infoData.submission_date * 1000; // Convert to milliseconds
    const currentTime = new Date().getTime();
    const ageSeconds = Math.floor((currentTime - uploadTime) / 1000);
    const REMOVAL_MIN_AGE_SECONDS = infoData.removal_min_age_seconds || 300;

    if (ageSeconds < REMOVAL_MIN_AGE_SECONDS) {
      return false;
    }
    return true;
  } catch (error) {
    console.error("Error checking password removal eligibility:", error);
    return false;
  }
}

async function handlePasswordRemoval(submission_hash, iconElement) {
  try {
    iconElement.style.pointerEvents = "none";
    iconElement.style.opacity = "0.5";

    const response = await fetch(`/remove_password/${submission_hash}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      // Remove the password item from display
      const passwordSpan = iconElement.closest(".password-item");
      if (passwordSpan) {
        passwordSpan.style.transition = "opacity 0.3s";
        passwordSpan.style.opacity = "0";
        setTimeout(() => passwordSpan.remove(), 300);
      }
    } else {
      // Silently fail - just re-enable the icon
      iconElement.style.pointerEvents = "auto";
      iconElement.style.opacity = "1";
    }
  } catch (error) {
    console.error("Password removal error:", error);
    iconElement.style.pointerEvents = "auto";
    iconElement.style.opacity = "1";
  }
}

/**
 * Image removal functionality
 */

let removalTimerIntervals = {};
let passwordTimerIntervals = {};

async function updateRemovalUI(submission_hash, infoData) {
  const resultRemovalDiv = document.getElementById("result-removal");
  resultRemovalDiv.innerHTML = "";

  try {

    // Extract upload timestamp from first_submission_date
    const uploadTime = new Date(infoData.first_submission_date).getTime();
    const currentTime = new Date().getTime();
    const ageSeconds = Math.floor((currentTime - uploadTime) / 1000);
    const REMOVAL_MIN_AGE_SECONDS = infoData.removal_min_age_seconds || 300;

    const removalContainer = document.createElement("div");
    removalContainer.className = "card removal-card";
    resultRemovalDiv.appendChild(removalContainer);

    if (ageSeconds < REMOVAL_MIN_AGE_SECONDS) {
      const remainingSeconds = REMOVAL_MIN_AGE_SECONDS - ageSeconds;
      removalContainer.innerHTML = `
        <h3><i class="fa fa-trash"></i> ${t("Remove Image")}</h3>
        <p>${t("Available in {s} seconds").replace("{s}", `<span id="removal-countdown">${remainingSeconds}</span>`)}</p>
        <button class="btn btn-primary" disabled id="remove-btn">${t("Remove Image")}</button>
      `;

      // Clear existing interval if any
      if (removalTimerIntervals[submission_hash]) {
        clearInterval(removalTimerIntervals[submission_hash]);
      }

      // Start countdown timer
      removalTimerIntervals[submission_hash] = setInterval(() => {
        const countdownEl = document.getElementById("removal-countdown");
        if (countdownEl) {
          const current = parseInt(countdownEl.textContent);
          if (current > 1) {
            countdownEl.textContent = current - 1;
          } else {
            clearInterval(removalTimerIntervals[submission_hash]);
            updateRemovalUI(submission_hash, infoData);
          }
        }
      }, 1000);
    } else {
      // Check for multiple IPs - we'll do this by attempting removal
      removalContainer.innerHTML = `
        <h3><i class="fa fa-trash"></i> ${t("Remove Image")}</h3>
        <button class="btn btn-primary" id="remove-btn">${t("Remove Image")}</button>
        <p id="removal-status"></p>
      `;

      const removeBtn = document.getElementById("remove-btn");
      removeBtn.addEventListener("click", async () => {
        removeBtn.disabled = true;
        const statusEl = document.getElementById("removal-status");

        try {
          const response = await fetch(`/remove/${submission_hash}`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
          });

          const data = await response.json();

          if (response.ok) {
            statusEl.innerHTML = `<span class="text-success"><i class="fa fa-check"></i> ${t("Image successfully removed")}</span>`;
            removeBtn.style.display = "none";
            setTimeout(() => { document.location = '/'; }, 2000);
          } else if (response.status === 403) {
            if (data.error.includes("multiple IP")) {
              statusEl.innerHTML = `<span class="text-danger"><i class="fa fa-warning"></i> ${escapeHtml(data.error)}</span>`;
            } else {
              statusEl.innerHTML = `<span class="text-danger"><i class="fa fa-warning"></i> ${escapeHtml(data.error)}</span>`;
            }
            removeBtn.disabled = false;
          } else {
            statusEl.innerHTML = `<span class="text-danger"><i class="fa fa-exclamation-circle"></i> ${t("Error:")} ${escapeHtml(data.error)}</span>`;
            removeBtn.disabled = false;
          }
        } catch (error) {
          statusEl.innerHTML = `<span class="text-danger"><i class="fa fa-exclamation-circle"></i> ${t("Network error occurred")}</span>`;
          removeBtn.disabled = false;
          console.error("Removal error:", error);
        }
      });
    }
  } catch (error) {
    console.error("Error updating removal UI:", error);
  }
}

/**
 * Parsing results from the server
 */

const WIKI_TOOLS = window.WIKI_TOOLS || [];
const LANG_PREFIX = window.LANG_PREFIX || "";

// Analyzer heading: links to the tool's wiki guide when one exists.
function analyzerTitle(tool) {
  const label = capitalize(tool.replace("_", " "));
  if (WIKI_TOOLS.includes(tool)) {
    return `<a class="analyzer-title-link" href="${LANG_PREFIX}/wiki/tools/${tool}"
      title="${t("Learn more")}">${label} <i class="fa fa-book-open fa-2xs"></i></a>`;
  }
  return label;
}

// Spinner shown between upload and the first results.
function renderAnalyzing() {
  const resultDiv = document.getElementById("result-analyzers");
  if (resultDiv.querySelector(".analyzer")) return; // results already streaming in
  resultDiv.innerHTML =
    `<div class="analyzing" role="status" aria-live="polite">` +
    `<span class="spinner" aria-hidden="true"></span>` +
    `<p class="mb-0">${t("Analyzing your file…")}</p></div>`;
}

function parseResult(result) {
  const resultDiv = document.getElementById("result-analyzers");
  resultDiv.innerHTML = "";

  for (const tool of TOOL_ORDER) {
    if (!Object.keys(result).includes(tool)) {
      // Skip if the tool is not in the result
      continue;
    }

    const analyzer = document.createElement("div");
    analyzer.className = `analyzer a-${escapeHtml(tool)}`;
    resultDiv.appendChild(analyzer);

    const ok = result[tool]["status"] === "ok";
    const badge = ok
      ? `<span class="analyzer-badge badge-ok"><i class="fa fa-check"></i> ${t("Success")}</span>`
      : `<span class="analyzer-badge badge-empty"><i class="fa fa-minus"></i> ${t("No result")}</span>`;
    analyzer.innerHTML += `<div class="analyzer-header"><h2>${analyzerTitle(tool)}</h2>${badge}</div>`;

    // Parse text output
    if (typeof result[tool]["output"] === "string") {
      const output = escapeHtml(result[tool]["output"]);
      analyzer.innerHTML += `<div class="alert alert-success" role="alert">${output}</div>`;
    } else if (Array.isArray(result[tool]["output"])) {
      if (result[tool]["output"].length > 0) {
        var code_content = `<div class="code-container position-relative mb-2">`;
        code_content += `<pre class="mb-0"><code>`;
        code_content += result[tool]["output"].map(line => escapeHtml(line)).join('\n').trim();
        code_content += `</code></pre>`;
        code_content += `<i class="fas fa-copy copy-icon"></i>`;
        code_content += `</div>`;
        analyzer.innerHTML += code_content;
      }
    } else if (typeof result[tool]["output"] === "object") {
      var table_content = `<div class="table-container">`;
      table_content += `<table>`;
      for (const key in result[tool]["output"]) {
        table_content += `<tr><td>${escapeHtml(key)}</td>`;
        table_content += `<td>${escapeHtml(
          result[tool]["output"][key]
        )}</td></tr>`;
      }
      table_content += `</table>`;
      table_content += `</table>`;
      analyzer.innerHTML += table_content;
    }

    // Parse images, downloads, ...
    if (result[tool]["status"] === "ok") {
      if ("images" in result[tool]) {
        // Channel labels come from the analyzer's own dict keys. Only the
        // decomposer/color_remapping RGB(A) sets get the canonical
        // Superimposed,Red,Green,Blue,(Alpha) ordering; every other analyzer
        // (e.g. the spectrogram's {Spectrogram, Waveform}) iterates its keys
        // as-is — which also fixes a 2-key dict previously rendering nothing.
        const imageKeys = Object.keys(result[tool]["images"]);
        const RGBA = ["Superimposed", "Red", "Green", "Blue", "Alpha"];
        const RGB = ["Superimposed", "Red", "Green", "Blue"];
        let channels = imageKeys;
        if (imageKeys.length === RGBA.length && RGBA.every((c) => imageKeys.includes(c))) {
          channels = RGBA;
        } else if (imageKeys.length === RGB.length && RGB.every((c) => imageKeys.includes(c))) {
          channels = RGB;
        }

        let title_h3 = "";
        for (const channel of channels) {
          const images = result[tool]["images"][channel];
          if (images) {
            title_h3 = capitalize(escapeHtml(channel));
            if (title_h3 != "Color Remapping"){
              analyzer.innerHTML += `<h3>${t(title_h3)}</h3>`;
            }
            for (const image of images) {
              analyzer.innerHTML += `<div class='results_img'><img src='${escapeHtml(
                image
              )}' alt='${escapeHtml(tool + " " + channel)}' loading='lazy'/></div>`;
            }
          }
        }
      }

      if ("image" in result[tool]) {
        // Parse image output
        analyzer.innerHTML += `<div class='results_img'><img src='${escapeHtml(
          result[tool]["image"]
        )}' alt='${escapeHtml(tool)}' loading='lazy'/></div>`;
      }

      if ("png_images" in result[tool]) {
        for (const image of result[tool]["png_images"]) {
          analyzer.innerHTML += `<div class='results_img'><img src='${escapeHtml(image)}' alt='${escapeHtml(tool)}' loading='lazy'/></div>`;
        }
      }

      if ("download" in result[tool]) {
        // Parse download link
        analyzer.innerHTML += `<br/><a href="${escapeHtml(
          result[tool]["download"]
        )}" target="_blank" class="btn btn-primary mt-2"><i class="fa fa-download"></i> ${t("Download file")}</a>`;
      }
    }

    // Render error and note inside the analyzer's own section (previously
    // these were appended as detached alerts, disconnected from the heading).
    if (result[tool]["error"] && (/[^\s]/.test(result[tool]["error"]))) {
      analyzer.innerHTML +=
        `<div class="alert alert-danger mb-0" role="alert">` +
        `<pre class="mb-0">${escapeHtml(result[tool]["error"].trim())}</pre></div>`;
    }

    if (result[tool]["note"] && (/[^\s]/.test(result[tool]["note"]))) {
      analyzer.innerHTML +=
        `<div class="alert alert-info mb-0 mt-2" role="alert">` +
        `${escapeHtml(result[tool]["note"].trim())}</div>`;
    }
  }
}

// Poll status of a submission. Polls are sequential (the next one is only
// scheduled after the current one finishes, so they can never stack), back
// off gently, and give up after a hard cap instead of hammering forever.
const POLL_START_INTERVAL_MS = 1000;
const POLL_MAX_INTERVAL_MS = 10000;
const POLL_MAX_TOTAL_MS = 15 * 60 * 1000; // longer than any RQ job timeout

function scheduleNextPoll(submission_hash, startedAt, interval) {
  if (Date.now() - startedAt > POLL_MAX_TOTAL_MS) {
    showDanger(t("❌ The analysis is taking too long. Please reload the page to check again."), true);
    return;
  }
  const next = Math.min(interval * 1.2, POLL_MAX_INTERVAL_MS);
  setTimeout(() => pollStatus(submission_hash, startedAt, next), interval);
}

async function pollStatus(submission_hash, startedAt, interval) {
  if (!window.location.pathname.endsWith(`/${submission_hash}`)) {
    window.history.pushState({}, "", `/${submission_hash}`);
  }
  startedAt = startedAt || Date.now();
  interval = interval || POLL_START_INTERVAL_MS;
  renderAnalyzing();

  let statusData;
  try {
    const statusResp = await fetch(`/status/${submission_hash}`);
    statusData = await statusResp.json();
  } catch (error) {
    // Network blip: keep the spinner and retry instead of dying silently.
    console.dir(error);
    scheduleNextPoll(submission_hash, startedAt, interval);
    return;
  }

  if (statusData.status === "completed") {
    let resultData;
    try {
      const resultResp = await fetch(`/result/${submission_hash}`);
      resultData = await resultResp.json();
    } catch (error) {
      console.dir(error);
      scheduleNextPoll(submission_hash, startedAt, interval);
      return;
    }
    fetchImageInfo(submission_hash);
    if ("error" in resultData) {
      showWarning(`❌ ${resultData.error}`, true);
    } else if ("results" in resultData) {
      parseResult(resultData.results);
    }
  } else if (statusData.status === "error") {
    showDanger(t("❌ Error during the analysis."), true);
  } else {
    // Render partial results while the analysis is still running.
    try {
      const resultResp = await fetch(`/result/${submission_hash}`);
      const resultData = await resultResp.json();
      if ("results" in resultData) {
        fetchImageInfo(submission_hash);
        parseResult(resultData.results);
      } else {
        renderAnalyzing();
      }
    } catch (error) {
      renderAnalyzing();
      console.dir(error);
    }
    scheduleNextPoll(submission_hash, startedAt, interval);
  }
}

/**
 * Drag and drop functionality
 */

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("image");
const browseBtn = document.getElementById("browse-btn");
const dragMsg = document.getElementById("drag-msg");

function showFilename(filename) {
  dragMsg.innerHTML = "📄 " + escapeHtml(filename);
}

if (browseBtn) {
  // Clicking the button triggers file input
  browseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });
  dropZone.addEventListener("click", () => {
    fileInput.click();
  });
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.boxShadow = "0 0 20px #9fef00";
  });
  dropZone.addEventListener("dragleave", () => {
    dropZone.style.boxShadow = "";
  });

  // Drag events
  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
    });
  });

  // Drop file
  dropZone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      fileInput.files = files; // Attach files to the hidden input
      showFilename(fileInput.files[0].name);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      showFilename(fileInput.files[0].name);
    }
  });

  // File upload Form submission

  document
    .getElementById("upload-form")
    .addEventListener("submit", function (e) {
      e.preventDefault();

      const fileInput = document.getElementById("image");
      const passwordInput = document.getElementById("password");
      const deepCheckbox = document.getElementById("deep");
      const progressContainer = document.getElementById("progress-container");
      const progressBar = document.getElementById("progress-bar");

      if (!fileInput.files.length) {
        showDanger(t("Please select a file."), true);
        return;
      }

      const formData = new FormData();
      formData.append("image", fileInput.files[0]);
      formData.append("password", passwordInput.value);
      formData.append("deep", deepCheckbox.checked);

      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/upload", true);

      xhr.upload.addEventListener("loadstart", () => {
        progressContainer.classList.remove("d-none");
        progressBar.style.width = "0%";
        progressBar.textContent = "0%";
      });

      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          progressBar.style.width = percent + "%";
          progressBar.textContent = percent + "%";
        }
      });

      xhr.onload = () => {
        if (xhr.status === 200) {
          try {
            const response = JSON.parse(xhr.responseText);
            if (response.submission_hash) {
              pollStatus(response.submission_hash);
            } else {
              showDanger(
                t("❌ Invalid server response: missing submission_hash."),
                true
              );
            }
          } catch (e) {
            showDanger(t("❌ Invalid server response."), true);
          }
        } else if (xhr.status == 413) {
          showDanger(t("❌ File too large. Please upload a smaller file."), true);
        } else {
          showDanger(`${t("❌ HTTP error")} ${xhr.status}`, true);
        }
        progressBar.style.width = "100%";
        progressBar.textContent = t("Upload complete");
        const uploadForm = document.getElementById("upload-form");
        slideUp(uploadForm);
      };

      xhr.onerror = () => {
        showDanger(t("❌ An error occurred during the transfer"), true);
      };

      xhr.send(formData);
    });
}

/**
 * Wiki search
 *
 * Lazy-fetches /wiki/search.json on the first keystroke, then does dependency-free
 * tokenized substring ranking (title > description > heading > body). No-op off
 * the wiki (the input/results elements only exist there).
 */
function initWikiSearch() {
  const input = document.getElementById("wiki-search");
  const box = document.getElementById("wiki-search-results");
  if (!input || !box) return;
  let index = null;

  async function ensureIndex() {
    if (index) return index;
    const resp = await fetch(`${LANG_PREFIX}/wiki/search.json`);
    index = (await resp.json()).pages;
    return index;
  }

  function score(haystack, terms) {
    const hay = (haystack || "").toLowerCase();
    return terms.reduce((s, term) => s + (hay.includes(term) ? 1 : 0), 0);
  }

  function render(hits) {
    if (!hits.length) {
      box.innerHTML = `<div class="wiki-search-empty">${t("No results")}</div>`;
      return;
    }
    box.innerHTML = hits
      .slice(0, 8)
      .map((hit) => {
        const anchor = hit.heading ? `#${hit.heading.id}` : "";
        const label = hit.heading
          ? `${escapeHtml(hit.page.title)} <span class="wiki-search-sep">&rsaquo;</span> ${escapeHtml(hit.heading.title)}`
          : escapeHtml(hit.page.title);
        return `<a class="wiki-search-hit" href="${LANG_PREFIX}${hit.page.path}${anchor}">${label}</a>`;
      })
      .join("");
  }

  async function run() {
    const terms = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) {
      box.innerHTML = "";
      return;
    }
    const pages = await ensureIndex();
    const hits = [];
    for (const page of pages) {
      const pageScore =
        score(page.title, terms) * 5 +
        score(page.description, terms) * 2 +
        score(page.text, terms);
      if (pageScore) hits.push({ page, score: pageScore + 3 });
      for (const heading of page.headings) {
        const headingScore = score(heading.title, terms) * 4;
        if (headingScore) hits.push({ page, heading, score: headingScore });
      }
    }
    hits.sort((a, b) => b.score - a.score);
    render(hits);
  }

  let debounce;
  input.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(run, 120);
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".wiki-search")) box.innerHTML = "";
  });
}
initWikiSearch();

/* Cheatsheet "Tell → Tool" table: instant row filter (opt-in via #tell-tool-filter). */
(function initTellToolFilter() {
  const input = document.getElementById("tell-tool-filter");
  if (!input) return;
  const scope = input.closest(".wiki-article") || document;
  const table = Array.from(scope.querySelectorAll("table")).find(
    (t) => input.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING
  );
  if (!table) return;
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    rows.forEach((row) => {
      row.hidden = !!q && row.textContent.toLowerCase().indexOf(q) === -1;
    });
  });
})();

