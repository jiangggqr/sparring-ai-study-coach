from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import Settings
from app.schemas import ExtractedMaterial


class PDFExtractionError(Exception):
    def __init__(
        self,
        *,
        code: str,
        public_message: str,
        status_code: int = 422,
    ):
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.status_code = status_code


def _clean_page_text(raw: str) -> str:
    text = raw.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_material(
    data: bytes,
    filename: str | None,
    settings: Settings,
) -> ExtractedMaterial:
    if len(data) > settings.pdf_max_bytes:
        raise PDFExtractionError(
            code="pdf_too_large",
            public_message=(
                f"Keep PDF files under {settings.pdf_max_bytes // (1024 * 1024)} MB."
            ),
            status_code=413,
        )
    if not data.startswith(b"%PDF-"):
        raise PDFExtractionError(
            code="not_a_pdf",
            public_message="That file is not a valid PDF. Choose a .pdf file and try again.",
            status_code=415,
        )

    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise PDFExtractionError(
                code="encrypted_pdf",
                public_message=(
                    "This PDF is password-protected. Export an unlocked copy, then upload it."
                ),
            )
    except PDFExtractionError:
        raise
    except (PdfReadError, ValueError, TypeError) as exc:
        raise PDFExtractionError(
            code="unreadable_pdf",
            public_message=(
                "Sparring could not read this PDF. Try exporting a fresh text-based copy."
            ),
        ) from exc

    page_count = len(reader.pages)
    if page_count == 0:
        raise PDFExtractionError(
            code="empty_pdf",
            public_message="This PDF has no pages.",
        )
    if page_count > settings.pdf_max_pages:
        raise PDFExtractionError(
            code="pdf_too_many_pages",
            public_message=(
                f"This prototype accepts up to {settings.pdf_max_pages} pages at a time. "
                "Upload one chapter or section."
            ),
            status_code=413,
        )

    parts: list[str] = []
    extracted_pages = 0
    pages_without_text = 0
    truncated = False
    current_chars = 0

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = _clean_page_text(page.extract_text() or "")
        except Exception:
            page_text = ""
        if not page_text:
            pages_without_text += 1
            continue

        section = f"[Page {page_number}]\n{page_text}"
        remaining = settings.material_max_chars - current_chars
        if remaining <= 0:
            truncated = True
            break
        if len(section) > remaining:
            section = section[:remaining].rstrip()
            truncated = True
        parts.append(section)
        extracted_pages += 1
        current_chars += len(section) + 2
        if truncated:
            break

    text = "\n\n".join(parts).strip()
    if len(text) < settings.pdf_min_extracted_chars:
        raise PDFExtractionError(
            code="pdf_has_no_text",
            public_message=(
                "This PDF contains too little selectable text. It may be a scan. "
                "Use a searchable/OCR copy, or paste the text instead."
            ),
        )

    warnings: list[str] = []
    if pages_without_text:
        warnings.append(
            f"{pages_without_text} page{'s' if pages_without_text != 1 else ''} "
            "had no extractable text."
        )
    if truncated:
        warnings.append(
            f"Only the first {settings.material_max_chars:,} extracted characters are "
            "used in this prototype."
        )

    safe_name = Path(filename or "uploaded.pdf").name[:180]
    return ExtractedMaterial(
        source_type="pdf",
        filename=safe_name,
        text=text,
        page_count=page_count,
        extracted_pages=extracted_pages,
        char_count=len(text),
        truncated=truncated,
        warnings=warnings,
    )
