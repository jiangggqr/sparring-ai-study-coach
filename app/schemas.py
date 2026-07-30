from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConceptPlan(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    why: str = Field(min_length=2, max_length=240)
    predict_q: str = Field(min_length=5, max_length=360)
    source_anchor: str = Field(min_length=8, max_length=240)


class StudyPlan(StrictModel):
    target: str = Field(min_length=10, max_length=360)
    concepts: list[ConceptPlan] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def concept_names_are_unique(self):
        names = [item.name.casefold().strip() for item in self.concepts]
        if len(set(names)) != 3:
            raise ValueError("concept names must be unique")
        return self


class QuizItem(StrictModel):
    kind: Literal["definition", "mechanism", "application"]
    stem: str = Field(min_length=5, max_length=500)
    options: list[str] = Field(min_length=4, max_length=4)
    answer: int = Field(ge=0, le=3)
    why: list[str] = Field(min_length=4, max_length=4)
    tag: list[str] = Field(min_length=4, max_length=4)
    source_anchor: str = Field(min_length=8, max_length=240)

    @field_validator("options", "why")
    @classmethod
    def non_empty_items(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("items cannot be empty")
        return value

    @model_validator(mode="after")
    def correct_option_has_no_misconception_tag(self):
        if self.tag[self.answer].strip():
            raise ValueError("the correct option must have an empty misconception tag")
        return self


class LessonOutput(StrictModel):
    explanation: str = Field(min_length=20, max_length=1600)
    explanation_anchor: str = Field(min_length=8, max_length=240)
    quiz: list[QuizItem] = Field(min_length=3, max_length=3)
    teachback_q: str = Field(min_length=8, max_length=500)

    @model_validator(mode="after")
    def question_order_is_fixed(self):
        if [item.kind for item in self.quiz] != [
            "definition",
            "mechanism",
            "application",
        ]:
            raise ValueError("quiz must test definition, mechanism, then application")
        return self


class TeachbackOutput(StrictModel):
    linked: bool
    covered: list[str] = Field(max_length=4)
    missing: list[str] = Field(max_length=4)
    feedback: str = Field(min_length=5, max_length=500)
    repair_prompt: str | None


class ColdQuiz(StrictModel):
    quiz: list[QuizItem] = Field(min_length=3, max_length=3)


class PlanIn(StrictModel):
    material: str


class LessonIn(StrictModel):
    material: str
    concept: str = Field(min_length=2, max_length=120)


class TeachbackIn(StrictModel):
    material: str
    concept: str = Field(min_length=2, max_length=120)
    answer: str = Field(max_length=2000)


class ColdIn(StrictModel):
    material: str
    quiz: list[QuizItem] = Field(min_length=3, max_length=3)


class EvidenceIn(StrictModel):
    event_type: Literal["prediction", "quiz", "teachback", "cold_test"]
    concept: str = Field(min_length=2, max_length=120)
    score: int | None = Field(default=None, ge=0, le=3)
    confidence: float | None = Field(default=None, ge=1, le=5)
    linked: bool | None = None
    review_stage: int | None = Field(default=None, ge=0, le=3)


class EvidenceReceipt(StrictModel):
    saved: bool


class HealthOut(StrictModel):
    ok: bool
    ai_ready: bool
    service: Literal["sparring"]


class ExtractedMaterial(StrictModel):
    source_type: Literal["pdf"]
    filename: str
    text: str
    page_count: int = Field(ge=1)
    extracted_pages: int = Field(ge=1)
    char_count: int = Field(ge=1)
    truncated: bool
    warnings: list[str] = Field(max_length=4)
