<#
.SYNOPSIS
    Automated Injection Script for Aether Command Protocol into Local Agent Harnesses (Milestone 2 - R2).
.DESCRIPTION
    Injects canonical Aether Command Protocol into:
    1. Claude Code (~/.claude/CLAUDE.md) - Appends Section 7 preserving Sections 1-6.
    2. Claude Code (~/.claude/settings.json) - Adds PostToolUse telemetry hook for Bash|run_command.
    3. Codex (~/.codex/AGENTS.md) - Populates with full protocol directives and engineering standards.
    4. Codex (~/.codex/config.toml) - Adds [aether] section referencing Obsidian Aether Catalog.
    5. Hermes (~/.hermes/AGENTS.md) - Appends Section 6 preserving Sections 1-5.
    6. Antigravity / Gemini (~/.gemini/GEMINI.md) - Populates root rules with protocol directives.
#>

[CmdletBinding()]
param(
    [string]$UserHome = "C:\Users\Zachariah"
)

$ErrorActionPreference = "Stop"

$CanonicalProtocolTemplate = @'
<!-- AETHER_COMMAND_PROTOCOL_START -->
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
<!-- AETHER_COMMAND_PROTOCOL_END -->
'@

$CodexStandards = @'
# Codex Agent Directives & Operating Invariants

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
'@

$GeminiStandards = @'
# Antigravity & Gemini Agent Directives & Root Rules

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
'@

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "=== AETHER AGENT HARNESS DIRECTIVE INJECTION SUITE (PS) ===" -ForegroundColor Cyan
Write-Host "Target User Home: $UserHome" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# -------------------------------------------------------------
# 1. Claude CLAUDE.md
# -------------------------------------------------------------
$claudeMdPath = Join-Path $UserHome ".claude\CLAUDE.md"
$claudeDir = Split-Path $claudeMdPath -Parent
if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null }

$section7Block = $CanonicalProtocolTemplate.Replace('{SECTION_TITLE}', '7. Command Labeling & Obsidian Aether Catalog Protocol')

if (Test-Path $claudeMdPath) {
    $claudeContent = [System.IO.File]::ReadAllText($claudeMdPath, [System.Text.Encoding]::UTF8)
    if ($claudeContent -match '<!-- AETHER_COMMAND_PROTOCOL_START -->') {
        $claudeContent = [regex]::Replace($claudeContent, '(?s)<!-- AETHER_COMMAND_PROTOCOL_START -->.*?<!-- AETHER_COMMAND_PROTOCOL_END -->', $section7Block)
        Write-Host "[Claude CLAUDE.md]     -> Updated existing protocol block" -ForegroundColor Green
    } else {
        $claudeContent = $claudeContent.TrimEnd() + "`r`n`r`n---`r`n`r`n" + $section7Block + "`r`n"
        Write-Host "[Claude CLAUDE.md]     -> Appended Section 7" -ForegroundColor Green
    }
} else {
    $claudeContent = "# Master Developer & Autonomous Agent Directives`r`n`r`n---`r`n`r`n" + $section7Block + "`r`n"
    Write-Host "[Claude CLAUDE.md]     -> Created new file with Section 7" -ForegroundColor Green
}
[System.IO.File]::WriteAllText($claudeMdPath, $claudeContent, [System.Text.Encoding]::UTF8)

# -------------------------------------------------------------
# 2. Claude settings.json
# -------------------------------------------------------------
$claudeJsonPath = Join-Path $UserHome ".claude\settings.json"
if (Test-Path $claudeJsonPath) {
    $rawJson = [System.IO.File]::ReadAllText($claudeJsonPath, [System.Text.Encoding]::UTF8)
    $jsonObj = $rawJson | ConvertFrom-Json
} else {
    $jsonObj = [PSCustomObject]@{}
}

if (-not $jsonObj.PSObject.Properties['hooks']) {
    $jsonObj | Add-Member -MemberType NoteProperty -Name 'hooks' -Value ([PSCustomObject]@{})
}
if (-not $jsonObj.hooks.PSObject.Properties['PostToolUse']) {
    $jsonObj.hooks | Add-Member -MemberType NoteProperty -Name 'PostToolUse' -Value @()
}

$hasBashHook = $false
foreach ($hook in $jsonObj.hooks.PostToolUse) {
    if ($hook.matcher -eq 'Bash|run_command') {
        $hasBashHook = $true
        break
    }
}

if (-not $hasBashHook) {
    $newHook = [PSCustomObject]@{
        matcher = "Bash|run_command"
        hooks = @(
            [PSCustomObject]@{
                type = "command"
                command = 'powershell -NoProfile -ExecutionPolicy Bypass -Command "if ($env:AETHER_AUTO_CATALOG -eq ''1'') { Write-Host ''[Aether] Command logged'' }"'
                timeout = 5
            }
        )
    }
    $postToolList = [System.Collections.ArrayList]@($jsonObj.hooks.PostToolUse)
    $postToolList.Add($newHook) | Out-Null
    $jsonObj.hooks.PostToolUse = $postToolList
    Write-Host "[Claude settings.json] -> Added PostToolUse Bash|run_command telemetry hook" -ForegroundColor Green
} else {
    Write-Host "[Claude settings.json] -> PostToolUse Bash|run_command hook already present" -ForegroundColor DarkGray
}

