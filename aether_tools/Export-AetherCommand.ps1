<#
.SYNOPSIS
    Exports bash and PowerShell commands labeled with function and use cases into the Obsidian Aether Catalog.
.DESCRIPTION
    Provides the Export-AetherCommand cmdlet and PSReadLine key handler (Ctrl+Shift+E)
    to export on-the-fly commands into Obsidian notes formatted according to the AetherCommandSchema (Draft 2020-12).
#>

function Sanitize-AetherSecret {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$InputText
    )

    $sanitized = $InputText
    # GitHub personal access tokens
    $sanitized = $sanitized -replace 'ghp_[A-Za-z0-9_]{20,}', '[REDACTED_GH_TOKEN]'
    $sanitized = $sanitized -replace 'gho_[A-Za-z0-9_]{20,}', '[REDACTED_GH_OAUTH]'
    $sanitized = $sanitized -replace 'github_pat_[A-Za-z0-9_]{22,}', '[REDACTED_GH_PAT]'
    # OpenAI / Anthropic / Generic API keys
    $sanitized = $sanitized -replace 'sk-[A-Za-z0-9_-]{20,}', '[REDACTED_API_KEY]'
    $sanitized = $sanitized -replace 'AIza[0-9A-Za-z-_]{35}', '[REDACTED_GOOGLE_API_KEY]'
    # Bearer authorization headers
    $sanitized = $sanitized -replace '(?i)(Authorization:\s*Bearer\s+)[A-Za-z0-9_\-\.~+/]+=*', '$1[REDACTED_BEARER_TOKEN]'
    # JWT tokens
    $sanitized = $sanitized -replace 'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-]+', '[REDACTED_JWT_TOKEN]'
    # Generic password / secret assignments
    $sanitized = $sanitized -replace '(?i)(password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*[''"]?([^\s''";&]+)[''"]?', '$1=[REDACTED_CREDENTIAL]'

    return $sanitized
}

