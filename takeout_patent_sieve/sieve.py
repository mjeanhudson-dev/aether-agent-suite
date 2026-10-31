"""
Track 2: Streaming Google Takeout & Patent Bootloader/Instantiator Synthesis Pipeline (`sieve.py`)
Implements:
1. O(1)-RAM Streaming Parser for Google Takeout (Gemini Apps MyActivity.json, Google Keep .json, Drive notes)
2. Multi-turn Thread Reconstructor (by /app/c/<conversation_id> or Δt < 45 min)
3. Zero-Dirty-Logic Quarantine Sieve (<tainted_raw_idea isolation="quarantined">)
4. Signal Density Scorer S(d) = w1*Count(PatentLexicon) + w2*Count(ArchPrimitives) + w3*I(HasCodeOrMath) + w4*ln(TurnDepth)
5. 128-Permutation MinHash / Shingle Jaccard Draft Collapser (preserving conception-date lineage)
6. SQLite + FTS5 Local Knowledge Vault
"""

from __future__ import annotations

import dataclasses
import unicodedata

HOMOGLYPH_MAP = {
    'а': 'a', 'с': 'c', 'е': 'e', 'о': 'o', 'р': 'p', 'ѕ': 's', 'х': 'x', 'у': 'y',
    'і': 'i', 'ј': 'j', 'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E', 'Н': 'H', 'І': 'I',
    'Ј': 'J', 'К': 'K', 'М': 'M', 'О': 'O', 'Р': 'P', 'Т': 'T', 'Х': 'X', 'У': 'Y',
}

def normalize_confusables(text: str) -> str:
    """Normalize Unicode confusables, strip zero-width characters, and map homoglyphs."""
    if not text:
        return ""
    # Strip zero-width & bidirectional formatting characters
    cleaned = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\u00ad]", "", text)
    # NFKD decomposition
    nfkd = unicodedata.normalize("NFKD", cleaned)
    # Map homoglyphs
    return "".join(HOMOGLYPH_MAP.get(ch, ch) for ch in nfkd)
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import html
import io
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple
import zipfile


PATENT_LEXICON: Tuple[str, ...] = (
    "claim",
    "embodiment",
    "invariant",
    "plurality",
    "apparatus",
    "method",
    "patent",
    "novel",
    "prior art",
    "conception",
    "smootherstep",
    "pre-compensation",
    "quarantine",
    "airlock",
    "lattice",
    "fair-queuing",
    "dwfq",
    "haptic",
    "telemetry",
    "consensus",
)

ARCH_PRIMITIVES: Tuple[str, ...] = (
    "ast",
    "hmac",
    "sha256",
    "sha-256",
    "sqlite",
    "fts5",
    "minhash",
    "1-euro",
    "xinput",
    "directinput",
    "hid",
    "grpc",
    "websocket",
    "onnx",
    "vad",
    "sidechain",
    "borda",
    "condorcet",
    "pinpoint",
    "macaroon",
    "taint",
)

# Prompt injection, shell sabotage, and dirty-logic override signatures
DIRTY_INJECTION_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|system)\s+(?:instructions|constraints)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:in\s+)?(?:dan|developer|unrestricted|jailbreak)\s+mode", re.IGNORECASE),
    re.compile(r"dangerouslySkipPermissions\s*[:=]\s*true", re.IGNORECASE),
    re.compile(r"--sandbox\s*=\s*none", re.IGNORECASE),
    re.compile(r"<\s*script\b[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"(?:rm\s+-rf\s+/|rmdir\s+/s\s+/q|format\s+[a-z]:|del\s+/f\s+/s\s+/q)", re.IGNORECASE),
    re.compile(r"(?:drop\s+table|union\s+select\s+null|;\s*shutdown\b)", re.IGNORECASE),
    re.compile(r"curl\s+[^\n|]+\|\s*(?:ba)?sh", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*override", re.IGNORECASE),
)

# Conversational dead-ends and explicitly abandoned tangents
DEAD_END_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?:never\s*mind|forget\s+that\s+tangent|scratch\s+that|ignore\s+that\s+last\s+idea)\b.*$", re.IGNORECASE),
    re.compile(r"^\s*(?:wait\s+no\s+that\s+is\s+wrong|dirty\s+hack\s+do\s+not\s+use|abandoned\s+draft)\b.*$", re.IGNORECASE),
)

