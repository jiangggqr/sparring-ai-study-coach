from __future__ import annotations

import json
import logging
import os
import re
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app import prompts
from app.config import Settings
from app.fixtures import fixture_cold, fixture_lesson, fixture_plan, fixture_teachback
from app.schemas import ColdQuiz, LessonOutput, QuizItem, StudyPlan, TeachbackOutput

logger = logging.getLogger("sparring.engine")
T = TypeVar("T", bound=BaseModel)


class EngineError(Exception):
    def __init__(
        self,
        *,
        code: str,
        public_message: str,
        log_message: str,
        status_code: int = 502,
        retryable: bool = True,
    ):
        super().__init__(log_message)
        self.code = code
        self.public_message = public_message
        self.log_message = log_message
        self.status_code = status_code
        self.retryable = retryable


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _require_grounded(anchor: str, material: str) -> None:
    if _normalized(anchor) not in _normalized(material):
        raise EngineError(
            code="grounding_failed",
            public_message=(
                "The generated lesson could not be verified against your material. "
                "Retry, or paste a more complete section."
            ),
            log_message=f"Unverified source anchor: {anchor[:80]!r}",
        )


def _validate_plan_grounding(plan: StudyPlan, material: str) -> StudyPlan:
    for concept in plan.concepts:
        _require_grounded(concept.source_anchor, material)
    return plan


def _validate_lesson_grounding(lesson: LessonOutput, material: str) -> LessonOutput:
    _require_grounded(lesson.explanation_anchor, material)
    for question in lesson.quiz:
        _require_grounded(question.source_anchor, material)
    return lesson


def _validate_cold_quiz(
    original: list[QuizItem],
    cold_quiz: ColdQuiz,
    material: str,
) -> ColdQuiz:
    for original_item, variant in zip(original, cold_quiz.quiz, strict=True):
        _require_grounded(variant.source_anchor, material)
        if _normalized(original_item.source_anchor) != _normalized(variant.source_anchor):
            raise EngineError(
                code="cold_variant_drift",
                public_message=(
                    "The delayed review drifted away from the original source. "
                    "Retry to create a safer variant."
                ),
                log_message="Cold-review source anchor changed",
            )
        if original_item.kind != variant.kind:
            raise EngineError(
                code="cold_variant_drift",
                public_message="The delayed review changed its learning objective. Please retry.",
                log_message="Cold-review item kind changed",
            )
        if _normalized(original_item.stem) == _normalized(variant.stem):
            raise EngineError(
                code="cold_variant_not_reworded",
                public_message="The delayed review was not reworded enough. Please retry.",
                log_message="Cold-review stem was unchanged",
            )
        original_options = {_normalized(option) for option in original_item.options}
        if any(_normalized(option) in original_options for option in variant.options):
            raise EngineError(
                code="cold_variant_not_reworded",
                public_message="The delayed review was not reworded enough. Please retry.",
                log_message="At least one cold-review option was unchanged",
            )
    return cold_quiz


class FixtureEngine:
    def is_ready(self) -> bool:
        return True

    def plan(self, material: str) -> StudyPlan:
        return _validate_plan_grounding(fixture_plan(material), material)

    def lesson(self, material: str, concept: str) -> LessonOutput:
        return _validate_lesson_grounding(fixture_lesson(material, concept), material)

    def teachback(self, material: str, concept: str, answer: str) -> TeachbackOutput:
        return fixture_teachback(material, concept, answer)

    def cold(self, material: str, quiz: list[QuizItem]) -> ColdQuiz:
        return _validate_cold_quiz(quiz, fixture_cold(quiz), material)


class RealEngine:
    def __init__(self, settings: Settings):
        self.model = settings.model
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self._client: OpenAI | None = None

    def is_ready(self) -> bool:
        return bool(self.api_key)

    def client(self) -> OpenAI:
        if not self.api_key:
            raise EngineError(
                code="ai_not_configured",
                public_message=(
                    "The AI service is not configured on this deployment. "
                    "Your pasted material is still saved in this browser."
                ),
                log_message="OPENAI_API_KEY is missing",
                status_code=503,
                retryable=False,
            )
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, timeout=60, max_retries=1)
        return self._client

    def parse(self, schema: type[T], system: str, user: str) -> T:
        try:
            response = self.client().responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                text_format=schema,
                store=False,
            )
            parsed = response.output_parsed
            if parsed is None:
                raise ValueError("response.output_parsed was empty")
            return parsed
        except EngineError:
            raise
        except (ValidationError, ValueError) as exc:
            raise EngineError(
                code="invalid_ai_output",
                public_message="The AI returned an incomplete learning step. Please retry.",
                log_message=f"Structured output validation failed: {exc}",
            ) from exc
        except Exception as exc:
            logger.exception("OpenAI request failed")
            raise EngineError(
                code="ai_unavailable",
                public_message=(
                    "The AI service is temporarily unavailable. Your progress is safe; "
                    "retry this step in a moment."
                ),
                log_message=f"{type(exc).__name__}: {exc}",
            ) from exc

    def plan(self, material: str) -> StudyPlan:
        result = self.parse(StudyPlan, prompts.PLAN_SYSTEM, prompts.plan_user(material))
        return _validate_plan_grounding(result, material)

    def lesson(self, material: str, concept: str) -> LessonOutput:
        result = self.parse(
            LessonOutput,
            prompts.LESSON_SYSTEM,
            prompts.lesson_user(material, concept),
        )
        return _validate_lesson_grounding(result, material)

    def teachback(self, material: str, concept: str, answer: str) -> TeachbackOutput:
        return self.parse(
            TeachbackOutput,
            prompts.TEACHBACK_SYSTEM,
            prompts.teachback_user(material, concept, answer),
        )

    def cold(self, material: str, quiz: list[QuizItem]) -> ColdQuiz:
        payload = json.dumps(
            [item.model_dump(mode="json") for item in quiz],
            ensure_ascii=False,
        )
        result = self.parse(ColdQuiz, prompts.COLD_SYSTEM, prompts.cold_user(payload))
        return _validate_cold_quiz(quiz, result, material)


def build_engine(settings: Settings) -> FixtureEngine | RealEngine:
    if settings.mode == "fixture":
        return FixtureEngine()
    return RealEngine(settings)
