"use strict";

const STORAGE_KEY = "sparring_state_v2";
const CORRUPT_KEY = "sparring_state_v2_recovery";
const DAY_MS = 86_400_000;
const REVIEW_DAYS = [1, 3, 7];
const LETTERS = ["A", "B", "C", "D"];
const MIN_MATERIAL_CHARS = 40;
const PDF_EXTRACTION_TIMEOUT_MS = 30 * 60_000;
const LIVE_AI_URL = "https://sparring-ai-study-coach.onrender.com/";
const IS_GITHUB_PAGES = window.location.hostname.endsWith(".github.io");
const STATIC_DEMO =
  IS_GITHUB_PAGES &&
  new URLSearchParams(window.location.search).get("staticDemo") === "1";

if (IS_GITHUB_PAGES && !STATIC_DEMO) {
  window.location.replace(LIVE_AI_URL);
}

const HOSTED_DEMO = STATIC_DEMO;

let demoEnginePromise = null;

function demoEngine() {
  if (!demoEnginePromise) demoEnginePromise = import("./demo-engine.mjs?v=7");
  return demoEnginePromise;
}

const app = document.getElementById("app");
const liveStatus = document.getElementById("live-status");
const saveStatus = document.getElementById("save-status");
const offlineBanner = document.getElementById("offline-banner");
const conflictBanner = document.getElementById("conflict-banner");
const loadNewerStateButton = document.getElementById("load-newer-state");
const resetButton = document.getElementById("reset-button");
const resetDialog = document.getElementById("reset-dialog");
const confirmReset = document.getElementById("confirm-reset");

const SAMPLE_MATERIAL = `Retrieval practice asks a learner to bring an idea back from memory before seeing the answer. The effort of trying makes later feedback more useful because the learner can compare an attempted answer with the source.

Confidence judgments add a second observation to each answer. A correct response with low confidence and an incorrect response with high confidence need different feedback, even when the quiz score alone looks similar.

Spaced practice returns to an idea after time has passed. A cold review changes the wording and removes hints, so the learner must reconstruct the relationship rather than recognize the original question. One, three, and seven days are a simple default schedule for this prototype, not a universal optimum.`;

function freshState() {
  return {
    version: 2,
    material: "",
    source: null,
    plan: null,
    planAccepted: false,
    current: 0,
    progress: {},
    queue: [],
    sessionComplete: false,
    sessionStartedAt: dateKey(new Date()),
    clockOffsetDays: 0,
    review: null,
    unsyncedEvidence: [],
    createdAt: new Date().toISOString(),
    lastSavedAt: null,
  };
}

let recoveryNotice = "";
let state = loadState();
let saveTimer = null;

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return freshState();
    const parsed = JSON.parse(raw);
    if (!parsed || parsed.version !== 2 || typeof parsed.material !== "string") {
      throw new Error("Unsupported saved state");
    }
    return { ...freshState(), ...parsed };
  } catch (_error) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) localStorage.setItem(CORRUPT_KEY, raw);
    } catch (_storageError) {
      // Continue in memory when browser storage is unavailable.
    }
    recoveryNotice =
      "A damaged saved session was set aside so the app could recover safely. You can start again below.";
    return freshState();
  }
}

function saveState(message = "Saved on this device") {
  state.lastSavedAt = new Date().toISOString();
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    saveStatus.textContent = message;
  } catch (_error) {
    saveStatus.textContent = "Could not save locally";
    announce("This browser could not save your latest changes.");
  }
}

function debouncedSave() {
  saveStatus.textContent = "Saving…";
  window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => saveState(), 300);
}

function esc(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      })[character],
  );
}

function announce(message) {
  liveStatus.textContent = "";
  window.setTimeout(() => {
    liveStatus.textContent = message;
  }, 30);
}

function setView(html, { focus = true } = {}) {
  app.innerHTML = html;
  resetButton.hidden = !state.plan;
  updateConnectivity();
  if (focus) {
    window.scrollTo({ top: 0, behavior: "instant" });
    const heading = document.getElementById("screen-title");
    if (heading) {
      document.title = `${heading.textContent.trim()} — Sparring`;
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    } else {
      app.focus({ preventScroll: true });
    }
  }
}

function dateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDateKey(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day, 12, 0, 0, 0);
}

function addDays(value, days) {
  const date = parseDateKey(value);
  date.setDate(date.getDate() + days);
  return dateKey(date);
}

function virtualToday() {
  return dateKey(new Date(Date.now() + state.clockOffsetDays * DAY_MS));
}

function formatDate(value) {
  if (!value) return "complete";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(parseDateKey(value));
}

function isDue(item) {
  return item.status === "scheduled" && item.dueAt && item.dueAt <= virtualToday();
}

function dueItems() {
  return state.queue
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => isDue(item));
}

function progressFor(index) {
  if (!state.progress[index]) {
    state.progress[index] = {
      prediction: "",
      predictionAt: null,
      lesson: null,
      lessonAcknowledged: false,
      quizResponses: [],
      pendingQuizResponse: null,
      teachbackAnswer: "",
      teachbackAttempts: 0,
      teachbackAssessment: null,
      completed: false,
    };
  }
  return state.progress[index];
}

function progressBar(label) {
  const segments = state.plan.concepts
    .map((_, index) => {
      const className =
        index < state.current ? "done" : index === state.current ? "active" : "";
      return `<div class="progress-segment ${className}" aria-hidden="true"><span></span></div>`;
    })
    .join("");
  return `
    <div
      class="progress-shell"
      role="progressbar"
      aria-label="Session concept progress"
      aria-valuemin="1"
      aria-valuemax="3"
      aria-valuenow="${Math.min(state.current + 1, 3)}"
      aria-valuetext="Concept ${Math.min(state.current + 1, 3)} of 3"
    >
      <div class="progress-meta">
        <span>${esc(label)}</span>
        <span>Concept ${Math.min(state.current + 1, 3)} of 3</span>
      </div>
      <div class="progress-track">${segments}</div>
    </div>`;
}

function errorPanel(error, retryId = "retry-action") {
  return `
    <div class="error-panel" role="alert">
      <p><strong>This step didn’t load.</strong></p>
      <p>${esc(error.message || "Please try again.")}</p>
      ${
        error.retryable !== false
          ? `<button id="${retryId}" class="button secondary" type="button">Retry this step</button>`
          : ""
      }
    </div>`;
}

class ApiError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.code = options.code || "request_failed";
    this.retryable = options.retryable !== false;
    this.status = options.status || 0;
  }
}

