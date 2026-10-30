<#
.SYNOPSIS
    Slow Simmer Token Budget & Synthesis Manager

.DESCRIPTION
    Helper script for /slow_simmer_stimulative_thinking.
    Manages active venture tracks, checks weekly budget posture, and stages
    synthesis runs into VENTURE_INCUBATOR.md.
#>

[CmdletBinding()]
param(
    [ValidateSet("Status", "Minimal", "Maximal", "Sanitize")]
    [string]$Mode = "Status",

    [string]$InputPath = "",
    [string]$TrackId = ""
)

$ErrorActionPreference = "Stop"
$incubatorPath = "C:\Users\Zachariah\Documents\antigravity\VENTURE_INCUBATOR.md"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "=== Aether Slow Simmer & Venture Engine ===" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

switch ($Mode) {
    "Status" {
        Write-Host "Active Incubator Vault: $incubatorPath"
        if (Test-Path $incubatorPath) {
            $tracks = Select-String -Path $incubatorPath -Pattern "## (?:🥩|🧬|🎮|⚖️|🛡️|✈️) Track \d+: (.+)"
            Write-Host "`nRegistered Venture Tracks in Vault:" -ForegroundColor Green
            foreach ($t in $tracks) {
                Write-Host "  - $($t.Matches[0].Groups[1].Value)" -ForegroundColor White
            }
        } else {
            Write-Warning "Incubator vault not found at $incubatorPath"
        }
    }

    "Sanitize" {
        if (-not $InputPath -or -not (Test-Path $InputPath)) {
            Write-Error "Please specify a valid -InputPath to sanitize."
        }
        Write-Host "Applying Zero-Dirty-Logic Quarantine Sieve to: $InputPath" -ForegroundColor Yellow
        $raw = Get-Content -Path $InputPath -Raw
        # Strip common instruction injections and conversational noise
        $sanitized = $raw -replace "(?i)(ignore previous instructions|system prompt|override default)", "[REDACTED_INJECTION]"
        $outPath = [System.IO.Path]::ChangeExtension($InputPath, ".sanitized.txt")
        Set-Content -Path $outPath -Value $sanitized -Encoding UTF8
        Write-Host "Sanitized passive reference created: $outPath" -ForegroundColor Green
    }

    default {
        Write-Host "Simmer Mode: $Mode initiated." -ForegroundColor Green
        Write-Host "Target Vault: $incubatorPath"
    }
}
