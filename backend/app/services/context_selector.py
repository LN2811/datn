import logging
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Iterable

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.models.models import (
    Assignments,
    CurriculumModules,
    LearningMaterials,
    MaterialChunk,
)
from app.services.material_chunk import MaterialChunkService
from app.services.ai_context_guard import CONTEXT_SELECTION_SIGNATURE
from app.services.ai_service import clean_extracted_text, deduplicate_passages

logger = logging.getLogger("uvicorn.error")

OUTLINE = "outline"
LESSON = "lesson"
QUIZ = "quiz"
ASSIGNMENT = "assignment"
CODE_REVIEW = "code_review"

SUPPORTED_PURPOSES = {OUTLINE, LESSON, QUIZ, ASSIGNMENT, CODE_REVIEW}
HEADING_PATTERN = re.compile(
    r"^\s*(?:#{1,6}\s+|(?:chapter|chuong|phan|bai|muc)\s+\d+|"
    r"\d+(?:\.\d+){0,5}[.)]?\s+).+",
    flags=re.IGNORECASE,
)
WORD_PATTERN = re.compile(r"[0-9a-zA-Z\u00c0-\u024f]+")
STOPWORDS = {
    "and", "are", "bai", "cac", "cho", "cua", "dung", "for", "hoc", "module",
    "noi", "phan", "tai", "the", "this", "trong", "with",
}


@dataclass(frozen=True)
class ContextSelection:
    purpose: str
    text: str
    total_chunks: int
    selected_chunks: int
    context_chars: int
    estimated_tokens: int
    retrieval_strategy: str
    explicit_override: bool = False
    _selector_signature: str = field(
        default=CONTEXT_SELECTION_SIGNATURE,
        init=False,
        repr=False,
    )
    _validated: bool = field(default=False, init=False, repr=False)


@dataclass(frozen=True)
class _ChunkRecord:
    material_title: str
    chunk_index: int
    content: str


