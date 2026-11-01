"""Unit tests for Aether Context Caching Engine."""

import os
import unittest
from unittest.mock import MagicMock, patch

from context_caching.context_cache import (
    DEFAULT_ADC_LOCATION,
    DEFAULT_ADC_PROJECT,
    DEFAULT_MODEL,
    create_context_cache,
    get_genai_client,
    query_cached_content,
)


class TestAetherContextCache(unittest.TestCase):
    def test_client_api_key_mode(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-mock-key"}, clear=True):
            with patch("google.genai.Client") as mock_client:
                get_genai_client()
                mock_client.assert_called_once_with(api_key="test-mock-key")

    def test_client_vertex_adc_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("google.genai.Client") as mock_client:
                get_genai_client()
                mock_client.assert_called_once_with(
                    vertexai=True,
                    project=DEFAULT_ADC_PROJECT,
                    location=DEFAULT_ADC_LOCATION,
                )

    def test_create_cache_parameters(self):
        mock_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache.name = "cachedContents/test-12345"
        mock_cache.expire_time = "2026-10-31T18:00:00Z"
        mock_client.caches.create.return_value = mock_cache

        res = create_context_cache(
            blueprint_text="Blueprint content",
            model_id="gemini-2.5-pro",
            ttl="1800s",
            client=mock_client,
        )

        self.assertEqual(res.name, "cachedContents/test-12345")
        mock_client.caches.create.assert_called_once()
        call_kwargs = mock_client.caches.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "gemini-2.5-pro")

    def test_query_cached_content_parameters(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Routing layer verified."
        mock_client.models.generate_content.return_value = mock_response

        res = query_cached_content(
            cache_name="cachedContents/test-12345",
            prompt="Analyze routing layer.",
            model_id="gemini-2.5-pro",
            temperature=0.5,
            client=mock_client,
        )

        self.assertEqual(res.text, "Routing layer verified.")
        mock_client.models.generate_content.assert_called_once()


if __name__ == "__main__":
    unittest.main()
