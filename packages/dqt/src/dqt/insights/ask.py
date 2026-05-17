"""Natural language ask resolution.

Steps:
  1. Fuzzy-match metric references against catalog (rapidfuzz ratio, threshold 70)
  2. Parse time window from phrases ("this week"=7, "yesterday"=1, "last N days"=N, default=7)
  3. Classify intent: "why" | "compare" | "list"
  4. If top match confidence < 70 or multiple matches within 5 points: return DisambiguationResult
  5. Otherwise: return AskResult
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

try:
    from rapidfuzz import fuzz, process as rf_process
    _RAPIDFUZZ = True
except ImportError:
    _RAPIDFUZZ = False


@dataclass
class AskResult:
    metric_fqn: str
    display_name: str
    intent: Literal["why", "compare", "list"]
    window_days: int
    confidence: float


@dataclass
class ClarifyOption:
    metric_fqn: str
    display_name: str
    confidence: float


@dataclass
class DisambiguationResult:
    original_question: str
    options: list[ClarifyOption] = field(default_factory=list)
    message: str = "Which metric did you mean?"


_WINDOW_PATTERNS: list[tuple[re.Pattern[str], int | None]] = [
    (re.compile(r"yesterday", re.I), 1),
    (re.compile(r"today", re.I), 1),
    (re.compile(r"this\s+week|past\s+week|last\s+week", re.I), 7),
    (re.compile(r"this\s+month|past\s+month|last\s+month", re.I), 30),
    (re.compile(r"last\s+(\d+)\s+days?", re.I), None),
    (re.compile(r"past\s+(\d+)\s+days?", re.I), None),
    (re.compile(r"since\s+(?:apr|april|jan|january|feb|february|mar|march|may|jun|june|jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\s+\d+", re.I), 14),
]

_INTENT_WHY = re.compile(r"\b(why|explain|what.?s driving|what caused|reason|driver|is.+data issue)\b", re.I)
_INTENT_COMPARE = re.compile(r"\b(compar|vs\.?|versus|against|alongside)\b", re.I)
_INTENT_LIST = re.compile(r"\b(show me|list|which metrics?|find|what metrics?)\b", re.I)

_CONFIDENCE_THRESHOLD = 70.0
_DISAMBIGUATION_GAP = 5.0

# Generic qualifier words that appear in metric names but don't discriminate the metric.
# When scoring, we treat these as low-weight and don't penalise their absence from the query.
_NAME_QUALIFIERS = frozenset({
    "new", "total", "gross", "net", "rate", "count", "average", "avg",
    "sum", "max", "min", "pct", "percent", "usd", "eur", "gbp",
})

# Stopwords to ignore when tokenising the question
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "this", "that", "these", "those",
    "in", "on", "at", "by", "for", "with", "about", "against", "between",
    "of", "to", "from", "up", "down", "so", "if", "it", "its", "me", "my",
    "we", "our", "you", "your", "he", "she", "they", "their", "what", "why",
    "how", "when", "where", "which", "who", "and", "or", "but", "not", "no",
    "drop", "spike", "increase", "decrease", "change", "high", "low", "move",
    "moved", "moving", "significantly", "week", "month", "day", "yesterday",
    "today", "last", "past", "recent", "did", "does", "going", "now",
})


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokens, dropping stopwords and short tokens."""
    tokens = re.findall(r"[a-z]+", text.lower())
    return {t for t in tokens if len(t) > 2 and t not in _STOPWORDS}


def _token_in_query(token: str, query_lower: str) -> bool:
    """Return True if token appears as a substring in the query (handles plurals/stems)."""
    return token in query_lower


