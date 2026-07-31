from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


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


def build_plan_and_lesson(client: TestClient, material: str) -> tuple[dict, dict]:
    plan_response = client.post("/api/plan", json={"material": material})
    assert plan_response.status_code == 200
    plan = plan_response.json()
    lesson_response = client.post(
        "/api/lesson",
        json={"material": material, "concept": plan["concepts"][0]["name"]},
    )
    assert lesson_response.status_code == 200
    return plan, lesson_response.json()


def test_health_is_ready_without_exposing_model_or_key(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "ai_ready": True,
        "service": "sparring",
    }
    assert "model" not in response.text
    assert "key" not in response.text


def test_plan_has_three_unique_grounded_concepts(client: TestClient, material: str):
    response = client.post("/api/plan", json={"material": material})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["concepts"]) == 3
    assert len({item["name"] for item in payload["concepts"]}) == 3
    for concept in payload["concepts"]:
        assert concept["plain_definition"]
        assert isinstance(concept["depends_on"], list)
        if concept["depends_on"]:
            assert concept["relationship_to_dependencies"]
        else:
            assert concept["relationship_to_dependencies"] is None
        assert concept["source_anchor"] in material.replace("\n", " ") or (
            " ".join(concept["source_anchor"].split()) in " ".join(material.split())
        )
    assert "understand" not in payload["target"].casefold()


def test_material_bounds_are_enforced(client: TestClient):
    too_short = client.post("/api/plan", json={"material": "x" * 39})
    assert too_short.status_code == 400
    assert "40" in too_short.json()["detail"]

    short_paragraph = (
        "A short grounded paragraph is enough to begin practice."
    )
    assert len(short_paragraph) < 200
    accepted = client.post("/api/plan", json={"material": short_paragraph})
    assert accepted.status_code == 200

    too_long = client.post("/api/plan", json={"material": "x" * 24_001})
    assert too_long.status_code == 413
    assert "24,000" in too_long.json()["detail"]


