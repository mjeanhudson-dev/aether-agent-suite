# Track 4: Arbiter Forge — Heterogeneous Cross-Model Consensus & PINPOINT Gatekeeper (`arbiter_forge`)

Zero-dependency Python reference implementation of the cross-model consensus and deterministic `PINPOINT` gatekeeping engine across Gemini, Claude, and Codex.

## Key Capabilities
1. **Heterogeneous Model Roles (`ModelRole`):**
   - `GEMINI_DEEP_SYNTHESIS`: Deep architectural coherence & mathematical invariant review.
   - `CLAUDE_ADVERSARIAL_AUDIT`: Red-team security, regression hunting, and critical security vetoes.
   - `CODEX_DETERMINISTIC_EXEC`: Algorithmic verification & test synthesis coverage.
2. **Borda & Condorcet Consensus (`ArbiterForgeGatekeeper.compute_consensus`):**
   - Computes pairwise Condorcet head-to-head matrices and rubric-weighted Borda counts while enforcing adversarial red-team vetoes.
3. **Blast-Radius Friction Gating (`compute_blast_radius`):**
   - Computes $B(a) \in [0, 100]$ and maps to `PASSIVE_TELEMETRY` ($B < 20$), `SOFT_CONFIRM` ($20 \le B < 70$), and `HARD_HAPTIC_DETENT` ($B \ge 70$, requiring explicit human ratification).
4. **Deterministic `PINPOINT` & Cryptographic SHA-256 Parity Gate (`verify_pinpoint_receipt`):**
   - Requires HMAC-SHA256 signed receipt with `exit_code == 0`, `passed_checks == total_checks > 0`, and 100% SHA-256 parity across Workspace, Desktop Staging, and Game Directory.

## Verification
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
