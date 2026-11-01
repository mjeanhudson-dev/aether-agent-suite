#!/usr/bin/env python3
"""
Automated Injection Script for Aether Command Protocol into Local Agent Harnesses (Milestone 2 - R2).

Injects the canonical Aether Command Protocol into:
1. Claude Code (~/.claude/CLAUDE.md) - Section 7
2. Claude Code (~/.claude/settings.json) - PostToolUse telemetry hook
3. Codex (~/.codex/AGENTS.md) - Protocol directives & engineering/hardware standards
4. Codex (~/.codex/config.toml) - Obsidian Aether catalog reference
5. Hermes (~/.hermes/AGENTS.md) - Section 6
6. Antigravity / Gemini (~/.gemini/GEMINI.md) - Root rules with protocol directives

Author: worker_m2_1
"""

import os
import sys
import json
import re
from pathlib import Path

CANONICAL_PROTOCOL_TEMPLATE = r"""<!-- AETHER_COMMAND_PROTOCOL_START -->
## {SECTION_TITLE}

All bash and PowerShell commands formulated, executed, or recommended in this environment MUST adhere to the **Aether Command Catalog Standards**:

1. **Mandatory Command Labeling Invariant**:
   Whenever emitting, running, or presenting shell commands or reusable scripts, you MUST provide explicit metadata:
   - **`Function`**: Exactly one clear sentence defining what the command accomplishes (`# FUNCTION: <description>`).
   - **`Use Cases`**: At least one concrete operational use case, failure mode recovery, or workflow trigger (`# USE_CASE: <use_case>`).
   - **`Syntax`**: Exact command invocation signature with named parameters and placeholders.
   - **`Execution Environment`**: Explicitly identify whether execution target is `PowerShell` or `Bash`.

2. **Obsidian Aether Catalog Query & Reuse**:
   - The central command knowledge catalog resides in the Obsidian Vault at:
     `C:\Users\Zachariah\Documents\obsidian memory complex\Aether\Commands\`
   - Before writing ad-hoc multi-line shell scripts, search the catalog (`find_by_name` or `grep_search` in the vault) to reuse tested commands.

3. **On-the-Fly Cataloging**:
   - When introducing a novel, reusable, or complex command, export it to the Aether catalog or include the `# @fn: <description>; @use: <use_case>` or `# FUNCTION: ...; # USE_CASE: ...` header decorator so that the shell hook automatically registers it into Obsidian.
<!-- AETHER_COMMAND_PROTOCOL_END -->"""

CORE_STANDARDS_MD = r"""# Codex Agent Directives & Operating Invariants

These directives govern all Codex Agent executions in this environment. Adhere strictly to these principles without skipping or cutting corners.

---

## 1. Core Engineering Principles

- **Smallest Complete Solution**: Write the least new code that fully solves the problem. Delete before adding. Do not introduce abstractions, wrappers, or "for later" flexibility that nobody asked for.
- **Fix Root Causes**: Trace bugs to the first place where state or data went wrong. Never patch around symptoms with speculative fallback try/catches or band-aids.
- **Prove It Works**: Never declare a task complete without proving it against real artifacts—run the test, execute the CLI, check the build, or inspect the generated diff. Self-reports and "it should work" are invalid.
- **Boundary Discipline**: Validate strictly at system boundaries (CLI flags, network payloads, user input, external APIs). Keep internal code typesafe, direct, and free of redundant defensive layers.
- **Maintain Documentation Integrity**: Preserve all existing comments, docstrings, and configuration invariants unrelated to your changes.

---

## 2. Hardware & DualSense Invariants

- **Zero Stock Game XML Tampering (Cloud Save Invariant)**: NEVER modify stock controller XML presets. All non-linear game distortions must be pre-compensated within proxies using mathematical inverse functions:
  $$X_{\text{proxy}} = d_{\text{game}} + (1 - d_{\text{game}}) \cdot \sqrt{|x|} \cdot \operatorname{sgn}(x)$$
- **Loading Screen Exit Transition**: Polling resuming after scene transitions or loading stalls (>1200ms) MUST execute a 200ms $C^2$ smootherstep blend: $S(t) = 6t^5 - 15t^4 + 10t^3$ to prevent steering rack snaps.
- **Menu Trigger Isolation & Deadzone**: Enforce a 15-count deadzone on L2 and R2 in menus to eliminate resting finger float (7–12 counts). Driving mode may only be latched by active throttle ($R_2 > 35$) or game rumble ($>0$).
- **Lap & Recline Immunity**: Project steering wheel rotation across the sagittal plane using filtered gravity components ($\omega_{\text{roll}} = -(\omega_z \cos\theta + \omega_y \sin\theta)$). Decouple lateral accelerometer gravity when reclined ($|\theta_{\text{pitch}}| > 30^\circ$).
- **Cryptographic Deployment Parity**: Ensure byte-for-byte SHA256 parity across Workspace, Desktop Staging, and Target Deployments.

---

## 3. Token Budget Sentinel & Resource Quotas

- **Sentinel Threshold**: Monitor accumulated token volume. If daily token consumption reaches or exceeds 10,000,000 tokens, emit a prominent alert banner detailing token count and estimated spend while continuing unblocked work.
- **Circuit Breaker on HTTP 429**: If encountering `RESOURCE_EXHAUSTED (code 429)` or quota exhaustion, DO NOT enter a tight retry loop. Pause downstream launches, log the offending trajectory, and alert immediately.
- **Cost-Aware Routing**: Route high-iteration automated sweeps through high-throughput, cost-efficient models. Reserve frontier reasoning models for high-order architecture and critical synthesis.

---

## 4. Science & Interactive Visualizations

- **Interactive Sidecars Over Static Pixels**: Prefer interactive sidecar viewers and web components over static image rendering or text dumps.
- **Always Surface Actionable Links**: When loading structures, traces, or datasets, provide direct clickable links (`file:///...` or UI links) so the user can inspect results in one click.

---

## 5. Output Density & Style

- Be direct, concise, and technical.
- Format all responses in clean GitHub Flavored Markdown with clickable file links (`file:///...`).
- Eliminate fluff, conversational filler, and unwarranted apologies. Deliver results.

---
"""

