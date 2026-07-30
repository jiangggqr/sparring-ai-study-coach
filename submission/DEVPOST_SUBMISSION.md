# Sparring - Devpost submission draft

## Project identity

**Name:** Sparring

**Tagline:** The AI study coach that refuses to think for you.

**One-line description:** Sparring turns a learner's own PDF into prediction, retrieval,
confidence judgment, teach-back, and spaced cold review - while keeping every meaningful
learning action with the learner.

**Source code:** https://github.com/jiangggqr/sparring-ai-study-coach

## Inspiration

AI can produce fluent explanations and answers in seconds. That convenience can create
the feeling of understanding before a learner has retrieved, judged, explained, or
reconstructed the idea. We wanted an AI learning tool whose contract is the opposite:
AI removes the setup work, but not the learning work.

## What it does

A learner uploads a text-based PDF or pastes a passage. Sparring extracts exactly three
concepts and one observable target. For each concept, the learner:

1. commits a low-stakes prediction;
2. compares it with one concise source-grounded explanation;
3. answers definition, mechanism, and application questions;
4. selects a confidence rating before any feedback;
5. teaches the relationship back in two lines and revises one gap when needed.

The concepts return on a transparent 1-3-7 day schedule. Each cold review changes the
surface wording, preserves the source anchor, hides hints until completion, and records
practice evidence without claiming permanent mastery.

## How we built it

- FastAPI and Uvicorn
- static semantic HTML, CSS, and JavaScript
- OpenAI Responses API with Pydantic Structured Outputs
- pypdf for in-memory PDF text extraction
- SQLite for observation-only practice evidence
- localStorage and a service worker for precise resume and recovery
- Docker and Render deployment configuration

Model credentials remain on the server. Generated source anchors are verified against
the learner's supplied material before they reach the UI. Deterministic fixtures are
separate from real-model execution so tests remain stable without masking production
failures.

## Challenges

The hardest design problem was keeping AI central without allowing it to do the learner's
work. We separated each responsibility: AI structures the practice and diagnoses a
response; the learner predicts, answers, judges confidence, explains, and returns later.

The hardest engineering problem was source integrity. Strict schemas alone are not enough,
so the server also rejects plan, lesson, or cold-review items whose source anchors cannot
be verified against the uploaded material.

## Accomplishments

- Complete PDF-to-cold-review flow in one responsive page.
- Explicit no-default confidence judgment before feedback.
- Different feedback for high-confidence errors and uncertain answers.
- Teach-back revision instead of automatically advancing after a weak explanation.
- Real date-based 1-3-7 review queue that remains complete after refresh.
- Recoverable loading, invalid PDF, missing key, model error, offline, and damaged saved
  state paths.
- Automated API and UI-contract coverage plus a full real-browser rehearsal.

## What we learned

Learning software needs stricter language than ordinary productivity software. A correct
answer is not permanent mastery, a confidence rating is not a metacognition score, and a
teach-back model judgment is a heuristic rather than an objective diagnosis. Those
distinctions changed both the interface and the data model.

## What's next

- OCR for scanned PDFs.
- A generated short-answer application item in delayed review.
- Optional account-based cross-device review sync.
- A small learner study measuring usability, delayed recall, and confidence-pattern
  changes without overclaiming outcomes.

## Judging alignment

### Educational impact

Sparring addresses passive AI reliance with observable learning actions. The prototype is
learning-science-informed; it does not claim that this demo proves improved grades or
long-term retention.

### Creative use of AI/ML

AI is not a chat ornament. It extracts learning structure, generates
misconception-oriented items, compares answer and confidence evidence, gives bounded
teach-back feedback, and constructs source-preserving cold variants.

### Technical execution

The demonstrated path is functional, source-checked, keyboard-operable, refresh-resumable,
and covered by deterministic tests. API keys remain server-side and PDF files are processed
in memory.

### Pitch and demo

The video shows one uninterrupted story: upload PDF, predict, commit a high-confidence
error, revise a teach-back, and return for a cold review. It targets 1:55-1:57, uses natural
English narration, and includes burned-in English subtitles.

## Claims policy

Safe claims:

- "Sparring requires an attempt before feedback."
- "Learners commit both an answer and a confidence judgment."
- "PDF text and generated source anchors are checked within the supplied material."
- "The prototype creates a default 1-3-7 review schedule."
- "Teach-back feedback is a heuristic relationship check."

Do not claim:

- scientifically proven improvement in grades, retention, or transfer;
- permanent or verified mastery;
- objective measurement of metacognition or understanding;
- zero hallucinations;
- OCR or PDF visual understanding;
- full personalization;
- medical or ADHD outcomes.