def test_pdf_upload_extracts_text_with_page_marker(client: TestClient):
    text = (
        "Retrieval practice makes an attempted answer visible before feedback. "
        "Confidence adds a judgment that can be compared with correctness. "
        "Spaced practice returns to the relationship after time has passed. "
    ) * 3
    response = client.post(
        "/api/extract/pdf",
        files={"file": ("my-notes.pdf", text_pdf_bytes(text), "application/pdf")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_type"] == "pdf"
    assert payload["filename"] == "my-notes.pdf"
    assert payload["page_count"] == 1
    assert payload["extracted_pages"] == 1
    assert payload["text"].startswith("[Page 1]")
    assert "Retrieval practice" in payload["text"]
    assert payload["truncated"] is False


def test_short_pdf_can_build_a_plan_without_pasting_more_text(client: TestClient):
    text = "A short PDF sentence is enough to build a grounded practice plan."
    assert 40 <= len(text) < 200
    extracted = client.post(
        "/api/extract/pdf",
        files={"file": ("short-notes.pdf", text_pdf_bytes(text), "application/pdf")},
    )
    assert extracted.status_code == 200

    plan = client.post("/api/plan", json={"material": extracted.json()["text"]})
    assert plan.status_code == 200
    assert len(plan.json()["concepts"]) == 3


def test_pdf_upload_rejects_invalid_and_image_only_files(client: TestClient):
    invalid = client.post(
        "/api/extract/pdf",
        files={"file": ("fake.pdf", b"not a PDF", "application/pdf")},
    )
    assert invalid.status_code == 415
    assert invalid.json()["code"] == "not_a_pdf"

    no_text = client.post(
        "/api/extract/pdf",
        files={"file": ("scan.pdf", text_pdf_bytes(""), "application/pdf")},
    )
    assert no_text.status_code == 422
    assert no_text.json()["code"] == "pdf_has_no_text"
    assert "OCR" in no_text.json()["detail"]


def test_lesson_schema_alignment_and_grounding(client: TestClient, material: str):
    _, lesson = build_plan_and_lesson(client, material)
    assert [item["kind"] for item in lesson["quiz"]] == [
        "definition",
        "mechanism",
        "application",
    ]
    assert len(lesson["explanation"].split()) <= 130
    assert " ".join(lesson["explanation_anchor"].split()) in " ".join(material.split())
    assert len({item["answer"] for item in lesson["quiz"]}) == 3
    for question in lesson["quiz"]:
        assert len(question["options"]) == 4
        assert len(question["why"]) == 4
        assert len(question["tag"]) == 4
        assert question["tag"][question["answer"]] == ""
        assert all(
            tag.strip()
            for index, tag in enumerate(question["tag"])
            if index != question["answer"]
        )
        assert len({option.casefold().strip() for option in question["options"]}) == 4
        assert not any(
            phrase in option.casefold()
            for phrase in (
                "the material presents",
                "the material uses",
                "without adding outside facts",
            )
            for option in question["options"]
        )
        assert " ".join(question["source_anchor"].split()) in " ".join(material.split())
        option_lengths = [len(option) for option in question["options"]]
        assert max(option_lengths) / min(option_lengths) < 1.7


def test_output_language_hint_tracks_english_and_chinese_material():
    from app.prompts import language_hint

    assert language_hint("Retrieval practice compares an attempted answer with the source.")
    assert language_hint("这是中文学习材料，用于解释概念之间的因果关系。") == "Simplified Chinese"


def test_sample_lessons_use_three_distinct_diagnostic_question_sets(
    client: TestClient,
    material: str,
):
    plan = client.post("/api/plan", json={"material": material}).json()
    for concept in plan["concepts"]:
        response = client.post(
            "/api/lesson",
            json={"material": material, "concept": concept["name"]},
        )
        assert response.status_code == 200
        lesson = response.json()
        option_sets = [
            tuple(option.casefold().strip() for option in item["options"])
            for item in lesson["quiz"]
        ]
        assert len(set(option_sets)) == 3
        for item in lesson["quiz"]:
            correct = item["options"][item["answer"]]
            assert " ".join(correct.split()).casefold() != " ".join(
                item["source_anchor"].split()
            ).casefold()


def test_teachback_requires_content_and_distinguishes_linked(client: TestClient, material: str):
    plan, _ = build_plan_and_lesson(client, material)
    concept = plan["concepts"][0]["name"]

    short = client.post(
        "/api/teachback",
        json={"material": material, "concept": concept, "answer": "too short"},
    )
    assert short.status_code == 400

    listed = client.post(
        "/api/teachback",
        json={
            "material": material,
            "concept": concept,
            "answer": "Retrieval practice, memory, feedback, source comparison.",
        },
    )
    assert listed.status_code == 200
    assert listed.json()["linked"] is False
    assert listed.json()["repair_prompt"]
    assert " ".join(listed.json()["source_anchor"].split()) in " ".join(material.split())

    linked = client.post(
        "/api/teachback",
        json={
            "material": material,
            "concept": concept,
            "answer": (
                "Retrieval practice matters because an attempted answer makes the later "
                "comparison with feedback visible."
            ),
        },
    )
    assert linked.status_code == 200
    assert linked.json()["linked"] is True
    assert linked.json()["repair_prompt"] is None
    assert " ".join(linked.json()["source_anchor"].split()) in " ".join(material.split())


def test_cold_review_is_reworded_and_preserves_anchors(client: TestClient, material: str):
    _, lesson = build_plan_and_lesson(client, material)
    response = client.post(
        "/api/cold",
        json={"material": material, "quiz": lesson["quiz"]},
    )
    assert response.status_code == 200
    cold = response.json()["quiz"]
    assert len(cold) == 3
    for original, variant in zip(lesson["quiz"], cold, strict=True):
        assert original["stem"] != variant["stem"]
        assert set(original["options"]).isdisjoint(set(variant["options"]))
        assert original["source_anchor"] == variant["source_anchor"]
        assert original["kind"] == variant["kind"]


def test_evidence_is_observational_and_does_not_store_material(
    client: TestClient,
    tmp_path: Path,
):
    response = client.post(
        "/api/evidence",
        json={
            "event_type": "quiz",
            "concept": "Retrieval practice",
            "score": 2,
            "confidence": 4,
            "linked": None,
            "review_stage": None,
        },
    )
    assert response.status_code == 200
    database = tmp_path / "sparring.sqlite3"
    with sqlite3.connect(database) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(learning_evidence)").fetchall()
        }
        row = connection.execute(
            "SELECT event_type, concept, score, confidence FROM learning_evidence"
        ).fetchone()
    assert "material" not in columns
    assert "answer" not in columns
    assert row == ("quiz", "Retrieval practice", 2, 4.0)


def test_real_mode_without_key_fails_honestly(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(mode="real", database_path=tmp_path / "real.sqlite3")
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/health")
        assert health.json()["ai_ready"] is False
        response = client.post(
            "/api/plan",
            json={"material": "A grounded paragraph. " * 20},
        )
    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == "ai_not_configured"
    assert "OPENAI_API_KEY" not in response.text
    assert payload["retryable"] is False


def test_static_shell_has_security_headers(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "'wasm-unsafe-eval'" in response.headers["content-security-policy"]
    assert "worker-src 'self' blob:" in response.headers["content-security-policy"]
    assert "img-src 'self' data: blob:" in response.headers["content-security-policy"]
    assert "unsafe-inline" not in response.headers["content-security-policy"]
