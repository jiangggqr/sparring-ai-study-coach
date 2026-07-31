from __future__ import annotations

import json
import math
import shutil
import subprocess
import textwrap
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
VIDEO_ROOT = ROOT / "submission" / "video"
AUDIO_DIR = VIDEO_ROOT / "audio"
SOURCE_VIDEO = VIDEO_ROOT / "source" / "live-demo-source.webm"
MARKERS = VIDEO_ROOT / "source" / "live-demo-markers.json"
CARD_DIR = VIDEO_ROOT / "cards"
WORK_DIR = VIDEO_ROOT / "work"
OUTPUT_DIR = VIDEO_ROOT / "output"

FFMPEG = (
    ROOT
    / ".venv313"
    / "lib"
    / "python3.13"
    / "site-packages"
    / "imageio_ffmpeg"
    / "binaries"
    / "ffmpeg-macos-aarch64-v7.1"
)

FINAL_VIDEO = OUTPUT_DIR / "sparring-devpost-demo-captioned.mp4"
FINAL_SRT = OUTPUT_DIR / "sparring-devpost-demo.srt"
TIMELINE_WAV = WORK_DIR / "narration-timeline.wav"
VISUALS = WORK_DIR / "visuals.mp4"

WIDTH = 1920
HEIGHT = 1080
FPS = 25
GAP_SECONDS = 0.45

IVORY = "#FAF7F0"
PAPER = "#FFFDF8"
INK = "#16231E"
MUTED = "#52615B"
GREEN = "#0D6B57"
DEEP_GREEN = "#0B4F40"
MINT = "#DCEFE9"
PALE_MINT = "#EFF7F3"
PALE_AMBER = "#FFF0DA"
AMBER_INK = "#704414"
RULE = "#D8D4C9"

FONT_REGULAR = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
FONT_DISPLAY = Path("/System/Library/Fonts/Supplemental/Georgia Bold.ttf")

SEGMENTS = [
    ("01-problem", 0.0),
    ("02-upload", 0.0),
    ("03-prediction", 0.0),
    ("04-confidence", 0.0),
    ("05-teachback", 0.0),
    ("06-cold-review", 0.0),
    ("07-technical", 0.0),
    ("08-close", 0.0),
]

CAPTIONS = [
    [
        ("AI can produce a polished answer\nin seconds.", 7),
        ("But here's the uncomfortable question:", 5),
        ("did I learn it, or did the AI simply do\nthe thinking for me?", 12),
    ],
    [
        ("Sparring changes that contract.", 4),
        ("I upload the PDF I actually need -\neven a scanned page.", 10),
        ("Private OCR recovers the text.", 5),
        ("Then GPT-5.6-sol builds a three-concept\nmap from that material alone.", 12),
    ],
    [
        ("Before any explanation,\nI make a quick prediction.", 8),
        ("It isn't a grade.", 4),
        ("It creates a real attempt I can compare\nwith one focused explanation...", 12),
        ("...and its source anchor.", 4),
    ],
    [
        ("Then I retrieve before feedback\nand rate my confidence.", 8),
        ("Here I'm very sure - and wrong.", 7),
        ("Sparring explains why my choice\nconflicts with the source...", 9),
        ("...and why another relationship\nis supported.", 8),
        ("That mismatch tells the coach\nmore than a score alone.", 10),
    ],
    [
        ("Next, I teach the idea back\nin my own words.", 9),
        ("If I only list parts, the AI asks\nfor the missing relationship.", 12),
        ("I revise it; the explanation stays mine.", 7),
    ],
    [
        ("Later, the objective returns\nin new wording...", 8),
        ("...with no hints before I commit.", 6),
        ("Passing schedules day three,\nthen day seven.", 7),
        ("Sparring records practice evidence,\nnot permanent mastery.", 9),
    ],
    [
        ("In the live demo, FastAPI keeps\nthe API key on the server.", 12),
        ("Structured Outputs enforce\nthe learning contract...", 7),
        ("...and every explanation and question\nincludes a verified anchor...", 10),
        ("...from the uploaded material.", 5),
    ],
    [
        ("Sparring:", 2),
        ("the AI study coach that refuses\nto think for you.", 10),
    ],
]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def rounded_rectangle(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    max_width: int,
    typeface: ImageFont.FreeTypeFont,
    fill: str,
    spacing: int = 10,
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=typeface) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    draw.multiline_text((x, y), "\n".join(lines), font=typeface, fill=fill, spacing=spacing)
    bbox = draw.multiline_textbbox((x, y), "\n".join(lines), font=typeface, spacing=spacing)
    return bbox[3]


