const MAX_PDF_BYTES = 20 * 1024 * 1024;
const MAX_PDF_PAGES = 80;
const MAX_MATERIAL_CHARS = 24_000;
const MIN_MATERIAL_CHARS = 40;
const MIN_PAGE_TEXT_CHARS = 20;
const OCR_LANGUAGES = ["eng", "chi_sim"];
const OCR_RENDER_SCALE = 2;
const MAX_OCR_CANVAS_PIXELS = 2_400_000;
const MAX_OCR_CANVAS_EDGE = 2_800;
const CONNECTORS = [
  " because ",
  " so ",
  " therefore ",
  " depends on ",
  " leads to ",
  " enables ",
  " causes ",
  " contrasts ",
  " because of ",
];

function demoError(message, code, retryable = false) {
  const error = new Error(message);
  error.code = code;
  error.retryable = retryable;
  return error;
}

function normalizedMaterial(raw) {
  const material = String(raw || "").trim();
  if (material.length < MIN_MATERIAL_CHARS) {
    throw demoError(
      `Provide at least one complete sentence (${MIN_MATERIAL_CHARS} characters) of study material.`,
      "material_too_short",
    );
  }
  if (material.length > MAX_MATERIAL_CHARS) {
    throw demoError(
      `Keep the material under ${MAX_MATERIAL_CHARS.toLocaleString()} characters for this demo.`,
      "material_too_long",
    );
  }
  return material;
}

function chunks(material) {
  const compact = material.trim().replace(/[ \t]+/g, " ");
  const paragraphs = compact
    .split(/\n\s*\n+/)
    .map((paragraph) => paragraph.trim())
    .filter((paragraph) => paragraph.length >= 35);
  const paragraphLeads = paragraphs.map(
    (paragraph) => paragraph.split(/(?<=[.!?。！？])\s+/, 1)[0].trim(),
  );
  if (paragraphLeads.length >= 3) return paragraphLeads.slice(0, 3);

  const candidates = compact
    .split(/(?<=[.!?。！？])\s+|\n+/)
    .map((part) => part.replace(/^[\s\-•]+|[\s\-•]+$/g, ""))
    .filter((part) => part.length >= 35);
  if (candidates.length >= 3) return candidates.slice(0, 3);

  const size = Math.max(35, Math.floor(compact.length / 3));
  const fallback = [];
  for (let index = 0; index < compact.length; index += size) {
    const part = compact.slice(index, index + size).trim();
    if (part.length >= 20) fallback.push(part);
  }
  return [...candidates, ...fallback].slice(0, 3);
}

function anchor(text) {
  return text.slice(0, 220).trim();
}