# Mathematical invariant extraction patterns (LaTeX blocks, inline equations, symbolic equations)
MATH_INVARIANT_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"\$\$([^$]+)\$\$", re.DOTALL),
    re.compile(r"\$([^$\n]{3,160})\$"),
    re.compile(
        r"\b([A-Za-z_][A-Za-z0-9_\\{}()^, ]{0,30}\s*(?:=|\\le|\\ge|<=|>=|\\approx|\\propto)\s*"
        r"[-+0-9A-Za-z_\\{}()^.*/ |,\[\]]{4,140})"
    ),
)

NORMATIVE_RULE_KEYWORDS: Tuple[str, ...] = (
    "must",
    "never",
    "invariant",
    "shall",
    "required",
    "enforce",
    "guarantees",
    "pre-compensat",
    "quarantine",
    "airlock",
    "deadzone",
    "smootherstep",
    "taint",
    "pinpoint",
)

HTML_TAG_RE = re.compile(r"<[^>]+>")
CONV_ID_RE = re.compile(r"/app/c/([A-Za-z0-9_-]+)")


def _strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"</\s*p\s*>", "\n", text, flags=re.IGNORECASE)
    text = HTML_TAG_RE.sub("", text)
    return html.unescape(text).strip()


def _parse_iso_timestamp(ts_str: str) -> datetime:
    if not ts_str:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    cleaned = ts_str.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class TakeoutRecord:
    record_id: str
    source_type: str  # "gemini_activity", "keep_note", "drive_doc"
    conversation_id: Optional[str]
    timestamp_iso: str
    prompt_text: str
    response_text: str
    labels: Tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def combined_text(self) -> str:
        parts = [p for p in (self.prompt_text.strip(), self.response_text.strip()) if p]
        return "\n\n".join(parts)

    @property
    def timestamp_dt(self) -> datetime:
        return _parse_iso_timestamp(self.timestamp_iso)


@dataclass
class ReconstructedThread:
    thread_id: str
    records: List[TakeoutRecord]
    conception_timestamp: str
    terminal_timestamp: str

    @property
    def turn_depth(self) -> int:
        return len(self.records)

    @property
    def combined_text(self) -> str:
        return "\n\n---\n\n".join(r.combined_text for r in self.records if r.combined_text)


@dataclass(frozen=True)
class QuarantinedArtifact:
    artifact_id: str
    raw_sha256: str
    quarantined_xml: str
    sanitized_text: str
    stripped_injections: Tuple[str, ...]
    stripped_dead_ends: Tuple[str, ...]
    extracted_invariants: Tuple[str, ...]
    extracted_domain_rules: Tuple[str, ...]
    signal_score: float
    taint_label: str = "QUARANTINED_DATA"


@dataclass(frozen=True)
class CanonicalPatentClaim:
    claim_id: str
    thread_id: str
    title: str
    canonical_text: str
    conception_timestamp: str
    terminal_timestamp: str
    revision_count: int
    lineage_hashes: Tuple[str, ...]
    extracted_invariants: Tuple[str, ...]
    extracted_domain_rules: Tuple[str, ...]
    signal_score: float
    quarantined_xml: str


