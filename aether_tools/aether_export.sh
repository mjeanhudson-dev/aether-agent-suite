#!/usr/bin/env bash
# ==============================================================================
# Aether Bash On-the-Fly Command Exporter & Hooks
# ==============================================================================
# Conforms to AetherCommandSchema (Draft 2020-12)

# Determine default vault path (convert Windows to POSIX if needed)
if [ -z "$AETHER_VAULT_PATH" ]; then
    if [ -d "/c/Users/Zachariah/Documents/obsidian memory complex" ]; then
        export AETHER_VAULT_PATH="/c/Users/Zachariah/Documents/obsidian memory complex"
    elif [ -d "/c/Users/Zachariah/Downloads/obsidian memory complex" ]; then
        export AETHER_VAULT_PATH="/c/Users/Zachariah/Downloads/obsidian memory complex"
    else
        export AETHER_VAULT_PATH="C:/Users/Zachariah/Documents/obsidian memory complex"
    fi
fi

# Credential sanitizer
aether_sanitize_secret() {
    local input="$1"
    # Redact GitHub tokens
    input=$(printf '%s' "$input" | sed -E 's/ghp_[A-Za-z0-9_]{20,}/[REDACTED_GH_TOKEN]/g')
    input=$(printf '%s' "$input" | sed -E 's/gho_[A-Za-z0-9_]{20,}/[REDACTED_GH_OAUTH]/g')
    input=$(printf '%s' "$input" | sed -E 's/github_pat_[A-Za-z0-9_]{22,}/[REDACTED_GH_PAT]/g')
    # Redact API keys
    input=$(printf '%s' "$input" | sed -E 's/sk-[-A-Za-z0-9_]{20,}/[REDACTED_API_KEY]/g')
    input=$(printf '%s' "$input" | sed -E 's/AIza[-0-9A-Za-z_]{35}/[REDACTED_GOOGLE_API_KEY]/g')
    # Redact Bearer tokens
    input=$(printf '%s' "$input" | sed -E 's/Authorization:[[:space:]]*Bearer[[:space:]]+[-A-Za-z0-9_.~+/=]+/Authorization: Bearer [REDACTED_BEARER_TOKEN]/gI')
    # Redact generic passwords
    input=$(printf '%s' "$input" | sed -E 's/(password|secret|token|api[_-]?key)[[:space:]]*[:=][[:space:]]*[^ ;&]+/\1=[REDACTED_CREDENTIAL]/gI')
    printf '%s' "$input"
}

# Export command to Obsidian Aether Catalog
aether_export_command() {
    local fn="$1"
    local use="$2"
    local syntax="$3"
    local safety="${4:-mutating}"
    local title="${5:-$fn}"
    local vault="${AETHER_VAULT_PATH}"
    local target_dir="${vault}/Aether/Commands/Bash"

    if [ -z "$fn" ] || [ -z "$use" ] || [ -z "$syntax" ]; then
        printf '[Aether Error] Missing required arguments: function, use case, or syntax.\n' >&2
        return 1
    fi

    mkdir -p "$target_dir" 2>/dev/null || {
        # Fallback to local staging if vault unavailable
        target_dir="${HOME}/.aether/staging"
        mkdir -p "$target_dir"
    }

    # Sanitize syntax
    local clean_syntax
    clean_syntax=$(aether_sanitize_secret "$syntax")

    # Generate slug
    local slug
    slug=$(printf '%s' "$title" | tr -cs 'a-zA-Z0-9_' '-' | tr '[:upper:]' '[:lower:]' | cut -c1-50)
    slug="${slug#-}"
    slug="${slug%-}"
    if [ -z "$slug" ]; then
        slug="cmd-bash-$RANDOM"
    fi

    local cmd_id="cmd-bash-${slug}"
    local note_file="${target_dir}/${slug}.md"
    local now
    now=$(date -Iseconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S%z")

    # Escape quotes for YAML
    local yaml_title
    yaml_title=$(printf '%s' "$title" | sed 's/"/\\"/g')
    local yaml_fn
    yaml_fn=$(printf '%s' "$fn" | sed 's/"/\\"/g')
    local yaml_use
    yaml_use=$(printf '%s' "$use" | sed 's/"/\\"/g')
    local yaml_syntax
    yaml_syntax=$(printf '%s' "$clean_syntax" | sed 's/"/\\"/g')

    cat <<EOF > "$note_file"
---
id: "${cmd_id}"
title: "${yaml_title}"
description: "${yaml_fn}"
use_cases:
  - "${yaml_use}"
syntax: "${yaml_syntax}"
execution_environment: "bash"
tags:
  - "commands/bash"
  - "type/cli"
timestamps:
  created: "${now}"
  updated: "${now}"
parameters: []
safety_level: "${safety}"
catalog: "aether"
type: "command-catalog"
version: "1.0.0"
---

# ${title}

## Description
${fn}

## Syntax
\`\`\`bash
${clean_syntax}
\`\`\`

## Use Cases
- ${use}

## Parameters
None.
EOF

    printf '[Aether] Exported bash command: %s\n' "$note_file"
    return 0
}

# Dedicated CLI wrapper
aether-cmd() {
    local fn=""
    local use=""
    local safety="mutating"
    while [ "$#" -gt 0 ]; do
        case "$1" in
            -f|--function) fn="$2"; shift 2 ;;
            -u|--use-case) use="$2"; shift 2 ;;
            -s|--safety) safety="$2"; shift 2 ;;
            --) shift; break ;;
            *) break ;;
        esac
    done
    local cmd="$*"
    if [ -n "$fn" ] && [ -n "$use" ] && [ -n "$cmd" ]; then
        aether_export_command "$fn" "$use" "$cmd" "$safety"
    fi
    eval "$cmd"
}

# Preexec trap hook for interactive sessions with decorator: # @fn: ...; @use: ...
aether_preexec_trap() {
    local current_cmd="$BASH_COMMAND"
    if [[ "$current_cmd" =~ \#\ *@fn:\ *(.+?)\;\ *@use:\ *(.+) ]]; then
        local fn="${BASH_REMATCH[1]}"
        local use="${BASH_REMATCH[2]}"
        local code
        code=$(printf '%s' "$current_cmd" | sed -E 's/#[[:space:]]*@fn:.*//')
        code="$(printf '%s' "$code" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        if [ -n "$code" ] && [ -n "$fn" ] && [ -n "$use" ]; then
            aether_export_command "$fn" "$use" "$code" "mutating"
        fi
    fi
}

# Install trap if interactive
if [[ "$-" == *i* ]]; then
    trap 'aether_preexec_trap' DEBUG
fi
