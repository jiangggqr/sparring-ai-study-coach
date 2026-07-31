const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(
  "/Applications/ChatGPT.app/Contents/Resources/cua_node/lib/node_modules/playwright",
);

const LIVE_URL = "https://sparring-ai-study-coach.onrender.com/?recording=final";
const SCANNED_PDF = "/private/tmp/sparring-arcadia-scanned.pdf";
const ROOT = __dirname;
const SOURCE_DIR = path.join(ROOT, "source");
const VIDEO_PATH = path.join(SOURCE_DIR, "live-demo-source.webm");
const MARKERS_PATH = path.join(SOURCE_DIR, "live-demo-markers.json");

fs.mkdirSync(SOURCE_DIR, { recursive: true });

function compact(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  let context;
  try {
    context = await browser.newContext({
      viewport: { width: 1440, height: 810 },
      recordVideo: {
        dir: SOURCE_DIR,
        size: { width: 1440, height: 810 },
      },
      colorScheme: "light",
      reducedMotion: "no-preference",
    });

    await context.addInitScript(() => {
      const installCursor = () => {
        if (document.getElementById("demo-cursor")) return;
        const style = document.createElement("style");
        style.textContent = `
          #demo-cursor {
            position: fixed;
            z-index: 2147483647;
            width: 22px;
            height: 22px;
            border: 3px solid #0d6b57;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.94);
            box-shadow: 0 2px 10px rgba(13, 107, 87, 0.25);
            pointer-events: none;
            opacity: 0;
            transform: translate(-50%, -50%) scale(1);
            transition: opacity 120ms ease, transform 130ms ease;
          }
          #demo-cursor.visible { opacity: 1; }
          #demo-cursor.clicking { transform: translate(-50%, -50%) scale(0.72); }
        `;
        document.head.appendChild(style);
        const cursor = document.createElement("div");
        cursor.id = "demo-cursor";
        document.body.appendChild(cursor);
        document.addEventListener("mousemove", (event) => {
          cursor.style.left = `${event.clientX}px`;
          cursor.style.top = `${event.clientY}px`;
          cursor.classList.add("visible");
        });
        document.addEventListener("mousedown", () => {
          cursor.classList.add("clicking");
        });
        document.addEventListener("mouseup", () => {
          window.setTimeout(() => cursor.classList.remove("clicking"), 90);
        });
      };
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installCursor);
      } else {
        installCursor();
      }
    });

    const page = await context.newPage();
    const video = page.video();
    const startedAt = Date.now();
    const clips = [];
    const lessonResponses = [];
    const browserFailures = [];

    page.on("pageerror", (error) => {
      browserFailures.push(`pageerror: ${error.message}`);
    });
    page.on("requestfailed", (request) => {
      browserFailures.push(
        `${request.method()} ${request.url()} ${request.failure()?.errorText}`,
      );
    });
    page.on("response", async (response) => {
      if (!response.url().endsWith("/api/lesson") || !response.ok()) return;
      try {
        lessonResponses.push(await response.json());
      } catch (_error) {
        // The visible UI remains the source of truth if diagnostic capture fails.
      }
    });

    const now = () => (Date.now() - startedAt) / 1000;
    const beginClip = (name) => ({ name, start: now() });
    const endClip = (clip) => {
      clip.end = now();
      clips.push(clip);
    };
    const hold = (milliseconds) => page.waitForTimeout(milliseconds);

    async function moveTo(locator) {
      await locator.scrollIntoViewIfNeeded();
      const box = await locator.boundingBox();
      if (!box) throw new Error("Could not locate a visible recording target.");
      await page.mouse.move(
        box.x + Math.min(box.width * 0.5, box.width - 12),
        box.y + Math.min(box.height * 0.5, box.height - 12),
        { steps: 18 },
      );
      await hold(180);
    }

    async function moveAndClick(locator) {
      await moveTo(locator);
      await locator.click();
    }

    async function waitForLesson(number) {
      const deadline = Date.now() + 15_000;
      while (lessonResponses.length < number && Date.now() < deadline) {
        await hold(100);
      }
      if (lessonResponses.length < number) {
        throw new Error(`Lesson response ${number} was not captured.`);
      }
      return lessonResponses[number - 1];
    }

    async function answerCurrentQuestion(lesson, index, options = {}) {
      const question = lesson.quiz[index];
      const selected = options.wrong
        ? (question.answer + 1) % question.options.length
        : question.answer;
      const answerLabel = page.locator(
        `label.option:has(input[name="answer"][value="${selected}"])`,
      );
      const confidence = options.confidence || 3;
      const confidenceLabel = page.locator(
        `label.confidence-choice:has(input[name="confidence"][value="${confidence}"])`,
      );
      await moveAndClick(answerLabel);
      await moveAndClick(confidenceLabel);
      await moveAndClick(page.locator("#lock-answer"));
      await page.locator(".feedback-card").waitFor({
        state: "visible",
        timeout: 30_000,
      });
      await hold(360);
    }

    async function finishQuiz(lesson, recordKinds = false) {
      for (let index = 0; index < 3; index += 1) {
        if (recordKinds && index > 0) {
          const kindClip = beginClip(`quiz_kind_${index + 1}`);
          await hold(1250);
          endClip(kindClip);
        }
        await answerCurrentQuestion(lesson, index, {
          wrong: index === 0 && recordKinds,
          confidence: index === 0 && recordKinds ? 5 : 3,
        });
        if (index === 0 && recordKinds) {
          await page.mouse.wheel(0, 360);
          await hold(250);
          const feedbackClip = beginClip("confidence_feedback");
          await hold(3600);
          endClip(feedbackClip);
        }
        await moveAndClick(page.locator("#next-question"));
        await hold(350);
      }
    }

    async function checkTeachback(answer) {
      await page.locator("#teachback").fill(answer);
      await moveAndClick(page.locator("#check-teachback"));
      await page.locator(".feedback-card h3").waitFor({
        state: "visible",
        timeout: 240_000,
      });
      await hold(360);
      return compact(await page.locator(".feedback-card h3").innerText());
    }

    await page.goto(LIVE_URL, {
      waitUntil: "networkidle",
      timeout: 120_000,
    });
    await page.evaluate(async () => {
      localStorage.clear();
      const registrations = await navigator.serviceWorker?.getRegistrations?.();
      await Promise.all((registrations || []).map((item) => item.unregister()));
      const names = await caches.keys();
      await Promise.all(names.map((name) => caches.delete(name)));
    });
    await page.reload({ waitUntil: "networkidle", timeout: 120_000 });
    await page.mouse.move(1180, 160, { steps: 8 });

    const homeClip = beginClip("home");
    await hold(3000);
    endClip(homeClip);

    const uploadZone = page.locator("label[for='pdf-upload']");
    await moveTo(uploadZone);
    const uploadClip = beginClip("upload_and_ocr");
    await page.locator("#pdf-upload").setInputFiles(SCANNED_PDF);
    await page.locator("#pdf-progress").waitFor({
      state: "visible",
      timeout: 15_000,
    });
    await hold(2800);
    endClip(uploadClip);

    await page.locator(".source-ready").waitFor({
      state: "visible",
      timeout: 240_000,
    });
    const readyClip = beginClip("pdf_ready");
    await hold(2600);
    endClip(readyClip);

    await moveAndClick(page.locator("#build-plan"));
    const planLoadingClip = beginClip("plan_loading");
    await hold(2200);
    endClip(planLoadingClip);
    await page.locator("#accept-plan").waitFor({
      state: "visible",
      timeout: 240_000,
    });
    await hold(400);

    const planClip = beginClip("practice_map");
    await hold(2700);
    await page.mouse.wheel(0, 620);
    await hold(2500);
    endClip(planClip);

    await moveAndClick(page.locator("#accept-plan"));
    await page.locator("#prediction").waitFor({ state: "visible" });
    const predictionClip = beginClip("prediction");
    await hold(700);
    await page.locator("#prediction").fill(
      "Humidity starts misting, while salinity changes fertilizer timing.",
    );
    await hold(1450);
    await moveAndClick(page.locator("#load-lesson"));
    await hold(1200);
    endClip(predictionClip);

    await page.locator("#begin-quiz").waitFor({
      state: "visible",
      timeout: 240_000,
    });
    const lessonOne = await waitForLesson(1);
    const explanationClip = beginClip("explanation");
    await hold(4100);
    endClip(explanationClip);

    await moveAndClick(page.locator("#begin-quiz"));
    await hold(350);
    const definitionClip = beginClip("quiz_kind_1");
    await hold(1700);
    endClip(definitionClip);
    await finishQuiz(lessonOne, true);

    await page.locator("#teachback").waitFor({ state: "visible" });
    const teachbackEntryClip = beginClip("teachback_entry");
    await hold(900);
    await page.locator("#teachback").fill(
      "Humidity is one reading. Salinity is another reading.",
    );
    await hold(1100);
    await moveAndClick(page.locator("#check-teachback"));
    await hold(1400);
    endClip(teachbackEntryClip);
    await page.locator(".feedback-card h3").waitFor({
      state: "visible",
      timeout: 240_000,
    });
    const firstTeachbackHeading = compact(
      await page.locator(".feedback-card h3").innerText(),
    );
    const teachbackFeedbackClip = beginClip("teachback_feedback");
    await hold(3000);
    endClip(teachbackFeedbackClip);

    if (firstTeachbackHeading.includes("Revise")) {
      await page.locator("#teachback").fill(
        "Low humidity starts misting because it falls below 45 percent, while the valves close only after humidity rises above 58 percent and salinity falls below 1.8.",
      );
      const revisionClip = beginClip("teachback_revision");
      await hold(1200);
      await moveAndClick(page.locator("#check-teachback"));
      await page.locator(".feedback-card h3").waitFor({
        state: "visible",
        timeout: 240_000,
      });
      await hold(2600);
      endClip(revisionClip);
    }

    await moveAndClick(page.locator("#complete-concept"));
    await page.locator("#prediction").waitFor({ state: "visible" });

    const remainingConcepts = [
      {
        prediction:
          "High salinity should pause fertilizer while water keeps flowing.",
        teachback:
          "After misting begins, salinity above 1.8 pauses fertilizer for thirty minutes while water continues, so fertilizer timing changes without closing the valves.",
      },
      {
        prediction:
          "Both recovered humidity and lower salinity are needed to close the valves.",
        teachback:
          "The recovery check closes the valves only when humidity is above 58 percent and salinity is below 1.8, because either condition alone is insufficient.",
      },
    ];

    for (let offset = 0; offset < remainingConcepts.length; offset += 1) {
      const concept = remainingConcepts[offset];
      await page.locator("#prediction").fill(concept.prediction);
      await moveAndClick(page.locator("#load-lesson"));
      await page.locator("#begin-quiz").waitFor({
        state: "visible",
        timeout: 240_000,
      });
      const lesson = await waitForLesson(offset + 2);
      await moveAndClick(page.locator("#begin-quiz"));
      await finishQuiz(lesson, false);
      await page.locator("#teachback").waitFor({ state: "visible" });
      let result = await checkTeachback(concept.teachback);
      if (result.includes("Revise")) {
        result = await checkTeachback(concept.teachback);
      }
      await moveAndClick(page.locator("#complete-concept"));
      await hold(350);
    }

    await page.getByText("Now let time do its part.", { exact: true }).waitFor({
      state: "visible",
      timeout: 30_000,
    });
    const dashboardClip = beginClip("review_dashboard");
    await hold(3600);
    endClip(dashboardClip);

    await moveAndClick(page.locator("#advance-day"));
    await page.locator("#start-review").waitFor({ state: "visible" });
    const dueClip = beginClip("review_due");
    await hold(2200);
    endClip(dueClip);

    await moveAndClick(page.locator("#start-review"));
    await page.locator("#load-cold-review").waitFor({ state: "visible" });
    const reviewIntroClip = beginClip("cold_review_intro");
    await hold(2800);
    endClip(reviewIntroClip);

    await moveAndClick(page.locator("#load-cold-review"));
    await hold(1300);
    await page.locator("#cold-form").waitFor({
      state: "visible",
      timeout: 240_000,
    });
    const coldQuestionClip = beginClip("cold_review_question");
    await hold(3800);
    endClip(coldQuestionClip);

    const finalState = {
      sourceUrl: LIVE_URL,
      scannedPdf: path.basename(SCANNED_PDF),
      clips,
      lessonCount: lessonResponses.length,
      firstTeachbackHeading,
      finalTitle: await page.title(),
      browserFailures,
    };

    await page.close();
    await context.close();
    context = undefined;
    const temporaryVideo = await video.path();
    fs.copyFileSync(temporaryVideo, VIDEO_PATH);
    fs.writeFileSync(MARKERS_PATH, JSON.stringify(finalState, null, 2));
    process.stdout.write(JSON.stringify({ video: VIDEO_PATH, ...finalState }, null, 2));
  } finally {
    if (context) await context.close().catch(() => {});
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