def logo(draw: ImageDraw.ImageDraw, x: int, y: int):
    rounded_rectangle(draw, (x, y, x + 56, y + 56), 12, GREEN)
    draw.text((x + 18, y + 7), "S", font=font(FONT_BOLD, 34), fill="white")
    draw.text((x + 76, y + 12), "Sparring", font=font(FONT_BOLD, 25), fill=INK)


def make_title_card() -> Path:
    output = CARD_DIR / "title.png"
    image = Image.new("RGB", (WIDTH, HEIGHT), IVORY)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 34, HEIGHT), fill=GREEN)
    logo(draw, 92, 70)
    draw.text((94, 258), "AI CAN ANSWER IN SECONDS.", font=font(FONT_BOLD, 28), fill=GREEN)
    draw.text((92, 320), "But did you", font=font(FONT_DISPLAY, 94), fill=INK)
    draw.text((92, 428), "learn it?", font=font(FONT_DISPLAY, 112), fill=DEEP_GREEN)
    draw_wrapped(
        draw,
        "Sparring turns a learner's own PDF into active practice - without taking over the thinking.",
        (100, 604),
        1030,
        font(FONT_REGULAR, 33),
        MUTED,
        14,
    )
    rounded_rectangle(draw, (100, 790, 1800, 906), 22, PAPER, RULE, 2)
    stages = ["PREDICT", "RETRIEVE", "CONFIDENCE", "TEACH BACK", "RETURN COLD"]
    x = 140
    for index, stage in enumerate(stages):
        draw.text((x, 829), stage, font=font(FONT_BOLD, 22), fill=DEEP_GREEN)
        x += int(draw.textlength(stage, font=font(FONT_BOLD, 22))) + 74
        if index < len(stages) - 1:
            draw.text((x - 44, 827), "->", font=font(FONT_BOLD, 23), fill=GREEN)
    draw.text((100, 985), "PROMETHEUS JULY AI CHALLENGE", font=font(FONT_BOLD, 18), fill=MUTED)
    image.save(output, quality=95)
    return output


def make_architecture_card() -> Path:
    output = CARD_DIR / "technical-architecture.png"
    image = Image.new("RGB", (WIDTH, HEIGHT), IVORY)
    draw = ImageDraw.Draw(image)
    logo(draw, 92, 70)
    draw.text((92, 214), "GROUNDED AI, BOUNDED ROLE", font=font(FONT_BOLD, 24), fill=GREEN)
    draw.text((92, 264), "The model never becomes the source.", font=font(FONT_DISPLAY, 62), fill=INK)
    stages = [
        ("1", "Learner PDF", "Text layer or private\nbrowser OCR"),
        ("2", "FastAPI", "Server-side key and\nbounded endpoints"),
        ("3", "GPT-5.6-sol", "Responses API +\nStructured Outputs"),
        ("4", "Anchor check", "Reject content not\nmatched to source"),
        ("5", "Practice UI", "Learner predicts,\nretrieves, explains"),
    ]
    box_w = 300
    gap = 32
    start_x = 92
    y1, y2 = 462, 762
    for index, (number, heading, body) in enumerate(stages):
        x1 = start_x + index * (box_w + gap)
        x2 = x1 + box_w
        rounded_rectangle(draw, (x1, y1, x2, y2), 25, PAPER, RULE, 3)
        rounded_rectangle(draw, (x1 + 28, y1 + 26, x1 + 86, y1 + 84), 16, MINT)
        draw.text((x1 + 49, y1 + 34), number, font=font(FONT_BOLD, 24), fill=DEEP_GREEN, anchor="ma")
        draw.text((x1 + 28, y1 + 116), heading, font=font(FONT_BOLD, 27), fill=INK)
        draw.multiline_text((x1 + 28, y1 + 169), body, font=font(FONT_REGULAR, 22), fill=MUTED, spacing=9)
        if index < len(stages) - 1:
            draw.text((x2 + 4, y1 + 125), "->", font=font(FONT_BOLD, 31), fill=GREEN)
    rounded_rectangle(draw, (92, 840, 1828, 972), 22, DEEP_GREEN)
    draw.text((128, 870), "AI structures the practice.", font=font(FONT_BOLD, 28), fill=MINT)
    draw.text((670, 870), "The learner makes every prediction, answer, and explanation.", font=font(FONT_REGULAR, 28), fill="white")
    image.save(output, quality=95)
    return output


