# Sparring demo video - final 1:35 production script

## Final deliverables

- Captioned MP4: `submission/video/output/sparring-devpost-demo-captioned.mp4`
- Standalone captions: `submission/video/output/sparring-devpost-demo.srt`
- Public download release:
  https://github.com/jiangggqr/sparring-ai-study-coach/releases/tag/devpost-submission-v1

The final video is 95.5 seconds, 1920x1080, H.264/AAC, and records the public Render
GPT-5.6-sol application. The source run used a pure scanned PDF and completed browser
OCR, a real model-generated three-concept map, three lessons, a teach-back revision, and
a delayed cold review without browser failures.

## Voice direction

The narration uses a warm, conversational English OpenAI TTS voice. It should sound like
a student sharing a useful discovery, not an announcer. The closing card discloses:
"Voiceover generated with OpenAI TTS."

## Final narration and picture

### 0:00-0:09 - The problem

**Picture:** Branded opening card, then the live upload screen.

> AI can produce a polished answer in seconds. But here's the uncomfortable question:
> did I learn it, or did the AI simply do the thinking for me?

### 0:09-0:26 - Upload, OCR, and map

**Picture:** Upload a pure scanned PDF, show OCR-ready state, then the real generated
three-concept map.

> Sparring changes that contract. I upload the PDF I actually need - even a scanned
> page. Private OCR recovers the text, then GPT-5.6-sol builds a three-concept map from
> that material alone.

### 0:26-0:38 - Prediction and explanation

**Picture:** Inspect the map, type a prediction, then reveal the focused explanation and
verified source anchor.

> Before any explanation, I make a quick prediction. It isn't a grade. It creates a real
> attempt I can compare with one focused explanation and its source anchor.

### 0:38-0:55 - Answer and confidence

**Picture:** Select a wrong option with confidence 5, lock it, and show the
high-confidence mismatch feedback.

> Then I retrieve before feedback and rate my confidence. Here I'm very sure - and wrong.
> Sparring explains why my choice conflicts with the source, and why another relationship
> is supported. That mismatch tells the coach more than a score alone.

### 0:55-1:05 - Teach-back revision

**Picture:** Submit a list-like explanation, show "Revise one connection," then type the
missing relationship.

> Next, I teach the idea back in my own words. If I only list parts, the AI asks for the
> missing relationship. I revise it; the explanation stays mine.

### 1:05-1:16 - Delayed cold review

**Picture:** Show the completed-session dashboard, advance the explicit demo day, and
open a reworded cold-review item.

> Later, the objective returns in new wording, with no hints before I commit. Passing
> schedules day three, then day seven. Sparring records practice evidence, not permanent
> mastery.

### 1:16-1:31 - Technical proof

**Picture:** Two branded architecture cards: bounded Responses API flow and source
integrity guardrails.

> In the live demo, FastAPI keeps the API key on the server. Structured Outputs enforce
> the learning contract, and every explanation and question includes a verified anchor
> from the uploaded material.

### 1:31-1:35 - Close

**Picture:** Sparring wordmark, live demo, source link, and AI-voice disclosure.

> Sparring: the AI study coach that refuses to think for you.

## Caption treatment

- English captions are burned into the MP4 and supplied separately as SRT.
- White sans-serif text uses a high-contrast dark background.
- Maximum two lines and 40 characters per rendered line.
- Captions remain inside the 1080p safe area.
