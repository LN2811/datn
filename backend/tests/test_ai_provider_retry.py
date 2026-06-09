import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from openai import RateLimitError
from groq import RateLimitError as GroqRateLimitError

from app.services.ai_service import call_llm
from app.services.ai_provider_client import (
    AIProviderClient,
    AIProviderRateLimitError,
    AIProviderResponse,
    AIProviderService,
)
from app.services.ai_transaction import AITransactionService
from app.services.context_selector import ContextSelector, OUTLINE


class AIProviderRetryTests(unittest.TestCase):
    @staticmethod
    def _rate_limit_error(code: str = "queue_exceeded") -> RateLimitError:
        response = Mock(status_code=429, headers={})
        response.request = Mock()
        return RateLimitError(
            "provider busy",
            response=response,
            body={"error": {"code": code}},
        )

    @staticmethod
    def _groq_rate_limit_error(code: str = "rate_limit_exceeded") -> GroqRateLimitError:
        response = Mock(status_code=429, headers={})
        response.request = Mock()
        return GroqRateLimitError(
            "provider busy",
            response=response,
            body={"error": {"code": code}},
        )

    @patch("app.services.ai_provider_client.time.sleep")
    @patch("app.services.ai_provider_client.OpenAI")
    def test_rate_limit_uses_bounded_exponential_backoff(
        self,
        openai_mock,
        sleep_mock,
    ):
        openai_mock.return_value.chat.completions.create.side_effect = [
            self._rate_limit_error(),
            self._rate_limit_error(),
            self._rate_limit_error(),
            self._rate_limit_error(),
        ]
        selection = ContextSelector(session=None).select_text(
            OUTLINE,
            "safe context",
            retrieval_strategy="test",
        )

        with self.assertLogs("uvicorn.error", level="WARNING") as logs:
            with self.assertRaises(AIProviderRateLimitError) as raised:
                AIProviderService.chat(
                    AIProviderClient(
                        provider="cerebras",
                        api_key="test-key",
                        base_url="https://example.test/v1",
                        model="test-model",
                    ),
                    [{"role": "user", "content": "prompt"}],
                    context_selection=selection,
                )

        self.assertEqual(sleep_mock.call_args_list, [call(10), call(30), call(60)])
        self.assertEqual(
            openai_mock.return_value.chat.completions.create.call_count,
            4,
        )
        self.assertEqual(raised.exception.error_code, "queue_exceeded")
        log_text = "\n".join(logs.output)
        self.assertIn("provider=cerebras", log_text)
        self.assertIn("model=test-model", log_text)
        self.assertIn("attempt=3", log_text)
        self.assertIn("wait_seconds=60", log_text)
        self.assertIn("error_code=queue_exceeded", log_text)

    @patch("app.services.ai_provider_client.time.sleep")
    @patch("app.services.ai_provider_client.OpenAI")
    def test_rate_limit_retry_returns_success_when_provider_recovers(
        self,
        openai_mock,
        sleep_mock,
    ):
        response = SimpleNamespace(
            usage=SimpleNamespace(total_tokens=12),
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            model="test-model",
        )
        openai_mock.return_value.chat.completions.create.side_effect = [
            self._rate_limit_error("rate_limit"),
            response,
        ]
        selection = ContextSelector(session=None).select_text(
            OUTLINE,
            "safe context",
            retrieval_strategy="test",
        )

        result = AIProviderService.chat(
            AIProviderClient(
                provider="cerebras",
                api_key="test-key",
                base_url="https://example.test/v1",
                model="test-model",
            ),
            [{"role": "user", "content": "prompt"}],
            context_selection=selection,
        )

        self.assertEqual(result.content, "ok")
        sleep_mock.assert_called_once_with(10)

    @patch("app.services.ai_transaction.settings.GROQ_MAX_TOKENS", 10)
    @patch("app.services.ai_transaction.AIProviderService.chat")
    @patch("app.services.ai_transaction.AITransactionService._get_groq_config")
    def test_groq_fallback_trims_context_before_request(
        self,
        get_groq_config_mock,
        provider_chat_mock,
    ):
        get_groq_config_mock.return_value = AIProviderClient(
            provider="groq",
            api_key="test-key",
            base_url="https://example.test/v1",
            model="groq-model",
        )
        provider_chat_mock.return_value = AIProviderResponse(content="ok")
        selection = ContextSelector(session=None).select_text(
            OUTLINE,
            "source-context " * 100,
            retrieval_strategy="test",
        )

        AITransactionService._chat_with_groq_fallback(
            messages=[{"role": "user", "content": f"SOURCE:\n{selection.text}"}],
            response_format=None,
            temperature=0.1,
            max_completion_tokens=100,
            context_selection=selection,
        )

        fallback_selection = provider_chat_mock.call_args.kwargs["context_selection"]
        fallback_messages = provider_chat_mock.call_args.args[1]
        self.assertLessEqual(fallback_selection.estimated_tokens, 10)
        self.assertNotEqual(fallback_selection.text, selection.text)
        self.assertIn(fallback_selection.text, fallback_messages[0]["content"])
        self.assertNotIn(selection.text, fallback_messages[0]["content"])

    @patch("app.services.ai_service.time.sleep")
    @patch("app.services.ai_service._get_client")
    def test_legacy_groq_gateway_uses_same_bounded_backoff(
        self,
        get_client_mock,
        sleep_mock,
    ):
        get_client_mock.return_value.chat.completions.create.side_effect = [
            self._groq_rate_limit_error(),
            self._groq_rate_limit_error(),
            self._groq_rate_limit_error(),
            self._groq_rate_limit_error(),
        ]
        selection = ContextSelector(session=None).select_text(
            OUTLINE,
            "safe context",
            retrieval_strategy="test",
        )

        with self.assertRaises(AIProviderRateLimitError):
            call_llm("prompt", context_selection=selection)

        self.assertEqual(sleep_mock.call_args_list, [call(10), call(30), call(60)])
        self.assertEqual(
            get_client_mock.return_value.chat.completions.create.call_count,
            4,
        )


if __name__ == "__main__":
    unittest.main()
