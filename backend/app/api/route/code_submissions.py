import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.authen.authen import Authen
from app.models.models import Users
from app.services.code_submissions import CodeSubmissionService

router = APIRouter()


class SubmissionCreateBody(BaseModel):
    assignment_id: uuid.UUID
    github_repo_url: str | None = None
    file_path: str | None = None
    commit_hash: str | None = None


@router.post("")
def submit_code(
    submission_in: SubmissionCreateBody,
    session: SessionDep,
    current_user: Users = Depends(Authen.get_current_user),
):
    return CodeSubmissionService(session).submit_code(
        user_id=current_user.id,
        assignment_id=submission_in.assignment_id,
        github_repo_url=submission_in.github_repo_url,
        file_path=submission_in.file_path,
        commit_hash=submission_in.commit_hash,
    )


@router.get("/best-score/{assignment_id}")
def get_best_score(
    assignment_id: uuid.UUID,
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    current_user: Users = Depends(Authen.get_current_user),
):
    target_user_id = user_id or current_user.id
    if target_user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    return {
        "assignment_id": str(assignment_id),
        "user_id": str(target_user_id),
        "best_score": CodeSubmissionService(session).get_best_score(
            user_id=target_user_id,
            assignment_id=assignment_id,
        ),
    }


@router.get("/history/{assignment_id}")
def get_submission_history(
    assignment_id: uuid.UUID,
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    current_user: Users = Depends(Authen.get_current_user),
):
    target_user_id = user_id or current_user.id
    if target_user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    return CodeSubmissionService(session).get_submission_history(
        user_id=target_user_id,
        assignment_id=assignment_id,
    )


@router.get("/{submission_id}")
def get_submission_detail(
    submission_id: uuid.UUID,
    session: SessionDep,
    _: Users = Depends(Authen.get_current_user),
):
    return CodeSubmissionService(session).get_submission_detail(
        submission_id=submission_id,
    )
