"""
Execution service interfacing with the Antigravity headless CLI (agy).
"""

import subprocess
import os
from typing import Dict, Any
from .config import config
from .airlock import validate_voice_prompt, clean_for_tts

class AgyExecutionService:
    def __init__(self, agy_path: str = config.AGY_PATH):
        self.agy_path = agy_path

    def run_prompt(
        self,
        prompt: str,
        continue_last: bool = True,
        effort: str = "high",
        workspace_dir: str | None = None,
        timeout_seconds: int = config.DEFAULT_TIMEOUT
    ) -> Dict[str, Any]:
        """
        Executes a prompt through the Antigravity CLI and returns TTS-ready results.
        """
        # Step 1: Pass through Typed Semantic Airlock
        is_safe, refusal_reason = validate_voice_prompt(prompt)
        if not is_safe:
            return {
                "status": "blocked",
                "reply": refusal_reason,
                "raw_output": "",
                "returncode": -1
            }

        target_cwd = workspace_dir if (workspace_dir and os.path.exists(workspace_dir)) else config.DEFAULT_WORKSPACE

        # Step 2: Build agy command
        cmd = [self.agy_path, "-p", prompt.strip()]
        if continue_last:
            cmd.append("-c")
        if effort in {"low", "medium", "high", "xhigh", "max"}:
            cmd.extend(["--effort", effort])

        # Step 3: Run subprocess
        try:
            result = subprocess.run(
                cmd,
                cwd=target_cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False
            )
            raw_out = result.stdout.strip()
            raw_err = result.stderr.strip()

            if result.returncode != 0:
                error_msg = raw_err or raw_out or f"Process exited with code {result.returncode}"
                return {
                    "status": "error",
                    "reply": f"Antigravity reported an error: {clean_for_tts(error_msg, max_words=50)}",
                    "raw_output": error_msg,
                    "returncode": result.returncode
                }

            tts_reply = clean_for_tts(raw_out)
            return {
                "status": "ok",
                "reply": tts_reply,
                "raw_output": raw_out,
                "returncode": 0
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "reply": f"Command timed out after {timeout_seconds} seconds. The agent may still be running in the background.",
                "raw_output": "TimeoutExpired",
                "returncode": -2
            }
        except FileNotFoundError:
            return {
                "status": "error",
                "reply": f"Antigravity CLI not found at path: {self.agy_path}.",
                "raw_output": "FileNotFoundError",
                "returncode": -3
            }
        except Exception as ex:
            return {
                "status": "error",
                "reply": f"Unexpected execution error: {str(ex)}",
                "raw_output": str(ex),
                "returncode": -4
            }

service = AgyExecutionService()