def _word_overlap_score(query: str, name: str) -> float:
    """Score name match against query using word overlap + substring bonus.

    Returns 0-100. Strategy:
    - Exact phrase match → 100
    - Score by fraction of *content* tokens (non-qualifier) that hit in the query.
      Qualifier tokens (new, rate, usd...) are optional and don't reduce the score.
    - Single content-token names that hit → 90
    - Multi-content-token names: proportional, floored at 75 if any content token hits
      (because a matching core noun is a strong signal even without qualifiers).
    """
    query_lower = query.lower()

    # Exact multi-word substring match (e.g. "new signups" in query)
    name_lower = name.lower()
    if name_lower in query_lower:
        return 100.0

    all_tokens = _tokenize(name)
    if not all_tokens:
        return 0.0

    # Split tokens into content (discriminating) vs qualifiers (non-discriminating)
    content_tokens = [t for t in all_tokens if t not in _NAME_QUALIFIERS]
    if not content_tokens:
        content_tokens = list(all_tokens)

    content_hits = sum(1 for t in content_tokens if _token_in_query(t, query_lower))

    if content_hits == 0:
        return 0.0

    # At least one content token hit: proportional score floored at 75
    proportion = content_hits / len(content_tokens)
    score = proportion * 90.0
    return max(score, 75.0)


def _extract_window(question: str) -> int:
    """Parse a time window in days from the question text. Default is 7."""
    for pattern, days in _WINDOW_PATTERNS:
        m = pattern.search(question)
        if m:
            if days is None:
                return int(m.group(1))
            return days
    return 7


def _classify_intent(question: str) -> Literal["why", "compare", "list"]:
    """Classify question intent as 'why', 'compare', or 'list'."""
    if _INTENT_COMPARE.search(question):
        return "compare"
    if _INTENT_LIST.search(question) and not _INTENT_WHY.search(question):
        return "list"
    return "why"


def _score_all(
    question: str, metric_catalog: list[dict[str, Any]]
) -> list[tuple[str, float, int]]:
    """Return list of (display_name, score, catalog_idx) sorted descending."""
    search_corpus = [m["display_name"] for m in metric_catalog]

    if _RAPIDFUZZ:
        raw = rf_process.extract(
            question, search_corpus, scorer=fuzz.partial_ratio, limit=len(search_corpus)
        )
        return [(name, float(score), idx) for name, score, idx in raw]

    results: list[tuple[str, float, int]] = []
    for i, name in enumerate(search_corpus):
        score = _word_overlap_score(question, name)
        results.append((name, score, i))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def resolve(
    question: str,
    *,
    metric_catalog: list[dict[str, Any]],
) -> AskResult | DisambiguationResult:
    """Resolve a natural language question to an AskResult or DisambiguationResult."""
    if not metric_catalog:
        return DisambiguationResult(original_question=question, options=[])

    intent = _classify_intent(question)
    window_days = _extract_window(question)

    # "list" with no specific metric reference -- return wildcard immediately
    if intent == "list" and not any(
        m["display_name"].split()[0].lower() in question.lower()
        for m in metric_catalog
    ):
        return AskResult(
            metric_fqn="*",
            display_name="all",
            intent="list",
            window_days=window_days,
            confidence=100.0,
        )

    matches = _score_all(question, metric_catalog)

    if not matches or matches[0][1] < _CONFIDENCE_THRESHOLD:
        return DisambiguationResult(
            original_question=question,
            options=[
                ClarifyOption(
                    metric_fqn=metric_catalog[idx]["fqn"],
                    display_name=name,
                    confidence=score,
                )
                for name, score, idx in matches[:4]
                if score >= 40.0
            ],
        )

    top_score = matches[0][1]
    close = [m for m in matches if top_score - m[1] <= _DISAMBIGUATION_GAP]
    if len(close) > 1:
        return DisambiguationResult(
            original_question=question,
            options=[
                ClarifyOption(
                    metric_fqn=metric_catalog[idx]["fqn"],
                    display_name=name,
                    confidence=score,
                )
                for name, score, idx in close[:4]
            ],
        )

    best_name, best_score, best_idx = matches[0]
    metric = metric_catalog[best_idx]
    return AskResult(
        metric_fqn=metric["fqn"],
        display_name=metric["display_name"],
        intent=intent,
        window_days=window_days,
        confidence=best_score,
    )