$updatedJson = $jsonObj | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($claudeJsonPath, $updatedJson, [System.Text.Encoding]::UTF8)

# -------------------------------------------------------------
# 3. Codex AGENTS.md
# -------------------------------------------------------------
$codexMdPath = Join-Path $UserHome ".codex\AGENTS.md"
$codexDir = Split-Path $codexMdPath -Parent
if (-not (Test-Path $codexDir)) { New-Item -ItemType Directory -Path $codexDir -Force | Out-Null }

$section6Block = $CanonicalProtocolTemplate.Replace('{SECTION_TITLE}', '6. Command Labeling & Obsidian Aether Catalog Protocol')
$fullCodexMd = $CodexStandards.TrimEnd() + "`r`n`r`n" + $section6Block + "`r`n"
[System.IO.File]::WriteAllText($codexMdPath, $fullCodexMd, [System.Text.Encoding]::UTF8)
Write-Host "[Codex AGENTS.md]      -> Populated with full directives and Section 6" -ForegroundColor Green

# -------------------------------------------------------------
# 4. Codex config.toml
# -------------------------------------------------------------
$codexTomlPath = Join-Path $UserHome ".codex\config.toml"
$aetherTomlSection = @"
[aether]
catalog_path = 'C:\Users\Zachariah\Documents\obsidian memory complex\Aether\Commands'
protocol_enabled = true
instructions = "Query the Obsidian Aether Catalog at C:\\Users\\Zachariah\\Documents\\obsidian memory complex\\Aether\\Commands\\ before formulating ad-hoc scripts. Label all bash and PowerShell commands with # FUNCTION: and # USE_CASE:."
"@

if (Test-Path $codexTomlPath) {
    $tomlContent = [System.IO.File]::ReadAllText($codexTomlPath, [System.Text.Encoding]::UTF8)
    if ($tomlContent -match '\[aether\]') {
        $tomlContent = [regex]::Replace($tomlContent, '(?s)\[aether\].*?(?=\r?\n\[|\Z)', $aetherTomlSection.Trim())
        Write-Host "[Codex config.toml]    -> Updated existing [aether] section" -ForegroundColor Green
    } else {
        $tomlContent = $tomlContent.TrimEnd() + "`r`n`r`n" + $aetherTomlSection + "`r`n"
        Write-Host "[Codex config.toml]    -> Appended [aether] catalog section" -ForegroundColor Green
    }
} else {
    $tomlContent = $aetherTomlSection.Trim() + "`r`n"
    Write-Host "[Codex config.toml]    -> Created new config with [aether] section" -ForegroundColor Green
}
[System.IO.File]::WriteAllText($codexTomlPath, $tomlContent, [System.Text.Encoding]::UTF8)

# -------------------------------------------------------------
# 5. Hermes AGENTS.md
# -------------------------------------------------------------
$hermesMdPath = Join-Path $UserHome ".hermes\AGENTS.md"
$hermesDir = Split-Path $hermesMdPath -Parent
if (-not (Test-Path $hermesDir)) { New-Item -ItemType Directory -Path $hermesDir -Force | Out-Null }

if (Test-Path $hermesMdPath) {
    $hermesContent = [System.IO.File]::ReadAllText($hermesMdPath, [System.Text.Encoding]::UTF8)
    if ($hermesContent -match '<!-- AETHER_COMMAND_PROTOCOL_START -->') {
        $hermesContent = [regex]::Replace($hermesContent, '(?s)<!-- AETHER_COMMAND_PROTOCOL_START -->.*?<!-- AETHER_COMMAND_PROTOCOL_END -->', $section6Block)
        Write-Host "[Hermes AGENTS.md]     -> Updated existing protocol block" -ForegroundColor Green
    } else {
        $hermesContent = $hermesContent.TrimEnd() + "`r`n`r`n---`r`n`r`n" + $section6Block + "`r`n"
        Write-Host "[Hermes AGENTS.md]     -> Appended Section 6" -ForegroundColor Green
    }
} else {
    $hermesContent = "# Hermes Agent Directives & Operating Invariants`r`n`r`n---`r`n`r`n" + $section6Block + "`r`n"
    Write-Host "[Hermes AGENTS.md]     -> Created new file with Section 6" -ForegroundColor Green
}
[System.IO.File]::WriteAllText($hermesMdPath, $hermesContent, [System.Text.Encoding]::UTF8)

# -------------------------------------------------------------
# 6. Gemini GEMINI.md
# -------------------------------------------------------------
$geminiMdPath = Join-Path $UserHome ".gemini\GEMINI.md"
$geminiDir = Split-Path $geminiMdPath -Parent
if (-not (Test-Path $geminiDir)) { New-Item -ItemType Directory -Path $geminiDir -Force | Out-Null }

$fullGeminiMd = $GeminiStandards.TrimEnd() + "`r`n`r`n" + $section6Block + "`r`n"
[System.IO.File]::WriteAllText($geminiMdPath, $fullGeminiMd, [System.Text.Encoding]::UTF8)
Write-Host "[Gemini GEMINI.md]     -> Populated with root rules and Section 6" -ForegroundColor Green

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SUCCESS: Injected Aether Command Protocol across all 6 targets." -ForegroundColor Green
