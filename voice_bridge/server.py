"""
FastAPI Server for Aether Voice & Mobile Quick-Button Bridge.
"""

import secrets
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import config
from .service import service

app = FastAPI(
    title="Aether Mobile Voice Bridge",
    description="Bridge mobile hardware buttons and voice dictation into Google Antigravity CLI",
    version="1.0.0"
)

# Enable CORS for local cross-origin webhook testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VoiceRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000, description="Voice transcription text")
    continue_last: bool = Field(True, description="Continue the most recent conversation turn")
    effort: str = Field("high", description="Reasoning effort: low|medium|high|xhigh|max")
    workspace_dir: Optional[str] = Field(None, description="Target workspace directory")

class CliCompatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    continue_last: bool = Field(True)

def verify_auth_token(
    x_auth_token: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Enforce constant-time cryptographic verification of inbound auth tokens.
    Supports either 'X-Auth-Token: <token>' or 'Authorization: Bearer <token>'.
    """
    provided_token = None
    if x_auth_token:
        provided_token = x_auth_token.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided_token = authorization[7:].strip()

    if not provided_token or not secrets.compare_digest(provided_token, config.SECRET_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing or invalid authentication token"
        )
    return True

@app.get("/health")
def health_check():
    """Health and status endpoint."""
    return {
        "status": "healthy",
        "service": "aether-voice-bridge",
        "agy_path": config.AGY_PATH,
        "workspace": config.DEFAULT_WORKSPACE
    }

@app.get("/antigravity/status", dependencies=[Depends(verify_auth_token)])
def bridge_status():
    """Protected status verification endpoint."""
    return {
        "status": "online",
        "agy_path": config.AGY_PATH,
        "default_workspace": config.DEFAULT_WORKSPACE,
        "timeout_seconds": config.DEFAULT_TIMEOUT
    }

@app.post("/antigravity/voice", dependencies=[Depends(verify_auth_token)])
def execute_voice_command(payload: VoiceRequest):
    """
    Primary endpoint for iOS Action Button and Android Side Key dictation.
    Returns TTS-optimized reply and execution status.
    """
    result = service.run_prompt(
        prompt=payload.prompt,
        continue_last=payload.continue_last,
        effort=payload.effort,
        workspace_dir=payload.workspace_dir
    )
    return result

@app.post("/antigravity/cli", dependencies=[Depends(verify_auth_token)])
def execute_cli_compat(payload: CliCompatRequest):
    """
    Compatibility endpoint matching standard webhook schema.
    """
    result = service.run_prompt(
        prompt=payload.prompt,
        continue_last=payload.continue_last,
        effort="high"
    )
    return result