function conceptName(text, index) {
  const words = text.match(/[A-Za-z][A-Za-z'-]*/g);
  if (words?.length) {
    const phrase = words.slice(0, 2).join(" ").replace(/[.,:;]+$/, "");
    return phrase || `Concept ${index + 1}`;
  }
  return text.slice(0, 12).replace(/[，。；：\s]+$/g, "") || `概念 ${index + 1}`;
}

function fixturePlan(rawMaterial) {
  const material = normalizedMaterial(rawMaterial);
  const pieces = chunks(material);
  while (pieces.length < 3) pieces.push(material.slice(0, 220));
  const seenNames = new Set();
  const names = pieces.slice(0, 3).map((piece, index) => {
    const baseName = conceptName(piece, index);
    let name = baseName;
    let suffix = index + 1;
    while (seenNames.has(name.toLocaleLowerCase())) {
      name = `${baseName} ${suffix}`;
      suffix += 1;
    }
    seenNames.add(name.toLocaleLowerCase());
    return name;
  });
  return {
    target: `After this session, you will be able to explain how ${names.join(", ")} fit together.`,
    concepts: pieces.slice(0, 3).map((piece, index) => ({
      name: names[index],
      why: "It is required to explain the material's central relationship.",
      predict_q: `Before reading closely, why might ${names[index]} matter here?`,
      source_anchor: anchor(piece),
    })),
  };
}

function selectConceptAnchor(material, concept) {
  const pieces = chunks(material);
  const conceptWords = concept.toLowerCase().split(/\s+/).filter(Boolean);
  const match = pieces.find((piece) => {
    const lowered = piece.toLowerCase();
    return conceptWords.every((word) => lowered.includes(word));
  });
  return anchor(match || pieces[0] || material);
}

function quizItem(kind, concept, sourceAnchor, correctIndex) {
  const correct = `The material describes this idea as: ${sourceAnchor}`;
  const distractors = [
    [
      `The material presents ${concept} as a term to memorize, while leaving the relationship between its elements unexplained.`,
      "isolated label",
    ],
    [
      `The material presents ${concept} as an isolated process that works without depending on the other ideas in the passage.`,
      "false independence",
    ],
    [
      `The material uses ${concept} to support the opposite relationship from the one stated in the cited passage.`,
      "reversed relationship",
    ],
  ];
  const rows = distractors.map(([text, tag]) => ({
    text,
    reason: "This changes or removes the relationship stated in the material.",
    tag,
  }));
  rows.splice(correctIndex, 0, {
    text: correct,
    reason: "This is the only option that matches the cited material.",
    tag: "",
  });
  const stems = {
    definition: `Which statement best captures ${concept} in the material?`,
    mechanism: `Which account best explains how ${concept} works?`,
    application: `Which explanation applies ${concept} without adding outside facts?`,
  };
  return {
    kind,
    stem: stems[kind],
    options: rows.map((row) => row.text),
    answer: correctIndex,
    why: rows.map((row) => row.reason),
    tag: rows.map((row) => row.tag),
    source_anchor: sourceAnchor,
  };
}

function fixtureLesson(rawMaterial, concept) {
  const material = normalizedMaterial(rawMaterial);
  const sourceAnchor = selectConceptAnchor(material, concept);
  return {
    explanation:
      `The big idea is the relationship in this passage: “${sourceAnchor}” ` +
      "It works by connecting the elements named there rather than treating them as " +
      "an isolated list. Use the quoted passage as the boundary: explain its relationship " +
      "without importing outside facts.",
    explanation_anchor: sourceAnchor,
    quiz: [
      quizItem("definition", concept, sourceAnchor, 1),
      quizItem("mechanism", concept, sourceAnchor, 2),
      quizItem("application", concept, sourceAnchor, 0),
    ],
    teachback_q:
      `Explain ${concept} to a classmate in two lines. Connect what it is to why ` +
      "the relationship in the material matters.",
  };
}

function fixtureTeachback(rawMaterial, concept, rawAnswer) {
  normalizedMaterial(rawMaterial);
  const answer = String(rawAnswer || "").trim();
  if (answer.length < 10) {
    throw demoError("Write your two-line explanation first.", "answer_too_short");
  }
  const normalized = ` ${answer.toLowerCase()} `;
  const linked = CONNECTORS.some((connector) => normalized.includes(connector));
  const excerpt = answer.split(/\s+/).slice(0, 7).join(" ").replace(/[,.;]+$/, "");
  if (linked) {
    return {
      linked: true,
      covered: [concept, "a stated relationship"],
      missing: [],
      feedback:
        `Your phrase “${excerpt}” connects ideas instead of merely naming them. ` +
        "Next, keep that causal link when the wording changes.",
      repair_prompt: null,
    };
  }
  return {
    linked: false,
    covered: [concept],
    missing: ["why the ideas connect"],
    feedback:
      `You named the relevant idea in “${excerpt},” but the relationship is still ` +
      "listed rather than explained. Add one because or so connection.",
    repair_prompt: `${concept} matters because…`,
  };
}

function reword(option) {
  const replacements = [
    ["The material describes this idea as:", "The source frames the idea this way:"],
    ["The material presents", "The source portrays"],
    ["The material uses", "The source uses"],
  ];
  for (const [before, after] of replacements) {
    if (option.includes(before)) return option.replace(before, after);
  }
  return `Restated for review: ${option}`;
}

function fixtureCold(quiz) {
  if (!Array.isArray(quiz) || quiz.length !== 3) {
    throw demoError("The review set could not be prepared.", "invalid_review");
  }
  return {
    quiz: quiz.map((item, index) => {
      const shift = (index + 1) % 4;
      const rotate = (values) => [...values.slice(shift), ...values.slice(0, shift)];
      return {
        ...item,
        stem: `Without looking back: ${item.stem}`,
        options: rotate(item.options).map(reword),
        answer: (item.answer - shift + 4) % 4,
        why: rotate(item.why),
        tag: rotate(item.tag),
      };
    }),
  };
}

export async function fixtureRequest(path, body) {
  await new Promise((resolve) => setTimeout(resolve, path === "evidence" ? 0 : 220));
  if (path === "plan") return fixturePlan(body.material);
  if (path === "lesson") return fixtureLesson(body.material, body.concept);
  if (path === "teachback") {
    return fixtureTeachback(body.material, body.concept, body.answer);
  }
  if (path === "cold") {
    normalizedMaterial(body.material);
    return fixtureCold(body.quiz);
  }
  if (path === "evidence") return { saved: true };
  throw demoError("This hosted demo action is unavailable.", "unsupported_action");
}

function abortError() {
  const error = new Error("PDF extraction was cancelled.");
  error.name = "AbortError";
  return error;
}

function throwIfAborted(signal) {
  if (signal?.aborted) throw abortError();
}

function reportPdfProgress(onProgress, progress) {
  if (typeof onProgress !== "function") return;
  try {
    onProgress(progress);
  } catch (_error) {
    // Progress rendering must never interrupt PDF extraction.
  }
}

function normalizePageText(rawText, preserveLines = false) {
  const text = String(rawText || "").replace(/\u0000/g, "");
  if (!preserveLines) return text.replace(/\s+/g, " ").trim();
  return text
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function abortable(promise, signal) {
  if (!signal) return promise;
  throwIfAborted(signal);
  return new Promise((resolve, reject) => {
    const onAbort = () => reject(abortError());
    signal.addEventListener("abort", onAbort, { once: true });
    promise.then(
      (value) => {
        signal.removeEventListener("abort", onAbort);
        resolve(value);
      },
      (error) => {
        signal.removeEventListener("abort", onAbort);
        reject(error);
      },
    );
  });
}

function createOcrCanvas() {
  if (typeof globalThis.OffscreenCanvas === "function") {
    return new globalThis.OffscreenCanvas(1, 1);
  }
  if (globalThis.document?.createElement) {
    return globalThis.document.createElement("canvas");
  }
  throw demoError(
    "This browser cannot run private text recognition for scanned PDF pages. Update the browser and try again.",
    "ocr_not_supported",
  );
}

function clearOcrCanvas(canvas) {
  canvas.width = 1;
  canvas.height = 1;
}

async function renderPageForOcr(pdfDocument, pageNumber, canvas, signal) {
  throwIfAborted(signal);
  const page = await abortable(pdfDocument.getPage(pageNumber), signal);
  let renderTask = null;
  const cancelRender = () => renderTask?.cancel();
  signal?.addEventListener("abort", cancelRender, { once: true });
  try {
    const baseViewport = page.getViewport({ scale: 1 });
    const basePixels = Math.max(1, baseViewport.width * baseViewport.height);
    const pixelScale = Math.sqrt(MAX_OCR_CANVAS_PIXELS / basePixels);
    const edgeScale =
      MAX_OCR_CANVAS_EDGE / Math.max(baseViewport.width, baseViewport.height, 1);
    const scale = Math.max(0.1, Math.min(OCR_RENDER_SCALE, pixelScale, edgeScale));
    const viewport = page.getViewport({ scale });
    canvas.width = Math.max(1, Math.ceil(viewport.width));
    canvas.height = Math.max(1, Math.ceil(viewport.height));
    const context = canvas.getContext("2d", {
      alpha: false,
      willReadFrequently: true,
    });
    if (!context) {
      throw demoError(
        "This browser could not prepare the scanned PDF page for text recognition.",
        "ocr_not_supported",
      );
    }
    context.save();
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.restore();
    renderTask = page.render({
      canvasContext: context,
      viewport,
      background: "rgb(255, 255, 255)",
    });
    await abortable(renderTask.promise, signal);
    return canvas;
  } catch (error) {
    if (signal?.aborted || error?.name === "RenderingCancelledException") {
      throw abortError();
    }
    throw error;
  } finally {
    signal?.removeEventListener("abort", cancelRender);
    page.cleanup();
  }
}

async function recognizeScannedPages(
  pdfDocument,
  pageRecords,
  candidatePageNumbers,
  { signal, onProgress },
) {
  if (!candidatePageNumbers.length) {
    return { ocrPageNumbers: [], lowConfidencePages: [], failedPages: [] };
  }

  reportPdfProgress(onProgress, {
    phase: "ocr_loading",
    totalPages: pdfDocument.numPages,
    ocrPageCount: candidatePageNumbers.length,
    progress: 0,
  });
  let tesseract;
  try {
    const tesseractModule = await import("./vendor/tesseract/tesseract.esm.min.js");
    tesseract = tesseractModule.default;
    if (typeof tesseract?.createWorker !== "function") throw new Error("OCR module unavailable");
  } catch (error) {
    if (signal?.aborted || error?.name === "AbortError") throw abortError();
    throw demoError(
      "Private text recognition files could not load. Check the connection once, then choose the PDF again.",
      "ocr_load_failed",
      true,
    );
  }
  throwIfAborted(signal);

  const baseUrl = new URL("./vendor/tesseract/", import.meta.url);
  const canvas = createOcrCanvas();
  let worker = null;
  let activePageNumber = candidatePageNumbers[0];
  let activeOcrIndex = 0;
  const workerPromise = tesseract.createWorker(
    OCR_LANGUAGES,
    tesseract.OEM?.LSTM_ONLY ?? 1,
    {
      workerPath: new URL("worker.min.js", baseUrl).href,
      corePath: new URL("core/", baseUrl).href,
      langPath: new URL("tessdata", baseUrl).href,
      workerBlobURL: false,
      logger: (message) => {
        const workerProgress = Number.isFinite(message?.progress)
          ? Math.max(0, Math.min(1, message.progress))
          : 0;
        reportPdfProgress(onProgress, {
          phase: message?.status === "recognizing text" ? "ocr" : "ocr_loading",
          page: activePageNumber,
          totalPages: pdfDocument.numPages,
          ocrPageIndex: activeOcrIndex,
          ocrPageCount: candidatePageNumbers.length,
          workerProgress,
          status: message?.status || "",
          progress:
            (Math.max(0, activeOcrIndex - 1) + workerProgress) /
            candidatePageNumbers.length,
        });
      },
    },
  );
  const terminateOnAbort = () => {
    if (worker) void worker.terminate();
  };
  signal?.addEventListener("abort", terminateOnAbort, { once: true });

  const ocrPageNumbers = [];
  const lowConfidencePages = [];
  const failedPages = [];
  try {
    try {
      worker = await abortable(workerPromise, signal);
    } catch (error) {
      if (signal?.aborted || error?.name === "AbortError") {
        void workerPromise.then((createdWorker) => createdWorker.terminate()).catch(() => {});
        throw abortError();
      }
      throw demoError(
        "Private text recognition could not start. Check the connection once so the OCR files can load, then choose the PDF again.",
        "ocr_load_failed",
        true,
      );
    }
    throwIfAborted(signal);
    await abortable(
      worker.setParameters({
        tessedit_pageseg_mode: "3",
        preserve_interword_spaces: "1",
        user_defined_dpi: "144",
      }),
      signal,
    );

    for (let index = 0; index < candidatePageNumbers.length; index += 1) {
      const pageNumber = candidatePageNumbers[index];
      activePageNumber = pageNumber;
      activeOcrIndex = index + 1;
      reportPdfProgress(onProgress, {
        phase: "ocr",
        page: pageNumber,
        totalPages: pdfDocument.numPages,
        ocrPageIndex: activeOcrIndex,
        ocrPageCount: candidatePageNumbers.length,
        workerProgress: 0,
        progress: index / candidatePageNumbers.length,
      });
      try {
        await renderPageForOcr(pdfDocument, pageNumber, canvas, signal);
        const result = await abortable(worker.recognize(canvas), signal);
        const recognizedText = normalizePageText(result?.data?.text, true);
        const nativeText = pageRecords.get(pageNumber)?.text || "";
        if (recognizedText.length > nativeText.length) {
          pageRecords.set(pageNumber, { text: recognizedText, method: "ocr" });
          ocrPageNumbers.push(pageNumber);
          if (Number.isFinite(result?.data?.confidence) && result.data.confidence < 45) {
            lowConfidencePages.push(pageNumber);
          }
        }
      } catch (error) {
        if (signal?.aborted || error?.name === "AbortError") throw abortError();
        failedPages.push(pageNumber);
      } finally {
        clearOcrCanvas(canvas);
      }
    }
    return { ocrPageNumbers, lowConfidencePages, failedPages };
  } finally {
    signal?.removeEventListener("abort", terminateOnAbort);
    clearOcrCanvas(canvas);
    if (worker) await worker.terminate().catch(() => {});
  }
}

export async function extractPdfInBrowser(file, { signal, onProgress } = {}) {
  throwIfAborted(signal);
  if (!file || (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf")) {
    throw demoError("Choose a PDF file.", "not_a_pdf");
  }
  if (file.size > MAX_PDF_BYTES) {
    throw demoError("Keep PDF files under 20 MB.", "pdf_too_large");
  }

  const pdfjs = await import("./vendor/pdf.mjs");
  pdfjs.GlobalWorkerOptions.workerSrc = new URL("./vendor/pdf.worker.mjs", import.meta.url).href;
  reportPdfProgress(onProgress, {
    phase: "opening",
    progress: 0,
  });
  const data = new Uint8Array(await file.arrayBuffer());
  throwIfAborted(signal);
  if (String.fromCharCode(...data.slice(0, 5)) !== "%PDF-") {
    throw demoError("This file does not appear to be a valid PDF.", "invalid_pdf");
  }

  let passwordRequired = false;
  const loadingTask = pdfjs.getDocument({
    data,
    cMapUrl: new URL("./vendor/cmaps/", import.meta.url).href,
    cMapPacked: true,
    standardFontDataUrl: new URL("./vendor/standard_fonts/", import.meta.url).href,
  });
  loadingTask.onPassword = () => {
    passwordRequired = true;
    loadingTask.destroy();
  };
  const abortLoading = () => loadingTask.destroy();
  signal?.addEventListener("abort", abortLoading, { once: true });

  let pdfDocument;
  try {
    try {
      pdfDocument = await loadingTask.promise;
    } catch (error) {
      if (signal?.aborted) throw abortError();
      if (passwordRequired || error?.name === "PasswordException") {
        throw demoError(
          "Password-protected PDFs are not supported. Upload an unlocked copy.",
          "encrypted_pdf",
        );
      }
      throw demoError(
        "The PDF could not be read. Export a fresh PDF and choose it again.",
        "invalid_pdf",
      );
    }

    throwIfAborted(signal);
    if (pdfDocument.numPages > MAX_PDF_PAGES) {
      throw demoError("Keep PDF files to 80 pages or fewer.", "pdf_too_many_pages");
    }
    const pageRecords = new Map();
    const ocrCandidates = [];
    const warnings = [];
    for (let pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber += 1) {
      throwIfAborted(signal);
      reportPdfProgress(onProgress, {
        phase: "reading",
        page: pageNumber,
        totalPages: pdfDocument.numPages,
        progress: (pageNumber - 1) / pdfDocument.numPages,
      });
      let page = null;
      try {
        page = await abortable(pdfDocument.getPage(pageNumber), signal);
        const textContent = await abortable(page.getTextContent(), signal);
        const text = normalizePageText(
          textContent.items
            .map((item) => ("str" in item ? item.str : ""))
            .join(" "),
        );
        pageRecords.set(pageNumber, { text, method: "text_layer" });
        if (text.length < MIN_PAGE_TEXT_CHARS) ocrCandidates.push(pageNumber);
      } catch (_error) {
        if (signal?.aborted) throw abortError();
        pageRecords.set(pageNumber, { text: "", method: "unreadable" });
        ocrCandidates.push(pageNumber);
      } finally {
        page?.cleanup();
      }
    }

    const ocrResult = await recognizeScannedPages(
      pdfDocument,
      pageRecords,
      ocrCandidates,
      { signal, onProgress },
    );
    const pageSections = [];
    let extractedPages = 0;
    let readableCharacters = 0;
    for (let pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber += 1) {
      const text = pageRecords.get(pageNumber)?.text?.trim() || "";
      if (!text) continue;
      extractedPages += 1;
      readableCharacters += text.length;
      pageSections.push(`[Page ${pageNumber}]\n${text}`);
    }

    if (readableCharacters < MIN_MATERIAL_CHARS) {
      throw demoError(
        `Text recognition found only ${readableCharacters} readable characters. Try a clearer or higher-resolution PDF with at least one complete sentence (${MIN_MATERIAL_CHARS} characters).`,
        "pdf_too_little_text",
      );
    }

    if (ocrResult.ocrPageNumbers.length) {
      warnings.push(
        `OCR read ${ocrResult.ocrPageNumbers.length} scanned page(s). Review the extracted text because image recognition can contain errors.`,
      );
    }
    if (ocrResult.lowConfidencePages.length) {
      warnings.push(
        `OCR confidence was low on page(s) ${ocrResult.lowConfidencePages.join(", ")}.`,
      );
    }
    if (ocrResult.failedPages.length) {
      warnings.push(
        `Page(s) ${ocrResult.failedPages.join(", ")} could not be recognized and were skipped.`,
      );
    }

    let text = pageSections.join("\n\n");
    let truncated = false;
    if (text.length > MAX_MATERIAL_CHARS) {
      text = text.slice(0, MAX_MATERIAL_CHARS).trimEnd();
      truncated = true;
      warnings.push(
        "Only the first 24,000 extracted characters are used in this prototype.",
      );
    }
    if (extractedPages < pdfDocument.numPages) {
      warnings.push(
        `${pdfDocument.numPages - extractedPages} page(s) did not contain readable text and were skipped.`,
      );
    }
    reportPdfProgress(onProgress, {
      phase: "complete",
      page: pdfDocument.numPages,
      totalPages: pdfDocument.numPages,
      progress: 1,
    });
    return {
      filename: file.name,
      text,
      page_count: pdfDocument.numPages,
      extracted_pages: extractedPages,
      ocr_pages: ocrResult.ocrPageNumbers.length,
      truncated,
      warnings,
    };
  } finally {
    signal?.removeEventListener("abort", abortLoading);
    if (typeof pdfDocument?.cleanup === "function") await pdfDocument.cleanup();
    await loadingTask.destroy().catch(() => {});
  }
}
