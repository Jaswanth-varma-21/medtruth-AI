"""Small text helpers shared by all agents (pure Python, no external packages)."""
import re

# Everyday function words: ignored when comparing a claim with its evidence.
STOPWORDS = set("""
a an the and or of to in on at by for with from as is are was were be been being it its this that these those
there here your you we they he she i not no but if then than so such can could may might will would should do
does did has have had into over under about also very more most some any each other which who whom what when
where why how up down out off just only own same too both few many much one two
""".split())

# Words that describe the report or the act of explaining rather than the medical content.
DISCOURSE = set("""
report reports reported say says said state states stated mean means meaning seen see doctor doctors radiologist
radiologists finding findings ask discuss cautious definite possible certain likely here usually often sometimes
picture image images xray ray
""".split())

_WORD = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_NEGATION = re.compile(r"\b(no|not|without|absent|negative|resolved|nor)\b", re.I)
_HEADING = re.compile(
    r"^\s*(?:[-*\u2022]\s*)?(?:findings|impression|technique|comparison|history|indication|"
    r"clinical history|clinical information|conclusion|report)\s*:\s*",
    re.I,
)


def stem(word: str) -> str:
    """Very light stemmer so 'effusions'/'effusion' and 'enlarged'/'enlarge' compare equal."""
    for _ in range(2):
        if len(word) > 5 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 5 and word.endswith(("ches", "shes", "sses", "xes", "zes")):
            word = word[:-2]
        elif len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        elif len(word) > 6 and word.endswith("ing"):
            word = word[:-3]
        elif len(word) > 5 and word.endswith("ed"):
            word = word[:-2]
    if len(word) > 4 and word.endswith("e"):
        word = word[:-1]
    return word


def tokens(text: str) -> list:
    """Lower-cased stemmed content words (stop-words and discourse words removed)."""
    out = []
    for raw in _WORD.findall(text.lower()):
        if raw in STOPWORDS or raw in DISCOURSE or len(raw) < 2:
            continue
        out.append(stem(raw))
    return out


def content_words(text: str) -> set:
    return set(tokens(text))


def numbers(text: str) -> list:
    return _NUMBER.findall(text)


def has_negation(text: str) -> bool:
    return bool(_NEGATION.search(text))


def split_sentences(text: str) -> list:
    """Split a report into sentences, keeping character offsets into the original text.

    A boundary is a newline, or . ! ? followed by whitespace/end (so '0.5 cm' stays in one piece).
    Section headings such as 'FINDINGS:' are removed.
    """
    spans = []
    n = len(text)
    start = 0

    def emit(a: int, b: int) -> None:
        seg = text[a:b]
        m = _HEADING.match(seg)
        if m:
            a += m.end()
            seg = text[a:b]
        lead = len(seg) - len(seg.lstrip(" \t-*\u2022"))
        a += lead
        seg = text[a:b]
        seg_stripped = seg.rstrip()
        b = a + len(seg_stripped)
        seg = seg_stripped
        if not re.search(r"[A-Za-z]{2,}", seg):
            return
        if seg.endswith(":") and len(seg.split()) <= 6:
            return
        spans.append({"start": a, "end": b, "text": seg})

    for i, ch in enumerate(text):
        if ch == "\n":
            emit(start, i)
            start = i + 1
        elif ch in ".!?" and (i + 1 == n or text[i + 1].isspace()):
            emit(start, i + 1)
            start = i + 1
    emit(start, n)
    return spans


def split_claims(text: str) -> list:
    return [s["text"] for s in split_sentences(text)]
