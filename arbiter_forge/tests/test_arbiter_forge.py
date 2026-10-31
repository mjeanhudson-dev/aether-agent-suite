"""
Track 4: Automated Verification Suite for Arbiter Forge (`test_arbiter_forge.py`)
Tests Borda/Condorcet consensus across Gemini/Claude/Codex, adversarial red-team vetoes,
blast-radius friction scoring, PINPOINT exit-code-0 enforcement, and SHA-256 deployment parity.
"""

import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from arbiter import (
    ArbiterForgeGatekeeper,
    CandidatePatch,
    FrictionTier,
    ModelBallot,
    ModelRole,
    PinpointVerificationReceipt,
    PromotionStatus,
    compute_blast_radius,
)


class TestArbiterForgeGatekeeper(unittest.TestCase):
    def setUp(self) -> None:
        self.gatekeeper = ArbiterForgeGatekeeper(signing_secret="test-pinpoint-secret-key")
        self.valid_sha = hashlib.sha256(b"verified-binary-build-v1").hexdigest()
        self.parity_targets = {
            "workspace": self.valid_sha,
            "desktop_staging": self.valid_sha,
            "game_directory": self.valid_sha,
        }

    def _make_candidates(self):
        c1 = CandidatePatch(
            candidate_id="patch_alpha",
            author_model=ModelRole.GEMINI_DEEP_SYNTHESIS,
            summary="Implement 200ms C2 smootherstep transition",
            diff_text="+ return t*t*t*(t*(t*6.0 - 15.0) + 10.0);",
            touched_files=("src/steering.cpp",),
            lines_changed=18,
        )
        c2 = CandidatePatch(
            candidate_id="patch_beta",
            author_model=ModelRole.CODEX_DETERMINISTIC_EXEC,
            summary="Linear ramp approximation",
            diff_text="+ return t;",
            touched_files=("src/steering.cpp",),
            lines_changed=6,
        )
        c3 = CandidatePatch(
            candidate_id="patch_gamma",
            author_model=ModelRole.CLAUDE_ADVERSARIAL_AUDIT,
            summary="Smootherstep + boundary clamp",
            diff_text="+ t = clamp(t, 0.0, 1.0);\n+ return 6*pow(t,5) - 15*pow(t,4) + 10*pow(t,3);",
            touched_files=("src/steering.cpp", "tests/test_steering.cpp"),
            lines_changed=35,
        )
        return [c1, c2, c3]

    def test_heterogeneous_consensus_and_pinpoint_promotion(self) -> None:
        candidates = self._make_candidates()
        ballots = [
            ModelBallot(
                voter_role=ModelRole.GEMINI_DEEP_SYNTHESIS,
                ranked_candidate_ids=("patch_gamma", "patch_alpha", "patch_beta"),
                scores_by_candidate={"patch_gamma": 96.0, "patch_alpha": 90.0, "patch_beta": 60.0},
            ),
            ModelBallot(
                voter_role=ModelRole.CLAUDE_ADVERSARIAL_AUDIT,
                ranked_candidate_ids=("patch_gamma", "patch_alpha", "patch_beta"),
                scores_by_candidate={"patch_gamma": 98.0, "patch_alpha": 88.0, "patch_beta": 50.0},
            ),
            ModelBallot(
                voter_role=ModelRole.CODEX_DETERMINISTIC_EXEC,
                ranked_candidate_ids=("patch_alpha", "patch_gamma", "patch_beta"),
                scores_by_candidate={"patch_alpha": 94.0, "patch_gamma": 92.0, "patch_beta": 70.0},
            ),
        ]

        receipt = PinpointVerificationReceipt.create_signed(
            candidate_id="patch_gamma",
            exit_code=0,
            total_checks=147,
            passed_checks=147,
            artifact_sha256_by_target=self.parity_targets,
            timestamp_iso="2026-10-30T21:00:00Z",
            signing_secret="test-pinpoint-secret-key",
        )

        decision = self.gatekeeper.evaluate_and_gate(
            candidates=candidates,
            ballots=ballots,
            receipts_by_candidate={"patch_gamma": receipt},
        )

        self.assertEqual(decision.status, PromotionStatus.PROMOTED)
        self.assertEqual(decision.selected_candidate_id, "patch_gamma")
        self.assertEqual(decision.consensus.condorcet_winner_id, "patch_gamma")
        self.assertTrue(decision.pinpoint_verified)
        self.assertTrue(decision.parity_verified)
        self.assertLess(decision.blast_radius_score, 20.0)
        self.assertEqual(decision.friction_tier, FrictionTier.PASSIVE_TELEMETRY)

    def test_adversarial_veto_disqualifies_compromised_top_voted_candidate(self) -> None:
        candidates = self._make_candidates()
        # Suppose Gemini & Codex rank patch_alpha #1, but Claude red-team vetoes patch_alpha
        ballots = [
            ModelBallot(
                voter_role=ModelRole.GEMINI_DEEP_SYNTHESIS,
                ranked_candidate_ids=("patch_alpha", "patch_gamma", "patch_beta"),
                scores_by_candidate={"patch_alpha": 95.0, "patch_gamma": 90.0},
            ),
            ModelBallot(
                voter_role=ModelRole.CODEX_DETERMINISTIC_EXEC,
                ranked_candidate_ids=("patch_alpha", "patch_gamma", "patch_beta"),
                scores_by_candidate={"patch_alpha": 95.0, "patch_gamma": 90.0},
            ),
            ModelBallot(
                voter_role=ModelRole.CLAUDE_ADVERSARIAL_AUDIT,
                ranked_candidate_ids=("patch_gamma", "patch_beta", "patch_alpha"),
                vetoed_candidate_ids=("patch_alpha",),
                audit_notes="Vetoed patch_alpha due to unguarded NaN on zero dt",
            ),
        ]

        consensus = self.gatekeeper.compute_consensus(candidates, ballots)
        self.assertIn("patch_alpha", consensus.vetoed_candidates)
        self.assertEqual(consensus.selected_winner_id, "patch_gamma")

    def test_pinpoint_failure_and_sha256_parity_mismatch_block_promotion(self) -> None:
        candidates = [self._make_candidates()[0]]
        ballots = [
            ModelBallot(
                voter_role=ModelRole.GEMINI_DEEP_SYNTHESIS,
                ranked_candidate_ids=("patch_alpha",),
            )
        ]

        # 1. Failing PINPOINT check (146/147 passed, exit_code=1)
        failing_receipt = PinpointVerificationReceipt.create_signed(
            candidate_id="patch_alpha",
            exit_code=1,
            total_checks=147,
            passed_checks=146,
            artifact_sha256_by_target=self.parity_targets,
            timestamp_iso="2026-10-30T21:00:00Z",
            signing_secret="test-pinpoint-secret-key",
        )
        dec_fail = self.gatekeeper.evaluate_and_gate(
            candidates, ballots, {"patch_alpha": failing_receipt}
        )
        self.assertEqual(dec_fail.status, PromotionStatus.BLOCKED_PINPOINT_FAILURE)
        self.assertFalse(dec_fail.pinpoint_verified)

        # 2. Passing PINPOINT checks, but Desktop Staging SHA-256 drifted from Workspace
        mismatched_targets = dict(self.parity_targets)
        mismatched_targets["desktop_staging"] = hashlib.sha256(b"stale-binary").hexdigest()
        mismatch_receipt = PinpointVerificationReceipt.create_signed(
            candidate_id="patch_alpha",
            exit_code=0,
            total_checks=147,
            passed_checks=147,
            artifact_sha256_by_target=mismatched_targets,
            timestamp_iso="2026-10-30T21:00:00Z",
            signing_secret="test-pinpoint-secret-key",
        )
        dec_parity = self.gatekeeper.evaluate_and_gate(
            candidates, ballots, {"patch_alpha": mismatch_receipt}
        )
        self.assertEqual(dec_parity.status, PromotionStatus.BLOCKED_PARITY_MISMATCH)
        self.assertTrue(dec_parity.pinpoint_verified)
        self.assertFalse(dec_parity.parity_verified)

        # 3. Tampered receipt signature
        tampered_receipt = PinpointVerificationReceipt(
            candidate_id="patch_alpha",
            exit_code=0,
            total_checks=147,
            passed_checks=147,
            artifact_sha256_by_target=self.parity_targets,
            timestamp_iso="2026-10-30T21:00:00Z",
            hmac_signature="0" * 64,
        )
        dec_sig = self.gatekeeper.evaluate_and_gate(
            candidates, ballots, {"patch_alpha": tampered_receipt}
        )
        self.assertEqual(dec_sig.status, PromotionStatus.BLOCKED_INVALID_SIGNATURE)

    def test_high_blast_radius_requires_human_ratification(self) -> None:
        high_blast_patch = CandidatePatch(
            candidate_id="patch_deploy_prod",
            author_model=ModelRole.GEMINI_DEEP_SYNTHESIS,
            summary="Deploy production release and update AGENTS.md",
            diff_text="+ Updated deployment config",
            touched_files=("AGENTS.md", "deploy/prod.yaml"),
            lines_changed=120,
            external_side_effects=("production_deploy", "git_push"),
        )
        score, tier, reasons = compute_blast_radius(high_blast_patch)
        self.assertGreaterEqual(score, 70.0)
        self.assertEqual(tier, FrictionTier.HARD_HAPTIC_DETENT)
        self.assertGreaterEqual(len(reasons), 2)

        ballots = [
            ModelBallot(
                voter_role=ModelRole.GEMINI_DEEP_SYNTHESIS,
                ranked_candidate_ids=("patch_deploy_prod",),
            )
        ]
        receipt = PinpointVerificationReceipt.create_signed(
            candidate_id="patch_deploy_prod",
            exit_code=0,
            total_checks=50,
            passed_checks=50,
            artifact_sha256_by_target=self.parity_targets,
            timestamp_iso="2026-10-30T21:00:00Z",
            signing_secret="test-pinpoint-secret-key",
        )

        # Without human ratification -> HELD_FOR_HUMAN_RATIFICATION
        held_decision = self.gatekeeper.evaluate_and_gate(
            [high_blast_patch], ballots, {"patch_deploy_prod": receipt}, human_ratified=False
        )
        self.assertEqual(held_decision.status, PromotionStatus.HELD_FOR_HUMAN_RATIFICATION)

        # With human ratification -> PROMOTED
        promoted_decision = self.gatekeeper.evaluate_and_gate(
            [high_blast_patch], ballots, {"patch_deploy_prod": receipt}, human_ratified=True
        )
        self.assertEqual(promoted_decision.status, PromotionStatus.PROMOTED)

    def test_condorcet_cycle_falls_back_to_borda_winner_and_empty_inputs(self) -> None:
        candidates = self._make_candidates()
        # Condorcet cycle: A > B > C, B > C > A, C > A > B, but patch_gamma has highest rubric score
        ballots = [
            ModelBallot(
                voter_role=ModelRole.GEMINI_DEEP_SYNTHESIS,
                ranked_candidate_ids=("patch_alpha", "patch_beta", "patch_gamma"),
                scores_by_candidate={"patch_alpha": 70.0, "patch_beta": 70.0, "patch_gamma": 99.0},
            ),
            ModelBallot(
                voter_role=ModelRole.CLAUDE_ADVERSARIAL_AUDIT,
                ranked_candidate_ids=("patch_beta", "patch_gamma", "patch_alpha"),
                scores_by_candidate={"patch_alpha": 70.0, "patch_beta": 70.0, "patch_gamma": 99.0},
            ),
            ModelBallot(
                voter_role=ModelRole.CODEX_DETERMINISTIC_EXEC,
                ranked_candidate_ids=("patch_gamma", "patch_alpha", "patch_beta"),
                scores_by_candidate={"patch_alpha": 70.0, "patch_beta": 70.0, "patch_gamma": 99.0},
            ),
        ]
        consensus = self.gatekeeper.compute_consensus(candidates, ballots)
        self.assertIsNone(consensus.condorcet_winner_id)
        self.assertEqual(consensus.borda_winner_id, "patch_gamma")
        self.assertEqual(consensus.selected_winner_id, "patch_gamma")

        # Empty candidate list edge case
        empty_dec = self.gatekeeper.evaluate_and_gate([], [], {})
        self.assertEqual(empty_dec.status, PromotionStatus.BLOCKED_NO_ELIGIBLE_CANDIDATES)


if __name__ == "__main__":
    unittest.main()
