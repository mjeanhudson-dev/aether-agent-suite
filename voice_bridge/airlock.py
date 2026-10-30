"""
Typed Semantic Airlock & Speech Pre-Compensator for Voice Bridge.
Guards against acoustic misrecognitions and optimizes text for mobile TTS playback.
"""

import re
from typing import Tuple

# Blacklist of catastrophic patterns that should never run from an unconfirmed voice utterance
DANGEROUS_PATTERNS = [
    r"\bformat\s+[a-zA-Z]:",             # format drive
    r"\brmdir(\.exe)?\s+.*(/[sS]|--recursive)\b", # windows recursive rmdir
    r"\bdel(\.exe)?\s+.*(/[sS]|/[fF]|/[qQ])",     # windows quiet/recursive wipe
    r"\brm\s+.*(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|--recursive)\b", # unix recursive wipe
    r"\bgit\s+reset\s+--hard\b",         # destructive uncommitted git loss
    r"\bgit\s+clean\s+-[a-zA-Z]*f",      # untracked wipe
    r"\bdrop\s+(database|table)\b",      # SQL database wipe
    r"\bshutdown(\.exe)?\s+/[sSrR]",     # system shutdown/reboot
    r"\b(Stop-Computer|Restart-Computer)\b", # powershell computer halt
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]

def validate_voice_prompt(prompt: str) -> Tuple[bool, str | None]:
    """
    Validates that a voice prompt does not contain catastrophic high-blast patterns.
    Returns (is_safe, refusal_reason).
    """
    clean = prompt.strip()
    if not clean:
        return False, "Prompt is empty."

    for pattern in COMPILED_PATTERNS:
        match = pattern.search(clean)
        if match:
            matched_phrase = match.group(0)
            return False, f"Safety airlock triggered. Destructive action pattern detected: '{matched_phrase}'. Request halted."

    return True, None

def clean_for_tts(raw_text: str, max_words: int = 150) -> str:
    """
    Cleans markdown and code formatting from agent replies so mobile TTS
    (Siri, Google Assistant, Tasker) can vocalize them smoothly without reading syntax.
    """
    if not raw_text:
        return "Task completed with no output."

    text = raw_text.strip()

    # Replace markdown fenced code blocks with audio summary
    text = re.sub(r"```[a-zA-Z0-9_-]*\n(.*?)```", " [code block omitted] ", text, flags=re.DOTALL)
    # Replace inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove markdown links, keep anchor text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove image links
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
    # Remove markdown header hashes
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold / italic markers
    text = re.sub(r"[*_]{1,3}", "", text)
    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Replace LaTeX math delimiters
    text = re.sub(r"\$\$([^\$]+)\$\$", r"\1", text)
    text = re.sub(r"\$([^\$]+)\$", r"\1", text)
    text = re.sub(r"\\\[(.*?)\\\]", r"\1", text)
    text = re.sub(r"\\\((.*?)\\\)", r"\1", text)
    # Collapse multiple newlines / spaces
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate if response is too long for comfortable spoken reading
    words = text.split()
    if len(words) > max_words:
        truncated = " ".join(words[:max_words])
        text = f"{truncated} ... (additional details truncated for voice. Check console for full response.)"

    return text