def make_guardrails_card() -> Path:
    output = CARD_DIR / "technical-guardrails.png"
    image = Image.new("RGB", (WIDTH, HEIGHT), IVORY)
    draw = ImageDraw.Draw(image)
    logo(draw, 92, 70)
    draw.text((92, 214), "SOURCE INTEGRITY", font=font(FONT_BOLD, 24), fill=GREEN)
    draw.text((92, 264), "Every output returns to the material.", font=font(FONT_DISPLAY, 60), fill=INK)
    cards = [
        ("STRUCTURED", "Schema-validated output", "Plans and lessons must match a bounded contract."),
        ("VERIFIED", "Source anchors are checked", "Unmatched anchors are rejected before they reach the learner."),
        ("PRIVATE", "The key stays server-side", "PDF bytes are not stored; evidence is minimized."),
    ]
    box_w = 526
    for index, (eyebrow, heading, body) in enumerate(cards):
        x1 = 92 + index * (box_w + 34)
        rounded_rectangle(draw, (x1, 450, x1 + box_w, 790), 28, PAPER, RULE, 3)
        rounded_rectangle(draw, (x1 + 28, 482, x1 + 190, 530), 18, MINT)
        draw.text((x1 + 109, 492), eyebrow, font=font(FONT_BOLD, 18), fill=DEEP_GREEN, anchor="ma")
        draw_wrapped(draw, heading, (x1 + 30, 570), box_w - 60, font(FONT_BOLD, 31), INK, 10)
        draw_wrapped(draw, body, (x1 + 30, 662), box_w - 60, font(FONT_REGULAR, 23), MUTED, 10)
    draw.text((92, 905), "NO WEB SEARCH", font=font(FONT_BOLD, 23), fill=DEEP_GREEN)
    draw.text((357, 905), "ONLY THE LEARNER'S MATERIAL", font=font(FONT_BOLD, 23), fill=DEEP_GREEN)
    draw.text((835, 905), "PRACTICE EVIDENCE - NOT PERMANENT MASTERY", font=font(FONT_BOLD, 23), fill=DEEP_GREEN)
    image.save(output, quality=95)
    return output


def make_end_card() -> Path:
    output = CARD_DIR / "end.png"
    image = Image.new("RGB", (WIDTH, HEIGHT), DEEP_GREEN)
    draw = ImageDraw.Draw(image)
    rounded_rectangle(draw, (92, 72, 148, 128), 12, MINT)
    draw.text((110, 79), "S", font=font(FONT_BOLD, 34), fill=DEEP_GREEN)
    draw.text((168, 83), "Sparring", font=font(FONT_BOLD, 25), fill="white")
    draw.text((94, 292), "Keep the", font=font(FONT_DISPLAY, 104), fill="white")
    draw.text((94, 410), "thinking.", font=font(FONT_DISPLAY, 126), fill=MINT)
    draw.text(
        (104, 594),
        "The AI study coach that refuses to think for you.",
        font=font(FONT_REGULAR, 34),
        fill="white",
    )
    rounded_rectangle(draw, (1130, 252, 1810, 338), 20, MINT)
    draw.text((1162, 276), "LIVE DEMO", font=font(FONT_BOLD, 20), fill=DEEP_GREEN)
    draw.text((1340, 272), "sparring-ai-study-coach.onrender.com", font=font(FONT_REGULAR, 20), fill=DEEP_GREEN)
    draw.text((1130, 390), "SOURCE", font=font(FONT_BOLD, 18), fill=MINT)
    draw.text((1130, 430), "github.com/jiangggqr/", font=font(FONT_REGULAR, 22), fill="white")
    draw.text((1130, 464), "sparring-ai-study-coach", font=font(FONT_REGULAR, 22), fill="white")
    draw.text((1130, 542), "Voiceover generated with OpenAI TTS.", font=font(FONT_REGULAR, 17), fill="#B7D8CF")
    image.save(output, quality=95)
    return output


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def clean_audio() -> list[Path]:
    outputs: list[Path] = []
    for stem, _ in SEGMENTS:
        source = AUDIO_DIR / f"{stem}.wav"
        destination = AUDIO_DIR / f"{stem}.clean.wav"
        run(
            [
                str(FFMPEG),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-c:a",
                "pcm_s16le",
                str(destination),
            ]
        )
        outputs.append(destination)
    return outputs