async function api(path, body, timeoutMs = 70_000) {
  if (HOSTED_DEMO) {
    const engine = await demoEngine();
    return engine.fixtureRequest(path, body);
  }
  if (!navigator.onLine) {
    throw new ApiError(
      "You’re offline. Your draft is safe; reconnect to generate this step.",
      { code: "offline", retryable: true },
    );
  }
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`/api/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new ApiError(payload.detail || "The request could not be completed.", {
        code: payload.code,
        retryable: payload.retryable,
        status: response.status,
      });
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError("The request took too long. Your progress is safe; retry this step.");
    }
    if (error instanceof ApiError) throw error;
    throw new ApiError("The server could not be reached. Your progress is safe in this browser.");
  } finally {
    window.clearTimeout(timeout);
  }
}

async function uploadPdf(file, { signal, onProgress } = {}) {
  if (!file || (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf")) {
    throw new ApiError("Choose a PDF file.", { code: "not_a_pdf", retryable: false });
  }
  if (file.size > 20 * 1024 * 1024) {
    throw new ApiError("Keep PDF files under 20 MB.", {
      code: "pdf_too_large",
      retryable: false,
    });
  }
  if (HOSTED_DEMO) {
    const engine = await demoEngine();
    return engine.extractPdfInBrowser(file, { signal, onProgress });
  }
  if (!navigator.onLine) {
    throw new ApiError(
      "You’re offline. Reconnect to extract a PDF; your existing draft remains safe.",
      { code: "offline", retryable: true },
    );
  }

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 70_000);
  const abortFromCaller = () => controller.abort();
  signal?.addEventListener("abort", abortFromCaller, { once: true });
  const formData = new FormData();
  formData.append("file", file, file.name);
  let useBrowserOcr = false;
  try {
    onProgress?.({ phase: "opening", progress: 0 });
    const response = await fetch("/api/extract/pdf", {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (payload.code === "pdf_has_no_text") {
        useBrowserOcr = true;
      } else {
        throw new ApiError(payload.detail || "The PDF could not be extracted.", {
          code: payload.code,
          retryable: payload.retryable,
          status: response.status,
        });
      }
    } else {
      return payload;
    }
  } catch (error) {
    if (error.name === "AbortError") {
      if (signal?.aborted) throw error;
      throw new ApiError("PDF extraction took too long. Try a smaller chapter or section.", {
        retryable: false,
      });
    }
    if (error instanceof ApiError) throw error;
    throw new ApiError("The PDF server could not be reached. Your existing draft is safe.", {
      retryable: false,
    });
  } finally {
    window.clearTimeout(timeout);
    signal?.removeEventListener("abort", abortFromCaller);
  }
  if (useBrowserOcr) {
    const engine = await demoEngine();
    return engine.extractPdfInBrowser(file, { signal, onProgress });
  }
  throw new ApiError("The PDF could not be extracted.", { retryable: false });
}

function setBusy(button, busy, label) {
  if (!button) return;
  if (busy) {
    button.dataset.originalLabel = button.textContent;
    button.textContent = label;
    button.dataset.busy = "true";
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  } else {
    button.textContent = button.dataset.originalLabel || button.textContent;
    button.dataset.busy = "false";
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
}

function queueEvidence(evidence) {
  state.unsyncedEvidence.push({
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    ...evidence,
  });
  saveState();
  flushEvidence();
}

let flushingEvidence = false;

async function flushEvidence() {
  if (flushingEvidence) return;
  if ((!navigator.onLine && !HOSTED_DEMO) || !state.unsyncedEvidence.length) return;
  flushingEvidence = true;
  const pending = [...state.unsyncedEvidence];
  try {
    for (const event of pending) {
      const { id, ...payload } = event;
      try {
        await api("evidence", payload, 15_000);
        state.unsyncedEvidence = state.unsyncedEvidence.filter((item) => item.id !== id);
        saveState();
      } catch (_error) {
        saveStatus.textContent = "Progress saved; evidence sync pending";
        return;
      }
    }
  } finally {
    flushingEvidence = false;
  }
}

function updateConnectivity() {
  offlineBanner.hidden = navigator.onLine;
  if (!navigator.onLine) {
    saveStatus.textContent = "Offline · saved locally";
  }
}

function updatePdfProgress(progress) {
  const panel = document.getElementById("pdf-progress");
  const title = document.getElementById("pdf-progress-title");
  const detail = document.getElementById("pdf-progress-detail");
  const meter = document.getElementById("pdf-progress-meter");
  const fill = document.getElementById("pdf-progress-fill");
  if (!panel || !title || !detail || !meter || !fill) return;

  panel.hidden = false;
  let titleText = "Opening your PDF";
  let detailText = "Checking the file before reading its pages.";
  let normalizedProgress = Math.max(0, Math.min(1, Number(progress?.progress) || 0));

  if (progress?.phase === "reading") {
    titleText = "Reading your PDF";
    detailText = `Checking page ${progress.page} of ${progress.totalPages} for text.`;
    normalizedProgress = 0.05 + normalizedProgress * 0.25;
  } else if (progress?.phase === "ocr_loading") {
    titleText = "Preparing private text recognition";
    detailText =
      "Scanned pages were found. Loading English and Chinese OCR in this browser.";
    normalizedProgress = 0.3 + normalizedProgress * 0.08;
  } else if (progress?.phase === "ocr") {
    titleText = `Reading scanned page ${progress.ocrPageIndex} of ${progress.ocrPageCount}`;
    detailText = `Processing PDF page ${progress.page} in this browser. Keep this tab open.`;
    normalizedProgress = 0.38 + normalizedProgress * 0.57;
  } else if (progress?.phase === "complete") {
    titleText = "Finishing your PDF";
    detailText = "The extracted text is ready to save on this device.";
    normalizedProgress = 1;
  }

  title.textContent = titleText;
  detail.textContent = detailText;
  const percent = Math.round(normalizedProgress * 100);
  meter.setAttribute("aria-valuenow", String(percent));
  meter.setAttribute("aria-valuetext", `${titleText}, ${percent}%`);
  fill.style.width = `${percent}%`;

  if (panel.dataset.lastAnnouncement !== titleText) {
    panel.dataset.lastAnnouncement = titleText;
    announce(titleText);
  }
}

function renderHome(error = null) {
  const trustMessage = HOSTED_DEMO
    ? "In this hosted demo, your PDF—including OCR for scanned pages—is read in this browser and is not uploaded. Extracted text and draft progress stay on this device."
    : "Text-based PDFs are read in server memory; scanned-page OCR runs in this browser. Files are not stored. Extracted text is sent to the configured AI service.";
  const hasPdfSource = state.source?.type === "pdf";
  const sourceSummary =
    hasPdfSource
      ? `
        <div class="source-summary" role="status">
          <div>
            <span class="source-ready">✓ PDF ready</span>
            <strong>${esc(state.source.filename)}</strong>
            <span>${state.source.extractedPages ?? state.source.pageCount} of ${state.source.pageCount} pages read · ${state.material.length.toLocaleString()} extracted characters${state.source.ocrPages ? ` · OCR on ${state.source.ocrPages} scanned page(s)` : ""}${state.source.edited ? " · edited" : ""}</span>
          </div>
          <button id="remove-source" class="text-button" type="button">Remove</button>
        </div>
        ${(state.source.warnings || [])
          .map((warning) => `<p class="source-warning">${esc(warning)}</p>`)
          .join("")}`
      : "";
  const materialEditor = hasPdfSource
    ? `
      <details class="source-editor">
        <summary>Review or edit extracted text <span>(optional)</span></summary>
        <div class="source-editor-body">
          <label class="field-label" for="material">
            <span>Text extracted from your PDF</span>
            <span id="character-count" class="field-hint">${state.material.length.toLocaleString()} / 24,000</span>
          </label>
          <textarea
            id="material"
            name="material"
            maxlength="24000"
            aria-describedby="material-help material-error"
          >${esc(state.material)}</textarea>
          <p id="material-help" class="microcopy">Editing is optional. Sparring will use this extracted text as the only learning source.</p>
          <p id="material-error" class="field-error" role="alert" hidden></p>
        </div>
      </details>`
    : `
      <div class="or-divider"><span>or paste text</span></div>
      <label class="field-label" for="material">
        <span>Paste study text</span>
        <span id="character-count" class="field-hint">${state.material.length.toLocaleString()} / 24,000</span>
      </label>
      <textarea
        id="material"
        name="material"
        maxlength="24000"
        aria-describedby="material-help material-error"
        placeholder="Paste lecture notes, a chapter excerpt, or a paper section…"
      >${esc(state.material)}</textarea>
      <p id="material-help" class="microcopy">A short paragraph is enough. Only this text is used as the learning source.</p>
      <p id="material-error" class="field-error" role="alert" hidden></p>`;
  setView(`
    <section class="screen hero" aria-labelledby="screen-title">
      <div class="hero-copy">
        <p class="eyebrow">Active practice from your own material</p>
        <h1 id="screen-title">Keep the thinking.</h1>
        <p class="lede">
          Sparring turns one passage into a focused loop: predict, retrieve, judge your
          confidence, explain, then return later without hints.
        </p>
        <ol class="principles">
          <li>
            <span class="number-dot">1</span>
            <span><strong>Attempt before feedback.</strong> Make your current thinking visible.</span>
          </li>
          <li>
            <span class="number-dot">2</span>
            <span><strong>Explain relationships.</strong> Don’t stop at recognizing an option.</span>
          </li>
          <li>
            <span class="number-dot">3</span>
            <span><strong>Return after time.</strong> Reconstruct the idea in new wording.</span>
          </li>
        </ol>
      </div>
      <div class="panel">
        <form id="material-form">
          <div class="upload-block">
            <label class="upload-zone" for="pdf-upload">
              <input
                id="pdf-upload"
                class="file-input"
                type="file"
                accept=".pdf,application/pdf"
              >
              <span class="upload-icon" aria-hidden="true">↑</span>
              <span>
                <strong>Upload your PDF</strong>
                <small>Text or scanned PDF · up to 20 MB and 80 pages</small>
              </span>
            </label>
            ${sourceSummary}
            <div id="pdf-progress" class="pdf-progress" role="status" aria-live="polite" hidden>
              <div class="pdf-progress-copy">
                <strong id="pdf-progress-title">Opening your PDF</strong>
                <span id="pdf-progress-detail">Checking the file before reading its pages.</span>
              </div>
              <div
                id="pdf-progress-meter"
                class="pdf-progress-meter"
                role="progressbar"
                aria-label="PDF reading progress"
                aria-valuemin="0"
                aria-valuemax="100"
                aria-valuenow="0"
              >
                <span id="pdf-progress-fill"></span>
              </div>
              <button id="cancel-pdf" class="text-button" type="button">Cancel PDF reading</button>
            </div>
          </div>
          ${materialEditor}
          <div class="button-row">
            <button id="build-plan" class="button" type="submit">${hasPdfSource ? "Build practice from this PDF" : "Build my practice"}</button>
            ${hasPdfSource ? "" : '<button id="use-sample" class="button secondary" type="button">Use sample material</button>'}
          </div>
          ${recoveryNotice ? `<div class="error-panel" role="status"><p>${esc(recoveryNotice)}</p></div>` : ""}
          ${
            error
              ? error.context === "pdf_cancelled"
                ? `<div class="cancelled-panel" role="status" tabindex="-1">
                    <p><strong>PDF reading was cancelled.</strong></p>
                    <p>Your existing material and progress are still saved. Choose a PDF whenever you’re ready.</p>
                  </div>`
                : error.context === "pdf"
                ? `<div class="error-panel" role="alert" tabindex="-1">
                    <p><strong>We couldn’t read this PDF yet.</strong></p>
                    <p>${esc(error.message || "Choose another PDF and try again.")}</p>
                    <p>Your existing material and progress are still saved. Choose the PDF above to retry.</p>
                  </div>`
                : errorPanel(error)
              : ""
          }
          <div class="trust-note">
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
              <path fill="currentColor" d="M8 1.5 13 3v3.8c0 3.2-2.1 6.1-5 7.7-2.9-1.6-5-4.5-5-7.7V3l5-1.5Zm0 2L5 4.4v2.4c0 2.2 1.2 4.2 3 5.5 1.8-1.3 3-3.3 3-5.5V4.4L8 3.5Z"/>
            </svg>
            <span>${esc(trustMessage)}</span>
          </div>
        </form>
      </div>
    </section>`);

  const textarea = document.getElementById("material");
  const count = document.getElementById("character-count");
  textarea.addEventListener("input", () => {
    state.material = textarea.value;
    if (state.source?.type === "pdf") state.source.edited = true;
    else state.source = textarea.value ? { type: "paste" } : null;
    count.textContent = `${textarea.value.length.toLocaleString()} / 24,000`;
    textarea.removeAttribute("aria-invalid");
    const materialError = document.getElementById("material-error");
    if (materialError) {
      materialError.textContent = "";
      materialError.hidden = true;
    }
    debouncedSave();
  });
  document.getElementById("pdf-upload").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    event.target.disabled = true;
    document.getElementById("material-form")?.setAttribute("aria-busy", "true");
    const buildButton = document.getElementById("build-plan");
    const sampleButton = document.getElementById("use-sample");
    if (sampleButton) sampleButton.disabled = true;
    setBusy(buildButton, true, "Reading your PDF…");
    const controller = new AbortController();
    let cancelReason = null;
    document.getElementById("cancel-pdf")?.addEventListener(
      "click",
      () => {
        cancelReason = "user";
        controller.abort();
        announce("Cancelling PDF reading.");
      },
      { once: true },
    );
    updatePdfProgress({ phase: "opening", progress: 0 });
    const timeout = window.setTimeout(() => {
      cancelReason = "timeout";
      controller.abort();
    }, PDF_EXTRACTION_TIMEOUT_MS);
    try {
      const result = await uploadPdf(file, {
        signal: controller.signal,
        onProgress: updatePdfProgress,
      });
      state.material = result.text;
      state.source = {
        type: "pdf",
        filename: result.filename,
        pageCount: result.page_count,
        extractedPages: result.extracted_pages,
        ocrPages: result.ocr_pages || 0,
        truncated: result.truncated,
        warnings: result.warnings,
        edited: false,
      };
      saveState("PDF extracted and saved");
      announce(
        `${result.filename} is ready: ${result.extracted_pages} of ${result.page_count} pages read${result.ocr_pages ? `, including ${result.ocr_pages} scanned page(s)` : ""}.`,
      );
      renderHome();
      document.getElementById("build-plan")?.focus();
    } catch (uploadError) {
      if (uploadError.name === "AbortError") {
        if (cancelReason === "user") {
          uploadError = new ApiError("No changes were made.", {
            code: "pdf_cancelled",
            retryable: false,
          });
          uploadError.context = "pdf_cancelled";
        } else {
          uploadError = new ApiError(
            "PDF reading did not finish within 30 minutes. Your existing material is still saved; try a shorter section.",
            { code: "pdf_timeout", retryable: false },
          );
          uploadError.context = "pdf";
        }
      } else {
        uploadError.context = "pdf";
      }
      renderHome(uploadError);
      document.querySelector(".error-panel, .cancelled-panel")?.focus();
    } finally {
      window.clearTimeout(timeout);
    }
  });
  document.getElementById("remove-source")?.addEventListener("click", () => {
    state.material = "";
    state.source = null;
    saveState("PDF removed");
    renderHome();
    document.getElementById("pdf-upload")?.focus();
  });
  document.getElementById("use-sample")?.addEventListener("click", () => {
    state.material = SAMPLE_MATERIAL;
    state.source = { type: "sample" };
    textarea.value = SAMPLE_MATERIAL;
    count.textContent = `${SAMPLE_MATERIAL.length.toLocaleString()} / 24,000`;
    saveState("Sample loaded and saved");
    textarea.focus();
  });
  document.getElementById("material-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    state.material = textarea.value.trim();
    saveState();
    if (state.material.length < MIN_MATERIAL_CHARS) {
      const materialError = document.getElementById("material-error");
      const message = hasPdfSource
        ? `This PDF contains only ${state.material.length} readable characters. Use a clearer PDF with at least one complete sentence (${MIN_MATERIAL_CHARS} characters), or edit the extracted text.`
        : `Add at least one complete sentence (${MIN_MATERIAL_CHARS} characters), or upload a PDF.`;
      if (materialError) {
        materialError.textContent = message;
        materialError.hidden = false;
      }
      textarea.setAttribute("aria-invalid", "true");
      document.querySelector(".source-editor")?.setAttribute("open", "");
      textarea.focus();
      return;
    }
    textarea.removeAttribute("aria-invalid");
    await buildPlan();
  });
  if (error && error.retryable !== false) {
    document.getElementById("retry-action")?.addEventListener("click", buildPlan);
  }
}

async function buildPlan() {
  const button = document.getElementById("build-plan") || document.getElementById("retry-action");
  setBusy(button, true, "Finding the learning structure…");
  announce("Sparring is building a three-concept practice plan.");
  try {
    const plan = await api("plan", { material: state.material });
    state.plan = plan;
    state.planAccepted = false;
    state.current = 0;
    state.progress = {};
    state.queue = [];
    state.sessionComplete = false;
    state.sessionStartedAt = virtualToday();
    state.review = null;
    saveState();
    announce("Your practice plan is ready.");
    renderPlan();
  } catch (error) {
    renderHome(error);
  }
}

function renderPlan() {
  const concepts = state.plan.concepts
    .map(
      (concept, index) => `
        <li class="card concept-row">
          <span class="concept-index">${index + 1}</span>
          <div>
            <h3>${esc(concept.name)}</h3>
            ${
              concept.plain_definition
                ? `<p class="concept-definition">${esc(concept.plain_definition)}</p>`
                : ""
            }
            <p>${esc(concept.why)}</p>
            ${
              concept.depends_on?.length
                ? `<p class="microcopy"><strong>Builds from:</strong> ${esc(concept.depends_on.join(", "))}${
                    concept.relationship_to_dependencies
                      ? ` · ${esc(concept.relationship_to_dependencies)}`
                      : ""
                  }</p>`
                : ""
            }
            <details class="anchor">
              <summary>View material anchor</summary>
              <blockquote>${esc(concept.source_anchor)}</blockquote>
            </details>
          </div>
        </li>`,
    )
    .join("");
  setView(`
    <section class="screen narrow" aria-labelledby="screen-title">
      <p class="eyebrow">Your practice map</p>
      <h1 id="screen-title">Three rounds. One observable target.</h1>
      <div class="target-card">
        <p class="eyebrow">By the end</p>
        <p>${esc(state.plan.target)}</p>
      </div>
      <ol class="concept-list">${concepts}</ol>
      <div class="button-row">
        <button id="accept-plan" class="button" type="button">Start concept 1</button>
        <button id="edit-material" class="button secondary" type="button">Edit material</button>
      </div>
      <p class="microcopy">The prediction is a low-stakes attempt, not an entrance test or ability judgment.</p>
    </section>`);
  document.getElementById("accept-plan").addEventListener("click", () => {
    state.planAccepted = true;
    saveState();
    renderCurrentConcept();
  });
  document.getElementById("edit-material").addEventListener("click", () => {
    state.plan = null;
    state.planAccepted = false;
    saveState();
    renderHome();
  });
}

function renderCurrentConcept() {
  if (state.current >= state.plan.concepts.length) {
    state.sessionComplete = true;
    saveState();
    renderDashboard();
    return;
  }
  const progress = progressFor(state.current);
  if (!progress.prediction) {
    renderPrediction();
  } else if (!progress.lesson) {
    renderPrediction(null, true);
  } else if (!progress.lessonAcknowledged) {
    renderLesson();
  } else if (progress.quizResponses.length < 3 || progress.pendingQuizResponse) {
    renderQuiz();
  } else {
    renderTeachback();
  }
}

function renderPrediction(error = null, saved = false) {
  const concept = state.plan.concepts[state.current];
  const progress = progressFor(state.current);
  setView(`
    <section class="screen narrow" aria-labelledby="screen-title">
      ${progressBar("Predict · no grade")}
      <div class="stage-header">
        <p class="eyebrow">10-second curiosity attempt</p>
        <h1 id="screen-title">${esc(concept.name)}</h1>
        <p class="muted">Trying first helps you compare your current model with the explanation that follows.</p>
      </div>
      <form id="prediction-form" class="prompt-card">
        <p class="prompt-text">${esc(concept.predict_q)}</p>
        <label class="field-label" for="prediction">
          <span>Your prediction</span>
          <span class="field-hint">One or two lines</span>
        </label>
        <textarea
          id="prediction"
          class="short"
          minlength="2"
          maxlength="600"
          placeholder="Make a real guess. It is safe to be wrong."
          required
          ${saved ? "readonly" : ""}
        >${esc(progress.prediction)}</textarea>
        <div class="button-row">
          <button id="load-lesson" class="button" type="submit">
            ${saved ? "Retry explanation" : "Commit prediction"}
          </button>
        </div>
        ${error ? errorPanel(error) : ""}
      </form>
    </section>`);

  const form = document.getElementById("prediction-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const textarea = document.getElementById("prediction");
    if (!progress.prediction) {
      progress.prediction = textarea.value.trim();
      if (progress.prediction.length < 2) {
        textarea.setCustomValidity("Write a brief prediction before continuing.");
        textarea.reportValidity();
        textarea.setCustomValidity("");
        return;
      }
      progress.predictionAt = new Date().toISOString();
      queueEvidence({
        event_type: "prediction",
        concept: concept.name,
        score: null,
        confidence: null,
        linked: null,
        review_stage: null,
      });
    }
    saveState();
    await loadLesson();
  });
  if (error && error.retryable !== false) {
    document.getElementById("retry-action")?.addEventListener("click", loadLesson);
  }
}

async function loadLesson() {
  const concept = state.plan.concepts[state.current];
  const progress = progressFor(state.current);
  const button = document.getElementById("load-lesson") || document.getElementById("retry-action");
  setBusy(button, true, "Preparing one focused explanation…");
  announce("Sparring is preparing the explanation and practice questions.");
  try {
    progress.lesson = await api("lesson", {
      material: state.material,
      concept: concept.name,
    });
    saveState();
    announce("The explanation is ready.");
    renderLesson();
  } catch (error) {
    renderPrediction(error, true);
  }
}

function renderLesson() {
  const concept = state.plan.concepts[state.current];
  const progress = progressFor(state.current);
  const lesson = progress.lesson;
  setView(`
    <section class="screen narrow" aria-labelledby="screen-title">
      ${progressBar("Explain · compare")}
      <div class="stage-header">
        <p class="eyebrow">Now compare</p>
        <h1 id="screen-title">${esc(concept.name)}</h1>
        <p class="muted">Notice what your prediction captured and what the material changes.</p>
      </div>
      <div class="compare-grid">
        <article class="compare-card prediction">
          <p class="eyebrow">Your prediction</p>
          <p>${esc(progress.prediction)}</p>
        </article>
        <article class="compare-card explanation">
          <p class="eyebrow">Focused explanation</p>
          <p>${esc(lesson.explanation)}</p>
          <details class="anchor">
            <summary>Verify against the material</summary>
            <blockquote>${esc(lesson.explanation_anchor)}</blockquote>
          </details>
        </article>
      </div>
      <div class="button-row">
        <button id="begin-quiz" class="button" type="button">Retrieve it now</button>
      </div>
    </section>`);
  document.getElementById("begin-quiz").addEventListener("click", () => {
    progress.lessonAcknowledged = true;
    saveState();
    renderQuiz();
  });
}

function optionMarkup(question, pending) {
  return question.options
    .map((option, index) => {
      let resultClass = "";
      let status = "";
      if (pending) {
        if (index === question.answer) {
          resultClass = "result-correct";
          status = index === pending.selected ? "Your answer · correct" : "Supported answer";
        } else if (index === pending.selected) {
          resultClass = "result-wrong";
          status = "Your answer · not supported";
        }
        else resultClass = "is-muted";
      }
      return `
        <label class="option ${resultClass}">
          <input
            type="radio"
            name="answer"
            value="${index}"
            ${pending?.selected === index ? "checked" : ""}
            ${pending ? "disabled" : ""}
          >
          <span class="option-letter">${LETTERS[index]}</span>
          <span>${esc(option)}${status ? `<span class="option-status">${esc(status)}</span>` : ""}</span>
        </label>`;
    })
    .join("");
}

function feedbackMessage(correct, confidence) {
  if (!correct && confidence >= 4) {
    return {
      title: "High-confidence mismatch",
      text: "Compare the two explanations carefully: fluency felt strong, but the material supports a different relationship.",
    };
  }
  if (!correct) {
    return {
      title: "Use a smaller source anchor",
      text: "Your uncertainty was informative. Rebuild the answer from the cited sentence before moving on.",
    };
  }
  if (confidence <= 2) {
    return {
      title: "Correct with low confidence",
      text: "The answer matches the material. Name the relationship once more so the success becomes easier to recognize later.",
    };
  }
  return {
    title: "Correct and committed",
    text: "Your answer and confidence point in the same direction on this item. Keep testing that pattern across new wording.",
  };
}

function renderQuiz() {
  const concept = state.plan.concepts[state.current];
  const progress = progressFor(state.current);
  const questionIndex = progress.quizResponses.length;
  const question = progress.lesson.quiz[questionIndex];
  const pending = progress.pendingQuizResponse;
  const message = pending ? feedbackMessage(pending.correct, pending.confidence) : null;

  setView(`
    <section class="screen narrow" aria-labelledby="screen-title">
      ${progressBar(`Retrieve · question ${questionIndex + 1} of 3`)}
      <div class="stage-header">
        <p class="eyebrow">${esc(question.kind)} check</p>
        <h1 id="screen-title">${esc(concept.name)}</h1>
      </div>
      <form id="quiz-form" class="prompt-card">
        <fieldset>
          <legend>${esc(question.stem)}</legend>
          <div class="option-list">${optionMarkup(question, pending)}</div>
        </fieldset>
        ${
          pending
            ? `
              <div class="feedback-card ${pending.correct ? "" : "error-tone"}">
                <h3>${esc(message.title)}</h3>
                <p>${esc(message.text)}</p>
                <div class="feedback-grid">
                  <div class="feedback-detail">
                    <p class="feedback-label">Your choice</p>
                    <p>${esc(question.why[pending.selected])}</p>
                  </div>
                  <div class="feedback-detail">
                    <p class="feedback-label">Supported answer</p>
                    <p>${esc(question.why[question.answer])}</p>
                  </div>
                </div>
                <details class="anchor">
                  <summary>Check the material anchor</summary>
                  <blockquote>${esc(question.source_anchor)}</blockquote>
                </details>
              </div>
              <div class="button-row">
                <button id="next-question" class="button" type="button">
                  ${questionIndex < 2 ? "Next question" : "Teach it back"}
                </button>
              </div>`
            : `
              <fieldset class="confidence-wrap">
                <legend>How confident are you before feedback?</legend>
                <p class="microcopy">Choose deliberately; there is no default.</p>
                <div class="confidence-scale">
                  ${[1, 2, 3, 4, 5]
                    .map(
                      (value) => `
                        <label class="confidence-choice">
                          <input type="radio" name="confidence" value="${value}">
                          <span>${value}</span>
                        </label>`,
                    )
                    .join("")}
                </div>
                <div class="scale-labels"><span>Guessing</span><span>Very sure</span></div>
              </fieldset>
              <div class="button-row">
                <button id="lock-answer" class="button" type="submit">Lock answer</button>
              </div>`
        }
      </form>
    </section>`);

  if (pending) {
    const feedbackHeading = document.querySelector(".feedback-card h3");
    if (feedbackHeading) {
      feedbackHeading.setAttribute("tabindex", "-1");
      feedbackHeading.focus({ preventScroll: true });
    }
    document.getElementById("next-question").addEventListener("click", () => {
      progress.quizResponses.push(pending);
      progress.pendingQuizResponse = null;
      if (progress.quizResponses.length === 3) {
        const score = progress.quizResponses.filter((item) => item.correct).length;
        const confidence =
          progress.quizResponses.reduce((sum, item) => sum + item.confidence, 0) / 3;
        queueEvidence({
          event_type: "quiz",
          concept: concept.name,
          score,
          confidence,
          linked: null,
          review_stage: null,
        });
      }
      saveState();
      renderCurrentConcept();
    });
    return;
  }

  document.getElementById("quiz-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const answer = new FormData(event.currentTarget).get("answer");
    const confidence = new FormData(event.currentTarget).get("confidence");
    if (answer === null || confidence === null) {
      announce("Choose both an answer and a confidence rating before locking in.");
      const firstMissing = answer === null
        ? event.currentTarget.querySelector('input[name="answer"]')
        : event.currentTarget.querySelector('input[name="confidence"]');
      firstMissing?.focus();
      return;
    }
    const selected = Number(answer);
    progress.pendingQuizResponse = {
      selected,
      confidence: Number(confidence),
      correct: selected === question.answer,
    };
    saveState();
    announce(
      progress.pendingQuizResponse.correct
        ? "Answer revealed: correct."
        : "Answer revealed: not correct yet.",
    );
    renderQuiz();
  });
}

function assessmentMarkup(assessment) {
  if (!assessment) return "";
  const covered = (assessment.covered || [])
    .map((item) => `<span class="tag good">Present · ${esc(item)}</span>`)
    .join("");
  const missing = (assessment.missing || [])
    .map((item) => `<span class="tag gap">Develop · ${esc(item)}</span>`)
    .join("");
  return `
    <div class="feedback-card ${assessment.linked ? "" : "error-tone"}" role="status">
      <h3>${assessment.linked ? "The relationship is connected." : "Revise one connection."}</h3>
      <p>${esc(assessment.feedback)}</p>
      <div class="tags">${covered}${missing}</div>
      ${
        assessment.repair_prompt
          ? `<p class="microcopy"><strong>Sentence stem:</strong> ${esc(assessment.repair_prompt)}</p>`
          : ""
      }
    </div>`;
}

function renderTeachback(error = null) {
  const concept = state.plan.concepts[state.current];
  const progress = progressFor(state.current);
  const assessment = progress.teachbackAssessment;
  const canRevise = assessment && !assessment.linked && progress.teachbackAttempts < 2;
  const completeReady = assessment && (assessment.linked || progress.teachbackAttempts >= 2);
  const relationshipCheckNote = HOSTED_DEMO
    ? "This preview uses a deterministic relationship check for offline rehearsal."
    : "The AI compares this explanation with a verified source anchor. It is practice feedback, not an objective diagnosis of understanding.";

  setView(`
    <section class="screen narrow" aria-labelledby="screen-title">
      ${progressBar("Explain · relationship check")}
      <div class="stage-header">
        <p class="eyebrow">Teach-back</p>
        <h1 id="screen-title">Connect the ideas in two lines.</h1>
        <p class="muted">${esc(progress.lesson.teachback_q)}</p>
      </div>
      <form id="teachback-form" class="prompt-card">
        ${assessmentMarkup(assessment)}
        <label class="field-label" for="teachback">
          <span>${canRevise ? "Your revision" : "Your explanation"}</span>
          <span class="field-hint">Use a real relationship, not just a connecting word</span>
        </label>
        <textarea
          id="teachback"
          class="short"
          minlength="10"
          maxlength="2000"
          placeholder="For example: X matters because…"
          ${completeReady ? "readonly" : ""}
          required
        >${esc(progress.teachbackAnswer)}</textarea>
        <div class="button-row">
          ${
            completeReady
              ? `<button id="complete-concept" class="button" type="button">
                  ${state.current < 2 ? "Continue to next concept" : "Finish session"}
                </button>`
              : `<button id="check-teachback" class="button" type="submit">
                  ${canRevise ? "Check my revision" : "Check the relationship"}
                </button>`
          }
          ${
            canRevise
              ? `<button id="continue-with-gap" class="button secondary" type="button">
                  Continue and review tomorrow
                </button>`
              : ""
          }
        </div>
        ${error ? errorPanel(error) : ""}
      </form>
      <p class="microcopy">${esc(relationshipCheckNote)}</p>
    </section>`);

  if (completeReady) {
    document.getElementById("complete-concept").addEventListener("click", completeConcept);
    return;
  }

  const textarea = document.getElementById("teachback");
  textarea.addEventListener("input", () => {
    progress.teachbackAnswer = textarea.value;
    debouncedSave();
  });
  document.getElementById("teachback-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    progress.teachbackAnswer = textarea.value.trim();
    if (progress.teachbackAnswer.length < 10) {
      textarea.setCustomValidity("Write at least one complete relationship.");
      textarea.reportValidity();
      textarea.setCustomValidity("");
      return;
    }
    await checkTeachback();
  });
  document.getElementById("continue-with-gap")?.addEventListener("click", completeConcept);
  if (error && error.retryable !== false) {
    document.getElementById("retry-action")?.addEventListener("click", checkTeachback);
  }
}

async function checkTeachback() {
  const concept = state.plan.concepts[state.current];
  const progress = progressFor(state.current);
  const button = document.getElementById("check-teachback") || document.getElementById("retry-action");
  setBusy(button, true, "Checking the relationship…");
  announce("Sparring is comparing your explanation with the material.");
  try {
    progress.teachbackAssessment = await api("teachback", {
      material: state.material,
      concept: concept.name,
      answer: progress.teachbackAnswer,
    });
    progress.teachbackAttempts += 1;
    queueEvidence({
      event_type: "teachback",
      concept: concept.name,
      score: null,
      confidence: null,
      linked: progress.teachbackAssessment.linked,
      review_stage: null,
    });
    saveState();
    announce(
      progress.teachbackAssessment.linked
        ? "The relationship is connected."
        : "One revision is recommended.",
    );
    renderTeachback();
  } catch (error) {
    renderTeachback(error);
  }
}

function completeConcept() {
  const concept = state.plan.concepts[state.current];
  const progress = progressFor(state.current);
  if (!state.queue.some((item) => item.conceptIndex === state.current)) {
    state.queue.push({
      conceptIndex: state.current,
      concept: concept.name,
      quiz: progress.lesson.quiz,
      reviewIndex: 0,
      dueAt: addDays(state.sessionStartedAt, REVIEW_DAYS[0]),
      status: "scheduled",
      lastScore: null,
    });
  }
  progress.completed = true;
  state.current += 1;
  if (state.current >= state.plan.concepts.length) state.sessionComplete = true;
  saveState();
  announce(
    state.sessionComplete
      ? "Session complete. Your review schedule is ready."
      : "Concept complete. Moving to the next round.",
  );
  route();
}

function confidencePattern(responses) {
  const all = responses.flat();
  return {
    attempts: all.length,
    highWrong: all.filter((item) => !item.correct && item.confidence >= 4).length,
    lowRight: all.filter((item) => item.correct && item.confidence <= 2).length,
  };
}

function renderDashboard() {
  const due = dueItems();
  const responses = Object.values(state.progress).map((item) => item.quizResponses || []);
  const pattern = confidencePattern(responses);
  const schedule = state.queue
    .map((item) => {
      const status = item.status === "scheduled_reviews_complete"
        ? "Schedule complete"
        : isDue(item)
          ? "Due now"
          : `Due ${formatDate(item.dueAt)}`;
      return `
        <li class="review-row">
          <span>${esc(item.concept)}</span>
          <span class="status-pill ${isDue(item) ? "due" : ""}">${esc(status)}</span>
        </li>`;
    })
    .join("");
  setView(`
    <section class="screen narrow" aria-labelledby="screen-title">
      <p class="eyebrow">Session complete</p>
      <h1 id="screen-title">Now let time do its part.</h1>
      <p class="lede">
        Today’s answers are practice evidence. The scheduled reviews check whether the
        relationships can be reconstructed later in new wording.
      </p>
      <div class="dashboard-grid">
        <article class="card">
          <h2>Confidence pattern</h2>
          <div class="stat-grid">
            <div class="stat"><strong>${pattern.attempts}</strong><span>committed answers</span></div>
            <div class="stat"><strong>${pattern.highWrong}</strong><span>high-confidence errors</span></div>
            <div class="stat"><strong>${pattern.lowRight}</strong><span>low-confidence correct</span></div>
          </div>
          <p class="microcopy">
            These are descriptive counts, not a metacognition score. More attempts are needed
            before drawing a stable conclusion.
          </p>
        </article>
        <article class="card">
          <p class="eyebrow">Review queue</p>
          <h2>${due.length ? `${due.length} due now` : "Nothing due yet"}</h2>
          <p class="muted">Default intervals: day 1, day 3, and day 7.</p>
          <div class="button-row">
            ${
              due.length
                ? `<button id="start-review" class="button" type="button">Start due review</button>`
                : `<button id="advance-day" class="button secondary" type="button">Demo · advance one day</button>`
            }
          </div>
        </article>
      </div>
      <article class="card card-spaced">
        <h2>Your schedule</h2>
        <ul class="review-list">${schedule}</ul>
      </article>
      <p class="microcopy">
        The 1–3–7 schedule is a transparent prototype heuristic, not a universal optimum.
      </p>
    </section>`);

  document.getElementById("start-review")?.addEventListener("click", () => {
    beginReview(due[0].index);
  });
  document.getElementById("advance-day")?.addEventListener("click", () => {
    state.clockOffsetDays += 1;
    saveState("Demo date advanced");
    announce(`Demo date advanced to ${formatDate(virtualToday())}.`);
    renderDashboard();
  });
}

function beginReview(queueIndex) {
  state.review = {
    queueIndex,
    phase: "intro",
    quiz: null,
    responses: [],
    outcomeApplied: false,
  };
  saveState();
  renderReviewIntro();
}

function renderReviewIntro(error = null) {
  const item = state.queue[state.review.queueIndex];
  setView(`
    <section class="screen narrow" aria-labelledby="screen-title">
      <p class="eyebrow">Delayed review ${item.reviewIndex + 1} of 3</p>
      <h1 id="screen-title">${esc(item.concept)}</h1>
      <div class="prompt-card">
        <p class="prompt-text">Same objective. New wording. No hints until all three answers are committed.</p>
        <p class="muted">
          This review checks current recall under this format; it does not certify permanent mastery.
        </p>
        <div class="button-row">
          <button id="load-cold-review" class="button" type="button">Begin cold review</button>
          <button id="back-dashboard" class="button secondary" type="button">Not now</button>
        </div>
        ${error ? errorPanel(error) : ""}
      </div>
    </section>`);
  document.getElementById("load-cold-review").addEventListener("click", loadColdReview);
  document.getElementById("back-dashboard").addEventListener("click", () => {
    state.review = null;
    saveState();
    renderDashboard();
  });
  if (error && error.retryable !== false) {
    document.getElementById("retry-action")?.addEventListener("click", loadColdReview);
  }
}

async function loadColdReview() {
  const item = state.queue[state.review.queueIndex];
  const button =
    document.getElementById("load-cold-review") || document.getElementById("retry-action");
  setBusy(button, true, "Creating a new version…");
  announce("Sparring is creating a reworded review from the same material anchors.");
  try {
    const result = await api("cold", {
      material: state.material,
      quiz: item.quiz,
    });
    state.review.quiz = result.quiz;
    state.review.phase = "questions";
    saveState();
    announce("Cold review ready. Feedback stays hidden until the end.");
    renderColdQuestion();
  } catch (error) {
    renderReviewIntro(error);
  }
}

function renderColdQuestion() {
  const review = state.review;
  if (review.responses.length >= review.quiz.length) {
    review.phase = "result";
    saveState();
    renderColdResult();
    return;
  }
  const questionIndex = review.responses.length;
  const question = review.quiz[questionIndex];
  setView(`
    <section class="screen narrow" aria-labelledby="screen-title">
      <div
        class="progress-shell"
        role="progressbar"
        aria-label="Cold review progress"
        aria-valuemin="1"
        aria-valuemax="3"
        aria-valuenow="${questionIndex + 1}"
        aria-valuetext="Question ${questionIndex + 1} of 3"
      >
        <div class="progress-meta">
          <span>Cold review · feedback hidden</span>
          <span>Question ${questionIndex + 1} of 3</span>
        </div>
        <div class="progress-track">
          ${[0, 1, 2]
            .map(
              (index) =>
                `<div class="progress-segment ${index <= questionIndex ? "active" : ""}" aria-hidden="true"><span></span></div>`,
            )
            .join("")}
        </div>
      </div>
      <form id="cold-form" class="prompt-card">
        <fieldset>
          <legend id="screen-title">${esc(question.stem)}</legend>
          <div class="option-list">${optionMarkup(question, null)}</div>
        </fieldset>
        <fieldset class="confidence-wrap">
          <legend>How confident are you before feedback?</legend>
          <div class="confidence-scale">
            ${[1, 2, 3, 4, 5]
              .map(
                (value) => `
                  <label class="confidence-choice">
                    <input type="radio" name="confidence" value="${value}">
                    <span>${value}</span>
                  </label>`,
              )
              .join("")}
          </div>
          <div class="scale-labels"><span>Guessing</span><span>Very sure</span></div>
        </fieldset>
        <div class="button-row">
          <button class="button" type="submit">
            ${questionIndex < 2 ? "Commit and continue" : "Commit final answer"}
          </button>
        </div>
      </form>
    </section>`);

  document.getElementById("cold-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const answer = data.get("answer");
    const confidence = data.get("confidence");
    if (answer === null || confidence === null) {
      announce("Choose both an answer and a confidence rating.");
      const missing = answer === null
        ? event.currentTarget.querySelector('input[name="answer"]')
        : event.currentTarget.querySelector('input[name="confidence"]');
      missing?.focus();
      return;
    }
    const selected = Number(answer);
    review.responses.push({
      selected,
      confidence: Number(confidence),
      correct: selected === question.answer,
    });
    saveState();
    renderColdQuestion();
  });
}

function applyReviewOutcome() {
  const review = state.review;
  if (review.outcomeApplied) return;
  const item = state.queue[review.queueIndex];
  const score = review.responses.filter((response) => response.correct).length;
  const passed = score >= 2;
  item.lastScore = score;
  if (passed && item.reviewIndex < REVIEW_DAYS.length - 1) {
    item.reviewIndex += 1;
    const scheduledDate = addDays(state.sessionStartedAt, REVIEW_DAYS[item.reviewIndex]);
    const minimumFutureDate = addDays(virtualToday(), 1);
    item.dueAt = scheduledDate > minimumFutureDate ? scheduledDate : minimumFutureDate;
    item.status = "scheduled";
  } else if (passed) {
    item.status = "scheduled_reviews_complete";
    item.dueAt = null;
  } else {
    item.dueAt = addDays(virtualToday(), 1);
    item.status = "scheduled";
  }
  review.score = score;
  review.passed = passed;
  review.outcomeApplied = true;
  const averageConfidence =
    review.responses.reduce((sum, response) => sum + response.confidence, 0) /
    review.responses.length;
  queueEvidence({
    event_type: "cold_test",
    concept: item.concept,
    score,
    confidence: averageConfidence,
    linked: null,
    review_stage: item.reviewIndex,
  });
  saveState();
}

function renderColdResult() {
  applyReviewOutcome();
  const review = state.review;
  const item = state.queue[review.queueIndex];
  const results = review.quiz
    .map((question, index) => {
      const response = review.responses[index];
      return `
        <article class="result-item ${response.correct ? "correct" : "wrong"}">
          <p class="feedback-label">${response.correct ? "Supported" : "Needs repair"} · confidence ${response.confidence}/5</p>
          <h3>${esc(question.stem)}</h3>
          <p>${esc(question.why[response.correct ? question.answer : response.selected])}</p>
          ${
            response.correct
              ? ""
              : `<p><strong>Supported answer:</strong> ${esc(question.why[question.answer])}</p>`
          }
        </article>`;
    })
    .join("");
  const heading = review.passed
    ? item.status === "scheduled_reviews_complete"
      ? "Scheduled reviews complete."
      : "Current recall supported."
    : "Repair, then return tomorrow.";
  const scheduleMessage = review.passed
    ? item.status === "scheduled_reviews_complete"
      ? "Across the planned 1–3–7 checks, the current evidence supports retention under these review conditions."
      : `The next reworded review is scheduled for ${formatDate(item.dueAt)}.`
    : `This concept returns on ${formatDate(item.dueAt)} after a short repair interval.`;
  setView(`
    <section class="screen narrow" aria-labelledby="screen-title">
      <p class="eyebrow">Cold review result · ${review.score}/3</p>
      <h1 id="screen-title">${heading}</h1>
      <p class="lede">${scheduleMessage}</p>
      <div class="result-list">${results}</div>
      <div class="button-row">
        <button id="return-dashboard" class="button" type="button">Return to review queue</button>
      </div>
    </section>`);
  announce(`Cold review complete: ${review.score} of 3. ${heading}`);
  document.getElementById("return-dashboard").addEventListener("click", () => {
    state.review = null;
    saveState();
    renderDashboard();
  });
}

function route() {
  if (!state.plan) {
    renderHome();
  } else if (!state.planAccepted) {
    renderPlan();
  } else if (state.review) {
    if (state.review.phase === "intro") renderReviewIntro();
    else if (state.review.phase === "questions") renderColdQuestion();
    else renderColdResult();
  } else if (state.sessionComplete) {
    renderDashboard();
  } else {
    renderCurrentConcept();
  }
}

resetButton.addEventListener("click", () => {
  resetDialog.showModal();
});

confirmReset.addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(CORRUPT_KEY);
  state = freshState();
  recoveryNotice = "";
  announce("Local Sparring progress cleared.");
  window.setTimeout(() => renderHome(), 0);
});

window.addEventListener("online", () => {
  updateConnectivity();
  announce("Back online. Pending progress will sync now.");
  flushEvidence();
});

window.addEventListener("offline", () => {
  updateConnectivity();
  announce("You are offline. Loaded work and drafts remain available.");
});

window.addEventListener("storage", (event) => {
  if (event.key === STORAGE_KEY && event.newValue) {
    conflictBanner.hidden = false;
    announce("A newer progress update is available from another tab.");
  }
});

loadNewerStateButton.addEventListener("click", () => {
  state = loadState();
  conflictBanner.hidden = true;
  announce("Newer progress loaded.");
  route();
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => {
      // The app remains usable without offline shell caching.
    });
  });
}

route();
flushEvidence();