class ContextSelector:
    def __init__(self, session: Session):
        self.session = session

    def select(
        self,
        purpose: str,
        project_id: uuid.UUID,
        module_id: uuid.UUID | None = None,
        *,
        assignment: Assignments | None = None,
        source_code: str | None = None,
        rubric: str | None = None,
        expected_outcomes: str | None = None,
        explicit_override: bool = False,
    ) -> ContextSelection:
        started_at = time.perf_counter()
        if purpose not in SUPPORTED_PURPOSES:
            raise ValueError(f"Unsupported context purpose: {purpose}")
        override_enabled = bool(
            explicit_override and settings.AI_CONTEXT_ADMIN_OVERRIDE_ENABLED
        )

        if purpose == CODE_REVIEW:
            selection = self._select_code_review(
                assignment=assignment,
                source_code=source_code or "",
                rubric=rubric,
                expected_outcomes=expected_outcomes,
                explicit_override=override_enabled,
            )
        elif purpose == ASSIGNMENT:
            selection = self._select_assignment(
                project_id=project_id,
                module_id=module_id,
                assignment=assignment,
                explicit_override=override_enabled,
            )
        elif purpose == QUIZ:
            selection = self._select_quiz(
                project_id=project_id,
                module_id=module_id,
                assignment=assignment,
                explicit_override=override_enabled,
            )
        else:
            chunks = self._load_project_chunks(project_id)
            if purpose == OUTLINE:
                selection = self._select_outline(
                    chunks,
                    explicit_override=override_enabled,
                )
            else:
                selection = self._select_lesson(
                    chunks,
                    module_id=module_id,
                    explicit_override=override_enabled,
                )

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        self._validate_selection(selection)
        logger.info(
            "AI context selected. purpose=%s total_chunks=%s selected_chunks=%s "
            "context_chars=%s estimated_tokens=%s retrieval_strategy=%s generation_time_ms=%s",
            selection.purpose,
            selection.total_chunks,
            selection.selected_chunks,
            selection.context_chars,
            selection.estimated_tokens,
            selection.retrieval_strategy,
            elapsed_ms,
        )
        return selection

    def select_text(
        self,
        purpose: str,
        text: str,
        *,
        retrieval_strategy: str,
        total_chunks: int = 0,
        selected_chunks: int = 0,
        explicit_override: bool = False,
    ) -> ContextSelection:
        if purpose not in SUPPORTED_PURPOSES:
            raise ValueError(f"Unsupported context purpose: {purpose}")
        override_enabled = bool(
            explicit_override and settings.AI_CONTEXT_ADMIN_OVERRIDE_ENABLED
        )
        selection = self._selection(
            purpose=purpose,
            text=(
                text
                if override_enabled
                else self._truncate(text, self._budget(purpose))
            ),
            total_chunks=total_chunks,
            selected_chunks=selected_chunks,
            retrieval_strategy=retrieval_strategy,
            explicit_override=override_enabled,
        )
        self._validate_selection(selection)
        logger.info(
            "AI context selected. purpose=%s total_chunks=%s selected_chunks=%s "
            "context_chars=%s estimated_tokens=%s retrieval_strategy=%s",
            selection.purpose,
            selection.total_chunks,
            selection.selected_chunks,
            selection.context_chars,
            selection.estimated_tokens,
            selection.retrieval_strategy,
        )
        return selection

    def trim_to_token_budget(
        self,
        selection: ContextSelection,
        *,
        max_tokens: int,
        retrieval_strategy_suffix: str,
    ) -> ContextSelection:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")
        if selection.estimated_tokens <= max_tokens:
            return selection
        trimmed = self._selection(
            purpose=selection.purpose,
            text=self._truncate(selection.text, max_tokens * 4),
            total_chunks=selection.total_chunks,
            selected_chunks=selection.selected_chunks,
            retrieval_strategy=(
                f"{selection.retrieval_strategy}_{retrieval_strategy_suffix}"
            ),
            explicit_override=False,
        )
        self._validate_selection(trimmed)
        logger.info(
            "AI context trimmed to token budget. purpose=%s token_budget=%s "
            "estimated_tokens_before_trim=%s estimated_tokens_after_trim=%s",
            selection.purpose,
            max_tokens,
            selection.estimated_tokens,
            trimmed.estimated_tokens,
        )
        return trimmed

    def _budget(self, purpose: str) -> int:
        budgets = {
            OUTLINE: settings.OUTLINE_MAX_CHARS,
            LESSON: settings.LESSON_MAX_CHARS,
            QUIZ: settings.QUIZ_MAX_CHARS,
            ASSIGNMENT: settings.ASSIGNMENT_MAX_CHARS,
            CODE_REVIEW: settings.AI_CONTEXT_CODE_REVIEW_CHARS,
        }
        return budgets[purpose]

    @staticmethod
    def _max_chunks(purpose: str) -> int | None:
        limits = {
            OUTLINE: settings.OUTLINE_MAX_CHUNKS,
            LESSON: settings.LESSON_MAX_CHUNKS,
            QUIZ: settings.QUIZ_MAX_CHUNKS,
            ASSIGNMENT: settings.ASSIGNMENT_MAX_CHUNKS,
            CODE_REVIEW: None,
        }
        return limits[purpose]

    def _allowed_chunk_count(
        self,
        purpose: str,
        *,
        total_chunks: int,
        explicit_override: bool,
    ) -> int:
        if explicit_override:
            return total_chunks
        max_chunks = self._max_chunks(purpose) or total_chunks
        if total_chunks > 1:
            return min(max_chunks, total_chunks - 1)
        return min(max_chunks, total_chunks)

    def _load_project_chunks(self, project_id: uuid.UUID) -> list[_ChunkRecord]:
        materials = self.session.exec(
            select(LearningMaterials)
            .where(LearningMaterials.project_id == project_id)
            .order_by(LearningMaterials.created_at)
        ).all()
        if not materials:
            raise HTTPException(
                status_code=404,
                detail="No learning materials found for this project",
            )

        records: list[_ChunkRecord] = []
        for material in materials:
            chunks = self.session.exec(
                select(MaterialChunk)
                .where(MaterialChunk.material_id == material.id)
                .order_by(MaterialChunk.chunk_index)
            ).all()
            if not chunks:
                try:
                    chunks = MaterialChunkService(self.session).save_material_chunk(
                        material_id=material.id,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to load context chunks. project_id=%s material_id=%s "
                        "error_type=%s error=%s",
                        project_id,
                        material.id,
                        type(exc).__name__,
                        exc,
                    )
                    continue
            records.extend(
                _ChunkRecord(
                    material_title=material.title,
                    chunk_index=chunk.chunk_index,
                    content=(chunk.content or "").strip(),
                )
                for chunk in chunks
                if (chunk.content or "").strip()
            )

        if not records:
            raise HTTPException(
                status_code=400,
                detail="No content extracted from learning materials",
            )
        cleaned_passages, duplicate_chunks_removed, duplicate_removed_chars = (
            deduplicate_passages(
                [
                    clean_extracted_text(record.content)
                    for record in records
                    if record.content
                ]
            )
        )
        logger.info(
            "Context chunks sanitized. project_id=%s total_chunks=%s selected_chunks=%s "
            "duplicate_chunks_removed=%s duplicate_removed_chars=%s",
            project_id,
            len(records),
            len(cleaned_passages),
            duplicate_chunks_removed,
            duplicate_removed_chars,
        )
        if not cleaned_passages:
            raise HTTPException(
                status_code=400,
                detail="No clean content extracted from learning materials",
            )
        return [
            _ChunkRecord(
                material_title="cleaned material",
                chunk_index=index,
                content=passage,
            )
            for index, passage in enumerate(cleaned_passages)
        ]

    def _select_outline(
        self,
        chunks: list[_ChunkRecord],
        *,
        explicit_override: bool,
    ) -> ContextSelection:
        budget = self._budget(OUTLINE)
        headings = self._collect_headings(chunks)
        max_chunks = self._allowed_chunk_count(
            OUTLINE,
            total_chunks=len(chunks),
            explicit_override=explicit_override,
        )
        representative_indices = self._outline_ranked_indices(
            chunks,
            max_selected=max_chunks,
        )
        heading_text = self._truncate(
            "DOCUMENT HEADINGS:\n" + "\n".join(headings),
            budget // 3,
        ) if headings else ""
        text, selected_count = self._join_chunks_with_budget(
            chunks,
            representative_indices,
            budget=budget,
            prefix=heading_text,
        )
        return self._selection(
            purpose=OUTLINE,
            text=text,
            total_chunks=len(chunks),
            selected_chunks=selected_count,
            retrieval_strategy="headings_plus_representative_start_middle_end",
            explicit_override=explicit_override,
        )

    def _select_lesson(
        self,
        chunks: list[_ChunkRecord],
        *,
        module_id: uuid.UUID | None,
        explicit_override: bool = False,
    ) -> ContextSelection:
        if module_id is None:
            raise ValueError("module_id is required for lesson context")
        module = self._get_module(module_id)
        query = " ".join(
            part for part in [module.title, module.description or ""] if part
        )
        selected_indices = self._rank_with_neighbors(
            chunks,
            query=query,
            top_k=settings.AI_CONTEXT_LESSON_TOP_K,
            neighbor_window=settings.AI_CONTEXT_LESSON_NEIGHBOR_WINDOW,
            max_selected=(
                self._allowed_chunk_count(
                    LESSON,
                    total_chunks=len(chunks),
                    explicit_override=explicit_override,
                )
            ),
        )
        text, selected_count = self._join_chunks_with_budget(
            chunks,
            selected_indices,
            budget=self._budget(LESSON),
        )
        return self._selection(
            purpose=LESSON,
            text=text,
            total_chunks=len(chunks),
            selected_chunks=selected_count,
            retrieval_strategy="keyword_similarity_top_k_with_neighbors",
            explicit_override=explicit_override,
        )

    def _select_quiz(
        self,
        *,
        project_id: uuid.UUID,
        module_id: uuid.UUID | None,
        assignment: Assignments | None,
        explicit_override: bool,
    ) -> ContextSelection:
        if module_id is not None:
            module = self._get_module(module_id)
            lesson_text = (module.content or "").strip()
            if lesson_text:
                return self._selection(
                    purpose=QUIZ,
                    text=self._truncate(lesson_text, self._budget(QUIZ)),
                    total_chunks=0,
                    selected_chunks=0,
                    retrieval_strategy="generated_lesson_content",
                    explicit_override=explicit_override,
                )
            chunks = self._load_project_chunks(project_id)
            query = " ".join(
                part for part in [module.title, module.description or ""] if part
            )
            selected_indices = self._rank_with_neighbors(
                chunks,
                query=query,
                top_k=settings.AI_CONTEXT_LESSON_TOP_K,
                neighbor_window=settings.AI_CONTEXT_LESSON_NEIGHBOR_WINDOW,
                max_selected=(
                    self._allowed_chunk_count(
                        QUIZ,
                        total_chunks=len(chunks),
                        explicit_override=explicit_override,
                    )
                ),
            )
            text, selected_count = self._join_chunks_with_budget(
                chunks,
                selected_indices,
                budget=self._budget(QUIZ),
            )
            return self._selection(
                purpose=QUIZ,
                text=text,
                total_chunks=len(chunks),
                selected_chunks=selected_count,
                retrieval_strategy="quiz_keyword_similarity_top_k_with_neighbors_fallback",
                explicit_override=explicit_override,
            )

        return self._select_assignment(
            project_id=project_id,
            module_id=getattr(assignment, "curriculum_module_id", None),
            assignment=assignment,
            purpose=QUIZ,
            explicit_override=explicit_override,
        )

    def _select_assignment(
        self,
        *,
        project_id: uuid.UUID,
        module_id: uuid.UUID | None,
        assignment: Assignments | None,
        purpose: str = ASSIGNMENT,
        explicit_override: bool = False,
    ) -> ContextSelection:
        module_text = ""
        if module_id is not None:
            module = self._get_module(module_id)
            module_text = "\n\n".join(
                part
                for part in [module.title, module.description or "", module.content or ""]
                if part
            )
        assignment_text = "\n\n".join(
            part
            for part in [
                getattr(assignment, "title", "") if assignment else "",
                getattr(assignment, "description", "") if assignment else "",
            ]
            if part
        )
        text = module_text or assignment_text
        return self._selection(
            purpose=purpose,
            text=self._truncate(text, self._budget(purpose)),
            total_chunks=0,
            selected_chunks=0,
            retrieval_strategy="module_content_only" if module_text else "assignment_metadata_only",
            explicit_override=explicit_override,
        )

    def _select_code_review(
        self,
        *,
        assignment: Assignments | None,
        source_code: str,
        rubric: str | None,
        expected_outcomes: str | None,
        explicit_override: bool,
    ) -> ContextSelection:
        assignment_description = (
            getattr(assignment, "description", "") if assignment else ""
        )
        metadata = "\n\n".join(
            part
            for part in [
                f"ASSIGNMENT DESCRIPTION:\n{assignment_description}" if assignment_description else "",
                f"GRADING RUBRIC:\n{rubric}" if rubric else "",
                f"EXPECTED OUTCOMES:\n{expected_outcomes}" if expected_outcomes else "",
            ]
            if part
        )
        source_budget = max(self._budget(CODE_REVIEW) - len(metadata) - 2, 0)
        text = "\n\n".join(
            part
            for part in [metadata, f"SOURCE CODE:\n{self._truncate(source_code, source_budget)}"]
            if part
        )
        return self._selection(
            purpose=CODE_REVIEW,
            text=self._truncate(text, self._budget(CODE_REVIEW)),
            total_chunks=0,
            selected_chunks=0,
            retrieval_strategy="source_code_plus_assignment_grading_metadata",
            explicit_override=explicit_override,
        )

    def _get_module(self, module_id: uuid.UUID) -> CurriculumModules:
        module = self.session.get(CurriculumModules, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        return module

    @classmethod
    def _collect_headings(cls, chunks: Iterable[_ChunkRecord]) -> list[str]:
        headings: list[str] = []
        seen: set[str] = set()
        for chunk in chunks:
            for line in chunk.content.splitlines():
                stripped = line.strip()
                if len(stripped) > 160 or not HEADING_PATTERN.match(stripped):
                    continue
                key = cls._fold(stripped)
                if key and key not in seen:
                    headings.append(stripped)
                    seen.add(key)
        return headings[:160]

    @staticmethod
    def _representative_indices(total: int, *, count: int) -> list[int]:
        if total <= 0:
            return []
        if count <= 1:
            return [0]
        if total <= count:
            return list(range(total))
        return sorted({round(index * (total - 1) / (count - 1)) for index in range(count)})

    @classmethod
    def _outline_ranked_indices(
        cls,
        chunks: list[_ChunkRecord],
        *,
        max_selected: int,
    ) -> list[int]:
        if max_selected <= 0:
            return []
        coverage_indices = cls._representative_indices(
            len(chunks),
            count=min(7, max_selected),
        )
        heading_ranked_indices = sorted(
            range(len(chunks)),
            key=lambda index: (
                sum(
                    1
                    for line in chunks[index].content.splitlines()
                    if HEADING_PATTERN.match(line.strip())
                ),
                -index,
            ),
            reverse=True,
        )
        selected: list[int] = []
        for index in [*coverage_indices, *heading_ranked_indices]:
            if index not in selected:
                selected.append(index)
            if len(selected) >= max_selected:
                break
        return selected

    @classmethod
    def _rank_with_neighbors(
        cls,
        chunks: list[_ChunkRecord],
        *,
        query: str,
        top_k: int,
        neighbor_window: int,
        max_selected: int | None = None,
    ) -> list[int]:
        query_terms = cls._terms(query)
        ranked = sorted(
            range(len(chunks)),
            key=lambda index: (
                cls._similarity_score(chunks[index].content, query_terms),
                -index,
            ),
            reverse=True,
        )
        selected: list[int] = []
        for index in ranked[: max(top_k, 1)]:
            for neighbor in range(index - neighbor_window, index + neighbor_window + 1):
                if 0 <= neighbor < len(chunks) and neighbor not in selected:
                    selected.append(neighbor)
        if max_selected is not None:
            selected = selected[:max_selected]
        return sorted(selected)

    @classmethod
    def _similarity_score(cls, content: str, query_terms: set[str]) -> float:
        if not query_terms:
            return 0.0
        content_terms = cls._terms(content)
        overlap = query_terms.intersection(content_terms)
        return len(overlap) / len(query_terms)

    @classmethod
    def _terms(cls, value: str) -> set[str]:
        return {
            term
            for term in WORD_PATTERN.findall(cls._fold(value))
            if len(term) >= 3 and term not in STOPWORDS
        }

    @staticmethod
    def _fold(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value or "")
        return "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        ).lower()

    @staticmethod
    def _format_chunk(chunk: _ChunkRecord) -> str:
        return f"[{chunk.material_title} - chunk {chunk.chunk_index}]\n{chunk.content}"

    @classmethod
    def _join_chunks_with_budget(
        cls,
        chunks: list[_ChunkRecord],
        indices: Iterable[int],
        *,
        budget: int,
        prefix: str = "",
    ) -> tuple[str, int]:
        selected_parts = [prefix] if prefix else []
        remaining = budget - len(prefix)
        selected_count = 0
        for index in indices:
            separator_chars = 2 if selected_parts else 0
            if remaining <= separator_chars:
                break
            part = cls._truncate(
                cls._format_chunk(chunks[index]),
                remaining - separator_chars,
            )
            if not part:
                continue
            selected_parts.append(part)
            selected_count += 1
            remaining -= len(part) + separator_chars
        return "\n\n".join(selected_parts).strip(), selected_count

    @staticmethod
    def _truncate(text: str, budget: int) -> str:
        if budget <= 0:
            return ""
        return (text or "").strip()[:budget].strip()

    @staticmethod
    def _selection(
        *,
        purpose: str,
        text: str,
        total_chunks: int,
        selected_chunks: int,
        retrieval_strategy: str,
        explicit_override: bool = False,
    ) -> ContextSelection:
        return ContextSelection(
            purpose=purpose,
            text=text,
            total_chunks=total_chunks,
            selected_chunks=selected_chunks,
            context_chars=len(text),
            estimated_tokens=max(1, len(text) // 4),
            retrieval_strategy=retrieval_strategy,
            explicit_override=explicit_override,
        )

    def _validate_selection(self, selection: ContextSelection) -> None:
        if selection.selected_chunks == selection.total_chunks and selection.total_chunks > 100:
            logger.warning(
                "Entire document context selected. Retrieval optimization bypassed. "
                "purpose=%s total_chunks=%s selected_chunks=%s context_chars=%s estimated_tokens=%s",
                selection.purpose,
                selection.total_chunks,
                selection.selected_chunks,
                selection.context_chars,
                selection.estimated_tokens,
            )
        if selection.explicit_override:
            object.__setattr__(selection, "_validated", True)
            return
        max_chunks = self._max_chunks(selection.purpose)
        if max_chunks is not None and selection.selected_chunks > max_chunks:
            raise RuntimeError(
                f"Context chunk budget exceeded for {selection.purpose}: "
                f"{selection.selected_chunks} > {max_chunks}"
            )
        max_chars = self._budget(selection.purpose)
        if selection.context_chars > max_chars:
            raise RuntimeError(
                f"Context character budget exceeded for {selection.purpose}: "
                f"{selection.context_chars} > {max_chars}"
            )
        object.__setattr__(selection, "_validated", True)
