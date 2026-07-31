# Sparring

**The AI study coach that refuses to think for you.**

[Open the live AI demo](https://sparring-ai-study-coach.onrender.com/) ·
[View the source](https://github.com/jiangggqr/sparring-ai-study-coach)

Sparring turns a learner's own PDF or pasted text into a short practice cycle:
predict, retrieve, judge confidence, explain relationships, and return later for a
reworded cold review.

It is not a general chatbot and it does not search the web. AI structures and
diagnoses the practice; the learner still makes every prediction, answer, confidence
judgment, and explanation.

## What the prototype does

1. Upload a text-based or scanned PDF, or paste a passage.
2. Generate exactly three source-grounded concepts and one observable session target.
3. Make a low-stakes prediction before the explanation.
4. Read one focused explanation and compare it with the prediction.
5. Answer definition, mechanism, and application questions.
6. Commit both an answer and a 1-5 confidence judgment before feedback.
7. Receive feedback that distinguishes high-confidence errors, uncertain errors,
   uncertain correct answers, and confident correct answers.
8. Teach the concept back in two lines and revise one missing relationship when needed.
9. Return on a transparent 1-3-7 day schedule for a reworded, no-hint cold review.

The interface calls all results **practice evidence**, not proof of permanent mastery.
The 1-3-7 schedule is an implementation heuristic, not a universal optimum.

## PDF support

- Text-based and scanned/image-only PDFs up to 20 MB and 80 pages.
- One complete sentence (40 readable characters) is enough to begin; there is no
  200-character paste requirement after a PDF is ready.
- Page markers are retained in the extracted study text.
- In the live AI demo, text-layer extraction runs in FastAPI server memory. Pages without
  enough selectable text automatically fall back to self-hosted Tesseract.js OCR in
  English and Simplified Chinese in the browser. Uploaded files are not stored.
- OCR runs one page at a time, shows page-level progress, can be cancelled, and reports
  partial results and low-confidence pages without erasing existing work.
- In the FastAPI build, text-layer PDF bytes are processed in server memory and are not
  written to disk; image-only PDFs use the same browser OCR fallback.
- The prototype uses at most the first 24,000 extracted characters and reports
  truncation clearly.
- Password-protected PDFs require an unlocked copy. Very low-resolution scans may still
  need a clearer export, and OCR text remains editable before practice begins.

In the live FastAPI build, extracted text is sent to the configured OpenAI model when AI
steps run. The explicit GitHub Pages fallback keeps extraction local and uses deterministic
practice fixtures. Browser progress, including extracted text, is saved in localStorage
on that device.

## Run locally

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Add a server-side OpenAI key to `.env`, then run:

```bash
uvicorn app.main:app --reload --port 8100
```

This command starts a local development server on port 8100. It is available only on
the computer running it; judges and other visitors should use the public live demo linked
at the top of this README.

### Deterministic demo mode

Automated tests and offline judging rehearsals use deterministic fixtures:

```bash
SPARRING_MODE=fixture uvicorn app.main:app --port 8100
```

Fixture mode and real-model execution are separate code paths. A real-model failure is
never silently replaced with a fixture response, and there is no evaluator switch or
mode badge in the learner UI.

### Live AI demo and deterministic fallback

The official live demo runs the FastAPI application and uses GPT-5.6-sol through the
server-side OpenAI Responses API:

https://sparring-ai-study-coach.onrender.com/

GitHub Pages now redirects to that live AI application. A deterministic browser-only
fallback remains available explicitly at:

https://jiangggqr.github.io/sparring-ai-study-coach/?staticDemo=1

The fallback uses the same interaction flow without a model key. PDF extraction,
scanned-page OCR, practice generation, and practice state remain on that device. It is
for deterministic fallback and test use, not the official AI demo.

## AI boundary

| Stage | AI's bounded job | Learner's job |
| --- | --- | --- |
| Plan | Extract three concepts, a target, and verbatim source anchors | Supply the source |
| Predict | Ask a curiosity question without revealing the answer | Commit a prediction |
| Explain | Produce one concise, source-grounded explanation | Compare it with the prediction |
| Quiz | Build misconception-oriented options and rationales | Answer and rate confidence |
| Teach-back | Heuristically check whether ideas are linked or listed | Explain and revise |
| Cold review | Reword the same objective while preserving source anchors | Recall without hints |

OpenAI calls use the Responses API with Pydantic Structured Outputs. Every generated
plan and lesson source anchor is checked against the supplied material before it is
returned to the browser. This reduces unsupported output; it is not a claim that any
generative system is infallible.

## Architecture

```text
Static HTML/CSS/JS
  |- PDF.js text extraction
  |- Tesseract.js scanned-page OCR (browser only)
  `- same-origin JSON / multipart requests
                     |
                     v
FastAPI
  |- in-memory PDF text extraction (pypdf)
  |- source-anchor validation
  |- OpenAI Responses API + Structured Outputs
  `- SQLite observation-only learning evidence
```

- API keys never enter client code.
- The SQLite evidence table stores event type, concept, score, confidence, linked
  status, and review stage. It does not store PDF bytes, source text, or learner answers.
- localStorage enables exact refresh recovery for prediction, question, teach-back, and
  cold-review stages.
- A service worker caches the static shell so already-loaded work can be reopened when
  the server is temporarily unreachable. New AI or PDF extraction requests still need a
  connection.

See [ARCHITECTURE.md](ARCHITECTURE.md) for contracts and failure states.

## Test

```bash
pytest
node --check static/app.js
node --check static/sw.js
```

The current suite covers API schemas, source anchoring, material limits, PDF extraction
and failure cases, the self-hosted OCR contract, teach-back revision, cold-review drift
checks, privacy-minimized evidence, missing-key behavior, security headers, accessibility
contracts, autosave, offline shell caching, and completion-state persistence. Real-browser
rehearsals cover English scans, Simplified Chinese scans, mixed text/scanned PDFs,
cancellation recovery, and 390 px mobile reflow.

## Deploy

### Public live AI demo

The official public, no-sign-in FastAPI and GPT-5.6-sol demo is:

https://sparring-ai-study-coach.onrender.com/

The GitHub Pages root redirects to the live AI demo. For an explicitly selected
deterministic fallback, use:

https://jiangggqr.github.io/sparring-ai-study-coach/?staticDemo=1

### FastAPI deployment

The repository includes:

- `Dockerfile` for any container host;
- `render.yaml` for Render;
- `/api/health` for deployment health checks.

Set `OPENAI_API_KEY`, keep `SPARRING_MODE=real`, and optionally override
`SPARRING_MODEL`. The FastAPI deployment exposes `/api/health`. SQLite on the included
free Render configuration is ephemeral and is used only for non-identifying practice
evidence.

## Known limitations

- No account or cross-device sync.
- OCR supports English and Simplified Chinese prose, but complex tables, equations,
  handwriting, vertical text, and low-resolution scans may be inaccurate.
- The learning engine uses extracted text; it does not reason directly over PDF layout,
  charts, or images.
- No notification delivery; reviews become due when the learner reopens the app.
- The browser can inspect client-delivered quiz answer data, so this is low-stakes
  practice rather than secure assessment.
- Learning-science-informed interaction has been implemented and tested as software;
  no controlled learning-outcome study has been run.

## Hackathon

Built as a new project for the
[Prometheus July AI Challenge](https://prometheus-july-ai-challenge.devpost.com/).
The official submission asks for a working educational AI prototype, a source-code
repository, and a demo video no longer than two minutes.

Submission assets, the natural English voiceover, and burn-in subtitle file are in
[`submission/`](submission/).

PDF.js and Tesseract.js are Apache-2.0. The pinned English and Simplified Chinese
language-data packages declare MIT. Vendored versions, checksums, and notices are in
[`static/vendor/`](static/vendor/).

## License

[MIT](LICENSE)
