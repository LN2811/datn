import uuid
import logging

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.models.models import LearningMaterials, MaterialChunk
from app.services.ai_service import (
    DIRTY_EXTRACTED_TEXT_ERROR,
    LOW_QUALITY_MATERIAL_ERROR,
    _split_passages,
    analyze_extracted_text_quality,
    clean_extracted_text,
    deduplicate_passages,
    is_extracted_text_quality_acceptable,
)
from app.services.file_parser import extract_text

logger = logging.getLogger("uvicorn.error")


class MaterialChunkService:
    def __init__(self, session: Session):
        self.session = session

    def save_material_chunk(
        self,
        *,
        material_id: uuid.UUID,
        text: str | None = None,
    ) -> list[MaterialChunk]:
        material = self.session.get(LearningMaterials, material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Learning material not found")

        existing = self.session.exec(
            select(MaterialChunk).where(MaterialChunk.material_id == material_id)
        ).all()
        if existing:
            return sorted(existing, key=lambda chunk: chunk.chunk_index)

        if text is None:
            source = material.file_path or material.external_link
            if not source:
                return []
            text = extract_text(source)

        raw_text = text or ""
        text = clean_extracted_text(raw_text)
        quality_report = analyze_extracted_text_quality(
            raw_text,
            cleaned_text=text,
        )
        logger.info(
            "Learning material extraction cleaned. material_id=%s extracted_chars=%s "
            "cleaned_chars=%s duplicate_removed_chars=%s final_chars=%s dirty_score=%s "
            "repeated_ratio=%s broken_word_ratio=%s abnormal_spacing_ratio=%s",
            material_id,
            quality_report.extracted_chars,
            quality_report.cleaned_chars,
            quality_report.duplicate_removed_chars,
            quality_report.final_chars,
            quality_report.dirty_score,
            quality_report.repeated_ratio,
            quality_report.broken_word_ratio,
            quality_report.abnormal_spacing_ratio,
        )
        if quality_report.dirty_score > settings.EXTRACTED_TEXT_MAX_DIRTY_SCORE:
            logger.warning(
                "Learning material extraction rejected as dirty. material_id=%s "
                "dirty_score=%s repeated_ratio=%s broken_word_ratio=%s "
                "abnormal_spacing_ratio=%s",
                material_id,
                quality_report.dirty_score,
                quality_report.repeated_ratio,
                quality_report.broken_word_ratio,
                quality_report.abnormal_spacing_ratio,
            )
            raise HTTPException(status_code=400, detail=DIRTY_EXTRACTED_TEXT_ERROR)
        if not is_extracted_text_quality_acceptable(text, quality_report=quality_report):
            raise HTTPException(status_code=400, detail=LOW_QUALITY_MATERIAL_ERROR)

        chunks, duplicate_chunks_removed, chunk_duplicate_removed_chars = (
            deduplicate_passages(_split_passages(text))
        )
        if not chunks:
            raise HTTPException(status_code=400, detail=LOW_QUALITY_MATERIAL_ERROR)

        saved_chunks: list[MaterialChunk] = []

        for index, chunk in enumerate(chunks):
            material_chunk = MaterialChunk(
                material_id=material_id,
                content=chunk,
                chunk_index=index,
            )
            self.session.add(material_chunk)
            saved_chunks.append(material_chunk)

        self.session.commit()
        for chunk in saved_chunks:
            self.session.refresh(chunk)

        logger.info(
            "Learning material chunks saved. material_id=%s chunks_count=%s cleaned_chars=%s",
            material_id,
            len(saved_chunks),
            len(text),
        )
        logger.info(
            "Learning material chunk deduplication completed. material_id=%s "
            "duplicate_chunks_removed=%s duplicate_removed_chars=%s final_chars=%s chunks_count=%s",
            material_id,
            duplicate_chunks_removed,
            quality_report.duplicate_removed_chars + chunk_duplicate_removed_chars,
            sum(len(chunk) for chunk in chunks),
            len(chunks),
        )
        return saved_chunks
