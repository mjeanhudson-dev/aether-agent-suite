<#
.SYNOPSIS
    Dual-engine retroactive cataloger for PowerShell and Bash workspace scripts.
.DESCRIPTION
    Scans workspace repositories for existing PowerShell (.ps1, .psm1) and Bash (.sh, .bash) scripts,
    extracts function descriptions, use cases, parameters, and syntax using native AST parsing
    (PowerShell) and lexer/regex parsing (Bash), sanitizes secrets, and generates schema-conforming
    markdown command notes in the Obsidian Aether Catalog.
#>

[CmdletBinding()]
param(
    [string[]]$SearchPaths = @(
        "C:\Users\Zachariah\.gemini\antigravity\scratch",
        "C:\Users\Zachariah\tools",
        "C:\Users\Zachariah\aether agent",
        "C:\Users\Zachariah\Downloads\obsidian memory complex\vault_imports\scripts"
    ),
    [string]$VaultPath = "C:\Users\Zachariah\Documents\obsidian memory complex",
    [string[]]$ExcludePatterns = @('\.git\', 'node_modules', 'vendor', '\.venv', 'dist', 'build', 'aether_tools')
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = "C:\Users\Zachariah\.gemini\antigravity\scratch\aether_tools" }
$exporterPath = Join-Path $scriptDir "Export-AetherCommand.ps1"

if (Test-Path $exporterPath) {
    . $exporterPath
} else {
    throw "Required dependency Export-AetherCommand.ps1 not found at: $exporterPath"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "=== AETHER RETROACTIVE SCRIPT CATALOGER (M1) ===" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Ensure target directories exist
$psCatalogDir = Join-Path $VaultPath "Aether\Commands\PowerShell"
$bashCatalogDir = Join-Path $VaultPath "Aether\Commands\Bash"
if (-not (Test-Path $psCatalogDir)) { New-Item -ItemType Directory -Path $psCatalogDir -Force | Out-Null }
if (-not (Test-Path $bashCatalogDir)) { New-Item -ItemType Directory -Path $bashCatalogDir -Force | Out-Null }

# Locate scripts with fast directory pruning
$targetPaths = $SearchPaths | Where-Object { Test-Path $_ }
Write-Host "Scanning active directories: $($targetPaths -join ', ')" -ForegroundColor Yellow

$scriptFiles = [System.Collections.Generic.List[System.IO.FileInfo]]::new()
$excludedNames = @('.git', 'node_modules', 'vendor', '.venv', 'dist', 'build', 'aether_tools')

foreach ($root in $targetPaths) {
    $queue = [System.Collections.Generic.Queue[string]]::new()
    $queue.Enqueue($root)
    while ($queue.Count -gt 0) {
        $cur = $queue.Dequeue()
        try {
            $dInfo = [System.IO.DirectoryInfo]::new($cur)
            foreach ($f in $dInfo.GetFiles()) {
                $ext = $f.Extension.ToLower()
                if ($ext -in '.ps1', '.psm1', '.sh', '.bash') {
                    $scriptFiles.Add($f)
                }
            }
            foreach ($sub in $dInfo.GetDirectories()) {
                if ($sub.Name.ToLower() -notin $excludedNames) {
                    $queue.Enqueue($sub.FullName)
                }
            }
        } catch {}
    }
}

Write-Host "Found $($scriptFiles.Count) candidate scripts for retroactive cataloging." -ForegroundColor Green

$stats = @{
    TotalScanned = $scriptFiles.Count
    PowerShellCount = 0
    BashCount = 0
    Errors = 0
    CatalogedNotes = @()
}

function Determine-SafetyLevel {
    param([string]$Content)
    if ($Content -match '(?i)(rm\s+-rf|Remove-Item.*-Recurse|Drop-Database|Format-Volume|Stop-Process\s+-Force|git\s+reset\s+--hard)') {
        return "destructive"
    } elseif ($Content -match '(?i)(New-Item|Set-Content|Add-Content|Set-Item|mkdir|touch|git\s+commit|mv\s+|cp\s+)') {
        return "mutating"
    } else {
        return "read-only"
    }
}

foreach ($file in $scriptFiles) {
    try {
        $title = $file.BaseName
        $ext = $file.Extension.ToLower()

        if ($ext -in '.ps1', '.psm1') {
            # ------------------------------------------------------------------
            # Engine 1: PowerShell AST Parser
            # ------------------------------------------------------------------
            $tokens = $null; $errors = $null
            $ast = [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors)
            $help = if ($ast) { $ast.GetHelpContent() } else { $null }

            $rawContent = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
            if ([string]::IsNullOrWhiteSpace($rawContent)) { $rawContent = "" }

            # Extract Function/Description
            $functionDesc = ""
            if ($help -and -not [string]::IsNullOrWhiteSpace($help.Synopsis)) {
                $functionDesc = $help.Synopsis.Trim()
            } elseif ($help -and -not [string]::IsNullOrWhiteSpace($help.Description)) {
                $descLines = $help.Description -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
                if ($descLines.Count -gt 0) { $functionDesc = $descLines[0].Trim() }
            }

            # Heuristic fallback if help content is empty
            if ([string]::IsNullOrWhiteSpace($functionDesc)) {
                if ($rawContent -match '(?s)^<#\s*(.*?)\s*#>') {
                    $commentBlock = $matches[1].Trim() -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
                    if ($commentBlock.Count -gt 0) {
                        $functionDesc = ($commentBlock[0] -replace '^[\s#*-]+', '').Trim()
                    }
                } elseif ($rawContent -match '(?m)^#\s*(.+)') {
                    $firstComment = $matches[1].Trim()
                    if ($firstComment.Length -ge 10) {
                        $functionDesc = $firstComment
                    }
                }
            }

            if ([string]::IsNullOrWhiteSpace($functionDesc) -or $functionDesc.Length -lt 5) {
                $cleanName = ($file.BaseName -replace '[-_]', ' ')
                $functionDesc = "Executes $cleanName script for automation, configuration, and environment orchestration."
            }

            # Extract Use Cases
            $useCases = @()
            if ($help -and -not [string]::IsNullOrWhiteSpace($help.Description)) {
                $useCases = @($help.Description -split "`r?`n" | Where-Object { $_.Trim().Length -gt 5 } | ForEach-Object { $_.Trim() })
            }

            if ($useCases.Count -eq 0) {
                # Derive use cases from script content and intent
                $cleanName = ($file.BaseName -replace '[-_]', ' ')
                $useCases = @(
                    "Automated invocation of $cleanName in local workflow",
                    "Orchestrates $($file.Name) task lifecycle and state management"
                )
            }

            # Extract Parameters from AST
            $params = @()
            if ($ast -and $ast.ParamBlock -and $ast.ParamBlock.Parameters) {
                foreach ($p in $ast.ParamBlock.Parameters) {
                    $pName = $p.Name.VariablePath.UserPath
                    $pType = if ($p.StaticType) { $p.StaticType.Name } else { "string" }
                    $isMandatory = $false
                    if ($p.Attributes) {
                        foreach ($attr in $p.Attributes) {
                            if ($attr.TypeName.FullName -eq 'Parameter') {
                                foreach ($namedArg in $attr.NamedArguments) {
                                    if ($namedArg.ArgumentName -eq 'Mandatory' -and $namedArg.Argument.Value -eq $true) {
                                        $isMandatory = $true
                                    }
                                }
                            }
                        }
                    }
                    $params += @{
                        name = "-$pName"
                        type = $pType.ToLower()
                        required = $isMandatory
                        description = "Specifies -$pName parameter for $($file.Name)"
                    }
                }
            }

            # Construct Syntax
            $paramSyntax = if ($params.Count -gt 0) {
                " " + (($params | ForEach-Object { "$($_.name) <$($_.type)>" }) -join " ")
            } else { "" }
            $syntax = "powershell -ExecutionPolicy Bypass -File `"$($file.FullName)`"$paramSyntax"

            $safety = Determine-SafetyLevel -Content $rawContent

            $tags = @("commands/powershell", "script/retroactive")
            if ($file.FullName -match 'scratch') { $tags += "source/scratch" }
            elseif ($file.FullName -match 'tools') { $tags += "source/tools" }
            elseif ($file.FullName -match 'aether agent') { $tags += "source/aether" }
            elseif ($file.FullName -match 'vault_imports') { $tags += "source/vault-imports" }

            $notePath = Export-AetherCommand -Description $functionDesc `
                                             -UseCases $useCases `
                                             -Syntax $syntax `
                                             -ExecutionEnvironment "powershell" `
                                             -Title $file.BaseName `
                                             -Parameters $params `
                                             -SafetyLevel $safety `
                                             -Tags $tags `
                                             -VaultPath $VaultPath

            $stats.PowerShellCount++
            $stats.CatalogedNotes += $notePath
            Write-Host "  [PS] Cataloged: $($file.Name) -> $(Split-Path -Leaf $notePath)" -ForegroundColor Green

        } elseif ($ext -in '.sh', '.bash') {
            # ------------------------------------------------------------------
            # Engine 2: Bash Lexer / Regex Parser
            # ------------------------------------------------------------------
            $rawContent = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
            if ([string]::IsNullOrWhiteSpace($rawContent)) { $rawContent = "" }

            # Extract header comment block
            $lines = $rawContent -split "`r?`n"
            $headerComments = @()
            foreach ($line in $lines) {
                $trimmed = $line.Trim()
                if ($trimmed.StartsWith('#!')) { continue } # Skip shebang
                if ($trimmed.StartsWith('#')) {
                    $cText = ($trimmed -replace '^#+\s*', '').Trim()
                    if ($cText.Length -gt 0 -and $cText -notmatch '^=+$' -and $cText -notmatch '^-+$') {
                        $headerComments += $cText
                    }
                } elseif (-not [string]::IsNullOrWhiteSpace($trimmed)) {
                    # Encountered first non-comment, non-empty code line
                    break
                }
            }

            $functionDesc = ""
            if ($headerComments.Count -gt 0) {
                $functionDesc = $headerComments[0]
            }

            if ([string]::IsNullOrWhiteSpace($functionDesc) -or $functionDesc.Length -lt 5) {
                $cleanName = ($file.BaseName -replace '[-_]', ' ')
                $functionDesc = "Executes $cleanName bash script for automation, builds, and platform operations."
            }

            $useCases = @()
            if ($headerComments.Count -gt 1) {
                $useCases = @($headerComments | Select-Object -Skip 1 | Where-Object { $_.Length -gt 5 })
            }

            if ($useCases.Count -eq 0) {
                $cleanName = ($file.BaseName -replace '[-_]', ' ')
                $useCases = @(
                    "Shell automation and workflow invocation for $cleanName",
                    "Execute $($file.Name) within Git Bash / Unix environment"
                )
            }

            # Discover function definitions
            $functions = [System.Collections.Generic.List[string]]::new()
            $matches = [regex]::Matches($rawContent, '(?m)^(?:function\s+)?([a-zA-Z0-9_-]+)\s*\(\)\s*\{')
            foreach ($m in $matches) {
                $fnName = $m.Groups[1].Value
                if ($fnName -and -not $functions.Contains($fnName)) {
                    $functions.Add($fnName)
                }
            }

            # Posix path normalization
            $posixPath = $file.FullName -replace '\\', '/' -replace '^([A-Za-z]):', '/$1'
            $syntax = "bash `"$posixPath`""
            if ($functions.Count -gt 0) {
                $syntax += " # Exports/defines: $($functions -join ', ')"
            }

            $safety = Determine-SafetyLevel -Content $rawContent

            $tags = @("commands/bash", "script/retroactive")
            if ($file.FullName -match 'scratch') { $tags += "source/scratch" }
            elseif ($file.FullName -match 'tools') { $tags += "source/tools" }
            elseif ($file.FullName -match 'aether agent') { $tags += "source/aether" }
            elseif ($file.FullName -match 'vault_imports') { $tags += "source/vault-imports" }

            $notePath = Export-AetherCommand -Description $functionDesc `
                                             -UseCases $useCases `
                                             -Syntax $syntax `
                                             -ExecutionEnvironment "bash" `
                                             -Title $file.BaseName `
                                             -SafetyLevel $safety `
                                             -Tags $tags `
                                             -VaultPath $VaultPath

            $stats.BashCount++
            $stats.CatalogedNotes += $notePath
            Write-Host "  [Bash] Cataloged: $($file.Name) -> $(Split-Path -Leaf $notePath)" -ForegroundColor Green
        }
    } catch {
        $stats.Errors++
        Write-Warning "Failed to catalog $($file.FullName): $_"
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "Cataloging Complete Summary:" -ForegroundColor Cyan
Write-Host "  Total Scripts Scanned:   $($stats.TotalScanned)"
Write-Host "  PowerShell Cataloged:    $($stats.PowerShellCount)"
Write-Host "  Bash Cataloged:          $($stats.BashCount)"
Write-Host "  Total Notes Produced:    $($stats.CatalogedNotes.Count)"
Write-Host "  Errors Encountered:      $($stats.Errors)"
Write-Host "==========================================================" -ForegroundColor Cyan

return $stats
