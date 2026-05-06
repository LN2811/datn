import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import LearningMaterials, MaterialChunk
from app.services.ai_service import clean_learning_material_text, _split_passages
from app.services.file_parser import extract_text


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
            return existing

        if text is None:
            source = material.file_path or material.external_link
            if not source:
                return []
            text = extract_text(source)

        text = clean_learning_material_text(text)

        chunks = _split_passages(text)
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

        return saved_chunks
