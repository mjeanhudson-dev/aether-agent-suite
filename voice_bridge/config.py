"""
Configuration and token security manager for Aether Voice Bridge.
"""

import os
import secrets
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / ".token"

def get_or_create_token() -> str:
    """Retrieve existing token or generate a persistent 48-char cryptographic secret."""
    env_token = os.environ.get("ANTIGRAVITY_VOICE_TOKEN")
    if env_token:
        return env_token.strip()

    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            return token

    # Generate new persistent cryptographically secure token
    new_token = secrets.token_hex(24)
    TOKEN_FILE.write_text(new_token, encoding="utf-8")
    return new_token

class BridgeConfig:
    HOST: str = os.environ.get("BRIDGE_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("BRIDGE_PORT", "8844"))
    SECRET_TOKEN: str = get_or_create_token()
    DEFAULT_WORKSPACE: str = str(BASE_DIR.parent)
    DEFAULT_TIMEOUT: int = int(os.environ.get("BRIDGE_TIMEOUT", "120"))

    # Auto-detect agy executable
    _agy_path = shutil.which("agy") or shutil.which("agy.exe")
    if not _agy_path:
        default_local = Path.home() / "AppData" / "Local" / "agy" / "bin" / "agy.exe"
        if default_local.exists():
            _agy_path = str(default_local)
        else:
            _agy_path = "agy"
    AGY_PATH: str = _agy_path

config = BridgeConfig()
