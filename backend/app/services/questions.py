import json
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import (
    Answers,
    AssessmentAttempt,
    Assignments,
    Criteria,
    CurriculumModules,
    Curriculums,
    QuestionOptions,
    Questions,
)
from app.services.ai_service import call_llm, clean_extracted_text
from app.services.ai_transaction import AITransactionService
from app.services.assessment_Result import AssessmentResultService
from app.services.context_selector import ContextSelection, ContextSelector, QUIZ
from app.services.quiz_templates import QUESTIONS_PER_QUIZ
from app.services.text_cleaner import clean_vietnamese_text, has_vietnamese_mark

logger = logging.getLogger("uvicorn.error")

MAX_QUIZ_SOURCE_CHARS = 2800
QUIZ_COMPLETION_TOKENS = 2600
QUIZ_RATE_LIMIT_COOLDOWN_SECONDS = 60
MIN_QUIZ_SOURCE_WORDS = 30
_QUIZ_RATE_LIMIT_RETRY_AT: datetime | None = None
GENERIC_TEMPLATE_PATTERNS = (
    "sau khi hoan thanh",
    "hanh dong tiep theo hop ly",
    "muon danh gia muc do hieu",
    "muc tieu chinh cua bai hoc",
    "khi hoc phan",
    "co nhieu thong tin",
    "chia nho noi dung",
    "dau hieu nao cho thay ban da hieu bai hoc",
    "cach tu kiem tra",
    "tu kiem tra sau khi hoc",
    "ghi nho noi dung",
    "loi hoc tap nao nen tranh",
    "trinh bay lai",
    "khi so sanh cac y",
    "khi ap dung kien thuc",
    "xac dinh dung yeu cau",
    "neu chua hieu mot doan",
    "tu dat cau hoi",
)
LESSON_SOURCE_SECTION_MARKERS = (
    "noi dung tu tai lieu",
    "noi dung nguon",
    "source text",
    "source_text",
)
LESSON_REVIEW_SECTION_MARKERS = (
    "cau hoi on tap",
    "cau hoi tu luyen",
    "cau hoi kiem tra",
)


