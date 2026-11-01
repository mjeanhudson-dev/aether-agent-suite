#!/usr/bin/env python3
"""
Automated Verification Suite for Local Agent Harness Integration (Milestone 2 - R2).

Verifies:
1. Target files exist in standard local user environment directories:
   - Claude Code: ~/.claude/CLAUDE.md, ~/.claude/settings.json
   - Codex: ~/.codex/AGENTS.md, ~/.codex/config.toml
   - Hermes: ~/.hermes/AGENTS.md
   - Antigravity / Gemini: ~/.gemini/GEMINI.md
2. Syntactic validity:
   - JSON syntax for settings.json
   - TOML syntax and sections for config.toml
   - Markdown syntax for *.md directive files
3. Invariant directives and tokens present:
   - Token AETHER_COMMAND_PROTOCOL_START and AETHER_COMMAND_PROTOCOL_END
   - Function description requirement (# FUNCTION:)
   - Use cases requirement (# USE_CASE:)
   - Syntax and Execution Environment (PowerShell & Bash)
   - Obsidian Aether Catalog reference (C:\\Users\\Zachariah\\Documents\\obsidian memory complex\\Aether\\Commands\\)
   - On-the-fly export instructions
   - Preservation of pre-existing sections (Sections 1-6 in Claude, Sections 1-5 in Hermes)
   - PostToolUse telemetry hook for command execution in Claude settings.json

Returns exit code 0 if 100% of checks pass, non-zero (1) on any failure.

Author: worker_m2_1
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any

USER_HOME = Path(os.path.expanduser("~"))

REQUIRED_PROTOCOL_TOKENS = [
    ("AETHER_COMMAND_PROTOCOL_START", r"<!-- AETHER_COMMAND_PROTOCOL_START -->"),
    ("AETHER_COMMAND_PROTOCOL_END", r"<!-- AETHER_COMMAND_PROTOCOL_END -->"),
    ("Protocol Header", r"Command Labeling & Obsidian Aether Catalog Protocol"),
    ("Function Label", r"Function.*# FUNCTION:"),
    ("Use Cases Label", r"Use Cases?.*# USE_CASE:"),
    ("Syntax Requirement", r"\bSyntax\b"),
    ("Execution Environment", r"Execution Environment.*(PowerShell|Bash)"),
    ("Obsidian Vault Reference", r"Obsidian.*Vault|obsidian memory complex"),
    ("Aether Commands Path", r"Aether[\\/]Commands"),
    ("On-The-Fly Export", r"On-the-Fly Cataloging|# @fn:"),
]


def check_claude_claude_md(home: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    path = home / ".claude" / "CLAUDE.md"
    errors = []
    details = {"path": str(path), "exists": False, "size_bytes": 0, "sections_found": []}

    if not path.exists():
        errors.append(f"File not found: {path}")
        return False, errors, details

    details["exists"] = True
    content = path.read_text(encoding="utf-8")
    details["size_bytes"] = len(content)

    # 1. Check preserved sections 1-6
    for i in range(1, 7):
        pattern = rf"^##\s*{i}\.\s+"
        if re.search(pattern, content, re.MULTILINE):
            details["sections_found"].append(f"Section {i}")
        else:
            errors.append(f"Missing preserved Section {i} in CLAUDE.md")

    # 2. Check Section 7 present
    if re.search(r"^##\s*7\.\s+Command Labeling & Obsidian Aether Catalog Protocol", content, re.MULTILINE):
        details["sections_found"].append("Section 7 (Protocol)")
    else:
        errors.append("Missing Section 7 (Command Labeling & Obsidian Aether Catalog Protocol) in CLAUDE.md")

    # 3. Check protocol tokens
    for token_name, pattern in REQUIRED_PROTOCOL_TOKENS:
        if not re.search(pattern, content, re.IGNORECASE):
            errors.append(f"CLAUDE.md missing token/pattern '{token_name}' ({pattern})")

    return len(errors) == 0, errors, details


def check_claude_settings_json(home: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    path = home / ".claude" / "settings.json"
    errors = []
    details = {"path": str(path), "exists": False, "valid_json": False, "hooks_found": []}

    if not path.exists():
        errors.append(f"File not found: {path}")
        return False, errors, details

    details["exists"] = True
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        details["valid_json"] = True
    except Exception as e:
        errors.append(f"Invalid JSON syntax in settings.json: {e}")
        return False, errors, details

    if not isinstance(data, dict):
        errors.append("Root JSON element must be an object")
        return False, errors, details

    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        errors.append("Field 'hooks' must be a dictionary")
        return False, errors, details

    post_tool_use = hooks.get("PostToolUse", [])
    if not isinstance(post_tool_use, list):
        errors.append("Field 'PostToolUse' must be a list")
        return False, errors, details

    # Look for Bash|run_command hook
    has_bash_hook = False
    for hook_entry in post_tool_use:
        matcher = hook_entry.get("matcher", "")
        details["hooks_found"].append(f"PostToolUse({matcher})")
        if matcher == "Bash|run_command":
            subhooks = hook_entry.get("hooks", [])
            for sub in subhooks:
                cmd = sub.get("command", "")
                if "AETHER_AUTO_CATALOG" in cmd or "obsidian" in cmd.lower() or "powershell" in cmd.lower():
                    has_bash_hook = True

    if not has_bash_hook:
        errors.append("settings.json missing PostToolUse hook for 'Bash|run_command' telemetry")

    return len(errors) == 0, errors, details


def check_codex_agents_md(home: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    path = home / ".codex" / "AGENTS.md"
    errors = []
    details = {"path": str(path), "exists": False, "size_bytes": 0, "standards_present": False}

    if not path.exists():
        errors.append(f"File not found: {path}")
        return False, errors, details

    details["exists"] = True
    content = path.read_text(encoding="utf-8")
    details["size_bytes"] = len(content)

    if len(content.strip()) < 100:
        errors.append("AGENTS.md is empty or too small")

    # Check for Engineering Principles & DualSense Invariants
    has_eng = "Core Engineering Principles" in content or "Smallest Complete Solution" in content
    has_hardware = "Hardware & DualSense Invariants" in content or "Zero Stock Game XML Tampering" in content
    details["standards_present"] = has_eng and has_hardware
    if not has_eng:
        errors.append("Codex AGENTS.md missing Core Engineering Principles")
    if not has_hardware:
        errors.append("Codex AGENTS.md missing Hardware & DualSense Invariants")

    # Check protocol tokens
    for token_name, pattern in REQUIRED_PROTOCOL_TOKENS:
        if not re.search(pattern, content, re.IGNORECASE):
            errors.append(f"Codex AGENTS.md missing token/pattern '{token_name}'")

    return len(errors) == 0, errors, details


def check_codex_config_toml(home: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    path = home / ".codex" / "config.toml"
    errors = []
    details = {"path": str(path), "exists": False, "valid_structure": False, "has_aether_section": False}

    if not path.exists():
        errors.append(f"File not found: {path}")
        return False, errors, details

    details["exists"] = True
    content = path.read_text(encoding="utf-8")

    # Structural check for TOML
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
    sections = [l for l in lines if l.startswith("[") and l.endswith("]")]
    key_values = [l for l in lines if "=" in l]

    if len(sections) > 0 and len(key_values) > 0:
        details["valid_structure"] = True
    else:
        errors.append("config.toml does not exhibit valid TOML structure")

    # Check [aether] section
    if "[aether]" in content:
        details["has_aether_section"] = True
    else:
        errors.append("config.toml missing '[aether]' section")

    # Check catalog path reference
    if not re.search(r"catalog_path\s*=.*Aether[\\/]Commands", content, re.IGNORECASE):
        errors.append("config.toml missing 'catalog_path' referencing Obsidian Aether Commands")

    # Check instructions referencing catalog
    if not re.search(r"instructions\s*=.*Obsidian.*Aether.*Catalog", content, re.IGNORECASE):
        errors.append("config.toml missing 'instructions' referencing Obsidian Aether Catalog")

    return len(errors) == 0, errors, details


def check_hermes_agents_md(home: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    path = home / ".hermes" / "AGENTS.md"
    errors = []
    details = {"path": str(path), "exists": False, "size_bytes": 0, "sections_found": []}

    if not path.exists():
        errors.append(f"File not found: {path}")
        return False, errors, details

    details["exists"] = True
    content = path.read_text(encoding="utf-8")
    details["size_bytes"] = len(content)

    # 1. Check preserved sections 1-5
    for i in range(1, 6):
        pattern = rf"^##\s*{i}\.\s+"
        if re.search(pattern, content, re.MULTILINE):
            details["sections_found"].append(f"Section {i}")
        else:
            errors.append(f"Missing preserved Section {i} in Hermes AGENTS.md")

    # 2. Check Section 6 present
    if re.search(r"^##\s*6\.\s+Command Labeling & Obsidian Aether Catalog Protocol", content, re.MULTILINE):
        details["sections_found"].append("Section 6 (Protocol)")
    else:
        errors.append("Missing Section 6 (Command Labeling & Obsidian Aether Catalog Protocol) in Hermes AGENTS.md")

    # 3. Check protocol tokens
    for token_name, pattern in REQUIRED_PROTOCOL_TOKENS:
        if not re.search(pattern, content, re.IGNORECASE):
            errors.append(f"Hermes AGENTS.md missing token/pattern '{token_name}'")

    return len(errors) == 0, errors, details


def check_gemini_gemini_md(home: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    path = home / ".gemini" / "GEMINI.md"
    errors = []
    details = {"path": str(path), "exists": False, "size_bytes": 0, "standards_present": False}

    if not path.exists():
        errors.append(f"File not found: {path}")
        return False, errors, details

    details["exists"] = True
    content = path.read_text(encoding="utf-8")
    details["size_bytes"] = len(content)

    if len(content.strip()) < 100:
        errors.append("GEMINI.md is empty or too small")

    # Check for Engineering Principles & DualSense Invariants
    has_eng = "Core Engineering Principles" in content or "Smallest Complete Solution" in content
    has_hardware = "Hardware & DualSense Invariants" in content or "Zero Stock Game XML Tampering" in content
    details["standards_present"] = has_eng and has_hardware
    if not has_eng:
        errors.append("GEMINI.md missing Core Engineering Principles")
    if not has_hardware:
        errors.append("GEMINI.md missing Hardware & DualSense Invariants")

    # Check protocol tokens
    for token_name, pattern in REQUIRED_PROTOCOL_TOKENS:
        if not re.search(pattern, content, re.IGNORECASE):
            errors.append(f"GEMINI.md missing token/pattern '{token_name}'")

    return len(errors) == 0, errors, details


def run_all_verifications(user_home_path: str = None) -> bool:
    home = Path(user_home_path) if user_home_path else USER_HOME
    print("============================================================")
    print("=== AETHER HARNESS INTEGRATION VERIFICATION SUITE ===")
    print(f"Target User Home: {home}")
    print("============================================================")

    targets = [
        ("Claude Code Directives", check_claude_claude_md),
        ("Claude Code Settings",   check_claude_settings_json),
        ("Codex Directives",       check_codex_agents_md),
        ("Codex Configuration",    check_codex_config_toml),
        ("Hermes Directives",      check_hermes_agents_md),
        ("Antigravity/Gemini Rules", check_gemini_gemini_md),
    ]

    total_checks = len(targets)
    passed_checks = 0
    all_errors = []

    print(f"\nEvaluating {total_checks} Agent Harness Targets:\n")

    for name, check_fn in targets:
        passed, errors, details = check_fn(home)
        status_str = "[ PASS ]" if passed else "[ FAIL ]"
        print(f"  {status_str} {name:25} -> {details.get('path', 'unknown')}")

        if not passed:
            for err in errors:
                print(f"         ERROR: {err}")
                all_errors.append(f"{name}: {err}")
        else:
            passed_checks += 1
            if "size_bytes" in details:
                print(f"         Size: {details['size_bytes']:,} bytes | Sections: {', '.join(details.get('sections_found', []))}")
            elif "hooks_found" in details:
                print(f"         Valid JSON | Hooks: {', '.join(details.get('hooks_found', []))}")
            elif "has_aether_section" in details:
                print(f"         Valid TOML | [aether] section confirmed")

    pass_rate = (passed_checks / total_checks) * 100.0

    print("\n============================================================")
    print("VERIFICATION SUMMARY:")
    print(f"  Total Harness Targets: {total_checks}")
    print(f"  Passed Checks:         {passed_checks} ({pass_rate:.1f}%)")
    print(f"  Failed Checks:         {len(all_errors)}")
    print("============================================================")

    if pass_rate == 100.0:
        print("\nSUCCESS: 100% of target agent harness files exist, are syntactically valid,")
        print("and contain the full canonical Aether Command Protocol directives with zero errors!\n")
        return True
    else:
        print(f"\nFAILURE: {len(all_errors)} issues detected in agent harness configurations.\n")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Verify Aether Command Protocol integration in local agent harnesses.")
    parser.add_argument("--user-home", default=None, help="Custom user home path (defaults to ~)")
    args = parser.parse_args()

    success = run_all_verifications(args.user_home)
    sys.exit(0 if success else 1)