class TakeoutArchiveStreamer:
    """
    Zero-Cloud O(1)-RAM Streaming Parser for Google Takeout Records (Gemini MyActivity, Keep, Drive).
    """

    @staticmethod
    def parse_gemini_activity_item(item: Dict[str, Any], idx: int = 0) -> TakeoutRecord:
        raw_title = str(item.get("title", "") or "")
        prompt_text = re.sub(r"^Prompted\s+", "", raw_title, flags=re.IGNORECASE).strip()
        title_url = str(item.get("titleUrl", "") or "")
        match = CONV_ID_RE.search(title_url)
        conv_id = match.group(1) if match else None

        time_iso = str(item.get("time", "") or "1970-01-01T00:00:00Z")
        safe_html_items = item.get("safeHtmlItem") or []
        html_chunks: List[str] = []
        if isinstance(safe_html_items, list):
            for entry in safe_html_items:
                if isinstance(entry, dict) and entry.get("html"):
                    html_chunks.append(_strip_html(str(entry["html"])))

        subtitles = item.get("subtitles") or []
        subtitle_texts: List[str] = []
        if isinstance(subtitles, list):
            for sub in subtitles:
                if isinstance(sub, dict) and sub.get("name"):
                    subtitle_texts.append(str(sub["name"]))

        response_text = "\n".join(c for c in html_chunks if c)
        rec_hash = hashlib.sha256(f"{title_url}|{time_iso}|{prompt_text}|{idx}".encode("utf-8")).hexdigest()[:12]

        return TakeoutRecord(
            record_id=f"gem_{rec_hash}",
            source_type="gemini_activity",
            conversation_id=conv_id,
            timestamp_iso=time_iso,
            prompt_text=prompt_text,
            response_text=response_text,
            labels=tuple(subtitle_texts),
            metadata={"titleUrl": title_url},
        )

    @staticmethod
    def parse_keep_note(note: Dict[str, Any], idx: int = 0) -> TakeoutRecord:
        title = str(note.get("title", "") or "")
        text_content = str(note.get("textContent", "") or "")
        list_items = note.get("listContent") or []
        if isinstance(list_items, list) and list_items:
            checklist = "\n".join(
                f"- [{'x' if it.get('isChecked') else ' '}] {it.get('text', '')}"
                for it in list_items
                if isinstance(it, dict)
            )
            text_content = f"{text_content}\n{checklist}".strip()

        usec = note.get("userEditedTimestampUsec") or note.get("createdTimestampUsec") or 0
        try:
            usec_int = int(usec)
            if usec_int > 0:
                dt = datetime.fromtimestamp(usec_int / 1_000_000.0, tz=timezone.utc)
                time_iso = dt.isoformat().replace("+00:00", "Z")
            else:
                time_iso = "1970-01-01T00:00:00Z"
        except (ValueError, TypeError, OSError):
            time_iso = "1970-01-01T00:00:00Z"

        raw_labels = note.get("labels") or []
        labels = tuple(
            str(lbl.get("name"))
            for lbl in raw_labels
            if isinstance(lbl, dict) and lbl.get("name")
        )
        rec_hash = hashlib.sha256(f"keep|{title}|{time_iso}|{idx}".encode("utf-8")).hexdigest()[:12]

        return TakeoutRecord(
            record_id=f"keep_{rec_hash}",
            source_type="keep_note",
            conversation_id=f"keep_{rec_hash}",
            timestamp_iso=time_iso,
            prompt_text=title,
            response_text=text_content,
            labels=labels,
            metadata={"isPinned": bool(note.get("isPinned", False))},
        )

    @classmethod
    def stream_from_records(cls, raw_items: Iterable[Dict[str, Any]]) -> Iterator[TakeoutRecord]:
        for idx, item in enumerate(raw_items):
            if not isinstance(item, dict):
                continue
            if "textContent" in item or "listContent" in item or "createdTimestampUsec" in item:
                yield cls.parse_keep_note(item, idx=idx)
            else:
                yield cls.parse_gemini_activity_item(item, idx=idx)

    @classmethod
    def _stream_json_file(cls, fp: io.TextIOBase) -> Iterator[TakeoutRecord]:
        first_char = ""
        while True:
            ch = fp.read(1)
            if not ch:
                return
            if not ch.isspace():
                first_char = ch
                break
        if first_char != "[":
            rest = first_char + fp.read()
            try:
                data = json.loads(rest)
                if isinstance(data, list):
                    yield from cls.stream_from_records(data)
                elif isinstance(data, dict):
                    yield from cls.stream_from_records([data])
            except Exception:
                pass
            return

        decoder = json.JSONDecoder()
        buffer = ""
        chunk_size = 65536
        idx = 0
        while True:
            chunk = fp.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            while True:
                buffer = buffer.lstrip()
                if not buffer or buffer[0] == "]":
                    break
                if buffer[0] == ",":
                    buffer = buffer[1:].lstrip()
                    if not buffer:
                        break
                try:
                    obj, offset = decoder.raw_decode(buffer)
                    buffer = buffer[offset:]
                    idx += 1
                    if isinstance(obj, dict):
                        if "title" in obj or "titleUrl" in obj:
                            yield cls.parse_gemini_activity_item(obj, idx=idx)
                        elif "user_turn" in obj or "prompt" in obj or "question" in obj:
                            yield cls.parse_chat_thread_turn(obj, idx=idx)
                        else:
                            yield cls.parse_chat_thread_turn(obj, idx=idx)
                except json.JSONDecodeError:
                    break

    @classmethod
    def stream_from_zip(cls, zip_path: Path | str) -> Iterator[TakeoutRecord]:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for idx, info in enumerate(zf.infolist()):
                if info.is_dir():
                    continue
                lower_name = info.filename.lower()
                if lower_name.endswith(".json"):
                    with zf.open(info, "r") as fp:
                        wrapper = io.TextIOWrapper(fp, encoding="utf-8", errors="replace")
                        yield from cls._stream_json_file(wrapper)
                elif lower_name.endswith((".md", ".txt")):
                    with zf.open(info, "r") as fp:
                        content = fp.read().decode("utf-8", errors="replace")
                        rec_hash = hashlib.sha256(f"drive|{info.filename}|{idx}".encode("utf-8")).hexdigest()[:12]
                        yield TakeoutRecord(
                            record_id=f"drv_{rec_hash}",
                            source_type="drive_doc",
                            conversation_id=f"drv_{rec_hash}",
                            timestamp_iso="1970-01-01T00:00:00Z",
                            prompt_text=Path(info.filename).stem,
                            response_text=content,
                        )

    @staticmethod
    def reconstruct_threads(
        records: Iterable[TakeoutRecord],
        max_cluster_gap_seconds: float = 45.0 * 60.0,
    ) -> List[ReconstructedThread]:
        """
        Reconstruct multi-turn conversation threads by grouping on `/app/c/<conversation_id>`
        or clustering contiguous timestamps within Δt < 45 minutes, sorted ascending by time.
        """
        by_explicit_id: Dict[str, List[TakeoutRecord]] = {}
        unthreaded: List[TakeoutRecord] = []

        for rec in records:
            if rec.conversation_id:
                by_explicit_id.setdefault(rec.conversation_id, []).append(rec)
            else:
                unthreaded.append(rec)

        threads: List[ReconstructedThread] = []

        for conv_id, group in by_explicit_id.items():
            sorted_group = sorted(group, key=lambda r: (r.timestamp_dt, r.record_id))
            threads.append(
                ReconstructedThread(
                    thread_id=conv_id,
                    records=sorted_group,
                    conception_timestamp=sorted_group[0].timestamp_iso,
                    terminal_timestamp=sorted_group[-1].timestamp_iso,
                )
            )

        if unthreaded:
            sorted_unthreaded = sorted(unthreaded, key=lambda r: (r.timestamp_dt, r.record_id))
            current_cluster: List[TakeoutRecord] = [sorted_unthreaded[0]]
            cluster_idx = 1

            for rec in sorted_unthreaded[1:]:
                prev_dt = current_cluster[-1].timestamp_dt
                gap = abs((rec.timestamp_dt - prev_dt).total_seconds())
                if gap <= max_cluster_gap_seconds:
                    current_cluster.append(rec)
                else:
                    t_id = f"cluster_{cluster_idx:04d}_{current_cluster[0].record_id}"
                    threads.append(
                        ReconstructedThread(
                            thread_id=t_id,
                            records=current_cluster,
                            conception_timestamp=current_cluster[0].timestamp_iso,
                            terminal_timestamp=current_cluster[-1].timestamp_iso,
                        )
                    )
                    cluster_idx += 1
                    current_cluster = [rec]

            if current_cluster:
                t_id = f"cluster_{cluster_idx:04d}_{current_cluster[0].record_id}"
                threads.append(
                    ReconstructedThread(
                        thread_id=t_id,
                        records=current_cluster,
                        conception_timestamp=current_cluster[0].timestamp_iso,
                        terminal_timestamp=current_cluster[-1].timestamp_iso,
                    )
                )

        return sorted(threads, key=lambda t: (_parse_iso_timestamp(t.conception_timestamp), t.thread_id))


