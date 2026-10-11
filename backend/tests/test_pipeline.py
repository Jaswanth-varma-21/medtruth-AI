"""Run:  python -m unittest discover -s tests -v   (from the backend folder)"""
import unittest

from app.agents.analysis_agent import analyze
from app.knowledge_base import KnowledgeBase
from app.pipeline import Pipeline
from app.samples import SAMPLES
from app.text_utils import has_negation, split_sentences

KB = KnowledgeBase()


def statuses(text):
    return {f["entry_id"]: f["status"] for f in analyze(text, KB)["findings"]}


class FakeLLM:
    enabled = True
    model = "fake"

    def __init__(self, reply):
        self.reply = reply

    def complete(self, system, user, timeout=60):
        return self.reply


class TestText(unittest.TestCase):
    def test_sentences_keep_decimals_and_drop_headings(self):
        spans = split_sentences("FINDINGS:\nA 0.5 cm nodule is seen. IMPRESSION: Stable.")
        self.assertEqual([s["text"] for s in spans], ["A 0.5 cm nodule is seen.", "Stable."])

    def test_offsets_point_into_original(self):
        text = "FINDINGS:\nThe lungs are clear. No pneumothorax."
        for s in split_sentences(text):
            self.assertEqual(text[s["start"]:s["end"]], s["text"])


class TestAnalysis(unittest.TestCase):
    def test_negation_list(self):
        s = statuses("There is no evidence of pneumonia, pleural effusion, or pneumothorax.")
        self.assertEqual(s["pneumonia"], "absent")
        self.assertEqual(s["pleural_effusion"], "absent")
        self.assertEqual(s["pneumothorax"], "absent")

    def test_post_negation(self):
        self.assertEqual(statuses("Pneumothorax is not seen.")["pneumothorax"], "absent")

    def test_hedging_is_local_to_its_clause(self):
        s = statuses("Right lower lobe opacity, possibly pneumonia, with small right pleural effusion.")
        self.assertEqual(s["pneumonia"], "uncertain")
        self.assertEqual(s["pleural_effusion"], "present")
        self.assertEqual(s["opacity"], "present")

    def test_new_clause_resets_negation(self):
        s = statuses("There is no pleural effusion and the cardiac silhouette is enlarged.")
        self.assertEqual(s["pleural_effusion"], "absent")
        self.assertEqual(s["cardiomegaly"], "present")

    def test_longest_term_wins(self):
        found = [f["entry_id"] for f in analyze("Airspace opacity in the right lower lobe.", KB)["findings"]]
        self.assertEqual(found, ["consolidation"])

    def test_cannot_exclude_is_uncertain_not_absent(self):
        self.assertEqual(statuses("Small pneumothorax cannot be excluded.")["pneumothorax"], "uncertain")


class TestKnowledgeBase(unittest.TestCase):
    def test_lead_sentences_have_no_negation_cue(self):
        """The Verification Agent's polarity check relies on this property."""
        from app.text_utils import split_claims
        for e in KB.entries:
            if e["kind"] == "abnormal":
                self.assertFalse(has_negation(split_claims(e["plain"])[0]), e["id"])


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.pipe = Pipeline(kb=KB, llm=FakeLLM("x"))

    def test_samples_run_and_template_is_fully_verified(self):
        for sample in SAMPLES:
            out = self.pipe.run(sample["text"], use_llm=False)
            self.assertGreater(out["summary"]["findings"], 0, sample["id"])
            self.assertEqual(out["summary"]["flagged"], 0, sample["id"])
            for f in out["findings"]:
                self.assertEqual(f["verification"]["status"], "verified", (sample["id"], f["title"]))

    def test_urgency_is_carried_through(self):
        out = self.pipe.run(SAMPLES[2]["text"], use_llm=False)
        ptx = next(f for f in out["findings"] if f["title"] == "Pneumothorax" and f["status"] == "present")
        self.assertEqual(ptx["urgency"], "prompt")

    def test_hallucinated_llm_text_is_flagged(self):
        pipe = Pipeline(kb=KB, llm=FakeLLM("You have pneumonia and must take antibiotics for 14 days."))
        out = pipe.run("There is consolidation in the right lower lobe.", use_llm=True)
        f = out["findings"][0]
        self.assertEqual(f["explanation"]["method"], "llm")
        self.assertEqual(f["verification"]["status"], "flagged")

    def test_contradiction_with_report_is_flagged(self):
        pipe = Pipeline(kb=KB, llm=FakeLLM("A pneumothorax is present in your lung."))
        out = pipe.run("There is no pneumothorax.", use_llm=True)
        claim = out["findings"][0]["verification"]["claims"][0]
        self.assertEqual(claim["label"], "unsupported")
        self.assertIn("contradicts the report wording", claim["reasons"])

    def test_faithful_llm_text_is_accepted(self):
        reply = "A pneumothorax means air has collected between the lung and the chest wall."
        pipe = Pipeline(kb=KB, llm=FakeLLM(reply))
        out = pipe.run("A small right pneumothorax is present.", use_llm=True)
        self.assertEqual(out["findings"][0]["verification"]["status"], "verified")

    def test_llm_failure_falls_back_to_template(self):
        class Broken(FakeLLM):
            def complete(self, *a, **k):
                raise RuntimeError("down")
        out = Pipeline(kb=KB, llm=Broken("")).run("There is consolidation.", use_llm=True)
        self.assertEqual(out["findings"][0]["explanation"]["method"], "template (LLM unavailable)")
        self.assertEqual(out["findings"][0]["verification"]["status"], "verified")

    def test_unmatched_text_gives_no_findings_and_short_text_errors(self):
        out = self.pipe.run("The patient was positioned upright for this study.", use_llm=False)
        self.assertEqual(out["summary"]["findings"], 0)
        with self.assertRaises(ValueError):
            self.pipe.run("hi", use_llm=False)


if __name__ == "__main__":
    unittest.main()
