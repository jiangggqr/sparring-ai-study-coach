from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text_pdf_bytes(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT\n/F1 12 Tf\n72 720 Td\n({escaped}) Tj\nET\n".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream",
    ]
    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode())
        document.extend(obj)
        document.extend(b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(document)


def test_browser_fixture_contract_matches_learning_flow():
    script = r"""
import { fixtureRequest } from "./static/demo-engine.mjs";

const material = `Retrieval practice asks a learner to bring an idea back from memory before seeing the answer. The effort of trying makes later feedback more useful because the learner can compare an attempted answer with the source.

Confidence judgments add a second observation to each answer. A correct response with low confidence and an incorrect response with high confidence need different feedback, even when the quiz score alone looks similar.

Spaced practice returns to an idea after time has passed. A cold review changes the wording and removes hints, so the learner must reconstruct the relationship rather than recognize the original question.`;

const plan = await fixtureRequest("plan", { material });
const lesson = await fixtureRequest("lesson", {
  material,
  concept: plan.concepts[0].name,
});
const listed = await fixtureRequest("teachback", {
  material,
  concept: plan.concepts[0].name,
  answer: "Retrieval practice, memory, feedback, and comparison are important ideas.",
});
const linked = await fixtureRequest("teachback", {
  material,
  concept: plan.concepts[0].name,
  answer: "Retrieval practice matters because an attempted answer can be compared with feedback.",
});
const cold = await fixtureRequest("cold", { material, quiz: lesson.quiz });
process.stdout.write(JSON.stringify({ plan, lesson, listed, linked, cold }));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert len(payload["plan"]["concepts"]) == 3
    for concept in payload["plan"]["concepts"]:
        assert " ".join(concept["source_anchor"].split()) in " ".join(
            (
                "Retrieval practice asks a learner to bring an idea back from memory "
                "before seeing the answer. The effort of trying makes later feedback "
                "more useful because the learner can compare an attempted answer with "
                "the source. Confidence judgments add a second observation to each "
                "answer. A correct response with low confidence and an incorrect "
                "response with high confidence need different feedback, even when the "
                "quiz score alone looks similar. Spaced practice returns to an idea "
                "after time has passed. A cold review changes the wording and removes "
                "hints, so the learner must reconstruct the relationship rather than "
                "recognize the original question."
            ).split()
        )

    lesson = payload["lesson"]
    assert [question["kind"] for question in lesson["quiz"]] == [
        "definition",
        "mechanism",
        "application",
    ]
    assert len({question["answer"] for question in lesson["quiz"]}) == 3
    assert payload["listed"]["linked"] is False
    assert payload["listed"]["repair_prompt"]
    assert payload["linked"]["linked"] is True
    assert payload["linked"]["repair_prompt"] is None
    for original, variant in zip(
        lesson["quiz"], payload["cold"]["quiz"], strict=True
    ):
        assert original["stem"] != variant["stem"]
        assert set(original["options"]).isdisjoint(variant["options"])
        assert original["source_anchor"] == variant["source_anchor"]


def test_service_worker_uses_its_pages_scope():
    worker = (ROOT / "static" / "sw.js").read_text()
    assert '"sparring-shell-v7"' in worker
    assert 'new URL("./", self.registration.scope)' in worker
    assert 'caches.match(ROOT_URL)' in worker
    assert '"/index.html"' not in worker
    assert '"/app.js"' not in worker


def test_scanned_pdf_ocr_runtime_is_self_hosted_and_lazy():
    engine = (ROOT / "static" / "demo-engine.mjs").read_text()
    vendor = ROOT / "static" / "vendor" / "tesseract"

    assert 'import("./vendor/tesseract/tesseract.esm.min.js")' in engine
    assert 'const OCR_LANGUAGES = ["eng", "chi_sim"]' in engine
    assert "tesseract.createWorker(" in engine
    assert 'workerBlobURL: false' in engine
    assert "cdn.jsdelivr.net" not in engine
    assert "ocr_pages:" in engine
    assert (vendor / "tesseract.esm.min.js").is_file()
    assert (vendor / "worker.min.js").is_file()
    assert (vendor / "core" / "tesseract-core-lstm.wasm.js").is_file()
    assert (vendor / "core" / "tesseract-core-simd-lstm.wasm.js").is_file()
    assert (
        vendor / "core" / "tesseract-core-relaxedsimd-lstm.wasm.js"
    ).is_file()
    assert (vendor / "tessdata" / "eng.traineddata.gz").is_file()
    assert (vendor / "tessdata" / "chi_sim.traineddata.gz").is_file()


def test_browser_pdf_adapter_extracts_text(tmp_path: Path):
    pdf_path = tmp_path / "browser-fixture.pdf"
    pdf_path.write_bytes(
        text_pdf_bytes(
            (
                "Retrieval practice makes an attempted answer visible before feedback. "
                "Confidence can then be compared with correctness. "
            )
            * 3
        )
    )
    script = f"""
globalThis.DOMMatrix = class DOMMatrix {{}};
globalThis.Path2D = class Path2D {{}};
const {{ readFile }} = await import("node:fs/promises");
const {{ extractPdfInBrowser }} = await import("./static/demo-engine.mjs");
const bytes = await readFile({json.dumps(str(pdf_path))});
const file = {{
  name: "browser-fixture.pdf",
  type: "application/pdf",
  size: bytes.byteLength,
  arrayBuffer: async () =>
    bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
}};
const result = await extractPdfInBrowser(file);
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert result["filename"] == "browser-fixture.pdf"
    assert result["page_count"] == 1
    assert result["extracted_pages"] == 1
    assert result["text"].startswith("[Page 1]")
    assert "Retrieval practice" in result["text"]
    assert result["truncated"] is False


def test_browser_pdf_adapter_accepts_short_pdf_and_builds_plan(tmp_path: Path):
    pdf_path = tmp_path / "short-browser-fixture.pdf"
    short_text = "A short PDF sentence is enough to build a grounded practice plan."
    assert 40 <= len(short_text) < 200
    pdf_path.write_bytes(text_pdf_bytes(short_text))
    script = f"""
globalThis.DOMMatrix = class DOMMatrix {{}};
globalThis.Path2D = class Path2D {{}};
const {{ readFile }} = await import("node:fs/promises");
const {{ extractPdfInBrowser, fixtureRequest }} = await import("./static/demo-engine.mjs");
const bytes = await readFile({json.dumps(str(pdf_path))});
const file = {{
  name: "short-browser-fixture.pdf",
  type: "application/pdf",
  size: bytes.byteLength,
  arrayBuffer: async () =>
    bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
}};
const extracted = await extractPdfInBrowser(file);
const plan = await fixtureRequest("plan", {{ material: extracted.text }});
process.stdout.write(JSON.stringify({{ extracted, plan }}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert result["extracted"]["extracted_pages"] == 1
    assert len(result["plan"]["concepts"]) == 3
    assert len({item["name"] for item in result["plan"]["concepts"]}) == 3