def build_audio_timeline(audio_paths: list[Path]) -> tuple[list[float], list[float]]:
    starts: list[float] = []
    durations: list[float] = []
    current = 0.0
    params = None
    chunks: list[bytes] = []

    for index, path in enumerate(audio_paths):
        with wave.open(str(path), "rb") as source:
            this_params = (
                source.getnchannels(),
                source.getsampwidth(),
                source.getframerate(),
                source.getcomptype(),
                source.getcompname(),
            )
            if params is None:
                params = this_params
            if this_params != params:
                raise ValueError(f"Audio parameters do not match: {path}")
            frames = source.readframes(source.getnframes())
            duration = source.getnframes() / source.getframerate()
            starts.append(current)
            durations.append(duration)
            chunks.append(frames)
            current += duration

            if index < len(audio_paths) - 1:
                silence_frames = int(source.getframerate() * GAP_SECONDS)
                chunks.append(b"\x00" * silence_frames * source.getnchannels() * source.getsampwidth())
                current += GAP_SECONDS

    assert params is not None
    with wave.open(str(TIMELINE_WAV), "wb") as output:
        output.setnchannels(params[0])
        output.setsampwidth(params[1])
        output.setframerate(params[2])
        output.setcomptype(params[3], params[4])
        for chunk in chunks:
            output.writeframes(chunk)
    return starts, durations


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{millis:03d}"


def write_subtitles(starts: list[float], durations: list[float]) -> None:
    entries: list[str] = []
    index = 1
    for section_start, duration, section_captions in zip(starts, durations, CAPTIONS):
        total_weight = sum(weight for _, weight in section_captions)
        cursor = section_start
        for caption_index, (caption, weight) in enumerate(section_captions):
            allocated = duration * weight / total_weight
            end = section_start + duration if caption_index == len(section_captions) - 1 else cursor + allocated
            entries.extend(
                [
                    str(index),
                    f"{srt_timestamp(cursor)} --> {srt_timestamp(max(cursor + 0.6, end - 0.035))}",
                    caption,
                    "",
                ]
            )
            index += 1
            cursor = end

    text = "\n".join(entries).rstrip() + "\n"
    FINAL_SRT.write_text(text, encoding="utf-8")
    (ROOT / "submission" / "demo_voiceover.srt").write_text(text, encoding="utf-8")


def encode_source_section(name: str, clips: list[tuple[float, float]], duration: float) -> Path:
    output = WORK_DIR / f"{name}.mp4"
    raw_duration = sum(end - start for start, end in clips)
    factor = duration / raw_duration
    filters: list[str] = []
    labels: list[str] = []
    for index, (start, end) in enumerate(clips):
        label_name = f"clip{index}"
        filters.append(
            f"[0:v]trim=start={start:.3f}:end={end:.3f},"
            f"setpts=PTS-STARTPTS,scale={WIDTH}:{HEIGHT}:flags=lanczos,"
            f"fps={FPS},setsar=1[{label_name}]"
        )
        labels.append(f"[{label_name}]")
    filters.append(f"{''.join(labels)}concat=n={len(clips)}:v=1:a=0[joined]")
    filters.append(
        f"[joined]setpts={factor:.9f}*PTS,"
        f"tpad=stop_mode=clone:stop_duration=1,"
        f"trim=duration={duration:.3f},setpts=PTS-STARTPTS,format=yuv420p[out]"
    )
    run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(SOURCE_VIDEO),
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[out]",
            "-an",
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )
    return output


def encode_still(name: str, image: Path, duration: float, fade_in=False, fade_out=False) -> Path:
    output = WORK_DIR / f"{name}.mp4"
    filters = [f"scale={WIDTH}:{HEIGHT}:flags=lanczos", f"fps={FPS}"]
    if fade_in:
        filters.append("fade=t=in:st=0:d=0.28")
    if fade_out:
        filters.append(f"fade=t=out:st={max(0, duration - 0.35):.3f}:d=0.35")
    filters.extend([f"trim=duration={duration:.3f}", "setpts=PTS-STARTPTS", "format=yuv420p"])
    run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image),
            "-vf",
            ",".join(filters),
            "-t",
            f"{duration:.3f}",
            "-an",
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )
    return output