class ZeroDirtyLogicSieve:
    """
    Implements the Zero-Dirty-Logic Quarantine Sieve:
    - Isolates raw archive streams inside `<tainted_raw_idea isolation="quarantined">`
    - Strips prompt injection payloads & conversational dead-ends
    - Extracts clean mathematical invariants and domain rules
    - Computes Signal Density Score S(d)
    """

    def __init__(
        self,
        w1_patent: float = 2.0,
        w2_arch: float = 1.5,
        w3_code_or_math: float = 5.0,
        w4_turn_depth: float = 3.0,
    ) -> None:
        self.w1 = w1_patent
        self.w2 = w2_arch
        self.w3 = w3_code_or_math
        self.w4 = w4_turn_depth

    def score_signal_density(self, text: str, turn_depth: int = 1) -> float:
        """
        S(d) = w1 * Count(PatentLexicon) + w2 * Count(ArchPrimitives) + w3 * I(HasCodeOrMath) + w4 * ln(TurnDepth)
        Uses word-boundary matching to prevent substring false positives ('ast' matching 'last' or 'fast').
        """
        if not text or not text.strip():
            return 0.0

        lower = text.lower()
        patent_pat = re.compile(r"\b(?:" + "|".join(re.escape(term) for term in PATENT_LEXICON) + r")\b", re.IGNORECASE)
        arch_pat = re.compile(r"\b(?:" + "|".join(re.escape(term) for term in ARCH_PRIMITIVES) + r")\b", re.IGNORECASE)
        patent_hits = len(patent_pat.findall(lower))
        arch_hits = len(arch_pat.findall(lower))

        has_math_or_code = bool(
            "$$" in text
            or "```" in text
            or re.search(r"[A-Za-z_]\([A-Za-z0-9_,]+\)\s*=", text)
            or re.search(r"\b(?:def|class|function|export|struct)\s+[A-Za-z_]", text)
            or re.search(r"\\(?:frac|sqrt|sum|operatorname|cos|sin|theta|omega|beta|lambda)\b", text)
        )

        depth = max(1, int(turn_depth))
        score = (
            self.w1 * float(patent_hits)
            + self.w2 * float(arch_hits)
            + self.w3 * (1.0 if has_math_or_code else 0.0)
            + self.w4 * math.log(float(depth))
        )
        return round(score, 4)

    def quarantine_and_sieve(
        self,
        raw_text: str,
        artifact_id: str = "raw_001",
        turn_depth: int = 1,
    ) -> QuarantinedArtifact:
        raw_str = raw_text or ""
        raw_sha256 = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

        # Escape XML/HTML entities so raw content can NEVER break out of <tainted_raw_idea>
        escaped_raw = html.escape(raw_str, quote=True)
        quarantined_xml = (
            f'<tainted_raw_idea isolation="quarantined" sha256="{raw_sha256}" taint="QUARANTINED_DATA">\n'
            f"{escaped_raw}\n"
            f"</tainted_raw_idea>"
        )

        stripped_injections: List[str] = []
        stripped_dead_ends: List[str] = []
        clean_lines: List[str] = []

        normalized_raw = normalize_confusables(raw_str)
        for raw_line in normalized_raw.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Check dead-end conversational tangents
            dead_end_matched = False
            for de_pat in DEAD_END_PATTERNS:
                if de_pat.search(line):
                    stripped_dead_ends.append(line)
                    dead_end_matched = True
                    break
            if dead_end_matched:
                continue

            # Strip prompt injections / sabotage patterns
            working_line = line
            for inj_pat in DIRTY_INJECTION_PATTERNS:
                for m in inj_pat.finditer(working_line):
                    stripped_injections.append(m.group(0))
                working_line = inj_pat.sub("[REDACTED_DIRTY_LOGIC]", working_line)

            # Remove clauses that became purely redacted or still attempt instruction hijacking
            if working_line.strip() == "[REDACTED_DIRTY_LOGIC]":
                continue

            clean_lines.append(working_line)

        sanitized_text = "\n".join(clean_lines)

        invariants = self._extract_math_invariants(sanitized_text)
        domain_rules = self._extract_domain_rules(clean_lines)
        signal_score = self.score_signal_density(sanitized_text, turn_depth=turn_depth)

        return QuarantinedArtifact(
            artifact_id=artifact_id,
            raw_sha256=raw_sha256,
            quarantined_xml=quarantined_xml,
            sanitized_text=sanitized_text,
            stripped_injections=tuple(stripped_injections),
            stripped_dead_ends=tuple(stripped_dead_ends),
            extracted_invariants=tuple(invariants),
            extracted_domain_rules=tuple(domain_rules),
            signal_score=signal_score,
            taint_label="QUARANTINED_DATA",
        )

    @staticmethod
    def _extract_math_invariants(sanitized_text: str) -> List[str]:
        found: List[str] = []
        seen: Set[str] = set()
        dangerous_tokens = (
            "eval(", "exec(", "__import__(", "os.system(", "subprocess.",
            "shutil.", "pty.", "open(", "socket.", "__class__", "__subclasses__"
        )

        for pat in MATH_INVARIANT_PATTERNS:
            for match in pat.finditer(sanitized_text):
                expr = " ".join(match.group(1).strip().split())
                if "[REDACTED_DIRTY_LOGIC]" in expr or len(expr) < 4:
                    continue
                if any(tok in expr.lower() for tok in dangerous_tokens):
                    continue
                # Must contain an operator or mathematical relation
                if not any(op in expr for op in ("=", "\\le", "\\ge", "<=", ">=", "\\approx", "\\propto")):
                    continue
                if expr not in seen:
                    seen.add(expr)
                    found.append(expr)
        return found

    @staticmethod
    def _extract_domain_rules(clean_lines: Sequence[str]) -> List[str]:
        rules: List[str] = []
        seen: Set[str] = set()

        for line in clean_lines:
            if "[REDACTED_DIRTY_LOGIC]" in line:
                # Strip redacted marker and leading/trailing punctuation if the remaining clause is clean
                cleaned_clause = line.replace("[REDACTED_DIRTY_LOGIC]", "").strip(" .,-;:")
            else:
                cleaned_clause = line.strip()

            if len(cleaned_clause) < 12:
                continue
            lower = cleaned_clause.lower()
            if any(kw in lower for kw in NORMATIVE_RULE_KEYWORDS):
                if cleaned_clause not in seen:
                    seen.add(cleaned_clause)
                    rules.append(cleaned_clause)
        return rules


