import unittest
import uuid
from unittest.mock import patch

from fastapi import HTTPException

from app.models.models import AICodeFeedback, Assignments
from app.services.Ai_code_feedback import AICodeFeedbackService
from app.services.code_submissions import CodeSubmissionService


class FakeSession:
    def __init__(self, assignment):
        self.assignment = assignment
        self.added = []
        self.commits = 0

    def get(self, model, item_id):
        if model is Assignments and item_id == self.assignment.id:
            return self.assignment
        return None

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1

    @staticmethod
    def refresh(_item):
        return None


class CodeSubmissionServiceTests(unittest.TestCase):
    @patch("app.services.code_submissions.UserSubscriptionService.check_subscription")
    def test_submit_returns_saved_submission_when_grading_fails(
        self,
        check_subscription_mock,
    ):
        assignment = Assignments(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            title="GitHub assignment",
            description="Submit repository",
        )
        session = FakeSession(assignment)
        service = CodeSubmissionService(session)

        with patch.object(
            service,
            "_trigger_ai_grading",
            side_effect=HTTPException(status_code=400, detail="No code files found"),
        ):
            submission = service.submit_code(
                user_id=uuid.uuid4(),
                assignment_id=assignment.id,
                github_repo_url="https://github.com/example/repo",
            )

        check_subscription_mock.assert_called_once()
        self.assertEqual(submission.assignment_id, assignment.id)
        self.assertEqual(submission.github_repo_url, "https://github.com/example/repo")
        self.assertIn(submission, session.added)

    def test_overall_score_fills_missing_component_scores(self):
        scores = CodeSubmissionService._normalize_score_fields(
            {
                "overall_score": 7.5,
                "code_quality_score": None,
                "logic_score": None,
                "performance_score": None,
            }
        )

        self.assertEqual(
            scores,
            {
                "code_quality_score": 7.5,
                "logic_score": 7.5,
                "performance_score": 7.5,
            },
        )

    def test_overall_score_only_fills_missing_scores(self):
        scores = CodeSubmissionService._normalize_score_fields(
            {
                "overall_score": 8.0,
                "code_quality_score": 9.0,
                "logic_score": 7.0,
            }
        )

        self.assertEqual(scores["code_quality_score"], 9.0)
        self.assertEqual(scores["logic_score"], 7.0)
        self.assertEqual(scores["performance_score"], 8.0)

    def test_feedback_score_average_uses_available_scores(self):
        self.assertEqual(
            AICodeFeedbackService._average_available_scores(9.0, None, 7.0),
            8.0,
        )
        self.assertIsNone(
            AICodeFeedbackService._average_available_scores(None, None, None)
        )

    def test_normalize_feedback_record_extracts_json_overview(self):
        feedback = AICodeFeedback(
            submission_id=uuid.uuid4(),
            overview=(
                '{"overview": "Tong quan", "flow_analysis": "Luong xu ly", '
                '"code_quality_score": 6.5, "logic_score": 7, '
                '"performance_score": 6, "strengths": "Tot", '
                '"weaknesses": "Can sua", '
                '"improvement_suggestions": "Tach ham"}'
            ),
        )

        changed = AICodeFeedbackService.normalize_feedback_record(feedback)

        self.assertTrue(changed)
        self.assertEqual(feedback.overview, "Tong quan")
        self.assertEqual(feedback.flow_analysis, "Luong xu ly")
        self.assertEqual(feedback.code_quality_score, 6.5)
        self.assertEqual(feedback.logic_score, 7.0)
        self.assertEqual(feedback.performance_score, 6.0)
        self.assertEqual(feedback.strengths, "Tot")
        self.assertEqual(feedback.weaknesses, "Can sua")
        self.assertEqual(feedback.improvement_suggestions, "Tach ham")


if __name__ == "__main__":
    unittest.main()
