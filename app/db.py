from __future__ import annotations

import sqlite3
from pathlib import Path

from app.schemas import EvidenceIn


class EvidenceStore:
    """Stores observation-only learning evidence, never source material or answers."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    concept TEXT NOT NULL,
                    score INTEGER,
                    confidence REAL,
                    linked INTEGER,
                    review_stage INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_evidence_session_created
                ON learning_evidence(session_id, created_at)
                """
            )

    def is_ready(self) -> bool:
        try:
            with self.connect() as connection:
                return connection.execute("SELECT 1").fetchone() == (1,)
        except sqlite3.Error:
            return False

    def record(self, session_id: str, evidence: EvidenceIn) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO learning_evidence (
                    session_id, event_type, concept, score,
                    confidence, linked, review_stage
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    evidence.event_type,
                    evidence.concept,
                    evidence.score,
                    evidence.confidence,
                    None if evidence.linked is None else int(evidence.linked),
                    evidence.review_stage,
                ),
            )
