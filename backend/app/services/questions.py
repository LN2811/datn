import json
import logging
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import (
    Answers,
    AssessmentAttempt,
    Assignments,
    Criteria,
    CurriculumModules,
    Curriculums,
    MaterialChunk,
    QuestionOptions,
    Questions,
)
from app.services.ai_service import call_llm
from app.services.quiz_templates import (
    QUESTIONS_PER_QUIZ,
    build_vietnamese_quiz_questions,
)
from app.services.text_cleaner import clean_vietnamese_text, has_vietnamese_mark

logger = logging.getLogger("uvicorn.error")


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
            return assignment

        assignment = Assignments(
            project_id=curriculum.project_id,
            title=assignment_title,
            description=f"Bài trắc nghiệm riêng cho bài học: {module.title}.",
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        return assignment

    @staticmethod
    def _build_module_questions(module: CurriculumModules) -> list[dict]:
        title = clean_vietnamese_text(module.title).strip() if module.title else "bài học này"
        description = clean_vietnamese_text(module.description or "").strip()
        return build_vietnamese_quiz_questions(title=title, description=description)

    @staticmethod
    def _is_legacy_unaccented_question_set(questions: list[Questions]) -> bool:
        if not questions:
            return False
        return all(not has_vietnamese_mark(question.content or "") for question in questions)

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
        created_questions: list[Questions] = []
        generated_questions = build_vietnamese_quiz_questions(
            title=title,
            description=description,
            count=QUESTIONS_PER_QUIZ,
        )

        for generated_question in generated_questions[start_index : start_index + count]:
            question = self._create_question_record(
                session=session,
                assignment=assignment,
                criteria_id=criteria_id,
                content=generated_question["content"],
                question_type="single_choice",
                explanation=generated_question.get("explanation"),
                generated_by="system",
            )
            if curriculum_module_id is not None:
                question.curriculum_module_id = curriculum_module_id
                session.add(question)
            self._create_option_records(
                session=session,
                question=question,
                raw_options=generated_question.get("options"),
            )
            created_questions.append(question)

        return created_questions

    @staticmethod
    def _normalize_options(raw_options) -> list[dict]:
        if not isinstance(raw_options, list):
            return []

        options: list[dict] = []
        correct_index: int | None = None

        for raw_option in raw_options[:4]:
            if isinstance(raw_option, dict):
                content = clean_vietnamese_text(str(
                    raw_option.get("content")
                    or raw_option.get("text")
                    or raw_option.get("label")
                    or ""
                )).strip()
                is_correct = bool(raw_option.get("is_correct", False))
            else:
                content = clean_vietnamese_text(str(raw_option or "")).strip()
                is_correct = False

            if not content:
                continue

            if is_correct and correct_index is None:
                correct_index = len(options)
            options.append(
                {
                    "content": content,
                    "is_correct": False,
                    "order_index": len(options),
                }
            )

        if len(options) < 2:
            return []

        if correct_index is None:
            correct_index = 0
        options[correct_index]["is_correct"] = True
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
        data = json.loads(self._strip_code_fences(response))
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            questions = data.get("question") or data.get("questions") or []
            if isinstance(questions, list):
                return [item for item in questions if isinstance(item, dict)]
        return []

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
    ) -> dict:
        assignment = session.get(Assignments, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        self._ensure_assignment_questions(
            session=session,
            assignment=assignment,
        )
        questions = self.get_questions(
            session=session,
            assignment_id=assignment_id,
            include_correct=False,
        )

        return {
            "assignment": {
                "id": str(assignment.id),
                "project_id": str(assignment.project_id),
                "title": assignment.title,
                "description": assignment.description,
            },
            "questions": [
                question for question in questions if question.get("options")
            ][:QUESTIONS_PER_QUIZ],
        }

    def _ensure_assignment_questions(
        self,
        *,
        session: Session,
        assignment: Assignments,
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
        if not questions or legacy_unaccented:
            self._create_template_questions(
                session=session,
                assignment=assignment,
                criteria_id=criteria.id,
                title=assignment.title,
                description=assignment.description or "",
                count=QUESTIONS_PER_QUIZ,
            )
            session.commit()
        elif len(questions) < QUESTIONS_PER_QUIZ:
            self._create_template_questions(
                session=session,
                assignment=assignment,
                criteria_id=criteria.id,
                title=assignment.title,
                description=assignment.description or "",
                start_index=len(questions),
                count=QUESTIONS_PER_QUIZ - len(questions),
            )
            session.commit()

        return session.exec(
            select(Questions)
            .where(assignment_field == assignment.id)
            .order_by(Questions.created_at.desc())
            .limit(QUESTIONS_PER_QUIZ)
        ).all()

    def _ensure_module_questions(
        self,
        *,
        session: Session,
        module: CurriculumModules,
        curriculum: Curriculums,
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
        if not questions or legacy_unaccented:
            self._create_template_questions(
                session=session,
                assignment=assignment,
                criteria_id=criteria.id,
                title=module.title,
                description=module.description or "",
                curriculum_module_id=module.id,
                count=QUESTIONS_PER_QUIZ,
            )
            session.commit()
        elif len(questions) < QUESTIONS_PER_QUIZ:
            self._create_template_questions(
                session=session,
                assignment=assignment,
                criteria_id=criteria.id,
                title=module.title,
                description=module.description or "",
                curriculum_module_id=module.id,
                start_index=len(questions),
                count=QUESTIONS_PER_QUIZ - len(questions),
            )
            session.commit()

        return session.exec(
            select(Questions)
            .where(Questions.curriculum_module_id == module.id)
            .order_by(Questions.created_at.desc())
            .limit(QUESTIONS_PER_QUIZ)
        ).all()

    def get_module_quiz(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
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

        return {
            "attempt_id": str(attempt.id),
            "assignment_id": str(assignment.id),
            "score": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
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

        return {
            "attempt_id": str(attempt.id),
            "module_id": str(module.id),
            "assignment_id": str(assignment_id) if assignment_id else None,
            "score": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
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
    ) -> list[Questions]:
        assignment = session.get(Assignments, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        criteria = session.get(Criteria, criteria_id)
        if not criteria:
            raise HTTPException(status_code=404, detail="Criteria not found")

        materials = list(getattr(assignment.project, "materials", []) or [])
        created_questions: list[Questions] = []

        for material in materials:
            if len(created_questions) >= QUESTIONS_PER_QUIZ:
                break
            chunks = session.exec(
                select(MaterialChunk)
                .where(MaterialChunk.material_id == material.id)
                .order_by(MaterialChunk.chunk_index)
            ).all()

            for chunk in chunks:
                if len(created_questions) >= QUESTIONS_PER_QUIZ:
                    break
                try:
                    teacher_instruction = clean_vietnamese_text(content)
                    source_content = clean_vietnamese_text(chunk.content)
                    response = call_llm(
                        f"""
Tạo đúng {QUESTIONS_PER_QUIZ} câu hỏi trắc nghiệm bằng tiếng Việt có dấu từ nội dung bên dưới.
Chỉ trả về JSON hợp lệ theo đúng định dạng này:
{{
  "questions": [
    {{
      "content": "Nội dung câu hỏi",
      "question_type": "single_choice",
      "options": [
        {{"content": "Đáp án A", "is_correct": false}},
        {{"content": "Đáp án B", "is_correct": true}},
        {{"content": "Đáp án C", "is_correct": false}},
        {{"content": "Đáp án D", "is_correct": false}}
      ],
      "explanation": "Giải thích ngắn gọn cho đáp án đúng"
    }}
  ]
}}

Quy tắc bắt buộc:
- Viết tiếng Việt tự nhiên và có dấu đầy đủ.
- Tạo đúng {QUESTIONS_PER_QUIZ} câu hỏi nếu nội dung đủ thông tin.
- Mỗi câu hỏi có đúng 4 lựa chọn.
- Mỗi câu hỏi có đúng 1 lựa chọn có "is_correct": true.
- Không tiết lộ đáp án đúng trong nội dung câu hỏi.

Yêu cầu bổ sung của giáo viên:
{teacher_instruction}

Nội dung nguồn:
{source_content}
""",
                        temperature=0.1,
                    )
                    remaining = QUESTIONS_PER_QUIZ - len(created_questions)
                    for item in self._parse_ai_questions(response)[:remaining]:
                        question_content = clean_vietnamese_text(
                            str(item.get("content") or "")
                        ).strip()
                        if not question_content or not has_vietnamese_mark(question_content):
                            continue
                        question = self._create_question_record(
                            session=session,
                            assignment=assignment,
                            criteria_id=criteria_id,
                            content=question_content,
                            question_type=str(item.get("question_type") or "single_choice"),
                            explanation=clean_vietnamese_text(
                                str(item.get("explanation") or "")
                            ).strip() or None,
                            generated_by=generated_by,
                        )
                        option_records = self._create_option_records(
                            session=session,
                            question=question,
                            raw_options=item.get("options"),
                        )
                        if not option_records:
                            session.delete(question)
                            continue
                        created_questions.append(question)
                except Exception as exc:
                    logger.warning(
                        "Failed to generate question from material chunk. chunk_id=%s error_type=%s error=%s",
                        chunk.id,
                        type(exc).__name__,
                        exc,
                    )

        cleaned_manual_content = clean_vietnamese_text(content).strip()
        if len(created_questions) < QUESTIONS_PER_QUIZ:
            created_questions.extend(
                self._create_template_questions(
                    session=session,
                    assignment=assignment,
                    criteria_id=criteria_id,
                    title=assignment.title,
                    description=cleaned_manual_content or assignment.description or "",
                    start_index=len(created_questions),
                    count=QUESTIONS_PER_QUIZ - len(created_questions),
                )
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