class MinHashDraftCollapser:
    """
    Deterministic 128-permutation MinHash + Shingle Jaccard Draft Collapser.
    Collapses iterative drafts (Jaccard >= threshold, default 0.70) into a single
    CanonicalPatentClaim promoting the latest terminal revision while preserving
    the earliest conception timestamp and full SHA-256 lineage.
    """

    def __init__(self, num_perm: int = 128, jaccard_threshold: float = 0.70) -> None:
        self.num_perm = num_perm
        self.jaccard_threshold = jaccard_threshold
        self._seeds: Tuple[bytes, ...] = tuple(f"minhash_salt_{i:03d}".encode("utf-8") for i in range(num_perm))

    @staticmethod
    def extract_shingles(text: str, k: int = 2) -> Set[str]:
        tokens = re.findall(r"[a-z0-9_]+", (text or "").lower())
        if not tokens:
            return set()
        if len(tokens) < k:
            return {" ".join(tokens)}
        shingles = {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}
        # Include unigram anchor tokens so short technical claims compare accurately
        shingles.update(t for t in tokens if len(t) > 3)
        return shingles

    def compute_signature(self, text: str) -> Tuple[int, ...]:
        shingles = self.extract_shingles(text)
        if not shingles:
            return tuple(0 for _ in range(self.num_perm))

        sig: List[int] = []
        encoded_shingles = [s.encode("utf-8") for s in sorted(shingles)]
        for salt in self._seeds:
            min_hash = min(
                int.from_bytes(hashlib.blake2b(sh, key=salt, digest_size=4).digest(), "big")
                for sh in encoded_shingles
            )
            sig.append(min_hash)
        return tuple(sig)

    def estimate_similarity(self, text_a: str, text_b: str) -> float:
        sh_a = self.extract_shingles(text_a)
        sh_b = self.extract_shingles(text_b)
        if not sh_a or not sh_b:
            return 0.0
        exact_jaccard = len(sh_a & sh_b) / float(len(sh_a | sh_b))
        sig_a = self.compute_signature(text_a)
        sig_b = self.compute_signature(text_b)
        minhash_est = sum(1 for a, b in zip(sig_a, sig_b) if a == b) / float(self.num_perm)
        return max(exact_jaccard, minhash_est)

    def collapse_thread_drafts(
        self,
        thread: ReconstructedThread,
        sieve: Optional[ZeroDirtyLogicSieve] = None,
    ) -> List[CanonicalPatentClaim]:
        active_sieve = sieve or ZeroDirtyLogicSieve()
        sorted_records = sorted(thread.records, key=lambda r: (r.timestamp_dt, r.record_id))
        if not sorted_records:
            return []

        clusters: List[List[Tuple[TakeoutRecord, QuarantinedArtifact]]] = []

        for rec in sorted_records:
            art = active_sieve.quarantine_and_sieve(
                rec.combined_text,
                artifact_id=rec.record_id,
                turn_depth=len(sorted_records),
            )
            placed = False
            for cluster in clusters:
                _, prev_art = cluster[-1]
                sim = self.estimate_similarity(prev_art.sanitized_text, art.sanitized_text)
                if sim >= self.jaccard_threshold:
                    cluster.append((rec, art))
                    placed = True
                    break
            if not placed:
                clusters.append([(rec, art)])

        claims: List[CanonicalPatentClaim] = []
        for idx, cluster in enumerate(clusters, start=1):
            first_rec, _ = cluster[0]
            terminal_rec, _ = cluster[-1]

            # Select canonical artifact based on highest signal density & completeness
            best_rec, best_art = max(
                cluster,
                key=lambda pair: (pair[1].signal_score, len(pair[1].sanitized_text), pair[0].timestamp_iso)
            )

            lineage_hashes = tuple(art.raw_sha256 for _, art in cluster)
            all_invariants: List[str] = []
            all_rules: List[str] = []
            for _, art in cluster:
                for inv in art.extracted_invariants:
                    if inv not in all_invariants:
                        all_invariants.append(inv)
                for rule in art.extracted_domain_rules:
                    if rule not in all_rules:
                        all_rules.append(rule)

            title = best_rec.prompt_text.splitlines()[0][:80] if best_rec.prompt_text else f"Claim {idx}"
            claims.append(
                CanonicalPatentClaim(
                    claim_id=f"claim_{thread.thread_id}_{idx:02d}",
                    thread_id=thread.thread_id,
                    title=title,
                    canonical_text=best_art.sanitized_text,
                    conception_timestamp=first_rec.timestamp_iso,
                    terminal_timestamp=terminal_rec.timestamp_iso,
                    revision_count=len(cluster),
                    lineage_hashes=lineage_hashes,
                    extracted_invariants=tuple(all_invariants),
                    extracted_domain_rules=tuple(all_rules),
                    signal_score=best_art.signal_score,
                    quarantined_xml=best_art.quarantined_xml,
                )
            )

        return claims


