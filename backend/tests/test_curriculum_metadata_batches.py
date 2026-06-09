import json
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from app.models.models import CurriculumModules
from app.services.context_selector import ContextSelector, OUTLINE
from app.services.curriculum_generate import (
    CurriculumGenerationService,
    CurriculumMetadataJSONError,
    SourceTopic,
)


def module_payload(order_index: int, *, title: str | None = None) -> dict:
    return {
        "title": title or f"Module {order_index}",
        "description": f"Description {order_index}",
        "learning_objectives": [f"Objective {order_index}"],
        "order_index": order_index,
    }


def source_topics(count: int) -> list[SourceTopic]:
    return [
        SourceTopic(
            order_index=index,
            heading=f"Module {index}",
            source_chunks=(f"cleaned material - chunk {index}",),
        )
        for index in range(1, count + 1)
    ]


class CurriculumMetadataBatchTests(unittest.TestCase):
    def setUp(self):
        self.service = CurriculumGenerationService()

    def test_expected_twenty_modules_are_saved_in_batches_of_five(self):
        requested_batches = []
        saved_batches = []

        result = self.service._run_module_metadata_batches(
            expected_modules=20,
            request_batch=lambda indices, repair: (
                requested_batches.append((indices, repair))
                or [module_payload(index) for index in indices]
            ),
            save_batch=lambda modules: saved_batches.append(modules),
        )

        self.assertEqual(result, {"saved_modules": 20, "missing_modules": []})
        self.assertEqual([len(batch) for batch in saved_batches], [5, 5, 5, 5])
        self.assertTrue(all(len(indices) <= 5 for indices, _ in requested_batches))
        self.assertTrue(all(not repair for _, repair in requested_batches))

    def test_service_saves_twenty_lazy_module_records(self):
        class FakeSession:
            def __init__(self):
                self.added = []

            def add(self, item):
                self.added.append(item)

            @staticmethod
            def commit():
                return None

            @staticmethod
            def refresh(_item):
                return None

        class StubService(CurriculumGenerationService):
            def _request_module_metadata_batch(
                self,
                *,
                session,
                user_id,
                project_id,
                context_selection,
                curriculum_title,
                curriculum_overview,
                order_indices,
                source_topics,
                repair,
            ):
                return [module_payload(index) for index in order_indices]

        session = FakeSession()
        curriculum = SimpleNamespace(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            title="Generated curriculum",
            overview="Overview",
            total_module=0,
        )
        context_selection = ContextSelector(session=None).select_text(
            OUTLINE,
            "clean source context",
            retrieval_strategy="test",
        )

        modules, missing, queued, quota_exceeded = StubService()._create_pending_modules_in_batches(
            session=session,
            curriculum=curriculum,
            user_id=uuid.uuid4(),
            context_selection=context_selection,
            source_topics=source_topics(20),
            expected_modules=20,
            preview_count=2,
        )

        self.assertEqual(missing, [])
        self.assertFalse(queued)
        self.assertFalse(quota_exceeded)
        self.assertEqual(len(modules), 20)
        self.assertEqual(curriculum.total_module, 20)
        self.assertEqual(
            [module.order_index for module in modules],
            list(range(1, 21)),
        )
        self.assertTrue(
            all(
                isinstance(module, CurriculumModules)
                and module.content is None
                and module.generate_status == "pending"
                for module in modules
            )
        )

    def test_missing_module_is_retried_separately(self):
        requested_batches = []
        saved_modules = []

        def request_batch(indices, repair):
            requested_batches.append((indices, repair))
            if indices == [1, 2, 3, 4, 5] and not repair:
                return [module_payload(index) for index in [1, 2, 4, 5]]
            return [module_payload(index) for index in indices]

        result = self.service._run_module_metadata_batches(
            expected_modules=6,
            request_batch=request_batch,
            save_batch=lambda modules: saved_modules.extend(modules),
        )

        self.assertEqual(result, {"saved_modules": 6, "missing_modules": []})
        self.assertIn(([3], True), requested_batches)
        self.assertEqual(
            sorted(module["order_index"] for module in saved_modules),
            [1, 2, 3, 4, 5, 6],
        )

    def test_duplicate_title_is_removed_and_regenerated(self):
        requested_batches = []

        def request_batch(indices, repair):
            requested_batches.append((indices, repair))
            if indices == [1, 2, 3] and not repair:
                return [
                    module_payload(1, title="Shared title"),
                    module_payload(2, title="Shared title"),
                    module_payload(3),
                ]
            return [module_payload(index, title=f"Repaired {index}") for index in indices]

        result = self.service._run_module_metadata_batches(
            expected_modules=3,
            request_batch=request_batch,
            save_batch=lambda _modules: None,
        )

        self.assertEqual(result, {"saved_modules": 3, "missing_modules": []})
        self.assertIn(([2], True), requested_batches)

    def test_invalid_json_retries_same_batch(self):
        requested_batches = []
        save_calls = []

        def request_batch(indices, repair):
            requested_batches.append((indices, repair))
            if len(requested_batches) == 1:
                return self.service._parse_module_metadata_response("{invalid json")
            return self.service._parse_module_metadata_response(
                json.dumps(
                    {"modules": [module_payload(index) for index in indices]}
                )
            )

        result = self.service._run_module_metadata_batches(
            expected_modules=4,
            request_batch=request_batch,
            save_batch=lambda modules: save_calls.append(modules),
        )

        self.assertEqual(result, {"saved_modules": 4, "missing_modules": []})
        self.assertEqual(requested_batches, [([1, 2, 3, 4], False)] * 2)
        self.assertEqual(len(save_calls), 1)

    def test_tolerant_parser_repairs_common_json_errors(self):
        modules = self.service._parse_module_metadata_response(
            """
            Here is the JSON:
            {
              "modules": [
                {
                  "order_index": 1
                  "title": "Internet",
                  "description": "Source grounded module",
                  "learning_objectives": ["Understand Internet"],
                  "source_headings": ["1. Internet"],
                }
              ],
            }
            """
        )

        self.assertEqual(modules[0]["order_index"], 1)
        self.assertEqual(modules[0]["title"], "Internet")

    def test_parser_salvages_complete_modules_from_truncated_batch(self):
        modules = self.service._parse_module_metadata_response(
            """
            {"modules":[
              {
                "order_index":1,
                "title":"Managing Internet Subnet Issues",
                "description":"An overview of subnet administration.",
                "learning_objectives":["Identify subnet problems"],
                "source_headings":["1.3 Vấn đề quản lý mạng Internet Subnet"]
              },
              {
                "order_index":2,
                "title":"Broken Module",
                "description":"This object is cut off
            """
        )

        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0]["order_index"], 1)
        self.assertEqual(modules[0]["title"], "Managing Internet Subnet Issues")

    def test_parser_repairs_missing_comma_between_module_objects(self):
        modules = self.service._parse_module_metadata_response(
            """
            {"modules":[
              {"order_index":1,"title":"Internet","description":"A","learning_objectives":["A"],"source_headings":["1. Internet"]}
              {"order_index":2,"title":"Router","description":"B","learning_objectives":["B"],"source_headings":["2. Router"]}
            ]}
            """
        )

        self.assertEqual([module["order_index"] for module in modules], [1, 2])

    def test_json_parse_failures_split_batch_then_reduce_remaining_batches(self):
        requested_batches = []
        saved_modules = []

        def request_batch(indices, repair):
            requested_batches.append((indices, repair))
            if len(indices) > 1 and indices == [1, 2, 3, 4, 5]:
                raise CurriculumMetadataJSONError("invalid json")
            return [module_payload(index) for index in indices]

        result = self.service._run_module_metadata_batches(
            expected_modules=10,
            request_batch=request_batch,
            save_batch=lambda modules: saved_modules.extend(modules),
        )

        self.assertEqual(result, {"saved_modules": 10, "missing_modules": []})
        self.assertEqual(
            requested_batches[:8],
            [
                ([1, 2, 3, 4, 5], False),
                ([1, 2, 3, 4, 5], False),
                ([1, 2, 3, 4, 5], False),
                ([1], False),
                ([2], False),
                ([3], False),
                ([4], False),
                ([5], False),
            ],
        )
        self.assertIn(([6, 7], False), requested_batches)
        self.assertIn(([8, 9], False), requested_batches)
        self.assertIn(([10], False), requested_batches)

    def test_missing_module_remains_partial_after_three_repair_rounds(self):
        requested_batches = []

        def request_batch(indices, repair):
            requested_batches.append((indices, repair))
            return [
                module_payload(index)
                for index in indices
                if index != 2
            ]

        result = self.service._run_module_metadata_batches(
            expected_modules=3,
            request_batch=request_batch,
            save_batch=lambda _modules: None,
        )

        self.assertEqual(result, {"saved_modules": 2, "missing_modules": [2]})
        self.assertEqual(requested_batches.count(([2], True)), 3)

    @patch("app.services.curriculum_generate.AITransactionService.chat")
    @patch("app.services.curriculum_generate.call_llm")
    def test_authenticated_metadata_request_uses_subscription_provider_router(
        self,
        call_llm_mock,
        transaction_chat_mock,
    ):
        transaction_chat_mock.return_value = json.dumps(
            {"modules": [module_payload(1)]}
        )
        context_selection = ContextSelector(session=None).select_text(
            OUTLINE,
            "clean source context",
            retrieval_strategy="test",
        )

        modules = self.service._request_module_metadata_batch(
            session=SimpleNamespace(),
            user_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            context_selection=context_selection,
            curriculum_title="Generated curriculum",
            curriculum_overview="Overview",
            order_indices=[1],
            source_topics=source_topics(1),
            repair=False,
        )

        self.assertEqual(modules, [module_payload(1)])
        transaction_chat_mock.assert_called_once()
        call_llm_mock.assert_not_called()

    def test_rate_limit_stops_batch_repairs_and_returns_queued(self):
        requested_batches = []

        def request_batch(indices, repair):
            requested_batches.append((indices, repair))
            raise HTTPException(status_code=429, detail="queue_exceeded")

        result = self.service._run_module_metadata_batches(
            expected_modules=10,
            request_batch=request_batch,
            save_batch=lambda _modules: None,
        )

        self.assertEqual(
            result,
            {
                "saved_modules": 0,
                "missing_modules": list(range(1, 11)),
                "queued": True,
            },
        )
        self.assertEqual(requested_batches, [([1, 2, 3, 4, 5], False)])

    def test_quota_exceeded_stops_without_retry_or_repair(self):
        requested_batches = []

        def request_batch(indices, repair):
            requested_batches.append((indices, repair))
            raise HTTPException(status_code=403, detail="AI usage limit reached")

        result = self.service._run_module_metadata_batches(
            expected_modules=10,
            request_batch=request_batch,
            save_batch=lambda _modules: None,
        )

        self.assertEqual(
            result,
            {
                "saved_modules": 0,
                "missing_modules": list(range(1, 11)),
                "quota_exceeded": True,
            },
        )
        self.assertEqual(requested_batches, [([1, 2, 3, 4, 5], False)])

    @patch(
        "app.services.curriculum_generate.settings.PREMIUM_AI_FALLBACK_TO_GROQ_ENABLED",
        True,
    )
    def test_enabled_groq_fallback_reduces_curriculum_batch_size(self):
        requested_batches = []

        result = self.service._run_module_metadata_batches(
            expected_modules=5,
            request_batch=lambda indices, repair: (
                requested_batches.append((indices, repair))
                or [module_payload(index) for index in indices]
            ),
            save_batch=lambda _modules: None,
        )

        self.assertEqual(result, {"saved_modules": 5, "missing_modules": []})
        self.assertEqual(
            requested_batches,
            [([1, 2], False), ([3, 4], False), ([5], False)],
        )

    def test_hallucinated_module_title_is_removed(self):
        valid_modules = self.service._normalize_module_metadata_batch(
            raw_modules=[
                module_payload(1, title="Internet"),
                module_payload(2, title="SEO and Digital Marketing"),
            ],
            requested_order_indices=[1, 2],
            used_title_keys=set(),
            source_topics={
                1: SourceTopic(1, "1. Internet", ("material - chunk 1",)),
                2: SourceTopic(2, "2. Router", ("material - chunk 2",)),
            },
        )

        self.assertEqual([module["title"] for module in valid_modules], ["Internet"])
        self.assertEqual(valid_modules[0]["source_headings"], ["1. Internet"])
        self.assertEqual(valid_modules[0]["source_chunks"], ["material - chunk 1"])

    def test_source_topics_preserve_document_order_after_ranking(self):
        topics = self.service._extract_source_topics(
            "\n".join(
                [
                    "[guide - chunk 0]",
                    "1. Internet",
                    "1.1 World Wide Web",
                    "[guide - chunk 1]",
                    "2. Router",
                    "2.1 Subnet",
                ]
            )
        )

        selected = self.service._select_source_topics(topics, max_topics=4)

        self.assertEqual(
            [topic.heading for topic in selected],
            ["1. Internet", "1.1 World Wide Web", "2. Router", "2.1 Subnet"],
        )
        self.assertEqual(selected[2].source_chunks, ("guide - chunk 1",))


if __name__ == "__main__":
    unittest.main()
