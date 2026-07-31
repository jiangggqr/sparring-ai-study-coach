"""Generate the competition narration with OpenAI's natural speech model.

The script reads the API key from the workspace-level .env without printing it.
It writes one WAV per storyboard section so timing can be adjusted independently.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.request


HERE = Path(__file__).resolve().parent
AUDIO_DIR = HERE / "audio"
WORKSPACE_ENV = HERE.parents[2] / ".env"
ENDPOINT = "https://api.openai.com/v1/audio/speech"

VOICE_DIRECTION = (
    "Speak in warm, natural, conversational English, like a thoughtful student "
    "showing judges a product that genuinely helped. Use varied sentence rhythm "
    "and brief human pauses. Sound curious at the opening, lightly surprised at "
    "the high-confidence mistake, and calm and assured at the end. Avoid an "
    "announcer cadence, salesy emphasis, monotone delivery, over-enunciation, "
    "and repeated upward inflection."
)


def load_api_key() -> str:
    direct = os.environ.get("OPENAI_API_KEY", "").strip()
    if direct:
        return direct
    if not WORKSPACE_ENV.exists():
        raise RuntimeError("OPENAI_API_KEY is unavailable.")
    for raw_line in WORKSPACE_ENV.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != "OPENAI_API_KEY":
            continue
        return value.strip().strip("\"'")
    raise RuntimeError("OPENAI_API_KEY is unavailable.")


def generate_segment(api_key: str, source: Path) -> Path:
    target = source.with_suffix(".wav")
    payload = json.dumps(
        {
            "model": "gpt-4o-mini-tts",
            "voice": "marin",
            "input": source.read_text(encoding="utf-8").strip(),
            "instructions": VOICE_DIRECTION,
            "response_format": "wav",
            "speed": 1.03,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            target.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Speech generation failed for {source.name} (HTTP {exc.code})."
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Speech generation could not connect for {source.name}."
        ) from exc
    return target


def main() -> None:
    api_key = load_api_key()
    sources = sorted(AUDIO_DIR.glob("[0-9][0-9]-*.txt"))
    if not sources:
        raise RuntimeError("No narration segment text files were found.")
    for source in sources:
        target = generate_segment(api_key, source)
        print(f"Generated {target.name}")


if __name__ == "__main__":
    main()
