from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "index.html").read_text()
JS = (ROOT / "static" / "app.js").read_text()
CSS = (ROOT / "static" / "styles.css").read_text()


def test_accessible_shell_contract():
    assert 'class="skip-link"' in HTML
    assert 'role="status" aria-live="polite"' in HTML
    assert "<dialog" in HTML
    assert ":focus-visible" in CSS
    assert "prefers-reduced-motion" in CSS
    assert "forced-colors" in CSS
    assert 'id="pdf-upload"' in JS
    assert 'accept=".pdf,application/pdf"' in JS
    assert "PDF files are read in server memory and not stored" in JS


def test_answer_and_confidence_require_explicit_radio_choices():
    assert 'type="radio"' in JS
    assert 'name="answer"' in JS
    assert 'name="confidence"' in JS
    assert "there is no default" in JS
    assert 'type="range"' not in JS


def test_recovery_and_offline_contract():
    assert "sparring_state_v2_recovery" in JS
    assert 'window.addEventListener("storage"' in JS
    assert 'window.addEventListener("offline"' in JS
    assert 'navigator.serviceWorker.register("./sw.js")' in JS
    assert "localStorage.removeItem(CORRUPT_KEY)" in JS
    assert (ROOT / "static" / "sw.js").exists()


def test_hosted_demo_keeps_files_local_and_uses_relative_assets():
    assert 'window.location.hostname.endsWith(".github.io")' in JS
    assert 'import("./demo-engine.mjs?v=5")' in JS
    assert "your PDF is read in this browser and is not uploaded" in JS
    assert 'href="/' not in HTML
    assert 'src="/' not in HTML
    assert (ROOT / "static" / "demo-engine.mjs").exists()
    assert (ROOT / "static" / "vendor" / "pdf.mjs").exists()
    assert (ROOT / "static" / "vendor" / "pdf.worker.mjs").exists()
    assert (ROOT / "static" / "vendor" / "PDFJS_LICENSE").exists()


def test_pdf_ready_state_does_not_require_a_second_paste():
    assert "Build practice from this PDF" in JS
    assert "Review or edit extracted text" in JS
    assert "(optional)" in JS
    assert 'minlength="200"' not in JS
    assert "Paste at least 200 characters" not in JS
    assert "const MIN_MATERIAL_CHARS = 40" in JS


def test_readme_uses_public_demo_as_the_judge_link():
    readme = (ROOT / "README.md").read_text()
    normalized_readme = " ".join(readme.split())
    assert "https://jiangggqr.github.io/sparring-ai-study-coach/" in readme
    assert "[http://localhost:8100]" not in readme
    assert "available only on the computer running it" in normalized_readme


def test_review_schedule_uses_dates_and_explicit_completion():
    assert "dueAt" in JS
    assert 'status: "scheduled"' in JS
    assert '"scheduled_reviews_complete"' in JS
    assert "Infinity" not in JS
    assert "mastered" not in JS.casefold()


def test_ui_avoids_strong_learning_claims():
    lowered = (HTML + JS).casefold()
    forbidden = [
        "scientifically proven",
        "guaranteed learning",
        "the only evidence of mastery",
        "solo test",
        "reading doesn't",
        "fully personalized",
    ]
    for claim in forbidden:
        assert claim not in lowered
