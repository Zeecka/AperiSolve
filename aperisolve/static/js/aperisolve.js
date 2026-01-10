const TOOL_ORDER = [
  "decomposer",
  "file",
  "exiftool",
  "binwalk",
  "foremost",
  "outguess",
  "pngcheck",
  "pcrt",
  "steghide",
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
    const textarea = icon.closest('.textarea-container').querySelector('textarea');

    if (textarea) {
      textarea.select();
      navigator.clipboard.writeText(textarea.value).then(() => {
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

async function fetchImageInfo(submission_hash) {
  const infoResp = await fetch(`/infos/${submission_hash}`);
  const infoData = await infoResp.json();

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

  mainImgLeft.innerHTML += `<div id="main_image"><img src="${infoData.image_path}"/></div>`;
  tableInfos.innerHTML += `<tr><td><i class="fa fa-backward-step"></i> First upload:</td><td>${infoData.first_submission_date}</td></tr>`;
  tableInfos.innerHTML += `<tr><td><i class="fa fa-history"></i> Last upload:</td><td>${infoData.last_submission_date}</td></tr>`;
  if (Array.isArray(infoData.names)) {
    const nameList = infoData.names
      .map((name) => `<code>${escapeHtml(name)}</code>`)
      .join(", ");
    tableInfos.innerHTML += `<tr><td><i class="fa fa-list"></i> Name(s):</td><td>${nameList}</td></tr>`;
  }
  tableInfos.innerHTML += `<tr><td><i class="fa fa-balance-scale"></i> Size:</td><td>${formatBytes(
    infoData.size
  )}</td></tr>`;
  tableInfos.innerHTML += `<tr><td><i class="fa fa-upload"></i> Upload count:</td><td>${infoData.upload_count}</td></tr>`;
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

  tdLabel.innerHTML = '<i class="fa fa-key"></i> Common password(s):';
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
      deleteIcon.title = "Remove password";
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
        <h3><i class="fa fa-trash"></i> Remove Image</h3>
        <p>Available in <span id="removal-countdown">${remainingSeconds}</span> seconds</p>
        <button class="btn btn-primary" disabled id="remove-btn">Remove Image</button>
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
        <h3><i class="fa fa-trash"></i> Remove Image</h3>
        <button class="btn btn-primary" id="remove-btn">Remove Image</button>
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
            statusEl.innerHTML = `<span class="text-success"><i class="fa fa-check"></i> Image successfully removed</span>`;
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
            statusEl.innerHTML = `<span class="text-danger"><i class="fa fa-exclamation-circle"></i> Error: ${escapeHtml(data.error)}</span>`;
            removeBtn.disabled = false;
          }
        } catch (error) {
          statusEl.innerHTML = `<span class="text-danger"><i class="fa fa-exclamation-circle"></i> Network error occurred</span>`;
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

    analyzer.innerHTML += `<h2>${capitalize(tool.replace("_", " "))}</h2>`;

    // Parse text output
    if (typeof result[tool]["output"] === "string") {
      output = escapeHtml(result[tool]["output"]);
      analyzer.innerHTML += `<div class="alert alert-success" role="alert">${output}</div>`;
    } else if (Array.isArray(result[tool]["output"])) {
      if (result[tool]["output"].length > 0) {
        var texarea_content = `<div class="textarea-container">`;
        texarea_content += `<textarea class="form-control w-100 mb-2" rows="8" readonly>`;
        for (const line of result[tool]["output"]) {
          texarea_content += escapeHtml(`${line}\n`);
        }
        texarea_content = texarea_content.trim();
        texarea_content += `</textarea>`;
        texarea_content += `<i class="fas fa-copy copy-icon"></i>`;
        texarea_content += `</div>`;
        analyzer.innerHTML += texarea_content;
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
        // Parse image output
        var channels = ["Superimposed", "Red", "Green", "Blue", "Alpha"];
        if (Object.keys(result[tool]["images"]).length == 1) {
          channels = ["Grayscale"];
        } else if (Object.keys(result[tool]["images"]).length == 4) {
          channels = ["Superimposed", "Red", "Green", "Blue"];
        }

        for (const channel of channels) {
          const images = result[tool]["images"][channel];
          analyzer.innerHTML += `<h3>${capitalize(escapeHtml(channel))}</h3>`;
          for (const image of images) {
            analyzer.innerHTML += `<div class='results_img'><img src='${escapeHtml(
              image
            )}'/></div>`;
          }
        }
      }

      if ("image" in result[tool]) {
        // Parse image output
        analyzer.innerHTML += `<div class='results_img'><img src='${escapeHtml(
          result[tool]["image"]
        )}'/></div>`;
      }

      if ("png_images" in result[tool]) {
        for (const image of result[tool]["png_images"]) {
          analyzer.innerHTML += `<div class='results_img'><img src='${escapeHtml(image)}'/></div>`;
        }
      }

      if ("download" in result[tool]) {
        // Parse download link
        analyzer.innerHTML += `<br/><a href="${escapeHtml(
          result[tool]["download"]
        )}" target="_blank" class="btn btn-primary mt-2"><i class="fa fa-download"></i> Download file</a>`;
      }
    }

    if (result[tool]["error"] && (/[^\s]/.test(result[tool]["error"]))) {
      showDanger(result[tool]["error"]);
    }

    if (result[tool]["note"] && (/[^\s]/.test(result[tool]["note"]))) {
      showInfo(result[tool]["note"]);
    }
  }
}

// Poll status of a submission
async function pollStatus(submission_hash) {
  if (!window.location.pathname.endsWith(`/${submission_hash}`)) {
    window.history.pushState({}, "", `/${submission_hash}`);
  }
  const statusResp = await fetch(`/status/${submission_hash}`);
  const statusData = await statusResp.json();
  if (statusData.status === "completed") {
    const resultResp = await fetch(`/result/${submission_hash}`);
    const resultData = await resultResp.json();
    fetchImageInfo(submission_hash);
    if ("error" in resultData) {
      showWarning(`❌ ${resultData.error}`, true);
    } else if ("results" in resultData) {
      parseResult(resultData.results);
    }
  } else if (statusData.status === "error") {
    //resultDiv.innerHTML = "";
    showDanger("❌ Error during the analysis.", true);
  } else {
    setTimeout(() => pollStatus(submission_hash), 1000);
    try {
      const resultResp = await fetch(`/result/${submission_hash}`);
      const resultData = await resultResp.json();
      if ("error" in resultData) {
        // showWarning(`❌ ${resultData.error}`, true);
      } else if ("results" in resultData) {
        fetchImageInfo(submission_hash);
        parseResult(resultData.results);
      }
    } catch (error) {
      console.dir(error);
    }
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
  dragMsg.innerHTML = "🖼️ " + escapeHtml(filename);
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
        showDanger("Please select an image.", true);
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
                "❌ Invalid server response: missing submission_hash.",
                true
              );
            }
          } catch (e) {
            showDanger("❌ Invalid server response.", true);
          }
        } else if (xhr.status == 413) {
          showDanger("❌ File too large. Please upload a smaller file.", true);
        } else {
          showDanger(`❌ HTTP error ${xhr.status}`, true);
        }
        progressBar.style.width = "100%";
        progressBar.textContent = "Upload complete";
        const uploadForm = document.getElementById("upload-form");
        slideUp(uploadForm);
      };

      xhr.onerror = () => {
        showDanger("❌ An error occurred during the transfer", true);
      };

      xhr.send(formData);
    });
}