function Export-AetherCommand {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true, Position=0)][string]$Description,
        [Parameter(Mandatory=$true, Position=1)][string[]]$UseCases,
        [Parameter(Mandatory=$true, Position=2)][string]$Syntax,
        [ValidateSet("powershell", "pwsh", "bash", "sh", "cmd")]
        [string]$ExecutionEnvironment = "powershell",
        [string[]]$Tags = @(),
        [ValidateSet("read-only", "mutating", "destructive")]
        [string]$SafetyLevel = "mutating",
        [hashtable[]]$Parameters = @(),
        [string[]]$Aliases = @(),
        [string]$Title = "",
        [string]$VaultPath = "C:\Users\Zachariah\Documents\obsidian memory complex",
        [switch]$PassThru
    )

    if ([string]::IsNullOrWhiteSpace($Description)) {
        throw "Description (function) cannot be null or empty."
    }
    if ($null -eq $UseCases -or $UseCases.Count -eq 0 -or [string]::IsNullOrWhiteSpace($UseCases[0])) {
        throw "UseCases must contain at least one non-empty string."
    }
    if ([string]::IsNullOrWhiteSpace($Syntax)) {
        throw "Syntax cannot be null or empty."
    }

    # Sanitize secrets in syntax
    $cleanSyntax = Sanitize-AetherSecret -InputText $Syntax

    # Set up timestamps
    $now = Get-Date
    $isoTimestamp = $now.ToString("yyyy-MM-ddTHH:mm:ss.fffzzz")

    # Generate title and slug
    if ([string]::IsNullOrWhiteSpace($Title)) {
        $Title = $Description
    }

    $cleanDesc = $Title -replace '[^a-zA-Z0-9_-]', '-' -replace '-+', '-'
    $slug = $cleanDesc.Trim('-').ToLower()
    if ($slug.Length -gt 50) { $slug = $slug.Substring(0, 50).Trim('-') }
    if ([string]::IsNullOrWhiteSpace($slug)) { $slug = "cmd-" + (Get-Random -Minimum 1000 -Maximum 9999) }

    $shellFolder = if ($ExecutionEnvironment -in 'powershell', 'pwsh') { "PowerShell" } else { "Bash" }
    $cmdId = "cmd-$($ExecutionEnvironment.ToLower())-$slug"

    # Default tags
    $finalTags = [System.Collections.Generic.List[string]]::new()
    $finalTags.Add("commands/$($ExecutionEnvironment.ToLower())")
    if ($Tags) {
        foreach ($t in $Tags) {
            if (-not $finalTags.Contains($t)) { $finalTags.Add($t) }
        }
    }
    if ($finalTags.Count -eq 1) {
        $finalTags.Add("type/cli")
    }

    $catalogDir = Join-Path $VaultPath "Aether\Commands\$shellFolder"
    if (-not (Test-Path $catalogDir)) {
        New-Item -ItemType Directory -Path $catalogDir -Force | Out-Null
    }

    $filePath = Join-Path $catalogDir "$slug.md"

    # Format YAML arrays
    $tagsYaml = ($finalTags | ForEach-Object { "  - `"$($_)`"" }) -join "`n"
    $useCasesYaml = ($UseCases | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { "  - `"$($_.Trim().Replace('"', '\"'))`"" }) -join "`n"
    
    $aliasesYaml = if ($Aliases -and $Aliases.Count -gt 0) {
        "`naliases:`n" + (($Aliases | ForEach-Object { "  - `"$($_)`"" }) -join "`n")
    } else {
        ""
    }

    $paramsYaml = if ($Parameters -and $Parameters.Count -gt 0) {
        $lines = @("parameters:")
        foreach ($p in $Parameters) {
            $lines += "  - name: `"$($p.name)`""
            $lines += "    type: `"$($p.type)`""
            $lines += "    required: $(if ($p.required) { 'true' } else { 'false' })"
            $lines += "    description: `"$($p.description)`""
            if ($p.ContainsKey('default') -and $null -ne $p.default) {
                $lines += "    default: `"$($p.default)`""
            }
        }
        $lines -join "`n"
    } else {
        "parameters: []"
    }

    # Escape quotes in description and syntax for YAML
    $yamlDesc = $Description.Replace('"', '\"')
    $yamlTitle = $Title.Replace('"', '\"')
    $yamlSyntax = $cleanSyntax.Replace('"', '\"')

    $fence = '```'
    $noteContent = @"
---
id: "$cmdId"
title: "$yamlTitle"
description: "$yamlDesc"
use_cases:
$useCasesYaml
syntax: "$yamlSyntax"
execution_environment: "$ExecutionEnvironment"
tags:
$tagsYaml$aliasesYaml
timestamps:
  created: "$isoTimestamp"
  updated: "$isoTimestamp"
$paramsYaml
safety_level: "$SafetyLevel"
catalog: "aether"
type: "command-catalog"
version: "1.0.0"
---

# $Title

## Description
$Description

## Syntax
$fence$ExecutionEnvironment
$cleanSyntax
$fence

## Use Cases
$(($UseCases | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { "- $($_.Trim())" }) -join "`n")

## Parameters
$(if ($Parameters -and $Parameters.Count -gt 0) {
    "| Name | Type | Required | Description |`n| :--- | :--- | :--- | :--- |`n" +
    (($Parameters | ForEach-Object { "| ``$($_.name)`` | $($_.type) | $(if ($_.required) { 'Yes' } else { 'No' }) | $($_.description) |" }) -join "`n")
} else {
    "None."
})
"@

    Set-Content -Path $filePath -Value $noteContent -Encoding UTF8
    Write-Verbose "[Aether] Exported command note: $filePath"

    if ($PassThru) {
        return (Get-Item $filePath)
    }
    return $filePath
}

function Register-AetherPSReadLineHandler {
    [CmdletBinding()]
    param()

    if (Get-Module -Name PSReadLine -ErrorAction SilentlyContinue) {
        try {
            Set-PSReadLineKeyHandler -Chord 'Ctrl+Shift+E' -BriefDescription 'ExportToAether' -LongDescription 'Exports annotated command buffer to Obsidian Aether' -ScriptBlock {
                $buffer = $null; $cursor = $null
                [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$buffer, [ref]$cursor)
                
                if ([string]::IsNullOrWhiteSpace($buffer)) {
                    Write-Host "`n[Aether] Command buffer is empty." -ForegroundColor Yellow
                    return
                }

                # Check if buffer contains annotation pattern: # @fn: ...; @use: ...
                if ($buffer -match '(?i)#\s*@fn:\s*(.+?);\s*@use:\s*(.+)') {
                    $fn = $matches[1].Trim()
                    $uses = $matches[2].Trim() -split ';\s*'
                    $code = ($buffer -replace '(?i)#\s*@fn:.*', '').Trim()
                    if ([string]::IsNullOrWhiteSpace($code)) { $code = $buffer }

                    $path = Export-AetherCommand -Description $fn -UseCases $uses -Syntax $code -ExecutionEnvironment "powershell"
                    Write-Host "`n[Aether] Exported to: $path" -ForegroundColor Green
                } else {
                    Write-Host "`n[Aether] To export on the fly, append decorator: # @fn: <description>; @use: <use_case_1>; <use_case_2>" -ForegroundColor Yellow
                }
            }
            Write-Verbose "[Aether] PSReadLine key handler registered (Ctrl+Shift+E)."
        } catch {
            Write-Warning "[Aether] Failed to register PSReadLine key handler: $_"
        }
    }
}

# Auto-register if in interactive session
if ($Host.UI.RawUI.KeyAvailable -or [System.Environment]::UserInteractive) {
    Register-AetherPSReadLineHandler
}
