import uuid
from typing import Any

from fastapi import HTTPException, Request
from sqlmodel import Session

from app.models.models import Projects, Users


class ProjectService:
    @staticmethod
    def _dump_payload(schema_obj: Any) -> dict:
        if hasattr(schema_obj, "model_dump"):
            return schema_obj.model_dump(exclude_unset=True)
        if hasattr(schema_obj, "dict"):
            return schema_obj.dict(exclude_unset=True)
        return {}

    @staticmethod
    def _resolve_user_id(request: Request | None, user_id: uuid.UUID | None = None) -> uuid.UUID:
        if user_id is not None:
            return user_id
        if request is not None and hasattr(request, "state") and hasattr(request.state, "user_id"):
            return request.state.user_id
        raise HTTPException(status_code=401, detail="Missing user context")

    async def create_project(
        self,
        *,
        session: Session,
        project_data: Any,
        request: Request | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        owner_id = self._resolve_user_id(request=request, user_id=user_id)
        payload = self._dump_payload(project_data)

        new_project = Projects(
            name=payload.get("name"),
            description=payload.get("description"),
            owner_id=owner_id,
        )
        if not new_project.name:
            raise HTTPException(status_code=400, detail="Project name is required")

        session.add(new_project)
        session.commit()
        session.refresh(new_project)

        owner = session.get(Users, owner_id)
        return {
            "id": str(new_project.id),
            "name": new_project.name,
            "description": new_project.description,
            "owner_id": str(new_project.owner_id),
            "owner_email": owner.email if owner else None,
        }

    async def update_project(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        project_data: Any,
        request: Request | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        current_user_id = self._resolve_user_id(request=request, user_id=user_id)
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.owner_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this project")

        payload = self._dump_payload(project_data)
        if payload.get("name") is not None:
            project.name = payload["name"]
        if payload.get("description") is not None and hasattr(project, "description"):
            project.description = payload["description"]

        session.add(project)
        session.commit()
        session.refresh(project)

        owner = session.get(Users, current_user_id)
        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "owner_id": str(project.owner_id),
            "owner_email": owner.email if owner else None,
        }

    async def delete_project(
        self,
        *,
        session: Session,
        project_id: uuid.UUID,
        request: Request | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        current_user_id = self._resolve_user_id(request=request, user_id=user_id)
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.owner_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this project")

        session.delete(project)
        session.commit()
        return {"message": "Project deleted successfully"}
