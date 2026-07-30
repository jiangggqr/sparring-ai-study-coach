from __future__ import annotations

import re

from app.schemas import ColdQuiz, ConceptPlan, LessonOutput, QuizItem, StudyPlan, TeachbackOutput


CONNECTORS = (
    " because ",
    " so ",
    " therefore ",
    " depends on ",
    " leads to ",
    " enables ",
    " causes ",
    " contrasts ",
    " because of ",
)


def _chunks(material: str) -> list[str]:
    compact = re.sub(r"[ \t]+", " ", material.strip())
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n+", compact)
        if len(paragraph.strip()) >= 35
    ]
    paragraph_leads = [
        re.split(r"(?<=[.!?。！？])\s+", paragraph, maxsplit=1)[0].strip()
        for paragraph in paragraphs
    ]
    if len(paragraph_leads) >= 3:
        return paragraph_leads[:3]
    candidates = [
        part.strip(" \n-•")
        for part in re.split(r"(?<=[.!?。！？])\s+|\n{1,}", compact)
        if len(part.strip()) >= 35
    ]
    if len(candidates) >= 3:
        return candidates[:3]
    size = max(35, len(compact) // 3)
    fallback = [compact[i : i + size].strip() for i in range(0, len(compact), size)]
    return (candidates + [item for item in fallback if len(item) >= 20])[:3]


def _anchor(text: str) -> str:
    return text[:220].strip()


def _name(text: str, index: int) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    if words:
        phrase = " ".join(words[:2]).rstrip(".,:;")
    else:
        phrase = text[:12].rstrip("，。；： ")
    return phrase


def fixture_plan(material: str) -> StudyPlan:
    pieces = _chunks(material)
    while len(pieces) < 3:
        pieces.append(material[:220])
    names = [_name(piece, index) for index, piece in enumerate(pieces[:3])]
    concepts = [
        ConceptPlan(
            name=name,
            why="It is required to explain the material's central relationship.",
            predict_q=f"Before reading closely, why might {name.split('. ', 1)[-1]} matter here?",
            source_anchor=_anchor(piece),
        )
        for name, piece in zip(names, pieces[:3], strict=True)
    ]
    return StudyPlan(
        target=(
            "After this session, you will be able to explain how "
            + ", ".join(names)
            + " fit together."
        ),
        concepts=concepts,
    )


def _quiz_item(
    kind: str,
    concept: str,
    anchor: str,
    correct_index: int,
    number: int,
) -> QuizItem:
    correct = f"The material describes this idea as: {anchor}"
    distractors = [
        (
            f"The material presents {concept} as a term to memorize, while leaving the "
            "relationship between its elements unexplained.",
            "isolated label",
        ),
        (
            f"The material presents {concept} as an isolated process that works without "
            "depending on the other ideas in the passage.",
            "false independence",
        ),
        (
            f"The material uses {concept} to support the opposite relationship from the one "
            "stated in the cited passage.",
            "reversed relationship",
        ),
    ]
    option_rows = [
        (text, "This changes or removes the relationship stated in the material.", tag)
        for text, tag in distractors
    ]
    option_rows.insert(
        correct_index,
        (correct, "This is the only option that matches the cited material.", ""),
    )
    options = [row[0] for row in option_rows]
    why = [row[1] for row in option_rows]
    tags = [row[2] for row in option_rows]
    stems = {
        "definition": f"Which statement best captures {concept} in the material?",
        "mechanism": f"Which account best explains how {concept} works?",
        "application": f"Which explanation applies {concept} without adding outside facts?",
    }
    return QuizItem(
        kind=kind,
        stem=stems[kind],
        options=options,
        answer=correct_index,
        why=why,
        tag=tags,
        source_anchor=anchor,
    )


def fixture_lesson(material: str, concept: str) -> LessonOutput:
    pieces = _chunks(material)
    anchor = _anchor(pieces[0] if pieces else material)
    explanation = (
        f"The big idea is the relationship in this passage: “{anchor}” "
        "It works by connecting the elements named there rather than treating them as "
        "an isolated list. Use the quoted passage as the boundary: explain its relationship "
        "without importing outside facts."
    )
    return LessonOutput(
        explanation=explanation,
        explanation_anchor=anchor,
        quiz=[
            _quiz_item("definition", concept, anchor, 1, 0),
            _quiz_item("mechanism", concept, anchor, 2, 1),
            _quiz_item("application", concept, anchor, 0, 2),
        ],
        teachback_q=(
            f"Explain {concept} to a classmate in two lines. Connect what it is to why "
            "the relationship in the material matters."
        ),
    )


def fixture_teachback(material: str, concept: str, answer: str) -> TeachbackOutput:
    normalized = f" {answer.casefold()} "
    linked = any(connector in normalized for connector in CONNECTORS)
    excerpt = " ".join(answer.strip().split()[:7]).rstrip(",.;:")
    if linked:
        return TeachbackOutput(
            linked=True,
            covered=[concept, "a stated relationship"],
            missing=[],
            feedback=(
                f'Your phrase “{excerpt}” connects ideas instead of merely naming them. '
                "Next, keep that causal link when the wording changes."
            ),
            repair_prompt=None,
        )
    return TeachbackOutput(
        linked=False,
        covered=[concept],
        missing=["why the ideas connect"],
        feedback=(
            f'You named the relevant idea in “{excerpt},” but the relationship is still '
            "listed rather than explained. Add one because or so connection."
        ),
        repair_prompt=f"{concept} matters because…",
    )


def fixture_cold(quiz: list[QuizItem]) -> ColdQuiz:
    def reword(option: str) -> str:
        replacements = (
            ("The material describes this idea as:", "The source frames the idea this way:"),
            ("The material presents", "The source portrays"),
            ("The material uses", "The source uses"),
        )
        for old, new in replacements:
            if old in option:
                return option.replace(old, new, 1)
        return f"Restated for review: {option}"

    rewritten: list[QuizItem] = []
    for index, item in enumerate(quiz):
        shift = (index + 1) % 4
        original_options = item.options[shift:] + item.options[:shift]
        options = [reword(option) for option in original_options]
        why = item.why[shift:] + item.why[:shift]
        tag = item.tag[shift:] + item.tag[:shift]
        rewritten.append(
            QuizItem(
                kind=item.kind,
                stem=f"Without looking back: {item.stem}",
                options=options,
                answer=(item.answer - shift) % 4,
                why=why,
                tag=tag,
                source_anchor=item.source_anchor,
            )
        )
    return ColdQuiz(quiz=rewritten)
