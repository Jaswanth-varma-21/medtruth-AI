"""Retrieval Agent: finds supporting evidence for each finding (the RAG step).

A small TF-IDF + cosine-similarity retriever written from scratch, so it runs without any
model download. To upgrade, replace `Retriever` with sentence-embeddings + a vector DB
(for example sentence-transformers + FAISS or Chroma) and keep the same `retrieve` signature.
"""
import math
from collections import Counter

from ..text_utils import tokens


class Retriever:
    def __init__(self, kb):
        self.kb = kb
        self.entries = kb.entries
        docs = []
        for e in self.entries:
            text = " ".join([e["title"], " ".join(e.get("terms", [])), e["summary"], e["plain"]])
            docs.append(tokens(text))
        n = len(docs)
        df = Counter()
        for toks in docs:
            df.update(set(toks))
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}
        self.vectors = [self._vector(toks) for toks in docs]

    def _vector(self, toks: list) -> dict:
        tf = Counter(t for t in toks if t in self.idf)
        vec = {t: (1 + math.log(c)) * self.idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def retrieve(self, query: str, k: int = 3) -> list:
        q = self._vector(tokens(query))
        scored = []
        for entry, vec in zip(self.entries, self.vectors):
            score = sum(w * vec.get(t, 0.0) for t, w in q.items())
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda s: -s[0])
        return [
            {
                "entry_id": e["id"],
                "title": e["title"],
                "summary": e["summary"],
                "plain": e["plain"],
                "evidence_text": " ".join([e["summary"], e["plain"], e.get("absent_plain", "")]).strip(),
                "source": self.kb.meta["source_note"],
                "score": round(score, 3),
            }
            for score, e in scored[:k]
        ]


def retrieve_for_finding(retriever: Retriever, finding: dict, k: int = 3) -> list:
    query = f"{finding['term']} {finding['term']} {finding['sentence']}"
    return retriever.retrieve(query, k)
