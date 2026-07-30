from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    mode: str = "real"
    model: str = "gpt-5.6"
    database_path: Path = PROJECT_ROOT / "data" / "sparring.sqlite3"
    static_dir: Path = PROJECT_ROOT / "static"
    material_min_chars: int = 40
    material_max_chars: int = 24_000
    pdf_max_bytes: int = 20 * 1024 * 1024
    pdf_max_pages: int = 80
    pdf_min_extracted_chars: int = 40
    expose_docs: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("SPARRING_MODE", "real").strip().lower()
        if mode not in {"real", "fixture"}:
            mode = "real"
        database_path = Path(
            os.getenv("SPARRING_DATABASE_PATH", str(cls.database_path))
        ).expanduser()
        return cls(
            mode=mode,
            model=os.getenv("SPARRING_MODEL", "gpt-5.6").strip(),
            database_path=database_path,
            static_dir=PROJECT_ROOT / "static",
            material_min_chars=int(os.getenv("SPARRING_MATERIAL_MIN", "40")),
            material_max_chars=int(os.getenv("SPARRING_MATERIAL_MAX", "24000")),
            pdf_max_bytes=int(os.getenv("SPARRING_PDF_MAX_BYTES", str(20 * 1024 * 1024))),
            pdf_max_pages=int(os.getenv("SPARRING_PDF_MAX_PAGES", "80")),
            pdf_min_extracted_chars=int(
                os.getenv("SPARRING_PDF_MIN_EXTRACTED_CHARS", "40")
            ),
            expose_docs=os.getenv("SPARRING_EXPOSE_DOCS", "0") == "1",
        )
