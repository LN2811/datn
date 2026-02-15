import asyncio
import logging
from datetime import date
from fastapi import HTTPException, Request, Depends
from sqlmodel import and_, asc, desc, func, select, Session
from uuid import UUID
from app.models.models import Projects, Users
from app.models.schemas.projects.project_schemas import ProjectCreate, ProjectUpdate, ProjectsPublic

logger = logging.getLogger(__name__)

class ProjectService:
    def__init__(self):
        self.session = Session()
    async def create_project(self, project_data: ProjectCreate, request: Request) -> ProjectsPublic:
        user_id = request.state.user_id
        new_project = Projects(
            name=project_data.name,
            account_id=project_data.account_id,
            user_id=user_id
        )
        self.session.add(new_project)
        self.session.commit()
        self.session.refresh(new_project)
        user = self.session.get(Users, user_id)
        return ProjectsPublic(
            id=new_project.id,
            name=new_project.name,
            is_active=new_project.is_active,
            created_at=new_project.created_at,
            updated_at=new_project.updated_at,
            user_id=user.id,
            user_name=user.name
        )
    async def update_project(self, project_id: UUID, project_data: ProjectUpdate, request: Request) -> ProjectsPublic:
        user_id = request.state.user_id
        project = self.session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this project")
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.is_active is not None:
            project.is_active = project_data.is_active
        project.updated_at = func.now()
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        user = self.session.get(Users, user_id)
        return ProjectsPublic(
            id=project.id,
            name=project.name,
            is_active=project.is_active,
            created_at=project.created_at,
            updated_at=project.updated_at,
            user_id=user.id,
            user_name=user.name
        )
    async def delete_project(self, project_id: UUID, request: Request) -> str:
        user_id = request.state.user_id
        project = self.session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this project")
        self.session.delete(project)
        self.session.commit()
        return "Project deleted successfully"