import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.code_submissions import CodeSubmissionService

router = APIRouter()


class GithubSubmissionRequest(BaseModel):
    assignment_id: uuid.UUID

    github_repo_url: str = Field(
        min_length=10,
        description="GitHub repository URL",
    )

    commit_hash: str | None = None


@router.post("/github")
def submit_github_repository(
    payload: GithubSubmissionRequest,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    return CodeSubmissionService(session).submit_code(
        user_id=current_user.id,
        assignment_id=payload.assignment_id,
        github_repo_url=payload.github_repo_url,
        commit_hash=payload.commit_hash,
    )