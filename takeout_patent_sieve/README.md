# Track 2: Streaming Google Takeout & Patent Bootloader/Instantiator Synthesis Pipeline (`takeout_patent_sieve`)

Zero-dependency Python streaming pipeline that parses Google Takeout archives (`MyActivity.json`, Google Keep `.json`, Drive `.md`/`.txt`), isolates raw archives inside the **Zero-Dirty-Logic Quarantine Sieve**, collapses iterative patent/architecture drafts via 128-permutation MinHash LSH, and compiles portable cross-model initialization seeds (`gemini_seed.json`, `claude_seed.md`, `codex_agents.md`, `AGENT_BOOTLOADER.md`).

## Key Capabilities
- **O(1)-RAM Archive Streamer (`TakeoutArchiveStreamer`):** Reconstructs multi-turn threads by `/app/c/<conversation_id>` or $\Delta t < 45\text{ min}$ timestamp windows.
- **Zero-Dirty-Logic Quarantine Sieve (`ZeroDirtyLogicSieve`):** Wraps raw text in `<tainted_raw_idea isolation="quarantined">` with HTML entity escaping against tag breakout, strips prompt injections and conversational dead-ends, and extracts clean mathematical invariants & normative domain rules.
- **Iterative Draft Collapse (`MinHashDraftCollapser`):** Collapses evolving drafts (Jaccard $\ge 0.70$) into canonical claims while preserving earliest conception timestamps and SHA-256 lineage.
- **Cross-Model Seed Instantiator (`CrossModelInstantiator`):** Emits cryptographically signed `gemini_seed.json`, `claude_seed.md`, `codex_agents.md`, and `AGENT_BOOTLOADER.md`.

## Verification
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