class TakeoutKnowledgeVault:
    """
    SQLite + FTS5 Local Knowledge Vault (`takeout_vault.db`) storing canonical claims,
    quarantined raw payloads, conception timestamps, and signal density scores.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._fts5_enabled = False
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS canonical_claims (
                claim_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                title TEXT NOT NULL,
                canonical_text TEXT NOT NULL,
                conception_timestamp TEXT NOT NULL,
                terminal_timestamp TEXT NOT NULL,
                revision_count INTEGER NOT NULL,
                lineage_hashes_json TEXT NOT NULL,
                invariants_json TEXT NOT NULL,
                domain_rules_json TEXT NOT NULL,
                signal_score REAL NOT NULL,
                quarantined_xml TEXT NOT NULL
            )
            """
        )
        try:
            cur.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
                    claim_id UNINDEXED,
                    title,
                    canonical_text,
                    invariants_text,
                    domain_rules_text
                )
                """
            )
            self._fts5_enabled = True
        except sqlite3.OperationalError:
            self._fts5_enabled = False
        self.conn.commit()

    def upsert_claim(self, claim: CanonicalPatentClaim) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO canonical_claims (
                claim_id, thread_id, title, canonical_text,
                conception_timestamp, terminal_timestamp, revision_count,
                lineage_hashes_json, invariants_json, domain_rules_json,
                signal_score, quarantined_xml
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim.claim_id,
                claim.thread_id,
                claim.title,
                claim.canonical_text,
                claim.conception_timestamp,
                claim.terminal_timestamp,
                claim.revision_count,
                json.dumps(list(claim.lineage_hashes)),
                json.dumps(list(claim.extracted_invariants)),
                json.dumps(list(claim.extracted_domain_rules)),
                claim.signal_score,
                claim.quarantined_xml,
            ),
        )
        if self._fts5_enabled:
            cur.execute("DELETE FROM claims_fts WHERE claim_id = ?", (claim.claim_id,))
            cur.execute(
                """
                INSERT INTO claims_fts (claim_id, title, canonical_text, invariants_text, domain_rules_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    claim.claim_id,
                    claim.title,
                    claim.canonical_text,
                    "\n".join(claim.extracted_invariants),
                    "\n".join(claim.extracted_domain_rules),
                ),
            )
        self.conn.commit()

    def search_claims(self, query: str, min_signal_score: float = 0.0) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        if self._fts5_enabled and query.strip():
            safe_q = re.sub(r"[^\w\s]", " ", query).strip()
            if safe_q:
                fts_expr = " OR ".join(f'"{tok}"' for tok in safe_q.split() if tok)
                rows = cur.execute(
                    """
                    SELECT c.* FROM canonical_claims c
                    JOIN claims_fts f ON c.claim_id = f.claim_id
                    WHERE claims_fts MATCH ? AND c.signal_score >= ?
                    ORDER BY c.signal_score DESC
                    """,
                    (fts_expr, min_signal_score),
                ).fetchall()
                return [dict(r) for r in rows]

        like_q = f"%{query.strip()}%"
        rows = cur.execute(
            """
            SELECT * FROM canonical_claims
            WHERE (canonical_text LIKE ? OR title LIKE ? OR invariants_json LIKE ?)
              AND signal_score >= ?
            ORDER BY signal_score DESC
            """,
            (like_q, like_q, like_q, min_signal_score),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
