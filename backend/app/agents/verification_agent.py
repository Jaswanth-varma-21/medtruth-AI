"""Verification Agent: checks that every claim in an explanation is supported.

For each sentence (claim) of the explanation it checks:
  1. Word support  - what share of its content words appear in the report sentence or in the
                     retrieved evidence (labelled supported / partly supported / not supported).
  2. Numbers       - every number in the claim must appear in the report or the evidence.
  3. Polarity      - the lead claim must not contradict the report (for example saying a finding
                     is present when the report says it was not seen). Applied to abnormal findings.
This is a deliberately transparent, lexical check. A stronger version can add an NLI model or an
LLM-as-judge on top, keeping the same output format.
"""
from ..text_utils import content_words, has_negation, numbers

SUPPORTED = 0.75
PARTIAL = 0.45


def _label(score: float) -> str:
    if score >= SUPPORTED:
        return "supported"
    if score >= PARTIAL:
        return "partial"
    return "unsupported"


def verify(finding: dict, explanation: dict, evidence: list, kind: str, report_text: str) -> dict:
    if explanation["method"] == "no-evidence":
        return {"status": "no_evidence", "confidence": "low", "score": 0.0, "claims": []}

    ev_text = " ".join(e["evidence_text"] for e in evidence)
    report_words = content_words(finding["sentence"])
    evidence_words = content_words(ev_text)
    allowed = report_words | evidence_words
    known_numbers = set(numbers(report_text)) | set(numbers(ev_text))

    claims = []
    for i, text in enumerate(explanation["claims"]):
        words = content_words(text)
        score = len(words & allowed) / len(words) if words else 1.0
        reasons = []

        bad = [n for n in numbers(text) if n not in known_numbers]
        if bad:
            reasons.append("number " + ", ".join(bad) + " is not in the report or the evidence")
            score = min(score, 0.2)

        if i == 0 and kind == "abnormal" and finding["status"] in ("present", "absent"):
            if has_negation(text) != (finding["status"] == "absent"):
                reasons.append("contradicts the report wording")
                score = 0.0

        origin = []
        if words & evidence_words:
            origin.append("knowledge base")
        if words & report_words:
            origin.append("report")
        label = _label(score)
        if label != "supported" and not reasons:
            reasons.append("some words are not found in the report or the evidence")
        claims.append(
            {"text": text, "support": round(score, 2), "label": label, "from": origin, "reasons": reasons}
        )

    scores = [c["support"] for c in claims] or [0.0]
    labels = {c["label"] for c in claims}
    if "unsupported" in labels:
        status = "flagged"
    elif "partial" in labels:
        status = "partial"
    else:
        status = "verified"

    top = evidence[0]["score"] if evidence else 0.0
    if status == "verified" and finding["status"] != "uncertain" and top >= 0.2:
        confidence = "high"
    elif status == "flagged":
        confidence = "low"
    else:
        confidence = "medium"
    return {
        "status": status,
        "confidence": confidence,
        "score": round(sum(scores) / len(scores), 2),
        "claims": claims,
    }