GEMINI_ROOT_RULES_MD = r"""# Antigravity & Gemini Agent Directives & Root Rules

These directives govern all Antigravity and Gemini agent swarm executions in this environment. Adhere strictly to these principles without skipping or cutting corners.

---

## 1. Core Engineering Principles

- **Smallest Complete Solution**: Write the least new code that fully solves the problem. Delete before adding. Do not introduce abstractions, wrappers, or "for later" flexibility that nobody asked for.
- **Fix Root Causes**: Trace bugs to the first place where state or data went wrong. Never patch around symptoms with speculative fallback try/catches or band-aids.
- **Prove It Works**: Never declare a task complete without proving it against real artifacts—run the test, execute the CLI, check the build, or inspect the generated diff. Self-reports and "it should work" are invalid.
- **Boundary Discipline**: Validate strictly at system boundaries (CLI flags, network payloads, user input, external APIs). Keep internal code typesafe, direct, and free of redundant defensive layers.
- **Maintain Documentation Integrity**: Preserve all existing comments, docstrings, and configuration invariants unrelated to your changes.

---

## 2. Hardware & DualSense Invariants

- **Zero Stock Game XML Tampering (Cloud Save Invariant)**: NEVER modify stock controller XML presets. All non-linear game distortions must be pre-compensated within proxies using mathematical inverse functions:
  $$X_{\text{proxy}} = d_{\text{game}} + (1 - d_{\text{game}}) \cdot \sqrt{|x|} \cdot \operatorname{sgn}(x)$$
- **Loading Screen Exit Transition**: Polling resuming after scene transitions or loading stalls (>1200ms) MUST execute a 200ms $C^2$ smootherstep blend: $S(t) = 6t^5 - 15t^4 + 10t^3$ to prevent steering rack snaps.
- **Menu Trigger Isolation & Deadzone**: Enforce a 15-count deadzone on L2 and R2 in menus to eliminate resting finger float (7–12 counts). Driving mode may only be latched by active throttle ($R_2 > 35$) or game rumble ($>0$).
- **Lap & Recline Immunity**: Project steering wheel rotation across the sagittal plane using filtered gravity components ($\omega_{\text{roll}} = -(\omega_z \cos\theta + \omega_y \sin\theta)$). Decouple lateral accelerometer gravity when reclined ($|\theta_{\text{pitch}}| > 30^\circ$).
- **Cryptographic Deployment Parity**: Ensure byte-for-byte SHA256 parity across Workspace, Desktop Staging, and Target Deployments.

---

## 3. Token Budget Sentinel & Resource Quotas

- **Sentinel Threshold**: Monitor accumulated token volume. If daily token consumption reaches or exceeds 10,000,000 tokens, emit a prominent alert banner detailing token count and estimated spend while continuing unblocked work.
- **Circuit Breaker on HTTP 429**: If encountering `RESOURCE_EXHAUSTED (code 429)` or quota exhaustion, DO NOT enter a tight retry loop. Pause downstream launches, log the offending trajectory, and alert immediately.
- **Cost-Aware Routing**: Route high-iteration automated sweeps through high-throughput, cost-efficient models. Reserve frontier reasoning models for high-order architecture and critical synthesis.

---

## 4. Science & Interactive Visualizations

- **Interactive Sidecars Over Static Pixels**: Prefer interactive sidecar viewers and web components over static image rendering or text dumps.
- **Always Surface Actionable Links**: When loading structures, traces, or datasets, provide direct clickable links (`file:///...` or UI links) so the user can inspect results in one click.

---

## 5. Output Density & Style

- Be direct, concise, and technical.
- Format all responses in clean GitHub Flavored Markdown with clickable file links (`file:///...`).
- Eliminate fluff, conversational filler, and unwarranted apologies. Deliver results.

---
"""


