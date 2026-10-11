"""Explanation Agent: writes the patient-friendly explanation for one finding.

Uses an LLM when one is configured (told to use ONLY the retrieved evidence);
otherwise, or if the LLM call fails, it falls back to a template built from the evidence.
The Verification Agent checks the result either way.
"""
from ..text_utils import split_claims

SYSTEM_PROMPT = (
    "You explain one sentence from a chest X-ray report to a patient with no medical background. "
    "Use ONLY the evidence text provided. Write 2 or 3 short sentences in plain language. "
    "Do not diagnose, do not suggest treatment, and do not add numbers, causes or facts that are "
    "not in the evidence. If the report is uncertain or says the finding was not seen, say so clearly."
)

STATUS_PHRASE = {
    "present": "The report describes this finding.",
    "absent": "The report says this was not seen.",
    "uncertain": "The report uses cautious wording, so this finding is possible but not certain.",
}


def _template(finding: dict, entry: dict, evidence: dict) -> str:
    title = entry["title"].lower()
    status = finding["status"]
    if status == "absent":
        extra = entry.get("absent_plain", "")
        return f"The report says {title} was not seen. {extra}".strip()
    if status == "uncertain":
        return f"The report is cautious here: it says {title} is possible, not definite. {evidence['plain']}"
    return evidence["plain"]


def explain(finding: dict, evidence: list, kb, llm=None) -> dict:
    match = next((e for e in evidence if e["entry_id"] == finding["entry_id"]), None)
    if match is None:
        return {
            "text": "No supporting evidence was found for this finding, so no explanation is given. "
                    "Please ask your doctor about this part of the report.",
            "claims": [],
            "method": "no-evidence",
        }
    entry = kb.by_id[finding["entry_id"]]
    method = "template"
    text = None
    if llm is not None and llm.enabled:
        prompt = (
            f"Report sentence: {finding['sentence']}\n"
            f"Status in the report: {STATUS_PHRASE[finding['status']]}\n"
            f"Evidence: {match['evidence_text']}\n\n"
            "Write the patient explanation now."
        )
        try:
            text = llm.complete(SYSTEM_PROMPT, prompt)
            method = "llm"
        except Exception:  # network error, bad key, timeout ...
            text = None
            method = "template (LLM unavailable)"
    if not text:
        text = _template(finding, entry, match)
    return {"text": text, "claims": split_claims(text), "method": method}
