from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.db import EvidenceStore
from app.engine import EngineError, build_engine
from app.pdf_extract import PDFExtractionError, extract_pdf_material
from app.schemas import (
    ColdIn,
    ColdQuiz,
    EvidenceIn,
    EvidenceReceipt,
    ExtractedMaterial,
    HealthOut,
    LessonIn,
    LessonOutput,
    PlanIn,
    StudyPlan,
    TeachbackIn,
    TeachbackOutput,
)

logger = logging.getLogger("sparring")


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings.from_env()
    store = EvidenceStore(cfg.database_path)
    engine = build_engine(cfg)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.initialize()
        yield

    api = FastAPI(
        title="Sparring",
        version="0.2.0",
        docs_url="/api/docs" if cfg.expose_docs else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    api.state.settings = cfg
    api.state.store = store
    api.state.engine = engine

    @api.middleware("http")
    async def session_and_security_headers(request: Request, call_next):
        session_id = request.cookies.get("sparring_session")
        new_session = not session_id or len(session_id) > 80
        if new_session:
            session_id = secrets.token_urlsafe(24)
        request.state.session_id = session_id
        response = await call_next(request)
        if new_session:
            response.set_cookie(
                "sparring_session",
                session_id,
                max_age=60 * 60 * 24 * 30,
                httponly=True,
                samesite="lax",
                secure=request.url.scheme == "https",
            )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self'; script-src 'self'; "
            "connect-src 'self'; object-src 'none'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'"
        )
        return response

    @api.exception_handler(EngineError)
    async def engine_error_handler(_: Request, exc: EngineError):
        logger.warning("Learning engine request failed: %s", exc.log_message)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.public_message,
                "code": exc.code,
                "retryable": exc.retryable,
            },
        )

    @api.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, __: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Check the submitted fields and try again.",
                "code": "invalid_request",
                "retryable": False,
            },
        )

    @api.exception_handler(PDFExtractionError)
    async def pdf_error_handler(_: Request, exc: PDFExtractionError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.public_message,
                "code": exc.code,
                "retryable": False,
            },
        )

    def material_or_400(raw: str) -> str:
        material = raw.strip()
        if len(material) < cfg.material_min_chars:
            raise HTTPException(
                400,
                "Provide at least one complete sentence "
                f"({cfg.material_min_chars} characters) of study material.",
            )
        if len(material) > cfg.material_max_chars:
            raise HTTPException(
                413,
                f"Keep the material under {cfg.material_max_chars:,} characters for this demo.",
            )
        return material

    @api.get("/api/health", response_model=HealthOut)
    def health() -> HealthOut:
        return HealthOut(
            ok=store.is_ready(),
            ai_ready=engine.is_ready(),
            service="sparring",
        )

    @api.post("/api/extract/pdf", response_model=ExtractedMaterial)
    async def extract_pdf(file: UploadFile = File(...)) -> ExtractedMaterial:
        filename = file.filename
        try:
            data = await file.read(cfg.pdf_max_bytes + 1)
        finally:
            await file.close()
        return extract_pdf_material(data, filename, cfg)

    @api.post("/api/plan", response_model=StudyPlan)
    def plan(body: PlanIn) -> StudyPlan:
        return engine.plan(material_or_400(body.material))

    @api.post("/api/lesson", response_model=LessonOutput)
    def lesson(body: LessonIn) -> LessonOutput:
        material = material_or_400(body.material)
        return engine.lesson(material, body.concept.strip())

    @api.post("/api/teachback", response_model=TeachbackOutput)
    def teachback(body: TeachbackIn) -> TeachbackOutput:
        material = material_or_400(body.material)
        answer = body.answer.strip()
        if len(answer) < 10:
            raise HTTPException(400, "Write your two-line explanation first.")
        return engine.teachback(material, body.concept.strip(), answer)

    @api.post("/api/cold", response_model=ColdQuiz)
    def cold(body: ColdIn) -> ColdQuiz:
        material = material_or_400(body.material)
        return engine.cold(material, body.quiz)

    @api.post("/api/evidence", response_model=EvidenceReceipt)
    def evidence(body: EvidenceIn, request: Request) -> EvidenceReceipt:
        store.record(request.state.session_id, body)
        return EvidenceReceipt(saved=True)

    static_dir = Path(cfg.static_dir)
    api.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return api


app = create_app()
