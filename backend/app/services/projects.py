import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.models.models import (
    AIAnalysis,
    AICodeFeedback,
    AIGeneratedSources,
    AIUsageLogs,
    Answers,
    AssessmentAttempt,
    AssessmentResults,
    Assignments,
    CodeSubmissions,
    Curriculums,
    CurriculumModules,
    LearningMaterials,
    MaterialChunk,
    Projects,
    QuestionOptions,
    Questions,
    Users,
)


class ProjectService:
    @staticmethod
    def _has_table(session: Session, table_name: str) -> bool:
        bind = session.get_bind()
        if bind is None:
            return False
        return inspect(bind).has_table(table_name)

    @staticmethod
    def _safe_exec_all(session: Session, statement):
        try:
            return session.exec(statement).all()
        except SQLAlchemyError:
            return []

    @staticmethod
    def _safe_exec_first(session: Session, statement):
        try:
            return session.exec(statement).first()
        except SQLAlchemyError:
            return None

    @staticmethod
    def _delete_records(session: Session, model, records, seen_ids: set | None = None) -> None:
        del model
        if seen_ids is None:
            seen_ids = set()
        for record in records:
            record_id = getattr(record, "id", id(record))
            if record_id in seen_ids:
                continue
            seen_ids.add(record_id)
            session.delete(record)

    @staticmethod
    def _serialize_datetime(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def _latest_datetime(*values: datetime | None) -> datetime | None:
        valid_values = [value for value in values if value is not None]
        if not valid_values:
            return None
        return max(valid_values)

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

    def _can_access_project(
        self,
        session: Session,
        *,
        project: Projects,
        user_id: uuid.UUID,
    ) -> bool:
        if project.owner_id == user_id:
            return True

        if self._has_table(session, AssessmentAttempt.__tablename__):
            has_attempt = self._safe_exec_first(
                session,
                select(AssessmentAttempt.id).where(
                    AssessmentAttempt.project_id == project.id,
                    AssessmentAttempt.user_id == user_id,
                ),
            )
            if has_attempt is not None:
                return True

        if self._has_table(session, AssessmentResults.__tablename__):
            has_result = self._safe_exec_first(
                session,
                select(AssessmentResults.id).where(
                    AssessmentResults.project_id == project.id,
                    AssessmentResults.user_id == user_id,
                ),
            )
            if has_result is not None:
                return True

        if self._has_table(session, Assignments.__tablename__) and self._has_table(
            session, CodeSubmissions.__tablename__
        ):
            has_submission = self._safe_exec_first(
                session,
                select(CodeSubmissions.id)
                .join(Assignments, CodeSubmissions.assignment_id == Assignments.id)
                .where(
                    Assignments.project_id == project.id,
                    CodeSubmissions.user_id == user_id,
                ),
            )
            if has_submission is not None:
                return True

        return False

    async def get_project(
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
        if not self._can_access_project(session, project=project, user_id=current_user_id):
            raise HTTPException(status_code=403, detail="Not authorized to view this project")

        owner = session.get(Users, project.owner_id)
        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "owner_id": str(project.owner_id),
            "owner_email": owner.email if owner else None,
            "is_owner": project.owner_id == current_user_id,
        }

    async def get_dashboard_overview(
        self,
        *,
        session: Session,
        request: Request | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        current_user_id = self._resolve_user_id(request=request, user_id=user_id)

        has_attempts_table = self._has_table(session, AssessmentAttempt.__tablename__)
        has_results_table = self._has_table(session, AssessmentResults.__tablename__)
        has_assignments_table = self._has_table(session, Assignments.__tablename__)
        has_submissions_table = self._has_table(session, CodeSubmissions.__tablename__)
        has_materials_table = self._has_table(session, LearningMaterials.__tablename__)
        has_analysis_table = self._has_table(session, AIAnalysis.__tablename__)

        owned_project_ids = session.exec(
            select(Projects.id).where(Projects.owner_id == current_user_id)
        ).all()
        attempted_project_ids = (
            self._safe_exec_all(
                session,
                select(AssessmentAttempt.project_id).where(AssessmentAttempt.user_id == current_user_id),
            )
            if has_attempts_table
            else []
        )
        result_project_ids = (
            self._safe_exec_all(
                session,
                select(AssessmentResults.project_id).where(AssessmentResults.user_id == current_user_id),
            )
            if has_results_table
            else []
        )
        submission_project_ids = (
            self._safe_exec_all(
                session,
                select(Assignments.project_id)
                .join(CodeSubmissions, CodeSubmissions.assignment_id == Assignments.id)
                .where(CodeSubmissions.user_id == current_user_id),
            )
            if has_assignments_table and has_submissions_table
            else []
        )

        project_ids = {
            *owned_project_ids,
            *attempted_project_ids,
            *result_project_ids,
            *submission_project_ids,
        }
        if not project_ids:
            return {
                "summary": {
                    "total_projects": 0,
                    "tracked_assignments": 0,
                    "submitted_assignments": 0,
                    "average_progress": 0,
                    "assessments_completed": 0,
                    "attention_needed": 0,
                    "last_activity_at": None,
                },
                "projects": [],
            }

        project_id_list = list(project_ids)
        projects = session.exec(
            select(Projects)
            .where(Projects.id.in_(project_id_list))
            .order_by(Projects.name.asc())
        ).all()

        assignments = (
            self._safe_exec_all(
                session,
                select(Assignments)
                .where(Assignments.project_id.in_(project_id_list))
                .order_by(Assignments.created_at.desc()),
            )
            if has_assignments_table
            else []
        )
        assignment_ids = [assignment.id for assignment in assignments]

        submissions = []
        if assignment_ids and has_submissions_table:
            submissions = self._safe_exec_all(
                session,
                select(CodeSubmissions)
                .where(
                    CodeSubmissions.user_id == current_user_id,
                    CodeSubmissions.assignment_id.in_(assignment_ids),
                )
                .order_by(CodeSubmissions.submitted_at.desc()),
            )

        quiz_attempts = []
        if assignment_ids and has_attempts_table:
            quiz_attempts = self._safe_exec_all(
                session,
                select(AssessmentAttempt)
                .where(
                    AssessmentAttempt.user_id == current_user_id,
                    AssessmentAttempt.assignment_id.in_(assignment_ids),
                    AssessmentAttempt.is_submitted == True,
                )
                .order_by(AssessmentAttempt.submitted_at.desc()),
            )

        materials = (
            self._safe_exec_all(
                session,
                select(LearningMaterials).where(LearningMaterials.project_id.in_(project_id_list)),
            )
            if has_materials_table
            else []
        )

        results = (
            self._safe_exec_all(
                session,
                select(AssessmentResults)
                .where(
                    AssessmentResults.user_id == current_user_id,
                    AssessmentResults.project_id.in_(project_id_list),
                )
                .order_by(AssessmentResults.created_at.desc()),
            )
            if has_results_table
            else []
        )

        latest_result_by_project: dict[uuid.UUID, AssessmentResults] = {}
        for result in results:
            if result.project_id not in latest_result_by_project:
                latest_result_by_project[result.project_id] = result

        latest_result_ids = [result.id for result in latest_result_by_project.values()]
        analyses = []
        if latest_result_ids and has_analysis_table:
            analyses = self._safe_exec_all(
                session,
                select(AIAnalysis).where(AIAnalysis.assessment_result_id.in_(latest_result_ids)),
            )
        analysis_by_result_id = {
            analysis.assessment_result_id: analysis
            for analysis in analyses
        }

        assignments_by_project: dict[uuid.UUID, list[Assignments]] = {}
        for assignment in assignments:
            assignments_by_project.setdefault(assignment.project_id, []).append(assignment)

        submissions_by_assignment: dict[uuid.UUID, list[CodeSubmissions]] = {}
        for submission in submissions:
            submissions_by_assignment.setdefault(submission.assignment_id, []).append(submission)

        quiz_attempts_by_assignment: dict[uuid.UUID, list[AssessmentAttempt]] = {}
        for attempt in quiz_attempts:
            if attempt.assignment_id is None:
                continue
            quiz_attempts_by_assignment.setdefault(attempt.assignment_id, []).append(attempt)

        material_count_by_project: dict[uuid.UUID, int] = {}
        for material in materials:
            material_count_by_project[material.project_id] = (
                material_count_by_project.get(material.project_id, 0) + 1
            )

        project_payloads = []
        last_activity_candidates: list[datetime] = []

        for project in projects:
            project_assignments = assignments_by_project.get(project.id, [])
            serialized_assignments = []
            submitted_assignments = 0
            total_submissions = 0
            project_assignment_activity: list[datetime] = []

            for assignment in project_assignments:
                assignment_submissions = submissions_by_assignment.get(assignment.id, [])
                assignment_quiz_attempts = quiz_attempts_by_assignment.get(assignment.id, [])
                submission_count = len(assignment_submissions) + len(assignment_quiz_attempts)
                total_submissions += submission_count
                if submission_count > 0:
                    submitted_assignments += 1

                latest_code_submission_at = (
                    assignment_submissions[0].submitted_at if assignment_submissions else None
                )
                latest_quiz_submission_at = (
                    assignment_quiz_attempts[0].submitted_at
                    if assignment_quiz_attempts
                    else None
                )
                latest_submission_at = self._latest_datetime(
                    latest_code_submission_at,
                    latest_quiz_submission_at,
                )
                best_score = None
                if hasattr(CodeSubmissions, "score") and assignment_submissions:
                    score_values = [
                        getattr(submission, "score", None)
                        for submission in assignment_submissions
                        if getattr(submission, "score", None) is not None
                    ]
                    if score_values:
                        best_score = max(score_values)

                assignment_activity = self._latest_datetime(
                    assignment.created_at,
                    latest_submission_at,
                )
                if assignment_activity is not None:
                    project_assignment_activity.append(assignment_activity)

                serialized_assignments.append(
                    {
                        "id": str(assignment.id),
                        "title": assignment.title,
                        "description": assignment.description,
                        "created_at": self._serialize_datetime(assignment.created_at),
                        "submission_count": submission_count,
                        "is_submitted": submission_count > 0,
                        "last_submitted_at": self._serialize_datetime(latest_submission_at),
                        "best_score": best_score,
                    }
                )

            assignments_total = len(project_assignments)
            assignments_pending = max(assignments_total - submitted_assignments, 0)
            progress_percentage = (
                round((submitted_assignments / assignments_total) * 100)
                if assignments_total > 0
                else 0
            )

            latest_result = latest_result_by_project.get(project.id)
            latest_analysis = (
                analysis_by_result_id.get(latest_result.id)
                if latest_result is not None
                else None
            )

            material_count = material_count_by_project.get(project.id, 0)
            project_last_activity = self._latest_datetime(
                max(project_assignment_activity) if project_assignment_activity else None,
                latest_result.created_at if latest_result is not None else None,
            )
            if project_last_activity is not None:
                last_activity_candidates.append(project_last_activity)

            if latest_result is None:
                next_action = "Hoan thanh bai tu danh gia de he thong AI goi y lo trinh phu hop."
            elif latest_result.readiness_level == "low":
                next_action = (
                    latest_analysis.recommendations
                    if latest_analysis is not None and latest_analysis.recommendations
                    else "Nen on lai kien thuc nen va chia nho muc tieu hoc tap."
                )
            elif assignments_pending > 0:
                next_action = f"Con {assignments_pending} bai tap chua nop. Uu tien hoan thanh cac moc dang mo."
            else:
                next_action = (
                    latest_analysis.recommendations
                    if latest_analysis is not None and latest_analysis.recommendations
                    else "Giu nhip hoc hien tai va danh gia lai dinh ky de cap nhat muc do san sang."
                )

            project_payloads.append(
                {
                    "id": str(project.id),
                    "name": project.name,
                    "description": project.description,
                    "is_owner": project.owner_id == current_user_id,
                    "assignments_total": assignments_total,
                    "assignments_completed": submitted_assignments,
                    "assignments_pending": assignments_pending,
                    "progress_percentage": progress_percentage,
                    "materials_count": material_count,
                    "submissions_total": total_submissions,
                    "last_activity_at": self._serialize_datetime(project_last_activity),
                    "next_action": next_action,
                    "latest_assessment": (
                        {
                            "result_id": str(latest_result.id),
                            "total_score": latest_result.total_score,
                            "readiness_level": latest_result.readiness_level,
                            "created_at": self._serialize_datetime(latest_result.created_at),
                            "analysis_text": (
                                latest_analysis.analysis_text if latest_analysis is not None else None
                            ),
                            "strengths": (
                                latest_analysis.strengths if latest_analysis is not None else None
                            ),
                            "weaknesses": (
                                latest_analysis.weaknesses if latest_analysis is not None else None
                            ),
                            "recommendations": (
                                latest_analysis.recommendations
                                if latest_analysis is not None
                                else None
                            ),
                        }
                        if latest_result is not None
                        else None
                    ),
                    "recent_assignments": serialized_assignments[:4],
                }
            )

        project_payloads.sort(
            key=lambda item: (
                item["last_activity_at"] is not None,
                item["last_activity_at"] or "",
                item["name"].lower(),
            ),
            reverse=True,
        )

        total_assignments = sum(item["assignments_total"] for item in project_payloads)
        total_submitted_assignments = sum(item["assignments_completed"] for item in project_payloads)
        assessments_completed = sum(
            1 for item in project_payloads if item["latest_assessment"] is not None
        )
        attention_needed = sum(
            1
            for item in project_payloads
            if (
                item["latest_assessment"] is None
                or item["assignments_pending"] > 0
                or (
                    item["latest_assessment"] is not None
                    and item["latest_assessment"]["readiness_level"] == "low"
                )
            )
        )

        return {
            "summary": {
                "total_projects": len(project_payloads),
                "tracked_assignments": total_assignments,
                "submitted_assignments": total_submitted_assignments,
                "average_progress": (
                    round((total_submitted_assignments / total_assignments) * 100)
                    if total_assignments > 0
                    else 0
                ),
                "assessments_completed": assessments_completed,
                "attention_needed": attention_needed,
                "last_activity_at": self._serialize_datetime(
                    max(last_activity_candidates) if last_activity_candidates else None
                ),
            },
            "projects": project_payloads,
        }

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

        curriculum_ids = session.exec(
            select(Curriculums.id).where(Curriculums.project_id == project_id)
        ).all()
        module_ids = (
            session.exec(
                select(CurriculumModules.id).where(CurriculumModules.curriculum_id.in_(curriculum_ids))
            ).all()
            if curriculum_ids
            else []
        )
        material_ids = session.exec(
            select(LearningMaterials.id).where(LearningMaterials.project_id == project_id)
        ).all()
        assignment_ids = session.exec(
            select(Assignments.id).where(Assignments.project_id == project_id)
        ).all()
        submission_ids = (
            session.exec(
                select(CodeSubmissions.id).where(CodeSubmissions.assignment_id.in_(assignment_ids))
            ).all()
            if assignment_ids
            else []
        )
        question_ids = session.exec(
            select(Questions.id).where(Questions.project_id == project_id)
        ).all()
        attempt_ids = session.exec(
            select(AssessmentAttempt.id).where(AssessmentAttempt.project_id == project_id)
        ).all()
        result_ids = session.exec(
            select(AssessmentResults.id).where(AssessmentResults.project_id == project_id)
        ).all()

        deleted_answer_ids: set = set()
        deleted_chunk_ids: set = set()

        if question_ids:
            self._delete_records(
                session,
                Answers,
                session.exec(select(Answers).where(Answers.question_id.in_(question_ids))).all(),
                deleted_answer_ids,
            )
        if attempt_ids:
            self._delete_records(
                session,
                Answers,
                session.exec(select(Answers).where(Answers.attempt_id.in_(attempt_ids))).all(),
                deleted_answer_ids,
            )
        if question_ids:
            self._delete_records(
                session,
                QuestionOptions,
                session.exec(
                    select(QuestionOptions).where(QuestionOptions.question_id.in_(question_ids))
                ).all(),
            )
        if submission_ids:
            self._delete_records(
                session,
                AICodeFeedback,
                session.exec(
                    select(AICodeFeedback).where(AICodeFeedback.submission_id.in_(submission_ids))
                ).all(),
            )

        if result_ids:
            self._delete_records(
                session,
                AIAnalysis,
                session.exec(
                    select(AIAnalysis).where(AIAnalysis.assessment_result_id.in_(result_ids))
                ).all(),
            )

        if material_ids:
            self._delete_records(
                session,
                MaterialChunk,
                session.exec(select(MaterialChunk).where(MaterialChunk.material_id.in_(material_ids))).all(),
                deleted_chunk_ids,
            )
        if module_ids:
            self._delete_records(
                session,
                MaterialChunk,
                session.exec(
                    select(MaterialChunk).where(MaterialChunk.curriculum_module_id.in_(module_ids))
                ).all(),
                deleted_chunk_ids,
            )

        self._delete_records(
            session,
            Questions,
            session.exec(select(Questions).where(Questions.project_id == project_id)).all(),
        )
        if submission_ids:
            self._delete_records(
                session,
                CodeSubmissions,
                session.exec(select(CodeSubmissions).where(CodeSubmissions.id.in_(submission_ids))).all(),
            )
        if assignment_ids:
            self._delete_records(
                session,
                Assignments,
                session.exec(select(Assignments).where(Assignments.id.in_(assignment_ids))).all(),
            )
        if result_ids:
            self._delete_records(
                session,
                AssessmentResults,
                session.exec(select(AssessmentResults).where(AssessmentResults.id.in_(result_ids))).all(),
            )
        if attempt_ids:
            self._delete_records(
                session,
                AssessmentAttempt,
                session.exec(select(AssessmentAttempt).where(AssessmentAttempt.id.in_(attempt_ids))).all(),
            )
        if material_ids:
            self._delete_records(
                session,
                LearningMaterials,
                session.exec(select(LearningMaterials).where(LearningMaterials.id.in_(material_ids))).all(),
            )
        if module_ids:
            self._delete_records(
                session,
                CurriculumModules,
                session.exec(select(CurriculumModules).where(CurriculumModules.id.in_(module_ids))).all(),
            )
        if curriculum_ids:
            self._delete_records(
                session,
                Curriculums,
                session.exec(select(Curriculums).where(Curriculums.id.in_(curriculum_ids))).all(),
            )

        self._delete_records(
            session,
            AIGeneratedSources,
            session.exec(select(AIGeneratedSources).where(AIGeneratedSources.project_id == project_id)).all(),
        )
        self._delete_records(
            session,
            AIUsageLogs,
            session.exec(select(AIUsageLogs).where(AIUsageLogs.project_id == project_id)).all(),
        )

        session.delete(project)
        session.commit()
        return {"message": "Project deleted successfully"}
