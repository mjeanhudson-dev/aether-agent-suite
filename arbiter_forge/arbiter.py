"""
Track 4: Heterogeneous Cross-Model Consensus & PINPOINT Gatekeeper (`arbiter.py`)
Implements:
1. Heterogeneous Model Roles:
   - GEMINI_DEEP_SYNTHESIS (Architecture, Mathematical Invariants & Full-Repo Coherence)
   - CLAUDE_ADVERSARIAL_AUDIT (Red-Team Security, Boundary Conditions & Regression Hunting)
   - CODEX_DETERMINISTIC_EXEC (Algorithmic Complexity, Static Invariants & Test Synthesis)
2. Blast-Radius Scorer B(a) in [0, 100] & Friction Tier Mapping:
   - B(a) < 20  -> PASSIVE_TELEMETRY
   - 20 <= B(a) < 70 -> SOFT_CONFIRM
   - B(a) >= 70 -> HARD_HAPTIC_DETENT (Requires explicit human ratification)
3. Borda Count & Condorcet Pairwise Consensus Engine with Adversarial Red-Team Veto
4. Deterministic PINPOINT Exit-Code-0 & Multi-Target SHA-256 Parity Gatekeeper
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


class ModelRole( str, Enum):
    GEMINI_DEEP_SYNTHESIS = "GEMINI_DEEP_SYNTHESIS"
    CLAUDE_ADVERSARIAL_AUDIT = "CLAUDE_ADVERSARIAL_AUDIT"
    CODEX_DETERMINISTIC_EXEC = "CODEX_DETERMINISTIC_EXEC"


class FrictionTier(str, Enum):
    PASSIVE_TELEMETRY = "PASSIVE_TELEMETRY"      # B(a) < 20
    SOFT_CONFIRM = "SOFT_CONFIRM"                # 20 <= B(a) < 70
    HARD_HAPTIC_DETENT = "HARD_HAPTIC_DETENT"    # B(a) >= 70


class PromotionStatus(str, Enum):
    PROMOTED = "PROMOTED"
    HELD_FOR_HUMAN_RATIFICATION = "HELD_FOR_HUMAN_RATIFICATION"
    BLOCKED_ADVERSARIAL_VETO = "BLOCKED_ADVERSARIAL_VETO"
    BLOCKED_PINPOINT_FAILURE = "BLOCKED_PINPOINT_FAILURE"
    BLOCKED_PARITY_MISMATCH = "BLOCKED_PARITY_MISMATCH"
    BLOCKED_INVALID_SIGNATURE = "BLOCKED_INVALID_SIGNATURE"
    BLOCKED_NO_ELIGIBLE_CANDIDATES = "BLOCKED_NO_ELIGIBLE_CANDIDATES"


SENSITIVE_PATH_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|/)(?:AGENTS|CLAUDE|MULTIAGENT_PROTOCOLS)\.md$", re.IGNORECASE),
    re.compile(r"(?:^|/)\.(?:env|agents|claude|cursor|gemini)(?:/|$)", re.IGNORECASE),
    re.compile(r"vehicleset_pc_xinput_.*\.xml$", re.IGNORECASE),
)

DANGEROUS_DIFF_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"dangerouslySkipPermissions\s*[:=]\s*true", re.IGNORECASE),
    re.compile(r"--sandbox\s*=\s*none", re.IGNORECASE),
    re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{20,})"),
    re.compile(r"(?:rm\s+-rf\s+/|rmdir\s+/s\s+/q|DROP\s+TABLE)", re.IGNORECASE),
)

EXTERNAL_SIDE_EFFECT_WEIGHTS: Dict[str, float] = {
    "git_push": 35.0,
    "production_deploy": 45.0,
    "financial_spend": 50.0,
    "network_egress": 25.0,
    "schema_migration": 30.0,
}


@dataclass(frozen=True)
class CandidatePatch:
    candidate_id: str
    author_model: ModelRole
    summary: str
    diff_text: str
    touched_files: Tuple[str, ...] = ()
    lines_changed: int = 0
    external_side_effects: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelBallot:
    voter_role: ModelRole
    ranked_candidate_ids: Tuple[str, ...]  # Ordered from 1st choice (index 0) to last choice
    scores_by_candidate: Dict[str, float] = field(default_factory=dict)  # 0.0..100.0 rubric score
    vetoed_candidate_ids: Tuple[str, ...] = ()
    audit_notes: str = ""


@dataclass(frozen=True)
class PinpointVerificationReceipt:
    candidate_id: str
    exit_code: int
    total_checks: int
    passed_checks: int
    artifact_sha256_by_target: Dict[str, str]  # e.g. {"workspace": "...", "staging": "...", "game_dir": "..."}
    timestamp_iso: str
    hmac_signature: str = ""

    def canonical_payload(self) -> str:
        payload = {
            "artifact_sha256_by_target": dict(sorted(self.artifact_sha256_by_target.items())),
            "candidate_id": self.candidate_id,
            "exit_code": int(self.exit_code),
            "passed_checks": int(self.passed_checks),
            "timestamp_iso": self.timestamp_iso,
            "total_checks": int(self.total_checks),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def create_signed(
        cls,
        candidate_id: str,
        exit_code: int,
        total_checks: int,
        passed_checks: int,
        artifact_sha256_by_target: Dict[str, str],
        timestamp_iso: str,
        signing_secret: str = "arbiter-forge-pinpoint-secret-v1",
    ) -> "PinpointVerificationReceipt":
        unsigned = cls(
            candidate_id=candidate_id,
            exit_code=exit_code,
            total_checks=total_checks,
            passed_checks=passed_checks,
            artifact_sha256_by_target=artifact_sha256_by_target,
            timestamp_iso=timestamp_iso,
            hmac_signature="",
        )
        sig = hmac.new(
            signing_secret.encode("utf-8"),
            unsigned.canonical_payload().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return cls(
            candidate_id=candidate_id,
            exit_code=exit_code,
            total_checks=total_checks,
            passed_checks=passed_checks,
            artifact_sha256_by_target=artifact_sha256_by_target,
            timestamp_iso=timestamp_iso,
            hmac_signature=sig,
        )


@dataclass(frozen=True)
class ConsensusResult:
    borda_scores: Dict[str, float]
    pairwise_matrix: Dict[str, Dict[str, int]]
    condorcet_winner_id: Optional[str]
    borda_winner_id: Optional[str]
    selected_winner_id: Optional[str]
    vetoed_candidates: Tuple[str, ...]


@dataclass(frozen=True)
class ArbiterDecision:
    status: PromotionStatus
    selected_candidate_id: Optional[str]
    blast_radius_score: float
    friction_tier: FrictionTier
    consensus: ConsensusResult
    pinpoint_verified: bool
    parity_verified: bool
    reason: str


def compute_blast_radius(patch: CandidatePatch) -> Tuple[float, FrictionTier, List[str]]:
    """
    Computes Blast-Radius Score B(a) in [0.0, 100.0] and maps to FrictionTier:
    - B(a) < 20  -> PASSIVE_TELEMETRY
    - 20 <= B(a) < 70 -> SOFT_CONFIRM
    - B(a) >= 70 -> HARD_HAPTIC_DETENT
    """
    score = 0.0
    reasons: List[str] = []

    # File count and line churn
    file_score = min(25.0, len(patch.touched_files) * 4.0)
    line_score = min(25.0, (max(0, patch.lines_changed) / 50.0) * 5.0)
    score += file_score + line_score

    # Sensitive path touches
    for fpath in patch.touched_files:
        norm_path = fpath.replace("\\", "/")
        for pat in SENSITIVE_PATH_PATTERNS:
            if pat.search(norm_path):
                score += 40.0
                reasons.append(f"Touches protected path: {norm_path}")
                break

    # External side effects
    for effect in patch.external_side_effects:
        w = EXTERNAL_SIDE_EFFECT_WEIGHTS.get(effect, 20.0)
        score += w
        reasons.append(f"External side effect: {effect} (+{w:.0f})")

    # Dangerous diff payloads
    for pat in DANGEROUS_DIFF_PATTERNS:
        if pat.search(patch.diff_text or ""):
            score += 65.0
            reasons.append(f"Dangerous diff pattern matched: {pat.pattern}")

    clamped = round(max(0.0, min(100.0, score)), 2)
    if clamped < 20.0:
        tier = FrictionTier.PASSIVE_TELEMETRY
    elif clamped < 70.0:
        tier = FrictionTier.SOFT_CONFIRM
    else:
        tier = FrictionTier.HARD_HAPTIC_DETENT

    return clamped, tier, reasons


class ArbiterForgeGatekeeper:
    """
    Cross-Model Consensus & Deterministic PINPOINT Gatekeeper.
    Combines Borda/Condorcet voting across Gemini, Claude, and Codex with
    adversarial red-team vetoes, blast-radius friction gating, and PINPOINT verification receipts.
    """

    DEFAULT_ROLE_WEIGHTS: Dict[ModelRole, float] = {
        ModelRole.GEMINI_DEEP_SYNTHESIS: 1.0,
        ModelRole.CLAUDE_ADVERSARIAL_AUDIT: 1.0,
        ModelRole.CODEX_DETERMINISTIC_EXEC: 1.0,
    }

    def __init__(
        self,
        signing_secret: str = "arbiter-forge-pinpoint-secret-v1",
        role_weights: Optional[Dict[ModelRole, float]] = None,
    ) -> None:
        self.signing_secret = signing_secret
        self.role_weights = dict(self.DEFAULT_ROLE_WEIGHTS)
        if role_weights:
            self.role_weights.update(role_weights)

    def compute_consensus(
        self,
        candidates: Sequence[CandidatePatch],
        ballots: Sequence[ModelBallot],
    ) -> ConsensusResult:
        candidate_ids = [c.candidate_id for c in candidates]
        n = len(candidate_ids)
        if n == 0:
            return ConsensusResult(
                borda_scores={},
                pairwise_matrix={},
                condorcet_winner_id=None,
                borda_winner_id=None,
                selected_winner_id=None,
                vetoed_candidates=(),
            )

        borda_scores: Dict[str, float] = {cid: 0.0 for cid in candidate_ids}
        pairwise: Dict[str, Dict[str, int]] = {
            a: {b: 0 for b in candidate_ids if b != a} for a in candidate_ids
        }
        vetoed: Set[str] = set()

        # Automatic red-team veto if diff contains dangerous secret/sabotage patterns
        for cand in candidates:
            for pat in DANGEROUS_DIFF_PATTERNS:
                if pat.search(cand.diff_text or ""):
                    vetoed.add(cand.candidate_id)

        for ballot in ballots:
            weight = self.role_weights.get(ballot.voter_role, 1.0)
            for v_id in ballot.vetoed_candidate_ids:
                if v_id in borda_scores:
                    vetoed.add(v_id)

            # Borda points: (N - 1 - rank) * weight + normalized quality rubric bonus (0..1)
            seen_in_ballot: Set[str] = set()
            for rank_idx, cid in enumerate(ballot.ranked_candidate_ids):
                if cid not in borda_scores or cid in seen_in_ballot:
                    continue
                seen_in_ballot.add(cid)
                base_borda = float(max(0, n - 1 - rank_idx)) * weight
                rubric_bonus = (float(ballot.scores_by_candidate.get(cid, 0.0)) / 100.0) * 0.5 * weight
                borda_scores[cid] = round(borda_scores[cid] + base_borda + rubric_bonus, 4)

            # Pairwise head-to-head tally for Condorcet matrix
            rank_map: Dict[str, int] = {}
            for idx, cid in enumerate(ballot.ranked_candidate_ids):
                if cid in borda_scores and cid not in rank_map:
                    rank_map[cid] = idx
            for cid in candidate_ids:
                if cid not in rank_map:
                    rank_map[cid] = n + 1

            for i, cid_a in enumerate(candidate_ids):
                for cid_b in candidate_ids[i + 1 :]:
                    if rank_map[cid_a] < rank_map[cid_b]:
                        pairwise[cid_a][cid_b] += 1
                    elif rank_map[cid_b] < rank_map[cid_a]:
                        pairwise[cid_b][cid_a] += 1

        eligible_ids = [cid for cid in candidate_ids if cid not in vetoed]

        # Determine Condorcet winner among eligible candidates
        condorcet_winner: Optional[str] = None
        for cid_a in eligible_ids:
            beats_all = True
            for cid_b in eligible_ids:
                if cid_a == cid_b:
                    continue
                if pairwise[cid_a][cid_b] <= pairwise[cid_b][cid_a]:
                    beats_all = False
                    break
            if beats_all:
                condorcet_winner = cid_a
                break

        borda_winner: Optional[str] = None
        if eligible_ids:
            borda_winner = max(eligible_ids, key=lambda cid: (borda_scores[cid], cid))

        selected_winner = condorcet_winner if condorcet_winner is not None else borda_winner

        return ConsensusResult(
            borda_scores=borda_scores,
            pairwise_matrix=pairwise,
            condorcet_winner_id=condorcet_winner,
            borda_winner_id=borda_winner,
            selected_winner_id=selected_winner,
            vetoed_candidates=tuple(sorted(vetoed)),
        )

    def verify_pinpoint_receipt(
        self,
        receipt: PinpointVerificationReceipt,
    ) -> Tuple[bool, bool, bool, str]:
        """
        Returns (signature_valid, pinpoint_passed, sha256_parity_ok, message).
        """
        expected_sig = hmac.new(
            self.signing_secret.encode("utf-8"),
            receipt.canonical_payload().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not receipt.hmac_signature or not hmac.compare_digest(expected_sig, receipt.hmac_signature):
            return False, False, False, "Invalid or tampered PINPOINT receipt HMAC signature"

        pinpoint_ok = (
            receipt.exit_code == 0
            and receipt.total_checks > 0
            and receipt.passed_checks == receipt.total_checks
        )
        if not pinpoint_ok:
            return (
                True,
                False,
                False,
                f"PINPOINT verification failed: exit_code={receipt.exit_code}, "
                f"passed={receipt.passed_checks}/{receipt.total_checks}",
            )

        targets = receipt.artifact_sha256_by_target
        if not targets:
            return True, True, False, "Missing artifact SHA-256 parity targets"

        unique_hashes = set(targets.values())
        if len(unique_hashes) != 1 or any(len(h) != 64 for h in unique_hashes):
            return (
                True,
                True,
                False,
                f"Cryptographic SHA-256 deployment parity mismatch across targets: {targets}",
            )

        return True, True, True, "100% PINPOINT pass and cryptographic SHA-256 parity verified"

    def evaluate_and_gate(
        self,
        candidates: Sequence[CandidatePatch],
        ballots: Sequence[ModelBallot],
        receipts_by_candidate: Dict[str, PinpointVerificationReceipt],
        human_ratified: bool = False,
    ) -> ArbiterDecision:
        consensus = self.compute_consensus(candidates, ballots)

        if not candidates:
            return ArbiterDecision(
                status=PromotionStatus.BLOCKED_NO_ELIGIBLE_CANDIDATES,
                selected_candidate_id=None,
                blast_radius_score=0.0,
                friction_tier=FrictionTier.PASSIVE_TELEMETRY,
                consensus=consensus,
                pinpoint_verified=False,
                parity_verified=False,
                reason="No candidate patches submitted",
            )

        if consensus.selected_winner_id is None:
            return ArbiterDecision(
                status=PromotionStatus.BLOCKED_ADVERSARIAL_VETO,
                selected_candidate_id=None,
                blast_radius_score=100.0,
                friction_tier=FrictionTier.HARD_HAPTIC_DETENT,
                consensus=consensus,
                pinpoint_verified=False,
                parity_verified=False,
                reason=f"All candidate patches were vetoed by adversarial audit: {consensus.vetoed_candidates}",
            )

        winner_id = consensus.selected_winner_id
        winner_patch = next(c for c in candidates if c.candidate_id == winner_id)
        blast_score, friction_tier, _ = compute_blast_radius(winner_patch)

        receipt = receipts_by_candidate.get(winner_id)
        if receipt is None:
            return ArbiterDecision(
                status=PromotionStatus.BLOCKED_PINPOINT_FAILURE,
                selected_candidate_id=winner_id,
                blast_radius_score=blast_score,
                friction_tier=friction_tier,
                consensus=consensus,
                pinpoint_verified=False,
                parity_verified=False,
                reason=f"Missing PINPOINT verification receipt for candidate {winner_id}",
            )

        sig_ok, pinpoint_ok, parity_ok, msg = self.verify_pinpoint_receipt(receipt)
        if not sig_ok:
            return ArbiterDecision(
                status=PromotionStatus.BLOCKED_INVALID_SIGNATURE,
                selected_candidate_id=winner_id,
                blast_radius_score=blast_score,
                friction_tier=friction_tier,
                consensus=consensus,
                pinpoint_verified=False,
                parity_verified=False,
                reason=msg,
            )

        if not pinpoint_ok:
            return ArbiterDecision(
                status=PromotionStatus.BLOCKED_PINPOINT_FAILURE,
                selected_candidate_id=winner_id,
                blast_radius_score=blast_score,
                friction_tier=friction_tier,
                consensus=consensus,
                pinpoint_verified=False,
                parity_verified=False,
                reason=msg,
            )

        if not parity_ok:
            return ArbiterDecision(
                status=PromotionStatus.BLOCKED_PARITY_MISMATCH,
                selected_candidate_id=winner_id,
                blast_radius_score=blast_score,
                friction_tier=friction_tier,
                consensus=consensus,
                pinpoint_verified=True,
                parity_verified=False,
                reason=msg,
            )

        # If Blast Radius >= 70 (HARD_HAPTIC_DETENT), require explicit human ratification
        if friction_tier == FrictionTier.HARD_HAPTIC_DETENT and not human_ratified:
            return ArbiterDecision(
                status=PromotionStatus.HELD_FOR_HUMAN_RATIFICATION,
                selected_candidate_id=winner_id,
                blast_radius_score=blast_score,
                friction_tier=friction_tier,
                consensus=consensus,
                pinpoint_verified=True,
                parity_verified=True,
                reason=(
                    f"Candidate {winner_id} passed consensus and PINPOINT checks, "
                    f"but blast radius B(a)={blast_score} >= 70 requires human steering ratification"
                ),
            )

        return ArbiterDecision(
            status=PromotionStatus.PROMOTED,
            selected_candidate_id=winner_id,
            blast_radius_score=blast_score,
            friction_tier=friction_tier,
            consensus=consensus,
            pinpoint_verified=True,
            parity_verified=True,
            reason=f"Candidate {winner_id} promoted via cross-model consensus and 100% PINPOINT parity",
        )
