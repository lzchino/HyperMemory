"""Cloud outbound redaction & allowlisting.

Goal: make it extremely hard to exfiltrate secrets in curated memory sync.

Policy model:
- allowlist mode (default): only allow text that does not match deny patterns.
- deny patterns are conservative and should prefer false-positives.

This module never logs original sensitive substrings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass
class RedactionResult:
    text: str
    redaction_count: int
    matched_rules: list[str]


# High-signal secret patterns. Conservative by design.
_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-\.=]{12,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"(?i)aws(.{0,20})?secret(.{0,20})?=\s*['\"]?[A-Za-z0-9/+=]{20,}['\"]?")),
    ("generic_api_key", re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*['\"]?\S{6,}['\"]?")),
    ("private_key_block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")),
]


def redact(text: str, extra_rules: Iterable[tuple[str, re.Pattern[str]]] = ()) -> RedactionResult:
    out = text
    matched: list[str] = []
    count = 0

    for name, rx in [*_RULES, *list(extra_rules)]:
        if rx.search(out):
            matched.append(name)
            # replace all occurrences
            out, n = rx.subn("[REDACTED]", out)
            count += n

    # Redact URL query parameters (often contain tokens)
    # Keep scheme/host/path, drop query value contents.
    url_q = re.compile(r"(https?://[^\s\?]+)\?([^\s]+)")
    if url_q.search(out):
        matched.append("url_query")
        out, n = url_q.subn(r"\1?[REDACTED_QUERY]", out)
        count += n

    return RedactionResult(text=out, redaction_count=count, matched_rules=sorted(set(matched)))
