<#
.SYNOPSIS
    Automated verification suite for the Obsidian Aether Command Catalog (PowerShell implementation).
.DESCRIPTION
    Validates that 100% of command notes in the Obsidian Aether Catalog contain valid frontmatter,
    non-empty function/description, non-empty use_cases array (>= 1), syntax, and valid execution environment.
#>

[CmdletBinding()]
param(
    [string]$VaultPath = "C:\Users\Zachariah\Documents\obsidian memory complex"
)

$commandsDir = Join-Path $VaultPath "Aether\Commands"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "=== AETHER CATALOG AUTOMATED VALIDATION SUITE (PS) ===" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target Directory: $commandsDir" -ForegroundColor Yellow

if (-not (Test-Path $commandsDir)) {
    Write-Error "Commands directory does not exist: $commandsDir"
    exit 1
}

$notes = Get-ChildItem -Path $commandsDir -Filter "*.md" -Recurse -File
Write-Host "Found $($notes.Count) catalog notes to validate.`n" -ForegroundColor Yellow

if ($notes.Count -eq 0) {
    Write-Error "Zero command notes found in catalog."
    exit 1
}

$passed = 0
$failed = 0
$failures = @()

foreach ($note in $notes) {
    $relPath = $note.FullName.Substring($commandsDir.Length).TrimStart('\', '/')
    $content = Get-Content -Path $note.FullName -Raw -ErrorAction SilentlyContinue

    if (-not ($content -match '(?s)^---\r?\n(.*?)\r?\n---')) {
        $failed++
        $failures += "$relPath : Missing YAML frontmatter delimiters"
        Write-Host "  [FAIL] $relPath (Missing YAML delimiters)" -ForegroundColor Red
        continue
    }

    $fm = $matches[1]
    $errs = @()

    # Check id
    if (-not ($fm -match '(?m)^id:\s*["'']?(cmd-(bash|powershell|pwsh|sh|cmd)-[a-z0-9_.-]+)["'']?')) {
        $errs += "Invalid or missing 'id'"
    }

    # Check function/description (non-empty, >= 5 chars)
    if ($fm -match '(?m)^(?:description|function):\s*["'']?(.+?)["'']?$') {
        $fnVal = $matches[1].Trim()
        if ($fnVal.Length -lt 5) {
            $errs += "Function/description too short (< 5 chars)"
        }
    } else {
        $errs += "Missing 'description' or 'function'"
    }

    # Check use_cases (must have at least 1 non-empty item)
    if ($fm -match '(?s)use_cases:\s*\r?\n((?:\s*-\s*.+\r?\n?)+)') {
        $ucLines = @($matches[1] -split "`r?`n" | Where-Object { $_.Trim().StartsWith('-') })
        if ($ucLines.Count -lt 1) {
            $errs += "use_cases array is empty"
        }
    } else {
        $errs += "Missing 'use_cases' array"
    }

    # Check syntax
    if (-not ($fm -match '(?m)^syntax:\s*["'']?(.+?)["'']?$')) {
        $errs += "Missing or empty 'syntax'"
    }

    # Check execution_environment
    if (-not ($fm -match '(?m)^execution_environment:\s*["'']?(powershell|pwsh|bash|sh|cmd)["'']?$')) {
        $errs += "Missing or invalid 'execution_environment'"
    }

    # Check catalog and type
    if (-not ($fm -match '(?m)^catalog:\s*["'']?aether["'']?$')) {
        $errs += "Missing or invalid 'catalog' (must be 'aether')"
    }
    if (-not ($fm -match '(?m)^type:\s*["'']?command-catalog["'']?$')) {
        $errs += "Missing or invalid 'type' (must be 'command-catalog')"
    }

    # Check timestamps
    if (-not ($fm -match 'created:') -or -not ($fm -match 'updated:')) {
        $errs += "Missing timestamps (created/updated)"
    }

    if ($errs.Count -eq 0) {
        $passed++
        Write-Host "  [PASS] $relPath" -ForegroundColor Green
    } else {
        $failed++
        $failures += "$relPath : $($errs -join '; ')"
        Write-Host "  [FAIL] $relPath -> $($errs -join ', ')" -ForegroundColor Red
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "VALIDATION SUMMARY:" -ForegroundColor Cyan
Write-Host "  Total Notes Scanned: $($notes.Count)"
Write-Host "  Passed:              $passed ($([math]::Round($passed / $notes.Count * 100, 1))%)"
Write-Host "  Failed:              $failed"
Write-Host "==========================================================" -ForegroundColor Cyan

if ($failed -eq 0 -and $passed -gt 0) {
    Write-Host "`nSUCCESS: 100% of cataloged command notes validate successfully with non-empty function and use cases!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nFAILURE: $failed command notes failed validation." -ForegroundColor Red
    exit 1
}