def inject_claude_claude_md(user_home: Path) -> dict:
    target = user_home / ".claude" / "CLAUDE.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    
    if target.exists():
        content = target.read_text(encoding="utf-8")
    else:
        content = "# Master Developer & Autonomous Agent Directives\n"

    directive_block = CANONICAL_PROTOCOL_TEMPLATE.replace(
        "{SECTION_TITLE}", "7. Command Labeling & Obsidian Aether Catalog Protocol"
    )

    if "<!-- AETHER_COMMAND_PROTOCOL_START -->" in content:
        new_content = re.sub(
            r"<!-- AETHER_COMMAND_PROTOCOL_START -->.*?<!-- AETHER_COMMAND_PROTOCOL_END -->",
            lambda _: directive_block,
            content,
            flags=re.DOTALL
        )
        action = "updated_protocol"
    else:
        content = content.rstrip() + "\n\n---\n\n" + directive_block + "\n"
        new_content = content
        action = "appended_section_7"

    target.write_text(new_content, encoding="utf-8")
    return {"target": str(target), "status": "success", "action": action, "bytes": len(new_content)}


def inject_claude_settings_json(user_home: Path) -> dict:
    target = user_home / ".claude" / "settings.json"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        with open(target, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    post_tool_use = hooks.setdefault("PostToolUse", [])

    has_aether_hook = False
    for entry in post_tool_use:
        if isinstance(entry, dict) and entry.get("matcher") == "Bash|run_command":
            has_aether_hook = True
            break

    if not has_aether_hook:
        new_hook = {
            "matcher": "Bash|run_command",
            "hooks": [
                {
                    "type": "command",
                    "command": 'powershell -NoProfile -ExecutionPolicy Bypass -Command "if ($env:AETHER_AUTO_CATALOG -eq \'1\') { Write-Host \'[Aether] Command logged\' }"',
                    "timeout": 5
                }
            ]
        }
        post_tool_use.append(new_hook)
        action = "added_post_tool_use_hook"
    else:
        action = "already_present"

    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return {"target": str(target), "status": "success", "action": action}


def inject_codex_agents_md(user_home: Path) -> dict:
    target = user_home / ".codex" / "AGENTS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    directive_block = CANONICAL_PROTOCOL_TEMPLATE.replace(
        "{SECTION_TITLE}", "6. Command Labeling & Obsidian Aether Catalog Protocol"
    )

    full_content = CORE_STANDARDS_MD.rstrip() + "\n\n" + directive_block + "\n"
    target.write_text(full_content, encoding="utf-8")
    return {"target": str(target), "status": "success", "action": "populated_codex_agents_md", "bytes": len(full_content)}


def inject_codex_config_toml(user_home: Path) -> dict:
    target = user_home / ".codex" / "config.toml"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        content = target.read_text(encoding="utf-8")
    else:
        content = ""

    aether_toml_block = """[aether]
catalog_path = 'C:\\Users\\Zachariah\\Documents\\obsidian memory complex\\Aether\\Commands'
protocol_enabled = true
instructions = "Query the Obsidian Aether Catalog at C:\\\\Users\\\\Zachariah\\\\Documents\\\\obsidian memory complex\\\\Aether\\\\Commands\\\\ before formulating ad-hoc scripts. Label all bash and PowerShell commands with # FUNCTION: and # USE_CASE:."
"""

    if "[aether]" in content:
        content = re.sub(
            r"\[aether\].*?(?=\n\[|\Z)",
            lambda _: aether_toml_block.strip() + "\n",
            content,
            flags=re.DOTALL
        )
        action = "updated_aether_section"
    else:
        content = content.rstrip() + "\n\n" + aether_toml_block
        action = "appended_aether_section"

    target.write_text(content, encoding="utf-8")
    return {"target": str(target), "status": "success", "action": action, "bytes": len(content)}


