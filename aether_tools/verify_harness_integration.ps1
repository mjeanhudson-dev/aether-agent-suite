<#
.SYNOPSIS
    Automated Verification Suite for Local Agent Harness Integration (Milestone 2 - R2).
.DESCRIPTION
    Verifies:
    1. Target agent harness files exist:
       - ~/.claude/CLAUDE.md
       - ~/.claude/settings.json
       - ~/.codex/AGENTS.md
       - ~/.codex/config.toml
       - ~/.hermes/AGENTS.md
       - ~/.gemini/GEMINI.md
    2. Syntactic validity (valid JSON for settings.json, valid TOML for config.toml, valid Markdown for *.md).
    3. Mandatory protocol directives and required tokens:
       - AETHER_COMMAND_PROTOCOL_START / END
       - Function description requirement (# FUNCTION:)
       - Use cases requirement (# USE_CASE:)
       - Syntax and Execution Environment (PowerShell & Bash)
       - Obsidian Aether Catalog lookup directive (C:\Users\Zachariah\Documents\obsidian memory complex\Aether\Commands\)
       - On-the-fly export instructions
       - Preservation of pre-existing sections (Sections 1-6 in Claude, Sections 1-5 in Hermes)
       - PostToolUse telemetry hook in Claude settings.json

    Asserts 100% pass rate. Exits with code 0 on success, code 1 on failure.
#>

[CmdletBinding()]
param(
    [string]$UserHome = "C:\Users\Zachariah"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "=== AETHER HARNESS INTEGRATION VERIFICATION SUITE (PS) ===" -ForegroundColor Cyan
Write-Host "Target User Home: $UserHome" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$TotalTargets = 6
$PassedTargets = 0
$Failures = @()

function Assert-ProtocolTokens {
    param(
        [string]$Content,
        [string]$TargetName
    )
    $errors = @()
    if ($Content -notmatch '<!-- AETHER_COMMAND_PROTOCOL_START -->') { $errors += "$TargetName missing AETHER_COMMAND_PROTOCOL_START marker" }
    if ($Content -notmatch '<!-- AETHER_COMMAND_PROTOCOL_END -->') { $errors += "$TargetName missing AETHER_COMMAND_PROTOCOL_END marker" }
    if ($Content -notmatch 'Command Labeling & Obsidian Aether Catalog Protocol') { $errors += "$TargetName missing protocol header" }
    if ($Content -notmatch 'Function.*# FUNCTION:') { $errors += "$TargetName missing Function requirement (# FUNCTION:)" }
    if ($Content -notmatch 'Use Cases?.*# USE_CASE:') { $errors += "$TargetName missing Use Cases requirement (# USE_CASE:)" }
    if ($Content -notmatch '\bSyntax\b') { $errors += "$TargetName missing Syntax requirement" }
    if ($Content -notmatch 'Execution Environment') { $errors += "$TargetName missing Execution Environment requirement" }
    if ($Content -notmatch 'PowerShell' -or $Content -notmatch 'Bash') { $errors += "$TargetName missing PowerShell/Bash environment specification" }
    if ($Content -notmatch 'Obsidian.*Vault|obsidian memory complex') { $errors += "$TargetName missing Obsidian Vault reference" }
    if ($Content -notmatch 'Aether[\\/]Commands') { $errors += "$TargetName missing Aether Commands path reference" }
    if ($Content -notmatch 'On-the-Fly Cataloging|# @fn:') { $errors += "$TargetName missing on-the-fly export instructions" }
    return $errors
}

# -------------------------------------------------------------
# 1. Claude CLAUDE.md
# -------------------------------------------------------------
$claudeMdPath = Join-Path $UserHome ".claude\CLAUDE.md"
$claudeMdPassed = $true
$claudeMdErrors = @()

if (-not (Test-Path $claudeMdPath)) {
    $claudeMdPassed = $false
    $claudeMdErrors += "File does not exist: $claudeMdPath"
} else {
    $content = [System.IO.File]::ReadAllText($claudeMdPath, [System.Text.Encoding]::UTF8)
    for ($i = 1; $i -le 6; $i++) {
        if ($content -notmatch "(?m)^##\s*$i\.\s+") {
            $claudeMdErrors += "Missing preserved Section $i in CLAUDE.md"
        }
    }
    if ($content -notmatch "(?m)^##\s*7\.\s+Command Labeling & Obsidian Aether Catalog Protocol") {
        $claudeMdErrors += "Missing Section 7 in CLAUDE.md"
    }
    $tokenErrors = Assert-ProtocolTokens -Content $content -TargetName "CLAUDE.md"
    $claudeMdErrors += $tokenErrors
    if ($claudeMdErrors.Count -gt 0) { $claudeMdPassed = $false }
}

if ($claudeMdPassed) {
    Write-Host "  [ PASS ] Claude Code Directives    -> $claudeMdPath" -ForegroundColor Green
    $PassedTargets++
} else {
    Write-Host "  [ FAIL ] Claude Code Directives    -> $claudeMdPath" -ForegroundColor Red
    foreach ($err in $claudeMdErrors) { Write-Host "         ERROR: $err" -ForegroundColor Red; $Failures += "Claude Directives: $err" }
}

# -------------------------------------------------------------
# 2. Claude settings.json
# -------------------------------------------------------------
$claudeJsonPath = Join-Path $UserHome ".claude\settings.json"
$claudeJsonPassed = $true
$claudeJsonErrors = @()

if (-not (Test-Path $claudeJsonPath)) {
    $claudeJsonPassed = $false
    $claudeJsonErrors += "File does not exist: $claudeJsonPath"
} else {
    try {
        $jsonContent = [System.IO.File]::ReadAllText($claudeJsonPath, [System.Text.Encoding]::UTF8)
        $jsonObj = $jsonContent | ConvertFrom-Json
        $hasBashHook = $false
        if ($jsonObj.hooks -and $jsonObj.hooks.PostToolUse) {
            foreach ($entry in $jsonObj.hooks.PostToolUse) {
                if ($entry.matcher -eq 'Bash|run_command') {
                    $hasBashHook = $true
                    break
                }
            }
        }
        if (-not $hasBashHook) {
            $claudeJsonErrors += "Missing PostToolUse telemetry hook for 'Bash|run_command'"
            $claudeJsonPassed = $false
        }
    } catch {
        $claudeJsonErrors += "Failed to parse JSON syntax: $_"
        $claudeJsonPassed = $false
    }
}

if ($claudeJsonPassed) {
    Write-Host "  [ PASS ] Claude Code Settings      -> $claudeJsonPath" -ForegroundColor Green
    $PassedTargets++
} else {
    Write-Host "  [ FAIL ] Claude Code Settings      -> $claudeJsonPath" -ForegroundColor Red
    foreach ($err in $claudeJsonErrors) { Write-Host "         ERROR: $err" -ForegroundColor Red; $Failures += "Claude Settings: $err" }
}

# -------------------------------------------------------------
# 3. Codex AGENTS.md
# -------------------------------------------------------------
$codexMdPath = Join-Path $UserHome ".codex\AGENTS.md"
$codexMdPassed = $true
$codexMdErrors = @()

if (-not (Test-Path $codexMdPath)) {
    $codexMdPassed = $false
    $codexMdErrors += "File does not exist: $codexMdPath"
} else {
    $content = [System.IO.File]::ReadAllText($codexMdPath, [System.Text.Encoding]::UTF8)
    if ($content.Trim().Length -lt 100) { $codexMdErrors += "Codex AGENTS.md is empty or too short" }
    if ($content -notmatch 'Core Engineering Principles') { $codexMdErrors += "Codex AGENTS.md missing Core Engineering Principles" }
    if ($content -notmatch 'Hardware & DualSense Invariants') { $codexMdErrors += "Codex AGENTS.md missing Hardware & DualSense Invariants" }
    $tokenErrors = Assert-ProtocolTokens -Content $content -TargetName "Codex AGENTS.md"
    $codexMdErrors += $tokenErrors
    if ($codexMdErrors.Count -gt 0) { $codexMdPassed = $false }
}

if ($codexMdPassed) {
    Write-Host "  [ PASS ] Codex Directives          -> $codexMdPath" -ForegroundColor Green
    $PassedTargets++
} else {
    Write-Host "  [ FAIL ] Codex Directives          -> $codexMdPath" -ForegroundColor Red
    foreach ($err in $codexMdErrors) { Write-Host "         ERROR: $err" -ForegroundColor Red; $Failures += "Codex Directives: $err" }
}

# -------------------------------------------------------------
# 4. Codex config.toml
# -------------------------------------------------------------
$codexTomlPath = Join-Path $UserHome ".codex\config.toml"
$codexTomlPassed = $true
$codexTomlErrors = @()

if (-not (Test-Path $codexTomlPath)) {
    $codexTomlPassed = $false
    $codexTomlErrors += "File does not exist: $codexTomlPath"
} else {
    $content = [System.IO.File]::ReadAllText($codexTomlPath, [System.Text.Encoding]::UTF8)
    if ($content -notmatch '\[aether\]') { $codexTomlErrors += "Missing [aether] section" }
    if ($content -notmatch 'catalog_path\s*=.*Aether[\\/]Commands') { $codexTomlErrors += "Missing catalog_path referencing Obsidian Aether Commands" }
    if ($content -notmatch 'instructions\s*=.*Obsidian.*Aether.*Catalog') { $codexTomlErrors += "Missing instructions referencing Obsidian Aether Catalog" }
    if ($codexTomlErrors.Count -gt 0) { $codexTomlPassed = $false }
}

if ($codexTomlPassed) {
    Write-Host "  [ PASS ] Codex Configuration       -> $codexTomlPath" -ForegroundColor Green
    $PassedTargets++
} else {
    Write-Host "  [ FAIL ] Codex Configuration       -> $codexTomlPath" -ForegroundColor Red
    foreach ($err in $codexTomlErrors) { Write-Host "         ERROR: $err" -ForegroundColor Red; $Failures += "Codex Configuration: $err" }
}

# -------------------------------------------------------------
# 5. Hermes AGENTS.md
# -------------------------------------------------------------
$hermesMdPath = Join-Path $UserHome ".hermes\AGENTS.md"
$hermesMdPassed = $true
$hermesMdErrors = @()

if (-not (Test-Path $hermesMdPath)) {
    $hermesMdPassed = $false
    $hermesMdErrors += "File does not exist: $hermesMdPath"
} else {
    $content = [System.IO.File]::ReadAllText($hermesMdPath, [System.Text.Encoding]::UTF8)
    for ($i = 1; $i -le 5; $i++) {
        if ($content -notmatch "(?m)^##\s*$i\.\s+") {
            $hermesMdErrors += "Missing preserved Section $i in Hermes AGENTS.md"
        }
    }
    if ($content -notmatch "(?m)^##\s*6\.\s+Command Labeling & Obsidian Aether Catalog Protocol") {
        $hermesMdErrors += "Missing Section 6 in Hermes AGENTS.md"
    }
    $tokenErrors = Assert-ProtocolTokens -Content $content -TargetName "Hermes AGENTS.md"
    $hermesMdErrors += $tokenErrors
    if ($hermesMdErrors.Count -gt 0) { $hermesMdPassed = $false }
}

if ($hermesMdPassed) {
    Write-Host "  [ PASS ] Hermes Directives         -> $hermesMdPath" -ForegroundColor Green
    $PassedTargets++
} else {
    Write-Host "  [ FAIL ] Hermes Directives         -> $hermesMdPath" -ForegroundColor Red
    foreach ($err in $hermesMdErrors) { Write-Host "         ERROR: $err" -ForegroundColor Red; $Failures += "Hermes Directives: $err" }
}

# -------------------------------------------------------------
# 6. Gemini GEMINI.md
# -------------------------------------------------------------
$geminiMdPath = Join-Path $UserHome ".gemini\GEMINI.md"
$geminiMdPassed = $true
$geminiMdErrors = @()

if (-not (Test-Path $geminiMdPath)) {
    $geminiMdPassed = $false
    $geminiMdErrors += "File does not exist: $geminiMdPath"
} else {
    $content = [System.IO.File]::ReadAllText($geminiMdPath, [System.Text.Encoding]::UTF8)
    if ($content.Trim().Length -lt 100) { $geminiMdErrors += "GEMINI.md is empty or too short" }
    if ($content -notmatch 'Core Engineering Principles') { $geminiMdErrors += "GEMINI.md missing Core Engineering Principles" }
    if ($content -notmatch 'Hardware & DualSense Invariants') { $geminiMdErrors += "GEMINI.md missing Hardware & DualSense Invariants" }
    $tokenErrors = Assert-ProtocolTokens -Content $content -TargetName "GEMINI.md"
    $geminiMdErrors += $tokenErrors
    if ($geminiMdErrors.Count -gt 0) { $geminiMdPassed = $false }
}

if ($geminiMdPassed) {
    Write-Host "  [ PASS ] Antigravity/Gemini Rules  -> $geminiMdPath" -ForegroundColor Green
    $PassedTargets++
} else {
    Write-Host "  [ FAIL ] Antigravity/Gemini Rules  -> $geminiMdPath" -ForegroundColor Red
    foreach ($err in $geminiMdErrors) { Write-Host "         ERROR: $err" -ForegroundColor Red; $Failures += "Gemini Directives: $err" }
}

# -------------------------------------------------------------
# Summary
# -------------------------------------------------------------
$passRate = [math]::Round(($PassedTargets / $TotalTargets) * 100.0, 1)

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SUMMARY:" -ForegroundColor Cyan
Write-Host "  Total Harness Targets: $TotalTargets" -ForegroundColor Yellow
Write-Host "  Passed Checks:         $PassedTargets ($passRate%)" -ForegroundColor $(if ($passRate -eq 100) { 'Green' } else { 'Yellow' })
Write-Host "  Failed Checks:         $($Failures.Count)" -ForegroundColor $(if ($Failures.Count -eq 0) { 'Green' } else { 'Red' })
Write-Host "============================================================" -ForegroundColor Cyan

if ($passRate -eq 100) {
    Write-Host "`nSUCCESS: 100% of target agent harness files exist, are syntactically valid," -ForegroundColor Green
    Write-Host "and contain the full canonical Aether Command Protocol directives with zero errors!`n" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nFAILURE: $($Failures.Count) issues detected in agent harness configurations.`n" -ForegroundColor Red
    exit 1
}
