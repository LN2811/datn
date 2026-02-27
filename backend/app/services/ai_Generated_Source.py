import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import Session, select, func

from app.models.models import AIGeneratedSources, Projects


class AIGeneratedSourceService:

    def create(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        source_url: Optional[str],
        title: Optional[str],
        content_summary: Optional[str],
        source_type: str = "web"
    ) -> AIGeneratedSources:

        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        source = AIGeneratedSources(
            project_id=project_id,
            source_url=source_url,
            title=title,
            content_summary=content_summary,
            source_type=source_type,
            created_at=datetime.utcnow()
        )

        session.add(source)
        session.commit()
        session.refresh(source)

        return source

    def get_by_project(
        self,
        *,
        session: Session,
        project_id: uuid.UUID
    ) -> List[AIGeneratedSources]:
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return session.exec(
            select(AIGeneratedSources)
            .where(AIGeneratedSources.project_id == project_id)
            .order_by(AIGeneratedSources.created_at.desc())
        ).all()

    def get_by_id(
        self,
        *,
        session: Session,
        source_id: uuid.UUID
    ) -> AIGeneratedSources:

        source = session.get(AIGeneratedSources, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        return source

    def update(
        self,
        *,
        session: Session,
        source_id: uuid.UUID,
        source_url: Optional[str] = None,
        title: Optional[str] = None,
        content_summary: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> AIGeneratedSources:

        source = session.get(AIGeneratedSources, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        if source_url is not None:
            source.source_url = source_url
        if title is not None:
            source.title = title
        if content_summary is not None:
            source.content_summary = content_summary
        if source_type is not None:
            source.source_type = source_type

        session.add(source)
        session.commit()
        session.refresh(source)

        return source

    def delete(
        self,
        *,
        session: Session,
        source_id: uuid.UUID
    ):

        source = session.get(AIGeneratedSources, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        session.delete(source)
        session.commit()

        return {"message": "Source deleted"}

    def search(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        keyword: str
    ) -> List[AIGeneratedSources]:
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        keyword = keyword.strip()
        if not keyword:
            return []

        return session.exec(
            select(AIGeneratedSources)
            .where(
                AIGeneratedSources.project_id == project_id,
                (AIGeneratedSources.title.ilike(f"%{keyword}%"))
                | (AIGeneratedSources.content_summary.ilike(f"%{keyword}%"))
            )
            .order_by(AIGeneratedSources.created_at.desc())
        ).all()

    def stats(
        self,
        *,
        session: Session,
        project_id: uuid.UUID
    ):
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        total_sources = session.exec(
            select(func.count(AIGeneratedSources.id))
            .where(AIGeneratedSources.project_id == project_id)
        ).one()

        by_type = session.exec(
            select(
                AIGeneratedSources.source_type,
                func.count(AIGeneratedSources.id)
            )
            .where(AIGeneratedSources.project_id == project_id)
            .group_by(AIGeneratedSources.source_type)
        ).all()

        return {
            "total_sources": total_sources,
            "by_type": by_type
        }
