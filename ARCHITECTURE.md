# Sparring architecture and contracts

## Product contract

The learner's uploaded PDF or pasted text is the only source. Sparring does not expose a
general chat box or a web-search tool. The active concept is taught and tested before the
app advances.

## Request flow

```mermaid
flowchart LR
    A["PDF upload or pasted text"] --> B["FastAPI validation"]
    B --> C["In-memory PDF extraction"]
    C --> D["Three-concept plan"]
    D --> E["Prediction"]
    E --> F["Explanation + 3 questions"]
    F --> G["Answer + confidence"]
    G --> H["Teach-back + one revision"]
    H --> I["1 / 3 / 7 review queue"]
    I --> J["Reworded cold review"]
```

The public GitHub Pages build is a judge-friendly adapter for the same interface. It
uses deterministic browser fixtures and a vendored Apache-2.0 PDF.js parser, so it can
be tried without distributing a model key. In that hosted build, both PDF extraction
and practice generation stay on the device. The FastAPI path remains the real-model
implementation and never silently falls back to fixtures.

## Structured output contracts

- `StudyPlan`: one observable target and exactly three unique concepts.
- `LessonOutput`: concise explanation; definition, mechanism, and application questions;
  one teach-back prompt.
- `QuizItem`: four options, a bounded answer index, one rationale and misconception tag
  per option, and a verbatim source anchor.
- `TeachbackOutput`: linked/listed heuristic, covered points, missing points, one feedback
  statement, and an optional repair sentence stem.
- `ColdQuiz`: exactly three variants that preserve item type and source anchor.

Pydantic forbids extra model fields. Cold-review variants are rejected if they keep the
same wording, change the item type, or change the source anchor.

## PDF contract

`POST /api/extract/pdf` accepts one multipart PDF:

- maximum 20 MB;
- maximum 80 pages;
- `%PDF-` magic header required;
- password-protected documents rejected;
- at least one complete sentence (40 readable characters);
- source markers use `[Page N]`;
- no upload bytes are written to disk.

If extracted text exceeds the 24,000-character learning-material cap, the API truncates
it and returns an explicit warning.

The hosted Pages adapter applies the same 20 MB, 80-page, text-only, page-marker, and
24,000-character limits in the browser. PDF.js and its worker are served from the same
origin; no third-party CDN receives the document.

## State and evidence

The browser owns resumable learning state. The server owns only observation events:

```text
session_id, event_type, concept, score, confidence,
linked, review_stage, created_at
```

The evidence table intentionally has no recommendation, source material, PDF, or learner
answer columns.

Review items use ISO local dates and explicit states:

- `scheduled`
- `scheduled_reviews_complete`

The final state uses `dueAt: null`; it never relies on `Infinity`, which JSON would
silently convert to `null` without an explicit status.

## Failure behavior

| Failure | Learner-visible behavior |
| --- | --- |
| Missing API key | Honest configuration error; no fixture fallback |
| Model timeout | Retry the same saved step |
| Invalid structured output | Incomplete-step error; no partial model text shown |
| Unverified source anchor | Response rejected and retry offered |
| Encrypted/scanned PDF | Export searchable copy or paste text |
| Offline during generated step | Draft retained; retry after connection |
| Evidence sync failure | Learning continues; event remains queued locally |
| Corrupt localStorage | Damaged state set aside; safe fresh session opens |

## Accessibility intent

- semantic headings, regions, forms, fieldsets, legends, and native radios;
- explicit answer and confidence choices with no confidence default;
- visible focus, skip link, title updates, and post-render focus management;
- non-color-only correct/incorrect labels;
- polite status and assertive error announcements;
- reduced-motion and forced-colors handling;
- responsive reflow at tablet and phone widths.

This is WCAG 2.2 AA intent and engineering verification, not a third-party compliance
certification.
