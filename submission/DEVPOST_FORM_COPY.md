# Sparring - Devpost form copy

## Elevator pitch

**The AI study coach that refuses to think for you.**

## About the project

# Sparring

**Live AI demo:** [sparring-ai-study-coach.onrender.com](https://sparring-ai-study-coach.onrender.com/)  
**Source code:** [github.com/jiangggqr/sparring-ai-study-coach](https://github.com/jiangggqr/sparring-ai-study-coach)

## Inspiration

Generative AI can produce polished explanations and answers in seconds. That is useful,
but it can also create the feeling of understanding before a learner has actually
retrieved an idea, tested a prediction, explained a relationship, or returned to it
later.

I wanted to build an AI learning tool with a different contract: let AI remove the setup
work, but keep the meaningful thinking with the learner.

Sparring is informed by prediction, retrieval practice, confidence calibration,
self-explanation, and delayed review. It does not search the web or replace the learner's
source material. The uploaded material remains the basis for every concept, explanation,
question, and review.

## What it does

A learner uploads a text-based or scanned PDF, or pastes a passage. Sparring then uses
GPT-5.6-sol to create exactly three source-grounded concepts and one observable session
target.

For each concept, the learner:

1. makes a low-stakes prediction before seeing the explanation;
2. compares that prediction with one focused explanation and its source anchor;
3. answers definition, mechanism, and application questions;
4. commits both an answer and a 1-5 confidence judgment before receiving feedback;
5. receives feedback that distinguishes, for example, a high-confidence error from an
   uncertain answer;
6. teaches the relationship back in their own words and revises a missing connection
   when necessary.

The concepts return through a transparent 1-3-7 day cold-review schedule. Review
questions use new wording, preserve the original learning objective, and hide hints until
the learner commits an answer.

Sparring records these interactions as **practice evidence**, not proof of permanent
mastery.

## How I built it

The learner interface is built with semantic HTML, CSS, and JavaScript. The backend uses
Python, FastAPI, Uvicorn, and SQLite and is deployed on Render.

GPT-5.6-sol is called through the server-side OpenAI Responses API. Pydantic Structured
Outputs enforce strict response schemas, while an additional validation layer checks that
generated source anchors can be found in the learner's supplied material before the
content reaches the interface. The OpenAI API key never enters the browser.

PDF processing combines:

- `pypdf` for in-memory server-side text extraction;
- PDF.js for browser-side extraction and recovery;
- Tesseract.js for English and Simplified Chinese scanned-page OCR in the browser.

Uploaded PDF files are not stored. The SQLite evidence store contains limited practice
observations such as event type, concept, score, confidence, and review stage - not PDF
bytes, source text, or learner answers. Local storage provides precise refresh recovery,
while a service worker caches the application shell.

## Challenges

### Keeping AI useful without letting it replace learning

The central design challenge was deciding what AI should do and what it must leave to the
learner. AI structures the practice, produces grounded variations, and evaluates bounded
responses. The learner still predicts, retrieves, chooses, judges confidence, explains,
revises, and returns later.

### Grounding generated content

A valid JSON response is not necessarily a grounded response. Structured Outputs solved
the shape of the model output, but not its source integrity. I therefore added
server-side anchor verification and reject generated plans or lessons when their cited
source text cannot be matched to the uploaded material.

### Supporting real-world PDFs

PDFs can contain selectable text, scanned pages, mixed content, damaged files, or
low-quality images. The extraction flow needed visible progress, cancellation,
partial-success handling, editable OCR results, and recovery without erasing the
learner's existing work.

### Representing learning honestly

A correct answer is not permanent mastery, and a confidence rating is not an objective
measurement of metacognition. The interface and data model therefore use careful terms
such as "practice evidence," "review due," and "needs another attempt."

## Accomplishments

I am proud that Sparring now provides a complete, public, no-sign-in path from PDF upload
to delayed cold review.

The working prototype includes:

- automatic scanned-page OCR;
- a three-concept map generated from the uploaded material;
- prediction before explanation;
- definition, mechanism, and application retrieval;
- mandatory confidence judgment before feedback;
- targeted handling of high-confidence mistakes;
- teach-back revision instead of automatic advancement;
- a real date-based 1-3-7 review queue;
- refresh recovery and offline-shell support;
- responsive, keyboard-operable interaction;
- recoverable loading, invalid-file, missing-key, model-error, and damaged-state paths;
- automated API and UI-contract tests plus real-browser rehearsals.

## What I learned

I learned that educational AI needs stronger boundaries than a general productivity
assistant.

Structured generation and grounding are separate engineering problems. Confidence
becomes meaningful only when paired with a committed answer. Teach-back feedback should
help the learner repair one relationship rather than rewrite the explanation for them.
Delayed-review data must describe observable attempts without turning them into
exaggerated claims about mastery.

I also learned that recovery states are part of the learning experience. Losing a
prediction or explanation after a refresh can interrupt the learner's thinking just as
seriously as a model failure.

## What's next

Next, I would like to add:

- stronger handling of complex layouts, equations, tables, and low-quality scans;
- generated short-answer application items for delayed review;
- optional account-based, cross-device review synchronization;
- learner-controlled notifications for due reviews;
- a small learner study measuring usability, delayed recall, and confidence patterns
  without overclaiming outcomes.

Sparring's goal is simple: use AI to create better opportunities for thinking - not to do
the thinking on the learner's behalf.

## Built with

1. OpenAI
2. GPT-5.6-sol
3. OpenAI Responses API
4. Structured Outputs
5. Python
6. FastAPI
7. Pydantic
8. Uvicorn
9. JavaScript
10. HTML5
11. CSS3
12. SQLite
13. pypdf
14. PDF.js
15. Tesseract.js
16. OCR
17. Docker
18. Render
19. Service Worker
20. Progressive Web App
21. Pytest
22. EdTech
23. Learning Science

## Upload a File

Recommended file: `Sparring_Devpost_Judge_Pack.pdf`

This is a concise, judge-friendly project brief. The source code is already available
through GitHub, and the demo video belongs in Devpost's separate video field. The PDF
contains no API key and stays well below the 35 MB upload limit.