def concat_videos(inputs: list[Path], output: Path) -> Path:
    list_file = WORK_DIR / f"{output.stem}-concat.txt"
    list_file.write_text(
        "\n".join(f"file '{path.resolve()}'" for path in inputs) + "\n",
        encoding="utf-8",
    )
    run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output),
        ]
    )
    return output


def build_visuals(durations: list[float]) -> None:
    section_durations = [
        duration + (GAP_SECONDS if index < len(durations) - 1 else 0.0)
        for index, duration in enumerate(durations)
    ]

    title_card = make_title_card()
    architecture_card = make_architecture_card()
    guardrails_card = make_guardrails_card()
    end_card = make_end_card()

    title_duration = 4.0
    section_1 = concat_videos(
        [
            encode_still("01-title", title_card, title_duration, fade_in=True),
            encode_source_section(
                "01-home",
                [(1.230, 4.233)],
                section_durations[0] - title_duration,
            ),
        ],
        WORK_DIR / "section-01.mp4",
    )
    section_2 = encode_source_section(
        "section-02",
        [(4.604, 7.414), (7.421, 10.022), (10.382, 12.582), (17.275, 22.485)],
        section_durations[1],
    )
    section_3 = encode_source_section(
        "section-03",
        [(17.275, 22.485), (22.843, 26.553), (57.438, 61.540)],
        section_durations[2],
    )
    section_4 = encode_source_section(
        "section-04",
        [(62.248, 74.591)],
        section_durations[3],
    )
    section_5 = encode_source_section(
        "section-05",
        [(76.742, 92.476)],
        section_durations[4],
    )
    section_6 = encode_source_section(
        "section-06",
        [(243.321, 252.641), (268.613, 272.415)],
        section_durations[5],
    )
    first_technical = 7.0
    section_7 = concat_videos(
        [
            encode_still("07-architecture", architecture_card, first_technical),
            encode_still(
                "07-guardrails",
                guardrails_card,
                section_durations[6] - first_technical,
            ),
        ],
        WORK_DIR / "section-07.mp4",
    )
    section_8 = encode_still(
        "section-08",
        end_card,
        section_durations[7],
        fade_out=True,
    )

    concat_videos(
        [
            section_1,
            section_2,
            section_3,
            section_4,
            section_5,
            section_6,
            section_7,
            section_8,
        ],
        VISUALS,
    )


def mux_final() -> None:
    subtitle_filter = (
        "tpad=stop_mode=clone:stop_duration=1,"
        f"subtitles={FINAL_SRT.as_posix()}:"
        "force_style='FontName=Arial,FontSize=18,"
        "PrimaryColour=&H00FFFFFF,BackColour=&HC40B1E19,"
        "OutlineColour=&HC40B1E19,BorderStyle=3,Outline=1,"
        "Shadow=0,MarginV=42,Alignment=2'"
    )
    run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(VISUALS),
            "-i",
            str(TIMELINE_WAV),
            "-vf",
            subtitle_filter,
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=7",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-shortest",
            "-movflags",
            "+faststart",
            str(FINAL_VIDEO),
        ]
    )


def main() -> None:
    if not SOURCE_VIDEO.exists() or not MARKERS.exists():
        raise FileNotFoundError("The verified live-demo recording is missing.")
    if not FFMPEG.exists():
        raise FileNotFoundError(f"ffmpeg is missing: {FFMPEG}")
    marker_data = json.loads(MARKERS.read_text(encoding="utf-8"))
    if marker_data.get("browserFailures"):
        raise RuntimeError(f"Recording contains browser failures: {marker_data['browserFailures']}")
    if marker_data.get("lessonCount") != 3:
        raise RuntimeError("Recording did not capture all three real-model lessons.")
    if "Revise" not in marker_data.get("firstTeachbackHeading", ""):
        raise RuntimeError("Recording did not capture the teach-back revision path.")

    for directory in (CARD_DIR, WORK_DIR, OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    audio_paths = clean_audio()
    starts, durations = build_audio_timeline(audio_paths)
    write_subtitles(starts, durations)
    build_visuals(durations)
    mux_final()

    print(
        json.dumps(
            {
                "video": str(FINAL_VIDEO),
                "subtitles": str(FINAL_SRT),
                "duration_seconds": wav_duration(TIMELINE_WAV),
                "source_recording_verified": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