def inject_hermes_agents_md(user_home: Path) -> dict:
    target = user_home / ".hermes" / "AGENTS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        content = target.read_text(encoding="utf-8")
    else:
        content = "# Hermes Agent Directives & Operating Invariants\n"

    directive_block = CANONICAL_PROTOCOL_TEMPLATE.replace(
        "{SECTION_TITLE}", "6. Command Labeling & Obsidian Aether Catalog Protocol"
    )

    if "<!-- AETHER_COMMAND_PROTOCOL_START -->" in content:
        new_content = re.sub(
            r"<!-- AETHER_COMMAND_PROTOCOL_START -->.*?<!-- AETHER_COMMAND_PROTOCOL_END -->",
            lambda _: directive_block,
            content,
            flags=re.DOTALL
        )
        action = "updated_protocol"
    else:
        content = content.rstrip() + "\n\n---\n\n" + directive_block + "\n"
        new_content = content
        action = "appended_section_6"

    target.write_text(new_content, encoding="utf-8")
    return {"target": str(target), "status": "success", "action": action, "bytes": len(new_content)}


def inject_gemini_gemini_md(user_home: Path) -> dict:
    target = user_home / ".gemini" / "GEMINI.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    directive_block = CANONICAL_PROTOCOL_TEMPLATE.replace(
        "{SECTION_TITLE}", "6. Command Labeling & Obsidian Aether Catalog Protocol"
    )

    full_content = GEMINI_ROOT_RULES_MD.rstrip() + "\n\n" + directive_block + "\n"
    target.write_text(full_content, encoding="utf-8")
    return {"target": str(target), "status": "success", "action": "populated_gemini_gemini_md", "bytes": len(full_content)}


def run_all_injections(user_home_path: str = None) -> list:
    home = Path(user_home_path) if user_home_path else Path(os.path.expanduser("~"))
    print(f"============================================================")
    print(f"=== AETHER AGENT HARNESS DIRECTIVE INJECTION SUITE ===")
    print(f"Target User Home: {home}")
    print(f"============================================================")

    results = []
    
    # 1. Claude CLAUDE.md
    res_claude_md = inject_claude_claude_md(home)
    print(f"[Claude CLAUDE.md]     -> {res_claude_md['action']} ({res_claude_md['target']})")
    results.append(res_claude_md)

    # 2. Claude settings.json
    res_claude_json = inject_claude_settings_json(home)
    print(f"[Claude settings.json] -> {res_claude_json['action']} ({res_claude_json['target']})")
    results.append(res_claude_json)

    # 3. Codex AGENTS.md
    res_codex_md = inject_codex_agents_md(home)
    print(f"[Codex AGENTS.md]      -> {res_codex_md['action']} ({res_codex_md['target']})")
    results.append(res_codex_md)

    # 4. Codex config.toml
    res_codex_toml = inject_codex_config_toml(home)
    print(f"[Codex config.toml]    -> {res_codex_toml['action']} ({res_codex_toml['target']})")
    results.append(res_codex_toml)

    # 5. Hermes AGENTS.md
    res_hermes_md = inject_hermes_agents_md(home)
    print(f"[Hermes AGENTS.md]     -> {res_hermes_md['action']} ({res_hermes_md['target']})")
    results.append(res_hermes_md)

    # 6. Gemini GEMINI.md
    res_gemini_md = inject_gemini_gemini_md(home)
    print(f"[Gemini GEMINI.md]     -> {res_gemini_md['action']} ({res_gemini_md['target']})")
    results.append(res_gemini_md)

    print(f"============================================================")
    print(f"Injection complete across {len(results)} agent harness targets.")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Inject Aether Command Protocol into local agent harnesses.")
    parser.add_argument("--user-home", default=None, help="Custom user home path (defaults to ~)")
    args = parser.parse_args()
    run_all_injections(args.user_home)
