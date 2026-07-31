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
COMPACT_CONNECTORS = ("因为", "所以", "因此", "导致", "依赖", "从而", "使得", "对比")


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
    return text[:180].strip()


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
    names: list[str] = []
    seen_names: set[str] = set()
    for index, piece in enumerate(pieces[:3]):
        base_name = _name(piece, index)
        name = base_name
        suffix = index + 1
        while name.casefold() in seen_names:
            name = f"{base_name} {suffix}"
            suffix += 1
        names.append(name)
        seen_names.add(name.casefold())
    concepts = []
    for name, piece in zip(names, pieces[:3], strict=True):
        definition = _anchor(piece)
        concepts.append(
            ConceptPlan(
                name=name,
                plain_definition=definition,
                why=f"It explains the process or distinction the source assigns to {name}.",
                predict_q=(
                    f"What result would you expect if the process named {name} were "
                    "removed or reversed?"
                ),
                depends_on=[],
                relationship_to_dependencies=None,
                source_anchor=definition,
            )
        )
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
) -> QuizItem:
    correct = anchor
    distractors = [
        (
            f"{concept} is only a label to memorize; it has no process, relationship, "
            "or observable result.",
            "label instead of process",
        ),
        (
            f"{concept} works only after the answer is supplied, so no attempt or "
            "comparison is needed.",
            "answer before attempt",
        ),
        (
            f"{concept} reverses the stated relationship, making the described cause "
            "produce its opposite result.",
            "causal direction reversed",
        ),
    ]
    option_rows = [
        (
            text,
            "This choice removes or reverses a required part of the anchored relationship.",
            tag,
        )
        for text, tag in distractors
    ]
    option_rows.insert(
        correct_index,
        (
            correct,
            "This preserves the process and relationship stated in the source anchor.",
            "",
        ),
    )
    options = [row[0] for row in option_rows]
    why = [row[1] for row in option_rows]
    tags = [row[2] for row in option_rows]
    stems = {
        "definition": f"Which meaning is essential to {concept}?",
        "mechanism": f"Which sequence preserves how {concept} produces its result?",
        "application": f"A learner follows {concept}. Which action matches the described process?",
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


def _known_fixture_lesson(material: str, concept: str) -> LessonOutput | None:
    """High-quality deterministic activities for the repository's public sample only."""

    key = concept.casefold().strip()
    lessons = {
        "retrieval practice": {
            "anchor": (
                "Retrieval practice asks a learner to bring an idea back from memory before "
                "seeing the answer."
            ),
            "explanation": (
                "Retrieval practice starts with an attempted answer, not with rereading. "
                "That attempt creates something concrete to compare with the source, which "
                "is why later feedback becomes more useful. The key sequence is recall first, "
                "then check: the effort exposes what the learner could reconstruct."
            ),
            "teachback": (
                "In two lines, connect the attempted answer, the source, and why feedback "
                "becomes more useful."
            ),
            "questions": [
                {
                    "kind": "definition",
                    "stem": "Which sequence is retrieval practice?",
                    "options": [
                        "Read the source, copy its answer, then try to remember the copy.",
                        "Try to recall the idea, then compare the attempt with the source.",
                        "Rate confidence in the idea, then skip checking the source.",
                        "Wait several days, then reread the original question and answer.",
                    ],
                    "answer": 1,
                    "why": [
                        "Seeing and copying the answer first removes the retrieval attempt.",
                        "The source defines retrieval as bringing the idea back before the answer.",
                        "Confidence is another observation; it does not replace retrieval.",
                        "Delay belongs to spaced review and still does not create an attempt here.",
                    ],
                    "tag": [
                        "answer shown before retrieval",
                        "",
                        "confidence confused with retrieval",
                        "delay confused with retrieval",
                    ],
                    "source_anchor": (
                        "Retrieval practice asks a learner to bring an idea back from memory "
                        "before seeing the answer."
                    ),
                },
                {
                    "kind": "mechanism",
                    "stem": "Why does trying before feedback make the feedback more useful?",
                    "options": [
                        "The attempt removes the need to compare the answer with the source.",
                        "The attempt proves the idea will remain available after a long delay.",
                        "The attempt gives the learner an answer to compare with the source.",
                        "The attempt turns confidence into a direct measure of correctness.",
                    ],
                    "answer": 2,
                    "why": [
                        "The source says comparison is the benefit, not something to remove.",
                        "The passage makes no permanence claim from one retrieval attempt.",
                        "The attempted answer makes a later source comparison possible.",
                        "The passage treats confidence and correctness as separate observations.",
                    ],
                    "tag": [
                        "comparison removed",
                        "single-attempt permanence",
                        "",
                        "confidence equals correctness",
                    ],
                    "source_anchor": (
                        "The effort of trying makes later feedback more useful because the "
                        "learner can compare an attempted answer with the source."
                    ),
                },
                {
                    "kind": "application",
                    "stem": (
                        "A learner closes the notes, writes an explanation, and then checks "
                        "the passage. Which step creates the retrieval event?"
                    ),
                    "options": [
                        "Writing the explanation before reopening and checking the notes.",
                        "Reopening the passage before making any attempt to explain it.",
                        "Reporting high confidence after reading the passage a second time.",
                        "Copying the passage so its wording remains available during recall.",
                    ],
                    "answer": 0,
                    "why": [
                        "The learner produces an answer from memory before seeing the source.",
                        "Opening the source first reverses the required order.",
                        "Confidence after rereading is not the attempted answer described here.",
                        "Keeping the wording visible prevents the stated memory-first attempt.",
                    ],
                    "tag": [
                        "",
                        "source checked before attempt",
                        "confidence substituted for recall",
                        "source remains visible",
                    ],
                    "source_anchor": (
                        "Retrieval practice asks a learner to bring an idea back from memory "
                        "before seeing the answer."
                    ),
                },
            ],
        },
        "confidence judgments": {
            "anchor": "Confidence judgments add a second observation to each answer.",
            "explanation": (
                "A confidence judgment records how certain a learner feels about an answer. "
                "It does not replace correctness; it adds a second observation. This lets "
                "feedback distinguish a low-confidence correct answer from a high-confidence "
                "error even when a quiz score alone would hide that difference."
            ),
            "teachback": (
                "In two lines, explain why correctness and confidence must remain separate "
                "observations when feedback is chosen."
            ),
            "questions": [
                {
                    "kind": "definition",
                    "stem": "What does a confidence judgment add to an answer?",
                    "options": [
                        "A guarantee that the selected answer is correct.",
                        "A replacement score based only on response speed.",
                        "A second observation about certainty in the answer.",
                        "A delayed review date for the same question.",
                    ],
                    "answer": 2,
                    "why": [
                        "Certainty is not a guarantee of correctness.",
                        "The source does not define confidence as response speed.",
                        "The passage explicitly calls confidence a second observation.",
                        "Review timing belongs to spaced practice, not confidence.",
                    ],
                    "tag": [
                        "confidence guarantees correctness",
                        "confidence confused with speed",
                        "",
                        "confidence confused with spacing",
                    ],
                    "source_anchor": (
                        "Confidence judgments add a second observation to each answer."
                    ),
                },
                {
                    "kind": "mechanism",
                    "stem": "Why can equal quiz scores still call for different feedback?",
                    "options": [
                        "Correctness is ignored whenever the learner reports high confidence.",
                        "Confidence reveals whether correct and incorrect answers felt certain.",
                        "Confidence changes every incorrect answer into partial credit.",
                        "Correctness and confidence are combined into one indistinguishable score.",
                    ],
                    "answer": 1,
                    "why": [
                        "The source keeps correctness relevant.",
                        "Confidence differentiates answers that the score alone makes look similar.",
                        "The passage does not award partial credit from confidence.",
                        "Combining the observations would erase the distinction being used.",
                    ],
                    "tag": [
                        "correctness ignored",
                        "",
                        "confidence creates credit",
                        "observations collapsed",
                    ],
                    "source_anchor": (
                        "A correct response with low confidence and an incorrect response with "
                        "high confidence need different feedback"
                    ),
                },
                {
                    "kind": "application",
                    "stem": "Which pair most clearly needs different feedback despite one answer each?",
                    "options": [
                        "A confident correct answer and another confident correct answer.",
                        "A low-confidence error and another low-confidence error.",
                        "A fast correct answer and another fast correct answer.",
                        "A low-confidence correct answer and a high-confidence error.",
                    ],
                    "answer": 3,
                    "why": [
                        "The pair has the same correctness and confidence pattern.",
                        "The pair has the same correctness and confidence pattern.",
                        "Response speed is not the second observation in the source.",
                        "The source explicitly contrasts these two evidence patterns.",
                    ],
                    "tag": [
                        "identical evidence patterns",
                        "identical error patterns",
                        "speed substituted for confidence",
                        "",
                    ],
                    "source_anchor": (
                        "A correct response with low confidence and an incorrect response with "
                        "high confidence need different feedback"
                    ),
                },
            ],
        },
        "spaced practice": {
            "anchor": "Spaced practice returns to an idea after time has passed.",
            "explanation": (
                "Spaced practice revisits an idea after a delay instead of repeating it only "
                "in the same sitting. In the source's cold review, changed wording and removed "
                "hints force reconstruction rather than recognition. The listed one-, three-, "
                "and seven-day intervals are a transparent default schedule for those returns."
            ),
            "teachback": (
                "In two lines, connect delayed return, changed wording, and why a cold review "
                "requires reconstruction rather than recognition."
            ),
            "questions": [
                {
                    "kind": "definition",
                    "stem": "Which feature makes practice spaced in this material?",
                    "options": [
                        "Returning to the idea after time has passed.",
                        "Repeating the same wording immediately with hints.",
                        "Giving feedback before the learner makes an attempt.",
                        "Replacing correctness with a confidence judgment.",
                    ],
                    "answer": 0,
                    "why": [
                        "The source defines spacing as a return after time.",
                        "Immediate repetition has no delay and preserves recognition cues.",
                        "Feedback order does not define spacing.",
                        "Confidence and spacing are separate ideas.",
                    ],
                    "tag": [
                        "",
                        "immediate repetition",
                        "feedback confused with spacing",
                        "confidence confused with spacing",
                    ],
                    "source_anchor": (
                        "Spaced practice returns to an idea after time has passed."
                    ),
                },
                {
                    "kind": "mechanism",
                    "stem": "Why does the cold review change wording and remove hints?",
                    "options": [
                        "To make the learner recognize the original question more quickly.",
                        "To make the review identical to the first attempt.",
                        "To require reconstruction of the relationship instead of recognition.",
                        "To turn the delayed review into a confidence-only judgment.",
                    ],
                    "answer": 2,
                    "why": [
                        "Changed wording reduces reliance on recognizing the original.",
                        "The cold review intentionally changes surface wording.",
                        "The source states this reconstruction purpose directly.",
                        "Confidence does not replace retrieval in the cold review.",
                    ],
                    "tag": [
                        "recognition treated as goal",
                        "cold review kept identical",
                        "",
                        "confidence substituted for recall",
                    ],
                    "source_anchor": (
                        "A cold review changes the wording and removes hints, so the learner "
                        "must reconstruct the relationship rather than recognize the original "
                        "question."
                    ),
                },
                {
                    "kind": "application",
                    "stem": "Which review follows the source's transparent default schedule?",
                    "options": [
                        "Three identical attempts in the same study session.",
                        "Reworded no-hint returns after one, three, and seven days.",
                        "One hinted attempt followed by no later return.",
                        "A confidence rating repeated without answering the question.",
                    ],
                    "answer": 1,
                    "why": [
                        "Same-session attempts do not use the stated spacing.",
                        "This combines the stated intervals with the cold-review format.",
                        "The source requires later returns for spaced practice.",
                        "A rating alone does not reconstruct the relationship.",
                    ],
                    "tag": [
                        "massed instead of spaced",
                        "",
                        "no delayed return",
                        "confidence substituted for retrieval",
                    ],
                    "source_anchor": (
                        "One, three, and seven days are a transparent default schedule here."
                    ),
                },
            ],
        },
    }
    spec = lessons.get(key)
    if spec is None:
        return None
    anchors = [spec["anchor"]] + [
        question["source_anchor"] for question in spec["questions"]
    ]
    if any(
        re.sub(r"\s+", " ", anchor).strip().casefold()
        not in re.sub(r"\s+", " ", material).strip().casefold()
        for anchor in anchors
    ):
        return None
    return LessonOutput(
        explanation=spec["explanation"],
        explanation_anchor=spec["anchor"],
        quiz=[QuizItem(**question) for question in spec["questions"]],
        teachback_q=spec["teachback"],
    )


def fixture_lesson(material: str, concept: str) -> LessonOutput:
    known = _known_fixture_lesson(material, concept)
    if known is not None:
        return known
    pieces = _chunks(material)
    concept_words = [
        word.casefold() for word in re.findall(r"[A-Za-z][A-Za-z'-]*", concept)
    ]
    matching_piece = next(
        (
            piece
            for piece in pieces
            if concept_words
            and all(word in piece.casefold() for word in concept_words[:2])
        ),
        pieces[0] if pieces else material,
    )
    anchor = _anchor(matching_piece)
    explanation = (
        f"{concept} is the process captured by this source relationship: “{anchor}” "
        "Focus on the order of the stated actions and the result that follows; changing "
        "either one changes the idea being taught."
    )
    return LessonOutput(
        explanation=explanation,
        explanation_anchor=anchor,
        quiz=[
            _quiz_item("definition", concept, anchor, 1),
            _quiz_item("mechanism", concept, anchor, 2),
            _quiz_item("application", concept, anchor, 0),
        ],
        teachback_q=(
            f"Explain {concept} to a classmate in two lines. Connect what it is to why "
            "the relationship in the material matters."
        ),
    )


def fixture_teachback(material: str, concept: str, answer: str) -> TeachbackOutput:
    normalized = f" {answer.casefold()} "
    linked = any(connector in normalized for connector in CONNECTORS) or any(
        connector in normalized for connector in COMPACT_CONNECTORS
    )
    pieces = _chunks(material)
    anchor = _anchor(
        next(
            (piece for piece in pieces if concept.casefold() in piece.casefold()),
            pieces[0] if pieces else material,
        )
    )
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
            source_anchor=anchor,
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
        source_anchor=anchor,
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
