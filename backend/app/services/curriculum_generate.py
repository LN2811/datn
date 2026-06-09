import json
import logging
import re
import time
import unicodedata
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
from json import JSONDecodeError

from fastapi import HTTPException
from sqlalchemy import update
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models.models import (
    Answers,
    Assignments,
    Criteria,
    CurriculumModules,
    Curriculums,
    LearningMaterials,
    Projects,
    QuestionOptions,
    Questions,
)
from app.services.ai_service import (
    ai_usage_tracking_context,
    build_module_source_description,
    calculate_expected_module_count,
    call_llm,
    extract_curriculum_outline_from_toc,
    generate_curriculum_outline_fallback,
    generate_lesson_content_from_source,
    generate_lesson_content_fallback,
)
from app.services.ai_transaction import AITransactionService
from app.services.context_selector import ContextSelection, ContextSelector, LESSON, OUTLINE
from app.services.questions import QuestionService
from app.services.quiz_templates import QUESTIONS_PER_QUIZ
from app.services.text_cleaner import clean_vietnamese_text, has_vietnamese_mark

logger = logging.getLogger("uvicorn.error")
MODULE_METADATA_BATCH_SIZE = 5
MODULE_METADATA_BATCH_RETRIES = 3
MODULE_METADATA_REPAIR_RETRIES = 3
MODULE_METADATA_JSON_FALLBACK_BATCH_SIZE = 2
SOURCE_CHUNK_MARKER_PATTERN = re.compile(r"^\[(.+?) - chunk (\d+)\]$")
SOURCE_HEADING_PATTERN = re.compile(
    r"^\s*(?:#{1,6}\s+|"
    r"(?:(?:chương|chuong|bài|bai|mục|muc|chapter|section|unit|lesson)\s+"
    r"\d+(?:\.\d+){0,5}[.):\-]?\s+)|"
    r"\d+(?:\.\d+){0,5}[.)]?\s+).+",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class SourceTopic:
    order_index: int
    heading: str
    source_chunks: tuple[str, ...]
    occurrence_count: int = 1
    rank_score: int = 0


class CurriculumMetadataJSONError(ValueError):
    pass


class CurriculumGenerationService:
    def _get_latest_curriculum(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
    ) -> Curriculums | None:
        return session.exec(
            select(Curriculums)
            .where(Curriculums.project_id == project_id)
            .order_by(Curriculums.created_at.desc())
        ).first()

    def _get_curriculum_modules(
        self,
        *,
        session: Session,
        curriculum_id: uuid.UUID,
    ) -> list[CurriculumModules]:
        return session.exec(
            select(CurriculumModules)
            .where(CurriculumModules.curriculum_id == curriculum_id)
            .order_by(CurriculumModules.order_index, CurriculumModules.created_at)
        ).all()

    def _get_project_curriculum_modules(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
    ) -> list[CurriculumModules]:
        return session.exec(
            select(CurriculumModules)
            .join(Curriculums, CurriculumModules.curriculum_id == Curriculums.id)
            .where(Curriculums.project_id == project_id)
            .order_by(Curriculums.created_at, CurriculumModules.order_index)
        ).all()

    def _delete_questions_for_modules(
        self,
        *,
        session: Session,
        modules: list[CurriculumModules],
    ) -> dict:
        module_ids = [module.id for module in modules if module.id]
        if not module_ids:
            return {
                "deleted_questions_count": 0,
                "deleted_options_count": 0,
                "deleted_answers_count": 0,
            }

        questions = session.exec(
            select(Questions).where(Questions.curriculum_module_id.in_(module_ids))
        ).all()
        question_ids = [question.id for question in questions]
        if not question_ids:
            return {
                "deleted_questions_count": 0,
                "deleted_options_count": 0,
                "deleted_answers_count": 0,
            }

        answers = session.exec(
            select(Answers).where(Answers.question_id.in_(question_ids))
        ).all()
        options = session.exec(
            select(QuestionOptions).where(QuestionOptions.question_id.in_(question_ids))
        ).all()

        for answer in answers:
            session.delete(answer)
        for option in options:
            session.delete(option)
        for question in questions:
            session.delete(question)

        session.commit()
        return {
            "deleted_questions_count": len(questions),
            "deleted_options_count": len(options),
            "deleted_answers_count": len(answers),
        }

    def _has_newer_materials(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        curriculum: Curriculums,
    ) -> bool:
        latest_material = session.exec(
            select(LearningMaterials)
            .where(LearningMaterials.project_id == project_id)
            .order_by(LearningMaterials.created_at.desc())
        ).first()
        if not latest_material:
            return False
        return latest_material.created_at > curriculum.created_at

    def _sync_curriculum_progress(
        self,
        *,
        session: Session,
        curriculum: Curriculums,
        modules: list[CurriculumModules],
    ) -> Curriculums:
        total_module = len(modules)
        ready_module = sum(
            1
            for module in modules
            if module.generate_status == "ready" and bool(module.content)
        )

        if (
            curriculum.total_module == total_module
            and curriculum.ready_module == ready_module
        ):
            return curriculum

        curriculum.total_module = total_module
        curriculum.ready_module = ready_module
        session.add(curriculum)
        session.commit()
        session.refresh(curriculum)
        return curriculum

    def _get_project_or_404(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
    ) -> Projects:
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def _collect_project_material_text(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        purpose: str = OUTLINE,
        module_id: uuid.UUID | None = None,
    ) -> str:
        return ContextSelector(session).select(
            purpose,
            project_id,
            module_id=module_id,
        ).text

    def _get_module_context_or_404(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
    ) -> tuple[Curriculums, CurriculumModules]:
        module = session.get(CurriculumModules, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        curriculum = session.get(Curriculums, module.curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")

        return curriculum, module

    @staticmethod
    def _question_assignment_field_name() -> str:
        if hasattr(Questions, "assignment_id"):
            return "assignment_id"
        if hasattr(Questions, "assignments_id"):
            return "assignments_id"
        raise HTTPException(
            status_code=500,
            detail="Question model does not define assignment reference field",
        )

    @staticmethod
    def _question_assignment_field():
        if hasattr(Questions, "assignment_id"):
            return getattr(Questions, "assignment_id")
        if hasattr(Questions, "assignments_id"):
            return getattr(Questions, "assignments_id")
        raise HTTPException(
            status_code=500,
            detail="Question model does not define assignment reference field",
        )

    def _get_or_create_lesson_criteria(self, *, session: Session) -> Criteria:
        criteria = session.exec(
            select(Criteria).where(Criteria.name == "Lesson comprehension")
        ).first()
        if criteria:
            return criteria

        criteria = Criteria(
            name="Lesson comprehension",
            description="Đánh giá mức độ hiểu nội dung bài học được tạo từ tài liệu.",
            weight=1.0,
        )
        session.add(criteria)
        session.commit()
        session.refresh(criteria)
        return criteria

    def _get_or_create_question_assignment(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        curriculum: Curriculums,
    ) -> Assignments:
        assignment_title = f"Bộ câu hỏi - {curriculum.title} ({curriculum.id.hex[:8]})"
        assignment = session.exec(
            select(Assignments).where(
                Assignments.project_id == project_id,
                Assignments.title == assignment_title,
            )
        ).first()
        if assignment:
            return assignment

        assignment = Assignments(
            project_id=project_id,
            title=assignment_title,
            description=(
                "Bộ câu hỏi được tạo đồng thời với các bài học AI "
                f"trong curriculum: {curriculum.title}."
            ),
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        return assignment

    @staticmethod
    def _build_questions_for_module(module: CurriculumModules) -> list[dict]:
        return []

    @staticmethod
    def _create_question_options(
        *,
        session: Session,
        question: Questions,
        options: list[dict],
    ) -> None:
        for index, option_data in enumerate(options):
            content = clean_vietnamese_text(
                str(option_data.get("content") or "")
            ).strip()
            if not content:
                continue

            session.add(
                QuestionOptions(
                    question_id=question.id,
                    content=content,
                    is_correct=bool(option_data.get("is_correct", False)),
                    order_index=index,
                )
            )

    def _ensure_question_set_for_modules(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        curriculum: Curriculums,
        modules: list[CurriculumModules],
        user_id: uuid.UUID | None = None,
    ) -> dict:
        if not modules:
            return {
                "question_assignment_id": None,
                "questions_count": 0,
            }

        criteria = self._get_or_create_lesson_criteria(session=session)
        assignment = self._get_or_create_question_assignment(
            session=session,
            project_id=project_id,
            curriculum=curriculum,
        )
        assignment_field = self._question_assignment_field()

        existing_questions = session.exec(
            select(Questions).where(assignment_field == assignment.id)
        ).all()
        expected_count = max(len(modules), 1) * QUESTIONS_PER_QUIZ
        question_service = QuestionService()
        legacy_unaccented = (
            bool(existing_questions)
            and all(not has_vietnamese_mark(question.content or "") for question in existing_questions)
        )
        generic_template = question_service._is_generic_template_question_set(existing_questions)
        if len(existing_questions) >= expected_count and not legacy_unaccented and not generic_template:
            return {
                "question_assignment_id": str(assignment.id),
                "questions_count": len(existing_questions),
            }

        created_questions: list[Questions] = []
        valid_existing_count = 0 if legacy_unaccented or generic_template else len(existing_questions)
        for module in modules:
            if not module.content:
                continue

            module_questions = session.exec(
                select(Questions)
                .where(Questions.curriculum_module_id == module.id)
                .order_by(Questions.created_at.desc())
            ).all()
            module_legacy_unaccented = (
                bool(module_questions)
                and all(not has_vietnamese_mark(question.content or "") for question in module_questions)
            )
            module_generic_template = question_service._is_generic_template_question_set(
                module_questions
            )
            if (
                len(module_questions) >= QUESTIONS_PER_QUIZ
                and not module_legacy_unaccented
                and not module_generic_template
            ):
                continue

            created_questions.extend(
                question_service._create_source_questions(
                    session=session,
                    assignment=assignment,
                    criteria_id=criteria.id,
                    source_text=question_service._extract_lesson_source_text(module.content),
                    curriculum_module_id=module.id,
                    generated_by="ai",
                    count=QUESTIONS_PER_QUIZ,
                    user_id=user_id,
                )
            )

        if created_questions:
            session.commit()
            for question in created_questions:
                session.refresh(question)

        return {
            "question_assignment_id": str(assignment.id),
            "questions_count": valid_existing_count + len(created_questions),
        }

    def _get_existing_question_meta(
        self,
        *,
        session: Session,
        modules: list[CurriculumModules],
    ) -> dict:
        module_ids = [module.id for module in modules if module.id]
        if not module_ids:
            return {"question_assignment_id": None, "questions_count": 0}
        questions = session.exec(
            select(Questions).where(Questions.curriculum_module_id.in_(module_ids))
        ).all()
        assignment_field_name = self._question_assignment_field_name()
        assignment_id = (
            getattr(questions[0], assignment_field_name, None)
            if questions
            else None
        )
        return {
            "question_assignment_id": str(assignment_id) if assignment_id else None,
            "questions_count": len(questions),
        }

    @staticmethod
    def _batch_order_indices(
        order_indices: list[int],
        *,
        batch_size: int = MODULE_METADATA_BATCH_SIZE,
    ) -> list[list[int]]:
        return [
            order_indices[index : index + batch_size]
            for index in range(0, len(order_indices), batch_size)
        ]

    @staticmethod
    def _module_title_key(title: str) -> str:
        return re.sub(r"\s+", " ", clean_vietnamese_text(title).strip()).casefold()

    @staticmethod
    def _fold_source_value(value: str) -> str:
        normalized = unicodedata.normalize("NFD", clean_vietnamese_text(value or ""))
        folded = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        ).lower()
        return re.sub(r"[^a-z0-9]+", " ", folded).strip()

    @classmethod
    def _source_topic_key(cls, heading: str) -> str:
        return re.sub(
            r"^(?:(?:chuong|bai|muc|chapter|section|unit|lesson)\s+)?"
            r"(?:\d+\s+)+",
            "",
            cls._fold_source_value(heading),
        ).strip()

    @classmethod
    def _source_topic_rank(cls, heading: str, occurrence_count: int) -> int:
        normalized = unicodedata.normalize("NFD", clean_vietnamese_text(heading or ""))
        raw_folded = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        ).lower()
        folded = cls._fold_source_value(heading)
        if re.match(r"^(?:chuong|chapter|unit)\s+\d+", folded):
            level_score = 40
        elif re.match(r"^(?:bai|lesson|section)\s+\d+", folded):
            level_score = 30
        elif re.match(r"^\d+(?:\.\d+)+\s+", raw_folded):
            level_score = 20
        elif re.match(r"^\d+\s+", folded):
            level_score = 35
        else:
            level_score = 10
        return level_score + min(occurrence_count, 10)

    @classmethod
    def _extract_source_topics(cls, text: str) -> list[SourceTopic]:
        current_chunk = "outline-context"
        ordered_keys: list[str] = []
        topic_data: dict[str, dict] = {}
        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            marker = SOURCE_CHUNK_MARKER_PATTERN.match(line)
            if marker:
                current_chunk = f"{marker.group(1)} - chunk {marker.group(2)}"
                continue
            if not SOURCE_HEADING_PATTERN.match(line):
                continue
            heading = re.sub(r"^#{1,6}\s+", "", line).strip()
            key = cls._source_topic_key(heading)
            if not key or len(key) < 3:
                continue
            if key not in topic_data:
                ordered_keys.append(key)
                topic_data[key] = {
                    "heading": heading,
                    "source_chunks": [],
                    "occurrence_count": 0,
                }
            topic_data[key]["occurrence_count"] += 1
            if current_chunk not in topic_data[key]["source_chunks"]:
                topic_data[key]["source_chunks"].append(current_chunk)

        if not topic_data:
            current_chunk = "outline-context"
            for raw_line in (text or "").splitlines():
                line = raw_line.strip()
                marker = SOURCE_CHUNK_MARKER_PATTERN.match(line)
                if marker:
                    current_chunk = f"{marker.group(1)} - chunk {marker.group(2)}"
                    continue
                if (
                    not line
                    or line == "DOCUMENT HEADINGS:"
                    or sum(char.isalpha() for char in line) < 4
                ):
                    continue
                heading = line[:120].strip()
                key = cls._source_topic_key(heading)
                if not key or key in topic_data:
                    continue
                ordered_keys.append(key)
                topic_data[key] = {
                    "heading": heading,
                    "source_chunks": [current_chunk],
                    "occurrence_count": 1,
                }
                if len(ordered_keys) >= 40:
                    break

        topics: list[SourceTopic] = []
        for position, key in enumerate(ordered_keys, start=1):
            data = topic_data[key]
            topics.append(
                SourceTopic(
                    order_index=position,
                    heading=data["heading"],
                    source_chunks=tuple(data["source_chunks"]),
                    occurrence_count=data["occurrence_count"],
                    rank_score=cls._source_topic_rank(
                        data["heading"],
                        data["occurrence_count"],
                    ),
                )
            )
        return topics

    @staticmethod
    def _select_source_topics(
        topics: list[SourceTopic],
        *,
        max_topics: int,
    ) -> list[SourceTopic]:
        ranked = sorted(
            topics,
            key=lambda topic: (-topic.rank_score, topic.order_index),
        )[:max_topics]
        return [
            SourceTopic(
                order_index=index,
                heading=topic.heading,
                source_chunks=topic.source_chunks,
                occurrence_count=topic.occurrence_count,
                rank_score=topic.rank_score,
            )
            for index, topic in enumerate(
                sorted(ranked, key=lambda topic: topic.order_index),
                start=1,
            )
        ]

    @classmethod
    def _heading_match_score(cls, title: str, heading: str) -> float:
        title_key = cls._source_topic_key(title)
        heading_key = cls._source_topic_key(heading)
        if not title_key or not heading_key:
            return 0.0
        if title_key in heading_key or heading_key in title_key:
            return 1.0
        title_terms = set(title_key.split())
        heading_terms = set(heading_key.split())
        overlap = len(title_terms.intersection(heading_terms)) / max(
            len(title_terms.union(heading_terms)),
            1,
        )
        sequence = SequenceMatcher(None, title_key, heading_key).ratio()
        return round(max(overlap, sequence), 4)

    @classmethod
    def _normalize_module_metadata_batch(
        cls,
        *,
        raw_modules: object,
        requested_order_indices: list[int],
        used_title_keys: set[str],
        source_topics: dict[int, SourceTopic] | None = None,
    ) -> list[dict]:
        if not isinstance(raw_modules, list):
            raise ValueError("AI response must contain a modules list")

        requested_indices = set(requested_order_indices)
        normalized_modules: list[dict] = []
        batch_indices: set[int] = set()
        batch_title_keys: set[str] = set()
        for raw_module in raw_modules:
            if not isinstance(raw_module, dict):
                continue
            try:
                order_index = int(raw_module.get("order_index"))
            except (TypeError, ValueError):
                continue
            title = clean_vietnamese_text(str(raw_module.get("title") or "")).strip()
            title_key = cls._module_title_key(title)
            source_topic = source_topics.get(order_index) if source_topics else None
            heading_match_score = (
                cls._heading_match_score(title, source_topic.heading)
                if source_topic
                else 1.0
            )
            if (
                order_index not in requested_indices
                or order_index in batch_indices
                or not title
                or not title_key
                or title_key in used_title_keys
                or title_key in batch_title_keys
                or (
                    source_topic is not None
                    and heading_match_score < settings.CURRICULUM_MIN_HEADING_MATCH_SCORE
                )
            ):
                continue
            description = clean_vietnamese_text(
                str(raw_module.get("description") or "")
            ).strip()
            raw_objectives = raw_module.get("learning_objectives")
            objectives = (
                [
                    clean_vietnamese_text(str(objective)).strip()
                    for objective in raw_objectives
                    if clean_vietnamese_text(str(objective)).strip()
                ][:5]
                if isinstance(raw_objectives, list)
                else []
            )
            if not objectives:
                continue
            normalized_modules.append(
                {
                    "title": title,
                    "description": description,
                    "learning_objectives": objectives,
                    "order_index": order_index,
                    "source_headings": (
                        [source_topic.heading] if source_topic else []
                    ),
                    "source_chunks": (
                        list(source_topic.source_chunks) if source_topic else []
                    ),
                    "heading_match_score": heading_match_score,
                    "hallucination_score": round(1 - heading_match_score, 4),
                }
            )
            batch_indices.add(order_index)
            batch_title_keys.add(title_key)

        return sorted(normalized_modules, key=lambda module: module["order_index"])

    def _run_module_metadata_batches(
        self,
        *,
        expected_modules: int,
        request_batch: Callable[[list[int], bool], list[dict]],
        save_batch: Callable[[list[dict]], None],
        source_topics: list[SourceTopic] | None = None,
    ) -> dict:
        saved_modules: dict[int, dict] = {}
        used_title_keys: set[str] = set()
        provider_rate_limited = False
        quota_exceeded = False
        json_fallback_batch_size: int | None = None
        source_topics_by_index = {
            topic.order_index: topic for topic in (source_topics or [])
        }

        def process_batch(order_indices: list[int], *, repair: bool) -> None:
            nonlocal provider_rate_limited, quota_exceeded, json_fallback_batch_size
            pending_indices = [
                order_index
                for order_index in order_indices
                if order_index not in saved_modules
            ]
            if not pending_indices:
                return

            json_parse_errors = 0
            for attempt in range(1, MODULE_METADATA_BATCH_RETRIES + 1):
                try:
                    raw_modules = request_batch(pending_indices, repair)
                    valid_modules = self._normalize_module_metadata_batch(
                        raw_modules=raw_modules,
                        requested_order_indices=pending_indices,
                        used_title_keys=used_title_keys,
                        source_topics=source_topics_by_index or None,
                    )
                except Exception as exc:
                    if isinstance(exc, CurriculumMetadataJSONError):
                        json_parse_errors += 1
                        logger.warning(
                            "Curriculum metadata JSON invalid. order_indices=%s "
                            "repair=%s attempt=%s error=%s",
                            pending_indices,
                            repair,
                            attempt,
                            exc,
                        )
                        continue
                    if isinstance(exc, HTTPException) and exc.status_code == 429:
                        provider_rate_limited = True
                        logger.warning(
                            "Curriculum metadata generation queued after provider "
                            "rate limit. order_indices=%s repair=%s",
                            pending_indices,
                            repair,
                        )
                        return
                    if isinstance(exc, HTTPException) and exc.status_code == 403:
                        quota_exceeded = True
                        logger.warning(
                            "Curriculum metadata generation stopped because AI quota "
                            "is unavailable. order_indices=%s repair=%s detail=%s",
                            pending_indices,
                            repair,
                            exc.detail,
                        )
                        return
                    logger.warning(
                        "Curriculum metadata batch invalid. order_indices=%s repair=%s "
                        "attempt=%s error_type=%s error=%s",
                        pending_indices,
                        repair,
                        attempt,
                        type(exc).__name__,
                        exc,
                    )
                    continue

                if valid_modules:
                    save_batch(valid_modules)
                    for module in valid_modules:
                        saved_modules[module["order_index"]] = module
                        used_title_keys.add(self._module_title_key(module["title"]))
                return

            if json_parse_errors >= MODULE_METADATA_BATCH_RETRIES and len(pending_indices) > 1:
                json_fallback_batch_size = MODULE_METADATA_JSON_FALLBACK_BATCH_SIZE
                logger.warning(
                    "Curriculum metadata batch JSON failed after max attempts. "
                    "Generating modules individually. order_indices=%s",
                    pending_indices,
                )
                for single_index in pending_indices:
                    process_batch([single_index], repair=repair)
                    if provider_rate_limited or quota_exceeded:
                        break

        all_indices = list(range(1, expected_modules + 1))
        batch_size = (
            max(1, min(settings.GROQ_FALLBACK_CURRICULUM_BATCH_SIZE, 2))
            if settings.PREMIUM_AI_FALLBACK_TO_GROQ_ENABLED
            else MODULE_METADATA_BATCH_SIZE
        )
        position = 0
        while position < len(all_indices):
            active_batch_size = json_fallback_batch_size or batch_size
            order_indices = all_indices[position : position + active_batch_size]
            process_batch(order_indices, repair=False)
            if provider_rate_limited or quota_exceeded:
                break
            position += active_batch_size

        for _ in range(MODULE_METADATA_REPAIR_RETRIES):
            if provider_rate_limited or quota_exceeded:
                break
            missing_modules = [
                order_index
                for order_index in all_indices
                if order_index not in saved_modules
            ]
            if not missing_modules:
                break
            repair_position = 0
            while repair_position < len(missing_modules):
                active_batch_size = json_fallback_batch_size or batch_size
                order_indices = missing_modules[
                    repair_position : repair_position + active_batch_size
                ]
                process_batch(order_indices, repair=True)
                if provider_rate_limited or quota_exceeded:
                    break
                repair_position += active_batch_size

        missing_modules = [
            order_index
            for order_index in all_indices
            if order_index not in saved_modules
        ]
        result = {
            "saved_modules": len(saved_modules),
            "missing_modules": missing_modules,
        }
        if provider_rate_limited:
            result["queued"] = True
        if quota_exceeded:
            result["quota_exceeded"] = True
        return result

    @staticmethod
    def _raw_response_preview(content: str) -> str:
        return re.sub(r"\s+", " ", (content or "").strip())[:500]

    @classmethod
    def _extract_json_object_candidate(cls, content: str) -> str:
        cleaned = (content or "").strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            return cleaned[start : end + 1].strip()
        return cleaned

    @staticmethod
    def _repair_json_candidate(candidate: str) -> str:
        repaired = candidate.strip()
        repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
        repaired = re.sub(r"}\s*{", "},{", repaired)
        repaired = re.sub(r"]\s*{", "],{", repaired)
        repaired = re.sub(
            r'("(?:(?:\\.)|[^"\\])*")\s+("[-_A-Za-z0-9]+"\s*:)',
            r"\1, \2",
            repaired,
        )
        repaired = re.sub(r"(\])\s+(\"[-_A-Za-z0-9]+\"\s*:)", r"\1, \2", repaired)
        repaired = re.sub(r"(\})\s+(\"[-_A-Za-z0-9]+\"\s*:)", r"\1, \2", repaired)
        repaired = re.sub(r"(\d|true|false|null)\s+(\"[-_A-Za-z0-9]+\"\s*:)", r"\1, \2", repaired)
        return repaired

    @classmethod
    def _extract_complete_module_objects(cls, candidate: str) -> list[str]:
        modules_key = candidate.find('"modules"')
        if modules_key == -1:
            modules_key = candidate.find("'modules'")
        array_start = candidate.find("[", modules_key if modules_key != -1 else 0)
        if array_start == -1:
            return []

        objects: list[str] = []
        object_start: int | None = None
        brace_depth = 0
        in_string = False
        quote_char = ""
        escaped = False
        for index in range(array_start + 1, len(candidate)):
            char = candidate[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote_char:
                    in_string = False
                continue
            if char in {'"', "'"}:
                in_string = True
                quote_char = char
                continue
            if char == "{":
                if brace_depth == 0:
                    object_start = index
                brace_depth += 1
                continue
            if char == "}":
                if brace_depth <= 0:
                    continue
                brace_depth -= 1
                if brace_depth == 0 and object_start is not None:
                    objects.append(candidate[object_start : index + 1])
                    object_start = None
        return objects

    @classmethod
    def _salvage_module_metadata_objects(cls, candidate: str) -> list[dict]:
        modules: list[dict] = []
        for object_candidate in cls._extract_complete_module_objects(candidate):
            for repaired_candidate in [
                object_candidate,
                cls._repair_json_candidate(object_candidate),
            ]:
                try:
                    parsed = json.loads(repaired_candidate)
                    if isinstance(parsed, dict):
                        modules.append(parsed)
                    break
                except JSONDecodeError:
                    continue
        return modules

    @classmethod
    def _parse_module_metadata_response(cls, content: str) -> list[dict]:
        candidate = cls._extract_json_object_candidate(content)
        parse_errors: list[JSONDecodeError] = []
        for json_candidate in [candidate, cls._repair_json_candidate(candidate)]:
            try:
                data = json.loads(json_candidate)
                break
            except JSONDecodeError as exc:
                parse_errors.append(exc)
        else:
            last_error = parse_errors[-1]
            salvaged_modules = cls._salvage_module_metadata_objects(candidate)
            if salvaged_modules:
                logger.warning(
                    "Curriculum metadata JSON parse failed, salvaged complete "
                    "module objects. error=%s recovered_modules=%s "
                    "raw_response_preview=%s",
                    last_error,
                    len(salvaged_modules),
                    cls._raw_response_preview(content),
                )
                return salvaged_modules
            logger.warning(
                "Curriculum metadata JSON parse failed. error=%s "
                "raw_response_preview=%s",
                last_error,
                cls._raw_response_preview(content),
            )
            raise CurriculumMetadataJSONError(str(last_error)) from last_error

        modules = data.get("modules") if isinstance(data, dict) else None
        if not isinstance(modules, list):
            raise ValueError("AI response must contain a modules list")
        return modules

    def _request_module_metadata_batch(
        self,
        *,
        session: Session,
        user_id: uuid.UUID | None,
        project_id: uuid.UUID,
        context_selection: ContextSelection,
        curriculum_title: str,
        curriculum_overview: str,
        order_indices: list[int],
        source_topics: list[SourceTopic],
        repair: bool,
    ) -> list[dict]:
        requested_topics = [
            {
                "order_index": topic.order_index,
                "source_heading": topic.heading,
                "source_chunks": list(topic.source_chunks),
            }
            for topic in source_topics
            if topic.order_index in order_indices
        ]
        schema = {
            "modules": [
                {
                    "order_index": 1,
                    "title": "string",
                    "description": "string",
                    "learning_objectives": ["string"],
                    "source_headings": ["string"],
                }
            ]
        }
        prompt = f"""
Return only raw JSON. Do not use markdown. Do not wrap the JSON in code fences.
Do not include explanations, comments, prose, or any text before or after JSON.
Create curriculum module metadata only for order_index values: {order_indices}.
Do not generate lesson content.
Each title must be specific and unique. Keep the exact requested order_index values.
{"This is a repair request for missing modules." if repair else ""}

Generate curriculum strictly from the provided material.
Do not invent topics.
Do not add knowledge that cannot be traced to the source material.
Preserve the topic order from the document.
Prefer chapter titles and section headings over inferred topics.
Every module must be supported by source content.

Curriculum title: {curriculum_title}
Curriculum overview: {curriculum_overview}

Required JSON schema:
{json.dumps(schema, ensure_ascii=False)}

ALLOWED_SOURCE_TOPICS:
{json.dumps(requested_topics, ensure_ascii=False)}

SOURCE_CONTEXT:
{context_selection.text}
""".strip()
        system_prompt = (
            "You generate domain-independent curriculum module metadata from source "
            "material. Return raw JSON only. Never use markdown, code fences, "
            "comments, explanations, or lesson content."
        )
        if user_id is not None:
            response = AITransactionService.chat(
                db=session,
                user_id=user_id,
                project_id=project_id,
                action_type="generate_curriculum_metadata",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_completion_tokens=900,
                response_format={"type": "json_object"},
                context_selection=context_selection,
            )
        else:
            logger.warning(
                "Curriculum metadata generation has no user_id. Falling back to the "
                "default provider. project_id=%s",
                project_id,
            )
            response = call_llm(
                prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_completion_tokens=900,
                response_format={"type": "json_object"},
                context_selection=context_selection,
            )
        return self._parse_module_metadata_response(response)

    def _create_pending_modules_in_batches(
        self,
        *,
        session: Session,
        curriculum: Curriculums,
        user_id: uuid.UUID | None,
        context_selection: ContextSelection,
        source_topics: list[SourceTopic],
        expected_modules: int,
        preview_count: int,
    ) -> tuple[list[CurriculumModules], list[int], bool, bool]:
        created_modules: list[CurriculumModules] = []

        def save_batch(modules: list[dict]) -> None:
            batch_records: list[CurriculumModules] = []
            for module_data in modules:
                order_index = module_data["order_index"]
                module = CurriculumModules(
                    curriculum_id=curriculum.id,
                    title=module_data["title"],
                    description=module_data["description"] or None,
                    learning_objectives=module_data["learning_objectives"],
                    source_headings=module_data["source_headings"],
                    source_chunks=module_data["source_chunks"],
                    heading_match_score=module_data["heading_match_score"],
                    hallucination_score=module_data["hallucination_score"],
                    content=None,
                    generate_status="pending",
                    is_preview=order_index <= preview_count,
                    order_index=order_index,
                )
                session.add(module)
                batch_records.append(module)
            session.commit()
            for module in batch_records:
                session.refresh(module)
            created_modules.extend(batch_records)

        result = self._run_module_metadata_batches(
            expected_modules=expected_modules,
            request_batch=lambda order_indices, repair: self._request_module_metadata_batch(
                session=session,
                user_id=user_id,
                project_id=curriculum.project_id,
                context_selection=context_selection,
                curriculum_title=curriculum.title,
                curriculum_overview=curriculum.overview or "",
                order_indices=order_indices,
                source_topics=source_topics,
                repair=repair,
            ),
            save_batch=save_batch,
            source_topics=source_topics,
        )
        curriculum.total_module = result["saved_modules"]
        curriculum.source_coverage_score = round(
            result["saved_modules"] / max(expected_modules, 1),
            4,
        )
        curriculum.heading_match_score = round(
            sum(module.heading_match_score or 0 for module in created_modules)
            / max(expected_modules, 1),
            4,
        )
        curriculum.hallucination_score = round(
            1 - curriculum.heading_match_score,
            4,
        )
        session.add(curriculum)
        session.commit()
        session.refresh(curriculum)

        return (
            sorted(created_modules, key=lambda module: module.order_index or 0),
            result["missing_modules"],
            bool(result.get("queued")),
            bool(result.get("quota_exceeded")),
        )

    def _enrich_module_descriptions_from_source(
        self,
        *,
        modules: list[dict],
        full_text: str,
    ) -> list[dict]:
        enriched_modules: list[dict] = []
        for module_data in modules:
            if not isinstance(module_data, dict):
                continue

            title = clean_vietnamese_text(str(module_data.get("title") or "")).strip()
            description = clean_vietnamese_text(
                str(module_data.get("description") or "")
            ).strip()
            if not title:
                enriched_modules.append(module_data)
                continue

            module_data = {
                **module_data,
                "title": title,
                "description": description or module_data.get("description"),
            }

            source_description = clean_vietnamese_text(
                build_module_source_description(
                    text=full_text,
                    module_title=title,
                    module_description=description,
                )
            )
            if source_description and source_description != description:
                module_data["description"] = (
                    f"{description}\n\n{source_description}"
                    if description
                    else source_description
                )
            enriched_modules.append(module_data)

        return enriched_modules

    def _generate_module_content(
        self,
        *,
        session: Session,
        curriculum: Curriculums,
        module: CurriculumModules,
        full_text: str,
        mark_preview: bool | None = None,
    ) -> CurriculumModules:
        if module.generate_status == "ready" and module.content:
            if mark_preview is not None and module.is_preview != mark_preview:
                module.is_preview = mark_preview
                session.add(module)
                session.commit()
                session.refresh(module)
            return module

        if module.generate_status == "generating":
            return module

        was_ready = module.generate_status == "ready" and bool(module.content)

        generating_values: dict[str, object] = {"generate_status": "generating"}
        if mark_preview is not None:
            generating_values["is_preview"] = mark_preview
        claim_result = session.exec(
            update(CurriculumModules)
            .where(
                CurriculumModules.id == module.id,
                CurriculumModules.generate_status != "generating",
            )
            .values(**generating_values)
        )
        session.commit()
        if claim_result.rowcount != 1:
            session.refresh(module)
            return module
        session.refresh(module)

        generation_started_at = time.perf_counter()
        try:
            if not full_text:
                full_text = self._collect_project_material_text(
                    session=session,
                    project_id=curriculum.project_id,
                    purpose=LESSON,
                    module_id=module.id,
                )
            content = generate_lesson_content_from_source(
                text=full_text,
                curriculum_title=curriculum.title,
                overview=curriculum.overview or "",
                module_title=module.title,
                module_description=module.description or "",
            ).strip()
            if not content:
                raise RuntimeError("AI returned empty lesson content")
        except Exception as exc:
            logger.warning(
                "Source lesson extraction failed. Falling back to source-based lesson. curriculum_id=%s module_id=%s error_type=%s error=%s",
                curriculum.id,
                module.id,
                type(exc).__name__,
                exc,
            )
            try:
                content = generate_lesson_content_fallback(
                    text=full_text,
                    curriculum_title=curriculum.title,
                    overview=curriculum.overview or "",
                    module_title=module.title,
                    module_description=module.description or "",
                ).strip()
            except Exception as fallback_exc:
                module.generate_status = "failed"
                session.add(module)
                session.commit()
                session.refresh(module)
                raise RuntimeError(str(fallback_exc)) from fallback_exc

            if not content:
                module.generate_status = "failed"
                session.add(module)
                session.commit()
                session.refresh(module)
                raise RuntimeError(str(exc)) from exc

        module.content = clean_vietnamese_text(content).strip()
        module.generate_status = "ready"
        if mark_preview is not None:
            module.is_preview = mark_preview
        if not was_ready:
            curriculum.ready_module = (curriculum.ready_module or 0) + 1

        session.add(module)
        session.add(curriculum)
        session.commit()
        session.refresh(module)
        session.refresh(curriculum)
        logger.info(
            "Lesson generated. purpose=%s curriculum_id=%s module_id=%s "
            "context_chars=%s generation_time_ms=%s",
            LESSON,
            curriculum.id,
            module.id,
            len(full_text),
            round((time.perf_counter() - generation_started_at) * 1000, 2),
        )

        return module

    def _mark_preview_modules(
        self,
        *,
        session: Session,
        curriculum: Curriculums,
        modules: list[CurriculumModules],
        project_id: uuid.UUID,
        preview_count: int,
    ) -> list[CurriculumModules]:
        preview_modules: list[CurriculumModules] = []
        preview_candidates = modules[:preview_count]
        for module in preview_candidates:
            if not module.is_preview:
                module.is_preview = True
                session.add(module)
            preview_modules.append(module)
        if preview_modules:
            session.commit()
            for module in preview_modules:
                session.refresh(module)

        return preview_modules

    def generate_from_curriculum(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        preview_count: int = 2,
        force_regenerate: bool = False,
        user_id: uuid.UUID | None = None,
        requested_module_count: int | None = None,
    ) -> dict:
        project = self._get_project_or_404(session=session, project_id=project_id)
        latest_curriculum = self._get_latest_curriculum(
            session=session,
            project_id=project_id,
        )
        deleted_question_meta = {
            "deleted_questions_count": 0,
            "deleted_options_count": 0,
            "deleted_answers_count": 0,
        }
        if force_regenerate and latest_curriculum:
            deleted_question_meta = self._delete_questions_for_modules(
                session=session,
                modules=self._get_project_curriculum_modules(
                    session=session,
                    project_id=project_id,
                ),
            )

        if (
            latest_curriculum
            and not force_regenerate
            and (
                requested_module_count is None
                or latest_curriculum.total_module == requested_module_count
            )
            and not self._has_newer_materials(
            session=session,
            project_id=project_id,
            curriculum=latest_curriculum,
            )
        ):
            existing_modules = self._get_curriculum_modules(
                session=session,
                curriculum_id=latest_curriculum.id,
            )
            if existing_modules:
                self._sync_curriculum_progress(
                    session=session,
                    curriculum=latest_curriculum,
                    modules=existing_modules,
                )
                preview_modules = self._mark_preview_modules(
                    session=session,
                    curriculum=latest_curriculum,
                    modules=existing_modules,
                    project_id=project_id,
                    preview_count=preview_count,
                )
                question_meta = self._get_existing_question_meta(
                    session=session,
                    modules=existing_modules,
                )
                session.refresh(latest_curriculum)
                existing_module_count = len(existing_modules)
                return {
                    "message": "Existing curriculum reused",
                    "status": (
                        "success"
                        if requested_module_count is None
                        or existing_module_count == requested_module_count
                        else "partial_success"
                    ),
                    "curriculum_id": str(latest_curriculum.id),
                    "total_module": latest_curriculum.total_module,
                    "ready_module": latest_curriculum.ready_module,
                    "saved_modules": existing_module_count,
                    "missing_modules": [],
                    **deleted_question_meta,
                    **question_meta,
                    "modules": preview_modules,
                }

        outline_context = ContextSelector(session).select(OUTLINE, project_id)
        full_text = outline_context.text

        generated_by = "toc"
        expected_module_count = calculate_expected_module_count(
            full_text,
            requested_count=requested_module_count,
            chunk_count=outline_context.total_chunks,
        )
        source_topics = self._select_source_topics(
            self._extract_source_topics(full_text),
            max_topics=expected_module_count,
        )
        if not source_topics:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract source-grounded topics from the uploaded "
                    "materials"
                ),
            )
        expected_module_count = len(source_topics)
        if user_id is not None:
            plan = AITransactionService._get_current_plan(session, user_id=user_id)
            AITransactionService._check_plan_limit(
                session,
                user_id=user_id,
                plan=plan,
            )
        logger.info(
            "Curriculum module count estimated. project_id=%s context_chars=%s "
            "expected_modules=%s requested_modules=%s source_topics=%s",
            project_id,
            len(full_text),
            expected_module_count,
            requested_module_count,
            len(source_topics),
        )
        outline = extract_curriculum_outline_from_toc(
            full_text,
            requested_module_count=requested_module_count,
        )
        if outline is None:
            generated_by = "source"
            try:
                outline = generate_curriculum_outline_fallback(
                    full_text,
                    requested_module_count=requested_module_count,
                )
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning(
                    "Source outline generation failed. project_id=%s error_type=%s error=%s",
                    project_id,
                    type(exc).__name__,
                    exc,
                )
                raise HTTPException(
                    status_code=400,
                    detail="Could not find a usable table of contents or headings in the uploaded materials",
                ) from exc

        curriculum_title = clean_vietnamese_text(
            str(outline.get("title") or f"Curriculum for {project.name}")
        ).strip() or f"Curriculum for {project.name}"
        curriculum_overview = clean_vietnamese_text(
            str(outline.get("overview") or "")
        ).strip()

        curriculum = Curriculums(
            project_id=project_id,
            title=curriculum_title,
            overview=curriculum_overview or None,
            generated_by=generated_by,
            total_module=0,
            ready_module=0,
        )
        session.add(curriculum)
        session.commit()
        session.refresh(curriculum)

        (
            created_modules,
            missing_modules,
            generation_queued,
            quota_exceeded,
        ) = self._create_pending_modules_in_batches(
            session=session,
            curriculum=curriculum,
            user_id=user_id,
            context_selection=outline_context,
            source_topics=source_topics,
            expected_modules=expected_module_count,
            preview_count=preview_count,
        )
        saved_modules = len(created_modules)
        generation_status = "partial_success"
        if quota_exceeded:
            generation_status = "quota_exceeded"
        elif generation_queued:
            generation_status = "queued"
        elif (
            saved_modules == expected_module_count
            and (curriculum.hallucination_score or 0)
            <= settings.CURRICULUM_MAX_HALLUCINATION_SCORE
        ):
            generation_status = "success"
        elif (
            curriculum.hallucination_score or 0
        ) > settings.CURRICULUM_MAX_HALLUCINATION_SCORE:
            generation_status = "rejected"
        if generation_status == "success":
            logger.info(
                "Curriculum generation completed. project_id=%s curriculum_id=%s "
                "expected_modules=%s saved_modules=%s",
                project_id,
                curriculum.id,
                expected_module_count,
                saved_modules,
            )
        else:
            logger.warning(
                "Curriculum generation incomplete. project_id=%s curriculum_id=%s "
                "expected_modules=%s saved_modules=%s missing_modules=%s",
                project_id,
                curriculum.id,
                expected_module_count,
                saved_modules,
                missing_modules,
            )

        preview_modules = self._mark_preview_modules(
            session=session,
            curriculum=curriculum,
            modules=created_modules,
            project_id=project_id,
            preview_count=preview_count,
        )

        all_modules = self._get_curriculum_modules(
            session=session,
            curriculum_id=curriculum.id,
        )
        self._sync_curriculum_progress(
            session=session,
            curriculum=curriculum,
            modules=all_modules,
        )
        question_meta = self._get_existing_question_meta(
            session=session,
            modules=all_modules,
        )
        logger.info(
            "Curriculum lazy question state loaded. project_id=%s curriculum_id=%s questions_count=%s",
            project_id,
            curriculum.id,
            question_meta.get("questions_count", 0),
        )
        session.refresh(curriculum)
        return {
            "message": "Curriculum outline created with lazy lesson generation",
            "status": generation_status,
            "curriculum_id": str(curriculum.id),
            "total_module": curriculum.total_module,
            "ready_module": curriculum.ready_module,
            "expected_modules": expected_module_count,
            "saved_modules": saved_modules,
            "missing_modules": missing_modules,
            "source_coverage_score": curriculum.source_coverage_score,
            "heading_match_score": curriculum.heading_match_score,
            "hallucination_score": curriculum.hallucination_score,
            **deleted_question_meta,
            **question_meta,
            "modules": preview_modules,
        }

    def ensure_module_ready(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
    ) -> CurriculumModules:
        curriculum, module = self._get_module_context_or_404(
            session=session,
            module_id=module_id,
        )

        if module.generate_status == "ready" and module.content:
            return module

        if module.generate_status == "generating":
            return module

        try:
            return self._generate_module_content(
                session=session,
                curriculum=curriculum,
                module=module,
                full_text="",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"AI service failed to generate module content: {exc}",
            ) from exc

    def prefetch_next_modules(
        self,
        *,
        session: Session,
        module_id: uuid.UUID,
        limit: int = 2,
    ) -> list[CurriculumModules]:
        curriculum, current_module = self._get_module_context_or_404(
            session=session,
            module_id=module_id,
        )

        next_modules = session.exec(
            select(CurriculumModules)
            .where(
                CurriculumModules.curriculum_id == curriculum.id,
                CurriculumModules.order_index > (current_module.order_index or 0),
                CurriculumModules.generate_status.in_(("pending", "failed")),
            )
            .order_by(CurriculumModules.order_index)
            .limit(limit)
        ).all()

        if not next_modules:
            return []

        generated_modules: list[CurriculumModules] = []
        for module in next_modules:
            try:
                generated_modules.append(
                    self._generate_module_content(
                        session=session,
                        curriculum=curriculum,
                        module=module,
                        full_text="",
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Prefetch lesson generation failed. curriculum_id=%s module_id=%s error_type=%s error=%s",
                    curriculum.id,
                    module.id,
                    type(exc).__name__,
                    exc,
                )

        self._sync_curriculum_progress(
            session=session,
            curriculum=curriculum,
            modules=self._get_curriculum_modules(
                session=session,
                curriculum_id=curriculum.id,
            ),
        )
        return generated_modules

    def prefetch_next_modules_background(
        self,
        *,
        module_id: uuid.UUID,
        limit: int = 2,
        user_id: uuid.UUID | None = None,
    ) -> None:
        with Session(engine) as session:
            module = session.get(CurriculumModules, module_id)
            curriculum = (
                session.get(Curriculums, module.curriculum_id)
                if module is not None
                else None
            )
            with ai_usage_tracking_context(
                session=session,
                user_id=user_id,
                project_id=curriculum.project_id if curriculum else None,
                action_type="generate_lesson",
            ):
                self.prefetch_next_modules(
                    session=session,
                    module_id=module_id,
                    limit=limit,
                )
