import json
import unittest
from unittest.mock import patch

from app import triage


class ValidateResultTests(unittest.TestCase):
    def test_accepts_valid_result(self):
        result = {
            "category": "other",
            "priority": "low",
            "summary": "The customer asks about account features.",
            "confidence": 0.9,
            "fallback": False,
        }
        self.assertEqual(triage.validate_result(json.dumps(result)), result)

    def test_rejects_missing_field(self):
        with self.assertRaises(ValueError):
            triage.validate_result('{"category":"other"}')

    def test_rejects_boolean_confidence(self):
        result = {
            "category": "other",
            "priority": "low",
            "summary": "",
            "confidence": True,
            "fallback": False,
        }
        with self.assertRaises(ValueError):
            triage.validate_result(json.dumps(result))

    def test_rejects_summary_over_200_characters(self):
        result = {
            "category": "other",
            "priority": "low",
            "summary": "x" * 201,
            "confidence": 0.9,
            "fallback": False,
        }
        with self.assertRaises(ValueError):
            triage.validate_result(json.dumps(result))


class ClassifyTests(unittest.TestCase):
    @patch.object(triage, "request_completion")
    @patch.object(triage, "PROMPT_PATH")
    def test_retries_invalid_json_then_returns_valid_result(self, prompt_path, request):
        prompt_path.read_text.return_value = "system prompt"
        result = {
            "category": "other",
            "priority": "low",
            "summary": "A general question.",
            "confidence": 0.8,
            "fallback": False,
        }
        request.side_effect = ["not json", json.dumps(result)]

        self.assertEqual(triage.classify("How does this work?"), result)
        self.assertEqual(request.call_count, 2)

    @patch.object(triage, "request_completion", side_effect=triage.ProviderError("offline"))
    @patch.object(triage, "PROMPT_PATH")
    def test_returns_fallback_after_provider_failure(self, prompt_path, _request):
        prompt_path.read_text.return_value = "system prompt"
        with patch("sys.stderr"):
            result = triage.classify("I need help.")

        self.assertEqual(result, triage.FALLBACK_RESULT)


if __name__ == "__main__":
    unittest.main()
