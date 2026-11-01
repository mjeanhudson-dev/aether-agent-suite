"""
Aether Context Caching Engine (Python / google-genai)
=====================================================
Provides explicit context caching for large system architectures, KPPC routing specs,
and multi-agent blueprints with automatic dual-mode authentication.
"""

import argparse
import os
import sys
from typing import Any, Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

DEFAULT_ADC_PROJECT = "project-31f97d8a-b7dd-449b-b4d"
DEFAULT_ADC_LOCATION = "us-central1"
DEFAULT_MODEL = "gemini-2.5-pro"


def get_genai_client(
    api_key: Optional[str] = None,
    project: Optional[str] = None,
    location: Optional[str] = None,
) -> Any:
    """Initializes Google GenAI Client with auto-fallback to Vertex AI ADC."""
    if genai is None:
        raise ImportError("google-genai package not found. Install via: pip install google-genai")

    # Mode 1: Check for explicit or environment API key (AI Studio)
    resolved_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if resolved_key:
        return genai.Client(api_key=resolved_key)

    # Mode 2: Fallback to authenticated Vertex AI Application Default Credentials (ADC)
    resolved_proj = project or os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_ADC_PROJECT)
    resolved_loc = location or os.environ.get("GOOGLE_CLOUD_LOCATION", DEFAULT_ADC_LOCATION)
    return genai.Client(vertexai=True, project=resolved_proj, location=resolved_loc)


def create_context_cache(
    blueprint_text: str,
    system_instruction: str = "You are Aether, the core collaborative co-pilot operating inside the MyAssistance control plane.",
    model_id: str = DEFAULT_MODEL,
    ttl: str = "3600s",
    client: Optional[Any] = None,
) -> Any:
    """Creates a Gemini explicit context cache with the specified TTL."""
    c = client or get_genai_client()
    print(f"Creating context cache for blueprint using {model_id} (TTL: {ttl})...")

    cache = c.caches.create(
        model=model_id,
        config=types.CreateCachedContentConfig(
            contents=[blueprint_text],
            system_instruction=system_instruction,
            ttl=ttl,
        ),
    )
    print("Cache successfully created!")
    print(f"Cache Resource Name: {cache.name}")
    print(f"Expires at: {cache.expire_time}")
    return cache


def query_cached_content(
    cache_name: str,
    prompt: str,
    model_id: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    client: Optional[Any] = None,
) -> Any:
    """Executes an inference query referencing an existing context cache ID."""
    c = client or get_genai_client()
    print(f"\nSending query referencing cache '{cache_name}'...")
    response = c.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            cached_content=cache_name,
            temperature=temperature,
        ),
    )
    print("\n--- Response ---")
    print(response.text)
    print("\n--- Usage Metadata ---")
    print(response.usage_metadata)
    return response


def list_context_caches(client: Optional[Any] = None) -> list:
    """Lists all active cached content resources."""
    c = client or get_genai_client()
    caches = list(c.caches.list())
    print(f"Found {len(caches)} active context caches:")
    for item in caches:
        print(f" - {item.name} (model: {item.model}, expires: {item.expire_time})")
    return caches


def main():
    parser = argparse.ArgumentParser(description="Aether Gemini Context Caching Runner")
    parser.add_argument("--list-caches", action="store_true", help="List active context caches")
    parser.add_argument("--test-cache", action="store_true", help="Run a test context caching workflow")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model ID (default: gemini-2.5-pro)")
    args = parser.parse_args()

    if args.list_caches:
        list_context_caches()
        return

    if args.test_cache:
        blueprint_path = os.path.join(os.path.dirname(__file__), "blueprint.md")
        if os.path.isfile(blueprint_path):
            with open(blueprint_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = "# MYASSISTANCE ARCHITECTURE BLUEPRINT & KERNEL SPEC\nKPPC coordination plane active."

        try:
            cache = create_context_cache(content, model_id=args.model)
            query_cached_content(cache.name, "Summarize the routing security in this blueprint.", model_id=args.model)
        except Exception as e:
            print(f"Context caching note: {e}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
