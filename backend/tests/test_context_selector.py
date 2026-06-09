import unittest
from types import SimpleNamespace

from app.services.context_selector import (
    CODE_REVIEW,
    LESSON,
    OUTLINE,
    QUIZ,
    ContextSelection,
    ContextSelector,
    _ChunkRecord,
)
from app.services.ai_context_guard import require_context_selection


class ContextSelectorTests(unittest.TestCase):
    def test_representative_indices_cover_start_middle_and_end(self):
        indices = ContextSelector._representative_indices(20, count=5)

        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 19)
        self.assertIn(10, indices)

    def test_keyword_ranking_includes_neighbor_chunks(self):
        chunks = [
            _ChunkRecord("Guide", 0, "unrelated introduction"),
            _ChunkRecord("Guide", 1, "setup details before authentication"),
            _ChunkRecord("Guide", 2, "jwt authentication token validation"),
            _ChunkRecord("Guide", 3, "refresh token example"),
            _ChunkRecord("Guide", 4, "unrelated appendix"),
        ]

        indices = ContextSelector._rank_with_neighbors(
            chunks,
            query="jwt authentication",
            top_k=1,
            neighbor_window=1,
        )

        self.assertEqual(indices, [1, 2, 3])

    def test_code_review_context_respects_budget_and_excludes_curriculum(self):
        selector = ContextSelector(session=None)
        assignment = SimpleNamespace(description="Implement login endpoint")

        selection = selector.select(
            CODE_REVIEW,
            project_id=None,
            assignment=assignment,
            source_code="print('code')\n" * 10_000,
            rubric="Correctness and readability",
            expected_outcomes="A working endpoint",
        )

        self.assertLessEqual(selection.context_chars, selector._budget(CODE_REVIEW))
        self.assertIn("SOURCE CODE:", selection.text)
        self.assertIn("GRADING RUBRIC:", selection.text)
        self.assertNotIn("curriculum", selection.text.lower())

    def test_outline_context_hard_limits_chunks_and_chars(self):
        selector = ContextSelector(session=None)
        chunks = [
            _ChunkRecord("Guide", index, f"# Section {index}\n" + ("content " * 2_000))
            for index in range(120)
        ]

        selection = selector._select_outline(chunks, explicit_override=False)
        selector._validate_selection(selection)

        self.assertLessEqual(selection.selected_chunks, 80)
        self.assertLess(selection.selected_chunks, selection.total_chunks)
        self.assertLessEqual(selection.context_chars, 60_000)

    def test_lesson_context_never_selects_entire_document(self):
        module = SimpleNamespace(title="authentication", description="jwt token")
        selector = ContextSelector(
            session=SimpleNamespace(get=lambda _model, _id: module)
        )
        chunks = [
            _ChunkRecord("Guide", index, "jwt authentication token " + ("content " * 50))
            for index in range(70)
        ]

        selection = selector._select_lesson(
            chunks,
            module_id="module-id",
            explicit_override=False,
        )
        selector._validate_selection(selection)

        self.assertLessEqual(selection.selected_chunks, 40)
        self.assertLess(selection.selected_chunks, selection.total_chunks)
        self.assertLessEqual(selection.context_chars, 40_000)

    def test_quiz_fallback_limits_selected_chunks(self):
        module = SimpleNamespace(
            title="authentication",
            description="jwt token",
            content=None,
        )
        chunks = [
            _ChunkRecord("Guide", index, "jwt authentication token " + ("content " * 50))
            for index in range(70)
        ]
        selector = ContextSelector(
            session=SimpleNamespace(get=lambda _model, _id: module)
        )
        selector._load_project_chunks = lambda _project_id: chunks

        selection = selector.select(QUIZ, project_id="project-id", module_id="module-id")

        self.assertLessEqual(selection.selected_chunks, 20)
        self.assertLess(selection.selected_chunks, selection.total_chunks)
        self.assertLessEqual(selection.context_chars, 20_000)

    def test_warning_when_entire_large_document_is_selected(self):
        selector = ContextSelector(session=None)
        selection = ContextSelection(
            purpose=OUTLINE,
            text="limited",
            total_chunks=101,
            selected_chunks=101,
            context_chars=7,
            estimated_tokens=1,
            retrieval_strategy="test",
            explicit_override=True,
        )

        with self.assertLogs("uvicorn.error", level="WARNING") as logs:
            selector._validate_selection(selection)

        self.assertIn(
            "Entire document context selected. Retrieval optimization bypassed.",
            "\n".join(logs.output),
        )

    def test_ai_gateway_guard_requires_selector_metadata(self):
        with self.assertRaisesRegex(RuntimeError, "ContextSelector metadata is required"):
            require_context_selection(None)
        with self.assertRaisesRegex(RuntimeError, "metadata was not validated"):
            require_context_selection(
                ContextSelection(
                    purpose=LESSON,
                    text="unsafe",
                    total_chunks=0,
                    selected_chunks=0,
                    context_chars=6,
                    estimated_tokens=1,
                    retrieval_strategy="manual",
                )
            )

        selection = ContextSelector(session=None).select_text(
            LESSON,
            "safe text",
            retrieval_strategy="test",
        )
        require_context_selection(selection)

    def test_groq_fallback_trim_respects_token_budget(self):
        selector = ContextSelector(session=None)
        selection = selector.select_text(
            OUTLINE,
            "content " * 4_000,
            retrieval_strategy="test",
        )

        trimmed = selector.trim_to_token_budget(
            selection,
            max_tokens=3500,
            retrieval_strategy_suffix="groq_fallback_trim",
        )

        self.assertLessEqual(trimmed.estimated_tokens, 3500)
        self.assertLess(trimmed.context_chars, selection.context_chars)
        require_context_selection(trimmed)


if __name__ == "__main__":
    unittest.main()
