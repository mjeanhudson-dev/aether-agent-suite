"""
Unit & Integration Tests for Aether Voice Bridge.
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess
from fastapi.testclient import TestClient

from voice_bridge.config import config
from voice_bridge.airlock import validate_voice_prompt, clean_for_tts
from voice_bridge.service import AgyExecutionService
from voice_bridge.server import app

class TestAirlock(unittest.TestCase):
    def test_benign_prompts_pass(self):
        prompts = [
            "What is the status of the repository?",
            "Run unit tests for the omnichorus engine.",
            "Write a python function to compute fibonacci numbers.",
            "Can you explain how the 1-Euro filter works in vibrant-darwin?"
        ]
        for p in prompts:
            is_safe, reason = validate_voice_prompt(p)
            self.assertTrue(is_safe, f"Benign prompt failed airlock: {p}")
            self.assertIsNone(reason)

    def test_destructive_patterns_blocked(self):
        hazardous = [
            "Please format C: right now",
            "Run rmdir /s on the directory",
            "del /f /s /q everything",
            "rm -rf / --no-preserve-root",
            "git reset --hard origin/main",
            "git clean -fdx",
            "drop database production_db",
            "drop table users",
            "shutdown /s /t 0",
            "Stop-Computer -Force"
        ]
        for h in hazardous:
            is_safe, reason = validate_voice_prompt(h)
            self.assertFalse(is_safe, f"Hazardous prompt escaped airlock: {h}")
            self.assertIn("Safety airlock triggered", reason)

    def test_tts_cleaning(self):
        markdown_text = (
            "### Analysis Complete\n\n"
            "Here is the result:\n"
            "```python\ndef test():\n    return 42\n```\n"
            "Use the `service.run()` method on [Documentation](https://example.com).\n"
            "The equation is $$E = mc^2$$ with **high** priority."
        )
        cleaned = clean_for_tts(markdown_text)
        self.assertNotIn("```", cleaned)
        self.assertNotIn("###", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("$$", cleaned)
        self.assertIn("[code block omitted]", cleaned)
        self.assertIn("service.run()", cleaned)
        self.assertIn("Documentation", cleaned)

class TestServerAuthAndEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.valid_token = config.SECRET_TOKEN

    def test_health_endpoint_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "aether-voice-bridge")

    def test_unauthorized_requests(self):
        # No header
        res1 = self.client.post("/antigravity/voice", json={"prompt": "hello"})
        self.assertEqual(res1.status_code, 401)

        # Invalid token
        res2 = self.client.post(
            "/antigravity/voice",
            json={"prompt": "hello"},
            headers={"X-Auth-Token": "wrong-token-value"}
        )
        self.assertEqual(res2.status_code, 401)

    def test_authorized_with_x_auth_token(self):
        with patch.object(AgyExecutionService, "run_prompt") as mock_run:
            mock_run.return_value = {"status": "ok", "reply": "Tests passed", "returncode": 0}
            response = self.client.post(
                "/antigravity/voice",
                json={"prompt": "Run unit tests"},
                headers={"X-Auth-Token": self.valid_token}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["reply"], "Tests passed")

    def test_authorized_with_bearer_token(self):
        with patch.object(AgyExecutionService, "run_prompt") as mock_run:
            mock_run.return_value = {"status": "ok", "reply": "Bridge online", "returncode": 0}
            response = self.client.get(
                "/antigravity/status",
                headers={"Authorization": f"Bearer {self.valid_token}"}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "online")

    def test_cli_compat_endpoint(self):
        with patch.object(AgyExecutionService, "run_prompt") as mock_run:
            mock_run.return_value = {"status": "ok", "reply": "Branch clean", "returncode": 0}
            response = self.client.post(
                "/antigravity/cli",
                json={"prompt": "git status", "continue_last": True},
                headers={"X-Auth-Token": self.valid_token}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")

    def test_airlock_blocks_execution_before_cli_invocation(self):
        service = AgyExecutionService()
        with patch("subprocess.run") as mock_sub:
            result = service.run_prompt("Please run rmdir /s on C:\\")
            self.assertEqual(result["status"], "blocked")
            self.assertIn("Safety airlock triggered", result["reply"])
            # Subprocess must never have been called!
            mock_sub.assert_not_called()

    def test_timeout_handling(self):
        service = AgyExecutionService()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["agy"], timeout=5)):
            result = service.run_prompt("Run long task", timeout_seconds=5)
            self.assertEqual(result["status"], "timeout")
            self.assertIn("timed out", result["reply"])
