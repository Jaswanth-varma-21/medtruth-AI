"""Analysis Agent: reads the report and extracts findings with their status.

Goal: turn free-text report sentences into structured findings
(which finding, in which sentence, and is it reported / not seen / uncertain).
Rule-based on purpose, so that its behaviour is explainable and testable.
"""
import re

from ..text_utils import split_sentences

_SEP = r"[;:]|\b(?:but|however|although|though|while|which|whereas)\b|,?\s*\band\s+(?:the|a|an|there)\b"
SEPARATORS = re.compile(_SEP, re.I)
COMMA_SEPARATORS = re.compile(r"," + "|" + _SEP, re.I)

NEG_PRE = re.compile(r"\b(no|nor|not|without|negative|free of|absence of|absent|resolved|cleared)\b")
NEG_POST = re.compile(
    r"^\W*(?:(?:is|are|was|were|has|have|been)\s+)*"
    r"(?:not\s+(?:seen|identified|present|visuali[sz]ed|evident|demonstrated|detected|appreciated)"
    r"|absent|resolved|ruled out)\b"
)
HEDGE = re.compile(
    r"\b(possible|possibly|probable|probably|suspected|suspicious|suggest(?:s|ed|ive|ing)?|may|might|could|"
    r"likely|questionable|equivocal|versus|concern for|differential|"
    r"cannot (?:be )?(?:excluded|ruled out)|can(?:not|'t) exclude)\b|\?"
)


def find_matches(sentence: str, kb) -> list:
    """Find KB terms in a sentence; the longest term wins when two overlap; one hit per entry."""
    hits = []
    for regex, entry_id in kb.patterns:
        for m in regex.finditer(sentence):
            hits.append((m.start(), m.end(), entry_id, m.group(0)))
    hits.sort(key=lambda h: (-(h[1] - h[0]), h[0]))
    chosen = []
    for h in hits:
        if any(h[0] < c[1] and c[0] < h[1] for c in chosen):
            continue
        if any(c[2] == h[2] for c in chosen):
            continue
        chosen.append(h)
    return sorted(chosen)


def _segment_around(sentence: str, start: int, end: int) -> str:
    left, right = 0, len(sentence)
    for m in COMMA_SEPARATORS.finditer(sentence):
        if m.end() <= start:
            left = m.end()
        elif m.start() >= end:
            right = m.start()
            break
    return sentence[left:right]


def detect_status(sentence: str, start: int, end: int) -> str:
    """Return 'absent' (negated), 'uncertain' (hedged) or 'present'."""
    before = sentence[:start].lower()
    cuts = [m.end() for m in SEPARATORS.finditer(before)]
    if cuts:
        before = before[cuts[-1]:]
    window = " ".join(before.split()[-8:])
    if NEG_PRE.search(window):
        return "absent"
    if NEG_POST.search(sentence[end:end + 40].lower()):
        return "absent"
    if HEDGE.search(_segment_around(sentence, start, end).lower()):
        return "uncertain"
    return "present"


def analyze(report_text: str, kb) -> dict:
    sentences = split_sentences(report_text)
    findings, matched_sentences = [], set()
    for idx, sent in enumerate(sentences):
        sent["index"] = idx
        for start, end, entry_id, surface in find_matches(sent["text"], kb):
            findings.append(
                {
                    "sentence_index": idx,
                    "sentence": sent["text"],
                    "entry_id": entry_id,
                    "term": surface,
                    "status": detect_status(sent["text"], start, end),
                }
            )
            matched_sentences.add(idx)
    for sent in sentences:
        sent["matched"] = sent["index"] in matched_sentences
    return {"sentences": sentences, "findings": findings}
