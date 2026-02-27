from fastapi import APIRouter

from app.api.route import(
    users,
    projects,
    questions,
    question_options,
    criteria,
    curriculum,
    curriculum_Module,
    assignments,
    assessment_results,
    assessmentAttempts,
    code_submissions,
    LearningMaterials,
    Pricing_plans,
    user_subscriptions,
    answers,
    ai_analysis,
    ai_usage_logs,
    ai_code_feedback,
    ai_generated_sources,
    login,
    authen
)

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(question_options.router, prefix="/question-options", tags=["question-options"])
api_router.include_router(criteria.router, prefix="/criteria", tags=["criteria"])
api_router.include_router(curriculum.router, prefix="/curriculums", tags=["curriculums"])
api_router.include_router(curriculum_Module.router, prefix="/curriculum-modules", tags=["curriculum-modules"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(assessment_results.router, prefix="/assessment-results", tags=["assessment-results"])
api_router.include_router(assessmentAttempts.router, prefix="/assessment-attempts", tags=["assessment-attempts"])
api_router.include_router(code_submissions.router, prefix="/code-submissions", tags=["code-submissions"])
api_router.include_router(LearningMaterials.router, prefix="/learning-materials", tags=["learning-materials"])
api_router.include_router(Pricing_plans.router, prefix="/pricing-plans", tags=["pricing-plans"])
api_router.include_router(user_subscriptions.router, prefix="/user-subscriptions", tags=["user-subscriptions"])
api_router.include_router(answers.router, prefix="/answers", tags=["answers"])
api_router.include_router(ai_analysis.router, prefix="/ai-analysis", tags=["ai-analysis"])
api_router.include_router(ai_usage_logs.router, prefix="/ai-usage-logs", tags=["ai-usage-logs"])
api_router.include_router(ai_code_feedback.router, prefix="/ai-code-feedback", tags=["ai-code-feedback"])
api_router.include_router(ai_generated_sources.router, prefix="/ai-generated-sources", tags=["ai-generated-sources"])
api_router.include_router(login.router, prefix="/auth", tags=["auth"])
api_router.include_router(authen.router, prefix="/authen", tags=["authen"])