import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship

class BaseModel(SQLModel):
    pass

class Users(BaseModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(nullable=False, unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    account_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    avatar_url: Optional[str] = None
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
    assignments_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="assignments.id",
    )
    curriculum_module_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="curriculum_modules.id",
    )

    content: str
    question_type: str = Field(default="single_choice")
    explanation: Optional[str] = None
    generated_by: str = Field(default="ai") 
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Projects = Relationship(back_populates="questions")
    criteria: Criteria = Relationship(back_populates="questions")
    answers: List["Answers"] = Relationship(back_populates="question")
    options: List["QuestionOptions"] = Relationship(back_populates="question")
    assignment: Optional["Assignments"] = Relationship(back_populates="questions")
    curriculum_module: Optional["CurriculumModules"] = Relationship(back_populates="questions")


class QuestionOptions(BaseModel, table=True):
    __tablename__ = "question_options"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    question_id: uuid.UUID = Field(foreign_key="questions.id")

    content: str
    is_correct: bool = Field(default=False)
    order_index: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    question: Questions = Relationship(back_populates="options")


class Answers(BaseModel, table=True):
    __tablename__ = "answers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    question_id: uuid.UUID = Field(foreign_key="questions.id")
    user_id: uuid.UUID = Field(foreign_key="users.id")
    attempt_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="assessment_attempts.id",
    )

    score: int = Field(ge=1, le=5)
    selected_option_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="question_options.id",
    )
    text_answer: Optional[str] = None
    is_correct: Optional[bool] = None
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
    curriculum_module_id: uuid.UUID = Field(default=None,foreign_key="curriculum_modules.id")
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
    file_path: Optional[str] = None
    commit_hash: Optional[str] = None
    score: Optional[float] = Field(default=None, ge=0.0)
    status: str = Field(default="submitted")
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    graded_at: Optional[datetime] = None

    assignment: Assignments = Relationship(back_populates="submissions")
    feedback: Optional["AICodeFeedback"] = Relationship(back_populates="submission")


class AICodeFeedback(BaseModel, table=True):
    __tablename__ = "ai_code_feedback"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    submission_id: uuid.UUID = Field(foreign_key="code_submissions.id")

    overview: str
    flow_analysis: Optional[str] = None
    code_quality_score: Optional[float] = Field(default=None, ge=0.0)
    logic_score: Optional[float] = Field(default=None, ge=0.0)
    performance_score: Optional[float] = Field(default=None, ge=0.0)
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    improvement_suggestions: Optional[str] = None
    generated_by: str = Field(default="ai")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    submission: CodeSubmissions = Relationship(back_populates="feedback")


class PricingPlans(BaseModel, table=True):
    __tablename__ = "pricing_plans"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, unique=True, index=True)
    description: Optional[str] = None
    ai_usage_limit: Optional[int] = None
    price: float
    billing_cycle: str = Field(default="monthly")
    max_project: Optional[int] = None
    is_active: bool = Field(default=True)
    is_featured: bool = Field(default=False)
    display_order: int = Field(default=0)
    bagde_text: Optional[str] = None
    created_at: datetime = Field(default_factory= datetime.utcnow)
    update_at: Optional[datetime] = None


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
    total_module: Optional[int] = None
    ready_module: int = 0
    source_coverage_score: Optional[float] = None
    heading_match_score: Optional[float] = None
    hallucination_score: Optional[float] = None

    project: Projects = Relationship(back_populates="curriculums")
    modules: List["CurriculumModules"] = Relationship(back_populates="curriculum")

class CurriculumModules(BaseModel, table=True):
    __tablename__ = "curriculum_modules"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    curriculum_id: uuid.UUID = Field(foreign_key="curriculums.id")

    title: str
    description: Optional[str] = None
    learning_objectives: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    source_headings: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    source_chunks: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    heading_match_score: Optional[float] = None
    hallucination_score: Optional[float] = None
    content: Optional[str] = None
    generate_status: str = "pending"
    order_index: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_preview: bool = False

    curriculum: Curriculums = Relationship(back_populates="modules")
    questions: List["Questions"] = Relationship(back_populates="curriculum_module")

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
    assignment_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="assignments.id",
    )
    answers: List["Answers"] = Relationship(back_populates="attempt")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None

    time_limit_minutes: Optional[int] = None

    is_submitted: bool = Field(default=False)
    is_time_up: bool = Field(default=False)
    project: Projects = Relationship(back_populates="assessment_attempts")
    user: Users = Relationship(back_populates="assessment_attempts")

class MaterialChunk(SQLModel, table=True):
    __tablename__ = "material_chunks"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    material_id: uuid.UUID = Field(foreign_key="learning_materials.id")
    curriculum_module_id: Optional[uuid.UUID] = Field(foreign_key="curriculum_modules.id", default=None)
    content: str = Field(nullable=False)
    chunk_index: int = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    material: Optional[LearningMaterials] = Relationship()
    curriculum_module: Optional[CurriculumModules] = Relationship()

class PaymentTransactions(BaseModel, table=True):
    __tablename__ = "payment_transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    plan_id: uuid.UUID = Field(foreign_key="pricing_plans.id")

    amount: int
    currency: str
    payment_provider: str
    order_id: str = Field(nullable=False, unique=True, index=True, max_length=100)
    request_id: str = Field(nullable=False, unique=True, index=True, max_length=100)
    provider_transaction_id: Optional[str] = None
    pay_url: Optional[str] = Field(default=None, max_length=1024)
    deeplink: Optional[str] = Field(default=None, max_length=1024)
    qr_code_url: Optional[str] = Field(default=None, max_length=1024)
    status: str = Field(default="pending")
    result_code: Optional[int] = None
    message: Optional[str] = Field(default=None, max_length=1024)
    paid_at: Optional[datetime] = None
    update_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class OrderBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    plan_id: uuid.UUID = Field(foreign_key="pricing_plans.id", nullable=False, index=True)

    order_code: str = Field(max_length=100, unique=True, index=True)

    plan_name: str = Field(max_length=255)
    amount: int
    currency: str = Field(default="VND", max_length=10)

    payment_method: str = Field(default="momo", max_length=50)

    status: str = Field(default="pending", max_length=30)
    payment_status: str = Field(default="unpaid", max_length=30)

    paid_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AiusageQuota(SQLModel):
    __tablename__ = "ai_usage_quota"
    id: uuid.UUID = Field(default_factory= uuid.UUID, primary_key= True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, unique=True)
    token_used: int = Field(default=0)
    reset_at: datetime
    update_at: datetime = Field(default_factory=datetime.utcnow)
