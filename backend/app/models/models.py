import uuid
from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship

class BaseModel(SQLModel):
    pass

class Users(BaseModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(nullable=False, unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    assessment_attempts: List["AssessmentAttempt"] = Relationship(back_populates="user")
    projects: List["Projects"] = Relationship(back_populates="owner")

class Projects(BaseModel, table=True):
    __tablename__ = "projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True)
    description: Optional[str] = None
    owner_id: uuid.UUID = Field(foreign_key="users.id")

    owner: Users = Relationship(back_populates="projects")
    materials: List["LearningMaterials"] = Relationship(back_populates="project")
    questions: List["Questions"] = Relationship(back_populates="project")
    assignments: List["Assignments"] = Relationship(back_populates="project")
    curriculums: List["Curriculums"] = Relationship(back_populates="project")
    ai_sources: List["AIGeneratedSources"] = Relationship(back_populates="project")
    ai_logs: List["AIUsageLogs"] = Relationship(back_populates="project")
    assessment_attempts: List["AssessmentAttempt"] = Relationship(back_populates="project")

class LearningMaterials(BaseModel, table=True):
    __tablename__ = "learning_materials"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id")
    uploaded_by: uuid.UUID = Field(foreign_key="users.id")

    title: str
    file_path: Optional[str] = None
    external_link: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Projects = Relationship(back_populates="materials")

class Criteria(BaseModel, table=True):
    __tablename__ = "criteria"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    description: Optional[str] = None
    weight: Optional[float] = Field(default=1.0)

    questions: List["Questions"] = Relationship(back_populates="criteria")


class Questions(BaseModel, table=True):
    __tablename__ = "questions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id")
    criteria_id: uuid.UUID = Field(foreign_key="criteria.id")
    assignments_id: uuid.UUID = Field(foreign_key="assignment.id")

    content: str
    generated_by: str = Field(default="ai") 
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Projects = Relationship(back_populates="questions")
    criteria: Criteria = Relationship(back_populates="questions")
    answers: List["Answers"] = Relationship(back_populates="question")
    assignment: Optional["Assignments"] = Relationship(back_populates="questions")


class Answers(BaseModel, table=True):
    __tablename__ = "answers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    question_id: uuid.UUID = Field(foreign_key="questions.id")
    user_id: uuid.UUID = Field(foreign_key="users.id")
    attempt_id: uuid.UUID = Field(
    foreign_key="assessment_attempts.id",
    nullable=False )

    score: int = Field(ge=1, le=5)
    answered_at: datetime = Field(default_factory=datetime.utcnow)

    question: Questions = Relationship(back_populates="answers")
    attempt: "AssessmentAttempt" = Relationship(back_populates="answers")


class AssessmentResults(BaseModel, table=True):
    __tablename__ = "assessment_results"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    project_id: uuid.UUID = Field(foreign_key="projects.id")

    total_score: Optional[float] = None
    readiness_level: str  # low / medium / high
    created_at: datetime = Field(default_factory=datetime.utcnow)

    analysis: Optional["AIAnalysis"] = Relationship(back_populates="result")


class AIAnalysis(BaseModel, table=True):
    __tablename__ = "ai_analysis"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    assessment_result_id: uuid.UUID = Field(
        foreign_key="assessment_results.id"
    )

    analysis_text: str
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    recommendations: Optional[str] = None
    generated_by: str = Field(default="ai")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    result: AssessmentResults = Relationship(back_populates="analysis")


class Assignments(BaseModel, table=True):
    __tablename__ = "assignments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id")

    title: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    project: Projects = Relationship(back_populates="assignments")
    submissions: List["CodeSubmissions"] = Relationship(back_populates="assignment")
    questions: List["Questions"] = Relationship(back_populates="assignment")


class CodeSubmissions(BaseModel, table=True):
    __tablename__ = "code_submissions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    assignment_id: uuid.UUID = Field(foreign_key="assignments.id")
    user_id: uuid.UUID = Field(foreign_key="users.id")

    github_repo_url: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

    assignment: Assignments = Relationship(back_populates="submissions")
    feedback: Optional["AICodeFeedback"] = Relationship(back_populates="submission")


class AICodeFeedback(BaseModel, table=True):
    __tablename__ = "ai_code_feedback"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    submission_id: uuid.UUID = Field(foreign_key="code_submissions.id")

    overview: str
    flow_analysis: Optional[str] = None
    improvement_suggestions: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    submission: CodeSubmissions = Relationship(back_populates="feedback")


class PricingPlans(BaseModel, table=True):
    __tablename__ = "pricing_plans"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    ai_usage_limit: Optional[int] = None
    price: float


class UserSubscriptions(BaseModel, table=True):
    __tablename__ = "user_subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    plan_id: uuid.UUID = Field(foreign_key="pricing_plans.id")

    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None

class Curriculums(BaseModel, table=True):
    __tablename__ = "curriculums"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id")

    title: str
    overview: Optional[str] = None
    generated_by: str = Field(default="ai")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Projects = Relationship(back_populates="curriculums")
    modules: List["CurriculumModules"] = Relationship(back_populates="curriculum")

class CurriculumModules(BaseModel, table=True):
    __tablename__ = "curriculum_modules"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    curriculum_id: uuid.UUID = Field(foreign_key="curriculums.id")

    title: str
    description: Optional[str] = None
    order_index: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    curriculum: Curriculums = Relationship(back_populates="modules")

class AIGeneratedSources(BaseModel, table=True):
    __tablename__ = "ai_generated"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id")

    source_url: Optional[str] = None
    title: Optional[str] = None
    content_summary: Optional[str] = None
    source_type: str = Field(default="web")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Projects = Relationship(back_populates="ai_sources")

class AIUsageLogs(BaseModel, table=True):
    __tablename__ = "ai_usage_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: uuid.UUID = Field(foreign_key="users.id")
    project_id: Optional[uuid.UUID] = Field(foreign_key="projects.id")

    action_type: str
    tokens_used: Optional[int] = None
    model_name: Optional[str] = None
    cost_amount: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Optional[Projects] = Relationship(back_populates="ai_logs")

class AssessmentAttempt(BaseModel, table=True):
    __tablename__ = "assessment_attempts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    project_id: uuid.UUID = Field(foreign_key="projects.id", nullable=False)
    answers: List["Answers"] = Relationship(back_populates="attempt")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None

    time_limit_minutes: Optional[int] = None

    is_submitted: bool = Field(default=False)
    is_time_up: bool = Field(default=False)
    project: Projects = Relationship(back_populates="assessment_attempts")
    user: Users = Relationship(back_populates="assessment_attempts")