class QuestionService:
    @staticmethod
    def _assignment_field():
        if hasattr(Questions, "assignment_id"):
            return getattr(Questions, "assignment_id")
        if hasattr(Questions, "assignments_id"):
            return getattr(Questions, "assignments_id")
        return None

    @staticmethod
    def _assignment_field_name() -> str:
        if hasattr(Questions, "assignment_id"):
            return "assignment_id"
        if hasattr(Questions, "assignments_id"):
            return "assignments_id"
        raise HTTPException(
            status_code=500,
            detail="Question model does not define assignment reference field",
        )

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        cleaned = (content or "").strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            if lines and lines[0].strip().lower() == "json":
                lines = lines[1:]
            cleaned = "\n".join(lines).strip()
        return cleaned

    @classmethod
    def _extract_json_candidate(cls, content: str) -> str:
        cleaned = cls._strip_code_fences(content)
        if not cleaned:
            return ""
        if (
            (cleaned.startswith("{") and cleaned.endswith("}"))
            or (cleaned.startswith("[") and cleaned.endswith("]"))
        ):
            return cleaned

        object_start = cleaned.find("{")
        object_end = cleaned.rfind("}")
        array_start = cleaned.find("[")
        array_end = cleaned.rfind("]")

        candidates: list[str] = []
        if object_start != -1 and object_end > object_start:
            candidates.append(cleaned[object_start : object_end + 1].strip())
        if array_start != -1 and array_end > array_start:
            candidates.append(cleaned[array_start : array_end + 1].strip())

        return max(candidates, key=len) if candidates else cleaned

    @staticmethod
    def _rate_limit_retry_at() -> datetime | None:
        retry_at = _QUIZ_RATE_LIMIT_RETRY_AT
        if retry_at is not None and retry_at > datetime.utcnow():
            return retry_at
        return None

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        error_text = str(exc).lower()
        return (
            "ratelimit" in type(exc).__name__.lower()
            or "rate limit" in error_text
            or "rate_limit" in error_text
            or "429" in error_text
        )

    @staticmethod
    def _mark_rate_limit_cooldown(exc: Exception) -> None:
        global _QUIZ_RATE_LIMIT_RETRY_AT

        retry_seconds = QUIZ_RATE_LIMIT_COOLDOWN_SECONDS
        match = re.search(r"try again in\s+([0-9.]+)s", str(exc), flags=re.IGNORECASE)
        if match:
            try:
                retry_seconds = max(retry_seconds, int(float(match.group(1))) + 2)
            except ValueError:
                pass

        _QUIZ_RATE_LIMIT_RETRY_AT = datetime.utcnow() + timedelta(seconds=retry_seconds)

    def _create_question_record(
        self,
        *,
        session: Session,
        assignment: Assignments,
        criteria_id: uuid.UUID,
        content: str,
        question_type: str = "single_choice",
        explanation: str | None = None,
        generated_by: str,
    ) -> Questions:
        cleaned_content = clean_vietnamese_text(content).strip()
        cleaned_explanation = clean_vietnamese_text(explanation or "").strip()
        question_data = {
            "project_id": assignment.project_id,
            "criteria_id": criteria_id,
            "content": cleaned_content,
            "question_type": question_type,
            "explanation": cleaned_explanation or None,
            "generated_by": generated_by,
            self._assignment_field_name(): assignment.id,
        }
        question = Questions(**question_data)
        session.add(question)
        session.flush()
        return question

    def _get_or_create_lesson_criteria(self, *, session: Session) -> Criteria:
        criteria = session.exec(
            select(Criteria).where(Criteria.name == "Lesson comprehension")
        ).first()
        if criteria:
            return criteria

        criteria = Criteria(
            name="Lesson comprehension",
            description="Đánh giá mức độ hiểu nội dung từng bài học.",
            weight=1.0,
        )
        session.add(criteria)
        session.commit()
        session.refresh(criteria)
        return criteria

    def _get_or_create_module_assignment(
        self,
        *,
        session: Session,
        module: CurriculumModules,
        curriculum: Curriculums,
    ) -> Assignments:
        assignment_title = f"Bài kiểm tra - {module.title} ({module.id.hex[:8]})"
        assignment = session.exec(
            select(Assignments).where(
                Assignments.project_id == curriculum.project_id,
                Assignments.title == assignment_title,
            )
        ).first()
        if assignment:
            if assignment.curriculum_module_id is None:
                assignment.curriculum_module_id = module.id
                session.add(assignment)
                session.commit()
                session.refresh(assignment)
            return assignment

        assignment = Assignments(
            project_id=curriculum.project_id,
            curriculum_module_id=module.id,
            title=assignment_title,
            description=f"Bài trắc nghiệm riêng cho bài học: {module.title}.",
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        return assignment

    @staticmethod
    def _build_module_questions(module: CurriculumModules) -> list[dict]:
        return []

    @staticmethod
    def _is_legacy_unaccented_question_set(questions: list[Questions]) -> bool:
        if not questions:
            return False
        return all(not has_vietnamese_mark(question.content or "") for question in questions)

    @staticmethod
    def _fold_for_matching(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value or "")
        folded = "".join(
            char
            for char in normalized
            if unicodedata.category(char) != "Mn"
        )
        return folded.replace("đ", "d").replace("Đ", "d").lower()

    @classmethod
    def _is_generic_template_content(cls, content: str) -> bool:
        folded_content = cls._fold_for_matching(content)
        return any(pattern in folded_content for pattern in GENERIC_TEMPLATE_PATTERNS)

    @classmethod
    def _is_generic_template_question_set(cls, questions: list[Questions]) -> bool:
        if not questions:
            return False

        generic_count = 0
        for question in questions:
            if cls._is_generic_template_content(question.content or ""):
                generic_count += 1

        return generic_count > (len(questions) / 2)

    @classmethod
    def _filter_generic_template_questions(
        cls,
        questions: list[Questions],
    ) -> list[Questions]:
        return [
            question
            for question in questions
            if not cls._is_generic_template_content(question.content or "")
        ]

    @staticmethod
    def _limit_source_text(source_text: str) -> str:
        cleaned = clean_extracted_text(source_text or "").strip()
        if len(cleaned) <= MAX_QUIZ_SOURCE_CHARS:
            return cleaned

        passages = [
            passage.strip()
            for passage in re.split(r"\n\s*\n+", cleaned)
            if passage.strip()
        ]
        if len(passages) <= 1:
            return cleaned[:MAX_QUIZ_SOURCE_CHARS].strip()

        selected: list[str] = []
        used_chars = 0
        target_count = min(len(passages), 8)
        indices = sorted(
            {
                round(step * (len(passages) - 1) / max(target_count - 1, 1))
                for step in range(target_count)
            }
        )
        per_passage_budget = max(
            1,
            (MAX_QUIZ_SOURCE_CHARS - (2 * max(len(indices) - 1, 0))) // len(indices),
        )
        for index in indices:
            passage = passages[index][:per_passage_budget].strip()
            addition = len(passage) + (2 if selected else 0)
            if used_chars + addition > MAX_QUIZ_SOURCE_CHARS:
                break
            selected.append(passage)
            used_chars += addition

        return "\n\n".join(selected).strip() or cleaned[:MAX_QUIZ_SOURCE_CHARS].strip()

    @staticmethod
    def _has_enough_source_text(source_text: str) -> bool:
        words = re.findall(r"[0-9A-Za-zÀ-ỹĐđ]+", source_text or "")
        return len(words) >= MIN_QUIZ_SOURCE_WORDS

    @classmethod
    def _extract_lesson_source_text(cls, lesson_content: str | None) -> str:
        cleaned = clean_vietnamese_text(lesson_content or "").strip()
        if not cleaned:
            return ""

        lines = cleaned.splitlines()
        source_lines: list[str] = []
        in_source_section = False
        for line in lines:
            stripped = line.strip()
            folded_header = cls._fold_for_matching(stripped.lstrip("#").strip())
            if stripped.startswith("#") and any(
                marker in folded_header for marker in LESSON_SOURCE_SECTION_MARKERS
            ):
                in_source_section = True
                continue

            if in_source_section and stripped.startswith("#"):
                break

            if in_source_section:
                source_lines.append(line)

        source_section = "\n".join(source_lines).strip()
        if cls._has_enough_source_text(source_section):
            return cls._limit_source_text(source_section)

        kept_lines: list[str] = []
        skip_section = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                folded_header = cls._fold_for_matching(stripped.lstrip("#").strip())
                skip_section = any(
                    marker in folded_header for marker in LESSON_REVIEW_SECTION_MARKERS
                )
                if skip_section:
                    continue

            if not skip_section:
                kept_lines.append(line)

        return cls._limit_source_text("\n".join(kept_lines))

    def _create_template_questions(
        self,
        *,
        session: Session,
        assignment: Assignments,
        criteria_id: uuid.UUID,
        title: str,
        description: str = "",
        curriculum_module_id: uuid.UUID | None = None,
        start_index: int = 0,
        count: int = QUESTIONS_PER_QUIZ,
    ) -> list[Questions]:
        return []

    @staticmethod
    def _coerce_correct_index(raw_value) -> int | None:
        if raw_value is None:
            return None
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return None
        return value if 0 <= value <= 3 else None

    @classmethod
    def _normalize_options(cls, raw_options, correct_index=None) -> list[dict]:
        if not isinstance(raw_options, list) or len(raw_options) != 4:
            return []

        options: list[dict] = []
        correct_indices: list[int] = []
        compact_correct_index = cls._coerce_correct_index(correct_index)

        for index, raw_option in enumerate(raw_options):
            if isinstance(raw_option, dict):
                content = clean_vietnamese_text(str(
                    raw_option.get("content")
                    or raw_option.get("text")
                    or raw_option.get("label")
                    or ""
                )).strip()
                raw_is_correct = raw_option.get("is_correct", False)
                is_correct = (
                    raw_is_correct is True
                    or (
                        isinstance(raw_is_correct, str)
                        and raw_is_correct.strip().lower() == "true"
                    )
                )
            else:
                content = clean_vietnamese_text(str(raw_option or "")).strip()
                is_correct = compact_correct_index == index

            if not content:
                return []

            if is_correct:
                correct_indices.append(len(options))
            options.append(
                {
                    "content": content,
                    "is_correct": False,
                    "order_index": len(options),
                }
            )

        if len(options) != 4 or len(correct_indices) != 1:
            return []

        options[correct_indices[0]]["is_correct"] = True
        return options

    def _create_option_records(
        self,
        *,
        session: Session,
        question: Questions,
        raw_options,
    ) -> list[QuestionOptions]:
        normalized_options = self._normalize_options(raw_options)
        option_records: list[QuestionOptions] = []

        for option_data in normalized_options:
            option = QuestionOptions(
                question_id=question.id,
                content=option_data["content"],
                is_correct=option_data["is_correct"],
                order_index=option_data["order_index"],
            )
            session.add(option)
            option_records.append(option)

        return option_records

    @staticmethod
    def _serialize_options(
        options: list[QuestionOptions],
        *,
        include_correct: bool = False,
    ) -> list[dict]:
        serialized = []
        for option in sorted(
            options,
            key=lambda item: (
                item.order_index is None,
                item.order_index or 0,
                item.created_at,
            ),
        ):
            option_data = {
                "id": str(option.id),
                "content": option.content,
                "order_index": option.order_index,
            }
            if include_correct:
                option_data["is_correct"] = option.is_correct
            serialized.append(option_data)
        return serialized

    def _parse_ai_questions(self, response: str) -> list[dict]:
        data = json.loads(self._extract_json_candidate(response))
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            questions = data.get("question") or data.get("questions") or []
            if isinstance(questions, list):
                return [item for item in questions if isinstance(item, dict)]
        return []

    @staticmethod
    def _build_source_quiz_prompt(source_text: str) -> str:
        return f"""
Return only valid JSON. No markdown. Write Vietnamese with accents.
Use only SOURCE_TEXT. Do not create study-method, note-taking, review, or self-check questions.
Create up to {QUESTIONS_PER_QUIZ} source-grounded multiple-choice questions.
Each item must test one concrete fact, definition, role, difference, date, person, or application in SOURCE_TEXT.
Each source_quote must be copied from SOURCE_TEXT.

Schema:
{{"questions":[{{"content":"...","options":["...","...","...","..."],"correct_index":0,"explanation":"...","source_quote":"..."}}]}}

Rules:
- correct_index is 0, 1, 2, or 3.
- Exactly 4 options per question.
- If the source is weak, return {{"questions":[]}}.

SOURCE_TEXT:
{source_text}
""".strip()

    @classmethod
    def _source_contains_quote(cls, *, source_text: str, source_quote: str) -> bool:
        normalized_source = " ".join(
            clean_vietnamese_text(source_text or "").lower().split()
        )
        normalized_quote = " ".join(
            clean_vietnamese_text(source_quote or "").lower().split()
        )
        if len(normalized_quote) < 12:
            return False
        return normalized_quote in normalized_source

    def _normalize_ai_question_item(
        self,
        item: dict,
        *,
        source_text: str,
    ) -> dict | None:
        question_content = clean_vietnamese_text(str(item.get("content") or "")).strip()
        if not question_content:
            return None
        if has_vietnamese_mark(source_text) and not has_vietnamese_mark(question_content):
            return None
        if self._is_generic_template_content(question_content):
            return None

        correct_index = None
        for key in ("correct_index", "answer_index", "correct_option_index"):
            if key in item:
                correct_index = item.get(key)
                break

        normalized_options = self._normalize_options(
            item.get("options"),
            correct_index=correct_index,
        )
        if len(normalized_options) != 4:
            return None

        source_quote = clean_vietnamese_text(str(item.get("source_quote") or "")).strip()
        if not self._source_contains_quote(
            source_text=source_text,
            source_quote=source_quote,
        ):
            return None

        explanation = clean_vietnamese_text(str(item.get("explanation") or "")).strip()
        return {
            "content": question_content,
            "question_type": "single_choice",
            "options": normalized_options,
            "explanation": explanation or None,
            "source_quote": source_quote,
        }

    def _generate_question_payloads_from_source(
        self,
        *,
        source_text: str,
        count: int = QUESTIONS_PER_QUIZ,
        session: Session | None = None,
        user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        context_selection: ContextSelection | None = None,
    ) -> list[dict]:
        source_text = self._limit_source_text(source_text)
        if not self._has_enough_source_text(source_text):
            return []

        retry_at = self._rate_limit_retry_at()
        if retry_at is not None:
            logger.info(
                "Skipping quiz question generation while AI provider is rate-limited. retry_at=%s",
                retry_at.isoformat(),
            )
            return []

        try:
            prompt = self._build_source_quiz_prompt(source_text)
            if session is not None and user_id is not None and project_id is not None:
                response = AITransactionService.chat(
                    db=session,
                    user_id=user_id,
                    project_id=project_id,
                    action_type="generate_quiz_questions",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    response_format={
                        "type": "json_object",
                    },
                    temperature=0.1,
                    max_completion_tokens=QUIZ_COMPLETION_TOKENS,
                    context_selection=context_selection,
                )
            else:
                response = call_llm(
                    prompt,
                    temperature=0.1,
                    max_completion_tokens=QUIZ_COMPLETION_TOKENS,
                    response_format={"type": "json_object"},
                    context_selection=context_selection,
                )

            raw_questions = self._parse_ai_questions(response)
        except HTTPException as exc:
            if exc.status_code == 429 or self._is_rate_limit_error(exc):
                self._mark_rate_limit_cooldown(exc)
                logger.warning(
                    "AI provider rate limit detected during quiz question generation. Marking cooldown. error=%s",
                    str(exc),
                )
                return []
            if exc.status_code in {400, 403}:
                raise
            logger.error(
                "AI provider returned an HTTP error during quiz question generation. status_code=%s error=%s",
                exc.status_code,
                str(exc.detail),
                exc_info=True,
            )
            return []
        except Exception as exc:
            if self._is_rate_limit_error(exc):
                self._mark_rate_limit_cooldown(exc)
                logger.warning(
                    "AI provider rate limit detected during quiz question generation. Marking cooldown. error=%s",
                    str(exc),
                )
            else:
                logger.error(
                    "Error during quiz question generation. error=%s",
                    str(exc),
                    exc_info=True,
                )
            return []
        normalized_questions: list[dict] = []
        for item in raw_questions:
            if len(normalized_questions) >= count:
                break
            normalized = self._normalize_ai_question_item(
                item,
                source_text=source_text,
            )
            if normalized:
                normalized_questions.append(normalized)
        logger.info(
            "Quiz questions generated. source_chars=%s requested_questions=%s generated_questions=%s",
            len(source_text),
            count,
            len(normalized_questions),
        )
        return normalized_questions

    def _create_source_questions(
        self,
        *,
        session: Session,
        assignment: Assignments,
        criteria_id: uuid.UUID,
        source_text: str,
        curriculum_module_id: uuid.UUID | None = None,
        generated_by: str = "ai",
        count: int = QUESTIONS_PER_QUIZ,
        user_id: uuid.UUID | None = None,
    ) -> list[Questions]:
        created_questions: list[Questions] = []
        context_selection = ContextSelector(session).select_text(
            QUIZ,
            source_text,
            retrieval_strategy="quiz_source_text_guard",
        )
        generated_questions = self._generate_question_payloads_from_source(
            source_text=context_selection.text,
            count=count,
            session=session,
            user_id=user_id,
            project_id=assignment.project_id if assignment else None,
            context_selection=context_selection,
        )

        for generated_question in generated_questions[:count]:
            explanation = generated_question.get("explanation") or ""
            source_quote = generated_question.get("source_quote") or ""
            if source_quote:
                source_note = f"Nguồn: {source_quote}"
                explanation = (
                    f"{explanation}\n{source_note}"
                    if explanation
                    else source_note
                )

            question = self._create_question_record(
                session=session,
                assignment=assignment,
                criteria_id=criteria_id,
                content=generated_question["content"],
                question_type="single_choice",
                explanation=explanation or None,
                generated_by=generated_by,
            )
            if curriculum_module_id is not None:
                question.curriculum_module_id = curriculum_module_id
                session.add(question)

            option_records = self._create_option_records(
                session=session,
                question=question,
                raw_options=generated_question.get("options"),
            )
            if len(option_records) != 4:
                session.delete(question)
                continue

            created_questions.append(question)

        return created_questions

    def _collect_assignment_source_text(
        self,
        *,
        session: Session,
        assignment: Assignments,
        fallback_text: str = "",
    ) -> str:
        selection = ContextSelector(session).select(
            QUIZ,
            assignment.project_id,
            module_id=assignment.curriculum_module_id,
            assignment=assignment,
        )
        return self._limit_source_text(selection.text or fallback_text)

    def get_questions(
        self,
        *,
        session: Session,
        assignment_id: uuid.UUID,
        include_correct: bool = False,
    ):
        assignment = session.get(Assignments, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        assignment_field = self._assignment_field()
        if assignment_field is None:
            raise HTTPException(
                status_code=500,
                detail="Question model does not define assignment reference field",
            )

        statement = (
            select(Questions, Criteria)
            .join(Criteria, Questions.criteria_id == Criteria.id)
            .where(assignment_field == assignment_id)
            .order_by(Questions.created_at.desc())
        )

        results = session.exec(statement).all()
        question_ids = [question.id for question, _ in results]
        option_rows: list[QuestionOptions] = []
        if question_ids:
            option_rows = session.exec(
                select(QuestionOptions).where(QuestionOptions.question_id.in_(question_ids))
            ).all()

        options_by_question: dict[uuid.UUID, list[QuestionOptions]] = {}
        for option in option_rows:
            options_by_question.setdefault(option.question_id, []).append(option)

        return [
            {
                "id": str(question.id),
                "content": question.content,
                "question_type": question.question_type,
                "explanation": question.explanation if include_correct else None,
                "assignment_id": str(assignment_id),
                "curriculum_module_id": (
                    str(question.curriculum_module_id)
                    if question.curriculum_module_id
                    else None
                ),
                "generated_by": question.generated_by,
                "created_at": question.created_at.isoformat(),
                "options": self._serialize_options(
                    options_by_question.get(question.id, []),
                    include_correct=include_correct,
                ),
                "criteria": {
                    "id": str(criteria.id),
                    "name": criteria.name,
                    "description": criteria.description,
                },
            }
            for question, criteria in results
        ]

    def get_assignment_quiz(
        self,
        *,
        session: Session,
        assignment_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        assignment = session.get(Assignments, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        questions = self._ensure_assignment_questions(
            session=session,
            assignment=assignment,
            user_id=user_id,
        )
        question_ids = [question.id for question in questions]
        option_rows: list[QuestionOptions] = []
        if question_ids:
            option_rows = session.exec(
                select(QuestionOptions).where(QuestionOptions.question_id.in_(question_ids))
            ).all()

        options_by_question: dict[uuid.UUID, list[QuestionOptions]] = {}
        for option in option_rows:
            options_by_question.setdefault(option.question_id, []).append(option)

        return {
            "assignment": {
                "id": str(assignment.id),
                "project_id": str(assignment.project_id),
                "title": assignment.title,
                "description": assignment.description,
            },
            "questions": [
                {
                    "id": str(question.id),
                    "content": question.content,
                    "question_type": question.question_type,
                    "explanation": None,
                    "assignment_id": str(assignment.id),
                    "curriculum_module_id": (
                        str(question.curriculum_module_id)
                        if question.curriculum_module_id
                        else None
                    ),
                    "generated_by": question.generated_by,
                    "created_at": question.created_at.isoformat(),
                    "options": self._serialize_options(
                        options_by_question.get(question.id, []),
                        include_correct=False,
                    ),
                }
                for question in questions
                if options_by_question.get(question.id)
            ][:QUESTIONS_PER_QUIZ],
        }

    def _ensure_assignment_questions(
        self,
        *,
        session: Session,
        assignment: Assignments,
        user_id: uuid.UUID | None = None,
    ) -> list[Questions]:
        assignment_field = self._assignment_field()
        if assignment_field is None:
            raise HTTPException(
                status_code=500,
                detail="Question model does not define assignment reference field",
            )

        questions = session.exec(
            select(Questions)
            .where(assignment_field == assignment.id)
            .order_by(Questions.created_at)
        ).all()

        criteria = self._get_or_create_lesson_criteria(session=session)
        legacy_unaccented = self._is_legacy_unaccented_question_set(questions)
        generic_template = self._is_generic_template_question_set(questions)
        valid_existing_questions = self._filter_generic_template_questions(questions)
        needs_generation = (
            not valid_existing_questions
            or legacy_unaccented
            or generic_template
            or len(valid_existing_questions) < QUESTIONS_PER_QUIZ
        )
        if needs_generation:
            created_questions = self._create_source_questions(
                session=session,
                assignment=assignment,
                criteria_id=criteria.id,
                user_id=user_id,
                source_text=self._collect_assignment_source_text(
                    session=session,
                    assignment=assignment,
                    fallback_text=assignment.description or assignment.title,
                ),
                count=QUESTIONS_PER_QUIZ,
            )
            if created_questions:
                session.commit()
                for question in created_questions:
                    session.refresh(question)
                return created_questions[:QUESTIONS_PER_QUIZ]
            if legacy_unaccented or not valid_existing_questions:
                return []

        latest_questions = session.exec(
            select(Questions)
            .where(assignment_field == assignment.id)
            .order_by(Questions.created_at.desc())
        ).all()
        return self._filter_generic_template_questions(latest_questions)[
            :QUESTIONS_PER_QUIZ
        ]

    def _ensure_module_questions(
        self,
        *,
        session: Session,
        module: CurriculumModules,
        curriculum: Curriculums,
        user_id: uuid.UUID | None = None,
    ) -> list[Questions]:
        questions = session.exec(
            select(Questions)
            .where(Questions.curriculum_module_id == module.id)
            .order_by(Questions.created_at)
        ).all()

        criteria = self._get_or_create_lesson_criteria(session=session)
        assignment = self._get_or_create_module_assignment(
            session=session,
            module=module,
            curriculum=curriculum,
        )

        legacy_unaccented = self._is_legacy_unaccented_question_set(questions)
        generic_template = self._is_generic_template_question_set(questions)
        valid_existing_questions = self._filter_generic_template_questions(questions)
        needs_generation = (
            not valid_existing_questions
            or legacy_unaccented
            or generic_template
            or len(valid_existing_questions) < QUESTIONS_PER_QUIZ
        )
        if needs_generation:
            selection = ContextSelector(session).select(
                QUIZ,
                curriculum.project_id,
                module_id=module.id,
            )
            created_questions = self._create_source_questions(
                session=session,
                assignment=assignment,
                criteria_id=criteria.id,
                user_id=user_id,
                source_text=self._extract_lesson_source_text(selection.text),
                curriculum_module_id=module.id,
                count=QUESTIONS_PER_QUIZ,
            )
            if created_questions:
                session.commit()
                for question in created_questions:
                    session.refresh(question)
                return created_questions[:QUESTIONS_PER_QUIZ]
            if legacy_unaccented or not valid_existing_questions:
                return []

        latest_questions = session.exec(
            select(Questions)
            .where(Questions.curriculum_module_id == module.id)
            .order_by(Questions.created_at.desc())
        ).all()
        return self._filter_generic_template_questions(latest_questions)[
            :QUESTIONS_PER_QUIZ
        ]

    def get_module_quiz(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        module = session.get(CurriculumModules, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        curriculum = session.get(Curriculums, module.curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        questions = self._ensure_module_questions(
            session=session,
            module=module,
            curriculum=curriculum,
            user_id=user_id,
        )
        question_ids = [question.id for question in questions]
        option_rows: list[QuestionOptions] = []
        if question_ids:
            option_rows = session.exec(
                select(QuestionOptions).where(QuestionOptions.question_id.in_(question_ids))
            ).all()

        options_by_question: dict[uuid.UUID, list[QuestionOptions]] = {}
        for option in option_rows:
            options_by_question.setdefault(option.question_id, []).append(option)

        return {
            "target": {
                "id": str(module.id),
                "project_id": str(curriculum.project_id),
                "title": module.title,
                "description": module.description,
                "type": "lesson",
            },
            "questions": [
                {
                    "id": str(question.id),
                    "content": question.content,
                    "question_type": question.question_type,
                    "explanation": None,
                    "assignment_id": (
                        str(question.assignments_id)
                        if question.assignments_id
                        else None
                    ),
                    "curriculum_module_id": str(module.id),
                    "generated_by": question.generated_by,
                    "created_at": question.created_at.isoformat(),
                    "options": self._serialize_options(
                        options_by_question.get(question.id, []),
                        include_correct=False,
                    ),
                }
                for question in questions
                if options_by_question.get(question.id)
            ],
        }

    @staticmethod
    def _build_quiz_evaluation(
        *,
        score: float,
        correct_count: int,
        total_questions: int,
    ) -> dict:
        if score > 80:
            readiness_level = "high"
            title = "Ket qua tot"
            summary = "Ban nam kha vung noi dung bai kiem tra."
            recommendations = [
                "Tiep tuc luyen tap voi cac cau hoi kho hon.",
                "Xem lai giai thich tung cau de tranh sai sot nho.",
            ]
        elif score >= 50:
            readiness_level = "medium"
            title = "Can on tap them"
            summary = "Ban da nam duoc mot phan noi dung, nhung van con diem can cung co."
            recommendations = [
                "On lai cac cau tra loi sai va phan giai thich.",
                "Lam lai bai sau khi xem lai tai lieu lien quan.",
            ]
        else:
            readiness_level = "low"
            title = "Can hoc lai kien thuc nen"
            summary = "Ket qua cho thay ban can cung co lai cac noi dung chinh truoc khi tiep tuc."
            recommendations = [
                "Doc lai bai hoc va ghi chu cac y chinh.",
                "Lam lai bai kiem tra sau khi on tung nhom cau hoi.",
            ]

        return {
            "readiness_level": readiness_level,
            "title": title,
            "summary": summary,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "score": score,
            "recommendations": recommendations,
        }

    @staticmethod
    def _serialize_assessment_result(result) -> dict | None:
        if not result:
            return None

        return {
            "id": str(result.id),
            "user_id": str(result.user_id),
            "project_id": str(result.project_id),
            "total_score": result.total_score,
            "readiness_level": result.readiness_level,
            "created_at": result.created_at.isoformat() if result.created_at else None,
        }

    def _create_quiz_assessment_result(
        self,
        *,
        session: Session,
        attempt_id: uuid.UUID,
    ) -> dict | None:
        result = AssessmentResultService(session).create_from_attempt(attempt_id)
        return self._serialize_assessment_result(result)

    def submit_assignment_quiz(
        self,
        *,
        session: Session,
        assignment_id: uuid.UUID,
        user_id: uuid.UUID,
        answers: list[dict],
    ) -> dict:
        assignment = session.get(Assignments, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        assignment_field = self._assignment_field()
        if assignment_field is None:
            raise HTTPException(
                status_code=500,
                detail="Question model does not define assignment reference field",
            )

        questions = session.exec(
            select(Questions)
            .where(assignment_field == assignment_id)
            .order_by(Questions.created_at)
        ).all()
        if not questions:
            raise HTTPException(status_code=400, detail="This assignment has no questions")

        selected_by_question: dict[uuid.UUID, uuid.UUID] = {}
        assignment_question_ids = {question.id for question in questions}
        for answer in answers:
            question_id = answer.get("question_id")
            selected_option_id = answer.get("selected_option_id")
            if question_id not in assignment_question_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Answer question does not belong to this assignment",
                )
            if question_id in selected_by_question:
                raise HTTPException(
                    status_code=400,
                    detail="Duplicate answer for the same question",
                )
            if selected_option_id:
                selected_by_question[question_id] = selected_option_id

        question_ids = [question.id for question in questions]
        option_rows = session.exec(
            select(QuestionOptions).where(QuestionOptions.question_id.in_(question_ids))
        ).all()
        options_by_question: dict[uuid.UUID, list[QuestionOptions]] = {}
        for option in option_rows:
            options_by_question.setdefault(option.question_id, []).append(option)

        questions = [
            question
            for question in questions
            if question.id in selected_by_question and options_by_question.get(question.id)
        ]
        if not questions:
            raise HTTPException(
                status_code=400,
                detail="This assignment has no multiple-choice questions",
            )

        attempt = AssessmentAttempt(
            user_id=user_id,
            project_id=assignment.project_id,
            assignment_id=assignment.id,
            is_submitted=True,
            submitted_at=datetime.utcnow(),
        )
        session.add(attempt)
        session.flush()

        correct_count = 0
        results: list[dict] = []

        for question in questions:
            options = options_by_question.get(question.id, [])
            selected_option_id = selected_by_question.get(question.id)
            selected_option = (
                next(
                    (
                        option
                        for option in options
                        if selected_option_id is not None and option.id == selected_option_id
                    ),
                    None,
                )
                if selected_option_id is not None
                else None
            )
            if selected_option_id is not None and selected_option is None:
                raise HTTPException(
                    status_code=400,
                    detail="Selected option does not belong to the question",
                )

            correct_option = next(
                (option for option in options if option.is_correct),
                None,
            )
            is_correct = bool(selected_option and selected_option.is_correct)
            if is_correct:
                correct_count += 1

            answer = Answers(
                question_id=question.id,
                user_id=user_id,
                attempt_id=attempt.id,
                score=5 if is_correct else 1,
                selected_option_id=selected_option.id if selected_option else None,
                is_correct=is_correct,
                answered_at=datetime.utcnow(),
            )
            session.add(answer)

            results.append(
                {
                    "question_id": str(question.id),
                    "selected_option_id": str(selected_option.id) if selected_option else None,
                    "correct_option_id": str(correct_option.id) if correct_option else None,
                    "is_correct": is_correct,
                    "explanation": question.explanation,
                }
            )

        total_questions = len(questions)
        percentage = round((correct_count / total_questions) * 100, 2)
        session.commit()
        session.refresh(attempt)
        assessment_result = self._create_quiz_assessment_result(
            session=session,
            attempt_id=attempt.id,
        )

        return {
            "attempt_id": str(attempt.id),
            "assignment_id": str(assignment.id),
            "score": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "evaluation": self._build_quiz_evaluation(
                score=percentage,
                correct_count=correct_count,
                total_questions=total_questions,
            ),
            "assessment_result": assessment_result,
            "results": results,
        }

    def submit_module_quiz(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
        user_id: uuid.UUID,
        answers: list[dict],
    ) -> dict:
        module = session.get(CurriculumModules, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        curriculum = session.get(Curriculums, module.curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        questions = self._ensure_module_questions(
            session=session,
            module=module,
            curriculum=curriculum,
            user_id=user_id,
        )
        question_ids = [question.id for question in questions]
        if not question_ids:
            raise HTTPException(status_code=400, detail="This lesson has no questions")

        selected_by_question: dict[uuid.UUID, uuid.UUID] = {}
        for answer in answers:
            question_id = answer.get("question_id")
            selected_option_id = answer.get("selected_option_id")
            if question_id not in question_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Answer question does not belong to this lesson",
                )
            if question_id in selected_by_question:
                raise HTTPException(
                    status_code=400,
                    detail="Duplicate answer for the same question",
                )
            selected_by_question[question_id] = selected_option_id

        option_rows = session.exec(
            select(QuestionOptions).where(QuestionOptions.question_id.in_(question_ids))
        ).all()
        options_by_question: dict[uuid.UUID, list[QuestionOptions]] = {}
        for option in option_rows:
            options_by_question.setdefault(option.question_id, []).append(option)

        questions = [
            question
            for question in questions
            if question.id in selected_by_question and options_by_question.get(question.id)
        ]
        if not questions:
            raise HTTPException(
                status_code=400,
                detail="This lesson has no multiple-choice questions",
            )

        assignment_id = questions[0].assignments_id if questions else None
        attempt = AssessmentAttempt(
            user_id=user_id,
            project_id=curriculum.project_id,
            assignment_id=assignment_id,
            is_submitted=True,
            submitted_at=datetime.utcnow(),
        )
        session.add(attempt)
        session.flush()

        correct_count = 0
        results: list[dict] = []

        for question in questions:
            options = options_by_question.get(question.id, [])
            selected_option_id = selected_by_question.get(question.id)
            selected_option = next(
                (
                    option
                    for option in options
                    if selected_option_id is not None and option.id == selected_option_id
                ),
                None,
            )
            if selected_option_id is not None and selected_option is None:
                raise HTTPException(
                    status_code=400,
                    detail="Selected option does not belong to the question",
                )

            correct_option = next(
                (option for option in options if option.is_correct),
                None,
            )
            is_correct = bool(selected_option and selected_option.is_correct)
            if is_correct:
                correct_count += 1

            answer = Answers(
                question_id=question.id,
                user_id=user_id,
                attempt_id=attempt.id,
                score=5 if is_correct else 1,
                selected_option_id=selected_option.id if selected_option else None,
                is_correct=is_correct,
                answered_at=datetime.utcnow(),
            )
            session.add(answer)

            results.append(
                {
                    "question_id": str(question.id),
                    "selected_option_id": str(selected_option.id) if selected_option else None,
                    "correct_option_id": str(correct_option.id) if correct_option else None,
                    "is_correct": is_correct,
                    "explanation": question.explanation,
                }
            )

        total_questions = len(questions)
        percentage = round((correct_count / total_questions) * 100, 2)
        session.commit()
        session.refresh(attempt)
        assessment_result = self._create_quiz_assessment_result(
            session=session,
            attempt_id=attempt.id,
        )

        return {
            "attempt_id": str(attempt.id),
            "module_id": str(module.id),
            "assignment_id": str(assignment_id) if assignment_id else None,
            "score": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "evaluation": self._build_quiz_evaluation(
                score=percentage,
                correct_count=correct_count,
                total_questions=total_questions,
            ),
            "assessment_result": assessment_result,
            "results": results,
        }

    def create_question(
        self,
        *,
        session: Session,
        assignment_id: uuid.UUID,
        criteria_id: uuid.UUID,
        content: str,
        generated_by: str = "ai",
        user_id: uuid.UUID | None = None,
    ) -> list[Questions]:
        assignment = session.get(Assignments, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        criteria = session.get(Criteria, criteria_id)
        if not criteria:
            raise HTTPException(status_code=404, detail="Criteria not found")

        source_text = self._collect_assignment_source_text(
            session=session,
            assignment=assignment,
            fallback_text=content,
        )
        created_questions = self._create_source_questions(
            session=session,
            assignment=assignment,
            criteria_id=criteria_id,
            source_text=source_text,
            generated_by=generated_by,
            count=QUESTIONS_PER_QUIZ,
            user_id=user_id,
        )

        if not created_questions:
            raise HTTPException(
                status_code=400,
                detail="No questions were created from the provided content or materials",
            )

        session.commit()
        for question in created_questions:
            session.refresh(question)
        return created_questions
