# Video export and submission checklist

## Performance

- Final runtime is 1:57 or shorter; never rely on a platform trimming the file.
- Natural English voice take selected using the direction in `VIDEO_SCRIPT.md`.
- No sentence is time-compressed until it sounds synthetic.
- Music, if used, sits at least 18 dB below the voice and has no vocals.
- First ten seconds state the problem and product promise.
- Actual working product is visible; no mockup is presented as implementation.

## English subtitles

- `demo_voiceover.srt` has been proofread against the selected audio take.
- English captions are burned into the video, not only supplied as a toggle.
- Maximum two lines, high contrast, no clipping on mobile.
- Captions never cover answer choices, confidence controls, feedback, or dates.
- A standalone `.srt` file is retained for accessible upload where supported.

Example burn-in command:

```bash
ffmpeg -i demo_clean.mp4 \
  -vf "subtitles=submission/demo_voiceover.srt:force_style='FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,BackColour=&H99000000,BorderStyle=3,Outline=1,MarginV=48'" \
  -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k \
  demo_captioned.mp4
```

## Submission

- Video is playable without sign-in.
- Source repository is public:
  https://github.com/jiangggqr/sparring-ai-study-coach
- Repository has no `.env`, API key, PDF, or personal learning material.
- README setup works from a fresh Python environment.
- Public demo URL returns 200, and the PDF-to-practice flow passes in a fresh browser.
- If a separate FastAPI host is submitted, its `/api/health` endpoint also returns 200.
- Devpost description uses only claims supported by the submitted build.
- Official limit checked again before upload; current official rule is no more than two
  minutes.
