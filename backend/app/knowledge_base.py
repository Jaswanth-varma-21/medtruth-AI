"""Loads the curated knowledge base and compiles the term patterns used by the Analysis Agent."""
import json
import re
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "data" / "knowledge_base.json"


class KnowledgeBase:
    def __init__(self, path=None):
        data = json.loads(Path(path or DEFAULT_PATH).read_text(encoding="utf-8"))
        self.meta = data["meta"]
        self.entries = data["entries"]
        self.by_id = {e["id"]: e for e in self.entries}
        self.patterns = []  # (compiled regex, entry id)
        for entry in self.entries:
            for term in entry.get("terms", []):
                self.patterns.append((re.compile(r"\b" + re.escape(term) + r"\b", re.I), entry["id"]))
            for raw in entry.get("patterns", []):
                self.patterns.append((re.compile(r"\b" + raw + r"\b", re.I), entry["id"]))
