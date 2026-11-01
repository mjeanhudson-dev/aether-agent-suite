#!/usr/bin/env python3
"""
Automated Verification Suite for Obsidian Aether Command Catalog (Milestone 1).
Validates 100% of cataloged markdown command notes against AetherCommandSchema.json
and asserts non-empty function/description and use_cases fields.
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path

# Optional external imports with zero-dependency fallback
try:
    import yaml
except ImportError:
    yaml = None

try:
    import jsonschema
except ImportError:
    jsonschema = None


def parse_simple_yaml_frontmatter(text: str) -> dict:
    """Robust parser for YAML frontmatter when PyYAML is unavailable."""
    data = {}
    lines = text.strip().splitlines()
    current_key = None
    current_list = None
    current_dict_key = None

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue

        # Check list item under current_key
        list_match = re.match(r"^(\s*)-\s*(.*)$", line)
        if list_match:
            val = list_match.group(2).strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if current_list is not None:
                if current_key == "parameters":
                    dict_item_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", val)
                    if dict_item_match:
                        k, v = dict_item_match.group(1), dict_item_match.group(2).strip().strip('"\'')
                        current_list.append({k: v})
                    else:
                        current_list.append(val)
                else:
                    current_list.append(val)
                continue

        # Check key-value pair
        kv_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if kv_match:
            k = kv_match.group(1).strip()
            v = kv_match.group(2).strip()

            if v == "" or v == "[]":
                if v == "[]":
                    data[k] = []
                    current_list = None
                else:
                    data[k] = []
                    current_list = data[k]
                current_key = k
                continue
            elif v == "{}":
                data[k] = {}
                current_list = None
                current_key = k
                continue

            # Strip quotes
            clean_val = v.strip('"\'')
            data[k] = clean_val
            current_key = k
            current_list = None
            continue

        # Nested dict fields (e.g. under timestamps)
        nested_match = re.match(r"^\s+([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if nested_match and current_key:
            nk = nested_match.group(1).strip()
            nv = nested_match.group(2).strip().strip('"\'')
            if not isinstance(data.get(current_key), dict):
                data[current_key] = {}
            data[current_key][nk] = nv
            continue

    return data


def extract_frontmatter(content: str) -> tuple[dict, str]:
    """Extract and parse YAML frontmatter from markdown content."""
    clean_content = content.lstrip("\ufeff").strip()
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", clean_content, re.DOTALL)
    if not match:
        raise ValueError("Missing YAML frontmatter delimiters ('---')")

    fm_raw = match.group(1)
    body = match.group(2)

    if yaml:
        try:
            fm_data = yaml.safe_load(fm_raw)
            if not isinstance(fm_data, dict):
                raise ValueError("Parsed frontmatter is not a dictionary")
            return fm_data, body
        except Exception:
            pass

    # Fallback parser
    fm_data = parse_simple_yaml_frontmatter(fm_raw)
    return fm_data, body


def validate_note_frontmatter(note_path: Path, schema: dict) -> list[str]:
    """Validates note frontmatter against requirements and JSON schema."""
    errors = []
    try:
        content = note_path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        return [f"Failed to read file: {e}"]

    try:
        fm, _ = extract_frontmatter(content)
    except Exception as e:
        return [f"Frontmatter extraction error: {e}"]

    # 1. Schema validation if jsonschema is available
    if jsonschema and schema:
        try:
            jsonschema.validate(instance=fm, schema=schema)
        except jsonschema.ValidationError as ve:
            errors.append(f"Schema violation at '{'.'.join(str(p) for p in ve.path)}': {ve.message}")
        except Exception as e:
            errors.append(f"Schema validation error: {e}")

    # 2. Strict invariant assertions
    # id check
    cmd_id = fm.get("id")
    if not cmd_id or not re.match(r"^cmd-(bash|powershell|pwsh|sh|cmd)-[a-z0-9_.-]+$", str(cmd_id)):
        errors.append(f"Invalid or missing 'id': {cmd_id}")

    # function / description check (MUST BE NON-EMPTY, minLength >= 5)
    description = fm.get("description") or fm.get("function")
    if not description or not isinstance(description, str) or len(description.strip()) < 5:
        errors.append("Missing, empty, or too short 'description'/'function' (minimum 5 characters required)")

    # use_cases check (MUST BE NON-EMPTY LIST, minItems >= 1)
    use_cases = fm.get("use_cases")
    if not use_cases:
        errors.append("Missing or empty 'use_cases' (minimum 1 use case required)")
    elif isinstance(use_cases, list):
        if len(use_cases) < 1:
            errors.append("'use_cases' array contains 0 items")
        else:
            for i, uc in enumerate(use_cases):
                if not isinstance(uc, str) or len(str(uc).strip()) < 3:
                    errors.append(f"use_cases[{i}] is empty or shorter than 3 characters")
    elif isinstance(use_cases, str):
        if len(use_cases.strip()) < 3:
            errors.append("'use_cases' string is empty")
    else:
        errors.append(f"'use_cases' must be an array or list of strings, got {type(use_cases).__name__}")

    # syntax check
    syntax = fm.get("syntax")
    if not syntax or not isinstance(syntax, str) or len(syntax.strip()) < 1:
        errors.append("Missing or empty 'syntax'")

    # execution_environment check
    env = fm.get("execution_environment")
    valid_envs = ["powershell", "pwsh", "bash", "sh", "cmd"]
    if not env or str(env).lower() not in valid_envs:
        errors.append(f"Invalid 'execution_environment': '{env}' (expected one of {valid_envs})")

    # catalog and type invariants
    if fm.get("catalog") != "aether":
        errors.append(f"Invalid or missing 'catalog': '{fm.get('catalog')}' (expected 'aether')")
    if fm.get("type") != "command-catalog":
        errors.append(f"Invalid or missing 'type': '{fm.get('type')}' (expected 'command-catalog')")

    # timestamps
    ts = fm.get("timestamps")
    if not ts:
        errors.append("Missing 'timestamps' object")
    elif isinstance(ts, dict):
        if not ts.get("created"):
            errors.append("Missing 'timestamps.created'")
        if not ts.get("updated"):
            errors.append("Missing 'timestamps.updated'")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Aether Obsidian Command Catalog Verifier")
    parser.add_argument(
        "--vault-path",
        default=r"C:\Users\Zachariah\Documents\obsidian memory complex",
        help="Path to the Obsidian vault root"
    )
    parser.add_argument(
        "--schema-path",
        default=r"C:\Users\Zachariah\.gemini\antigravity\scratch\aether_tools\AetherCommandSchema.json",
        help="Path to AetherCommandSchema.json"
    )
    args = parser.parse_args()

    vault_path = Path(args.vault_path)
    commands_dir = vault_path / "Aether" / "Commands"
    schema_path = Path(args.schema_path)

    print("=" * 60)
    print("=== AETHER COMMAND CATALOG VERIFICATION SUITE ===")
    print("=" * 60)
    print(f"Vault Directory:   {vault_path}")
    print(f"Commands Target:   {commands_dir}")
    print(f"Schema Definition: {schema_path}")

    # Load schema
    schema = None
    if schema_path.exists():
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            print("Successfully loaded Draft 2020-12 JSON Schema.")
        except Exception as e:
            print(f"Warning: Failed to parse schema file: {e}")
    else:
        print(f"Warning: Schema file not found at {schema_path}")

    if not commands_dir.exists():
        print(f"ERROR: Commands catalog directory does not exist: {commands_dir}")
        sys.exit(1)

    notes = list(commands_dir.rglob("*.md"))
    print(f"Discovered {len(notes)} catalog notes to validate.\n")

    if not notes:
        print("ERROR: Zero command notes found in catalog. Run Invoke-AetherRetroactiveCatalog first.")
        sys.exit(1)

    total_count = len(notes)
    passed_count = 0
    failed_count = 0
    failure_details = []

    for note in sorted(notes):
        rel_path = note.relative_to(commands_dir)
        errs = validate_note_frontmatter(note, schema)
        if not errs:
            passed_count += 1
            print(f"  [PASS] {rel_path}")
        else:
            failed_count += 1
            print(f"  [FAIL] {rel_path}")
            for err in errs:
                print(f"         -> {err}")
            failure_details.append((str(rel_path), errs))

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY:")
    print(f"  Total Notes Scanned: {total_count}")
    print(f"  Passed Validation:   {passed_count} ({passed_count/total_count*100:.1f}%)")
    print(f"  Failed Validation:   {failed_count}")
    print("=" * 60)

    if failed_count == 0 and passed_count > 0:
        print("\nSUCCESS: 100% of cataloged command notes validate against schema and contain non-empty function and use case fields!")
        sys.exit(0)
    else:
        print(f"\nFAILURE: {failed_count} command notes violated schema constraints.")
        sys.exit(1)


if __name__ == "__main__":
    main()
