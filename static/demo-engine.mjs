const MAX_PDF_BYTES = 20 * 1024 * 1024;
const MAX_PDF_PAGES = 80;
const MAX_MATERIAL_CHARS = 24_000;
const MIN_MATERIAL_CHARS = 200;
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
      `Paste at least ${MIN_MATERIAL_CHARS} characters of study material.`,
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
  const names = pieces.slice(0, 3).map(conceptName);
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

export async function extractPdfInBrowser(file) {
  if (!file || (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf")) {
    throw demoError("Choose a PDF file.", "not_a_pdf");
  }
  if (file.size > MAX_PDF_BYTES) {
    throw demoError("Keep PDF files under 20 MB.", "pdf_too_large");
  }

  const pdfjs = await import("./vendor/pdf.mjs");
  pdfjs.GlobalWorkerOptions.workerSrc = new URL("./vendor/pdf.worker.mjs", import.meta.url).href;
  const data = new Uint8Array(await file.arrayBuffer());
  if (new TextDecoder("latin1").decode(data.slice(0, 5)) !== "%PDF-") {
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

  let document;
  try {
    document = await loadingTask.promise;
  } catch (error) {
    if (passwordRequired || error?.name === "PasswordException") {
      throw demoError(
        "Password-protected PDFs are not supported. Upload an unlocked copy or paste the text.",
        "encrypted_pdf",
      );
    }
    throw demoError(
      "The PDF could not be read. Try a searchable PDF or paste the relevant text.",
      "invalid_pdf",
    );
  }

  try {
    if (document.numPages > MAX_PDF_PAGES) {
      throw demoError("Keep PDF files to 80 pages or fewer.", "pdf_too_many_pages");
    }
    const pageSections = [];
    const warnings = [];
    let extractedPages = 0;
    for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
      try {
        const page = await document.getPage(pageNumber);
        const textContent = await page.getTextContent();
        const text = textContent.items
          .map((item) => ("str" in item ? item.str : ""))
          .join(" ")
          .replace(/\s+/g, " ")
          .trim();
        if (text) {
          extractedPages += 1;
          pageSections.push(`[Page ${pageNumber}]\n${text}`);
        }
      } catch (_error) {
        warnings.push(`Page ${pageNumber} could not be read and was skipped.`);
      }
    }

    if (!pageSections.length) {
      throw demoError(
        "No selectable text was found. Upload an OCR/searchable PDF or paste the relevant text.",
        "pdf_no_text",
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
    if (extractedPages < document.numPages) {
      warnings.unshift(
        `${document.numPages - extractedPages} page(s) contained no selectable text.`,
      );
    }
    return {
      filename: file.name,
      text,
      page_count: document.numPages,
      extracted_pages: extractedPages,
      truncated,
      warnings,
    };
  } finally {
    if (typeof document.cleanup === "function") await document.cleanup();
    await loadingTask.destroy();
  }
}
