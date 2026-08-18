"""
Intent catalog for the LEGACY intent-classification front-end.

NEUTRALISED FOR AP. The router runs the template-direct path
(config.USE_VECTOR_RETRIEVAL = True): vector retrieve -> LLM rerank -> extract
entities for the chosen template's slots. That path never reads these tables.

They stay as empty dicts rather than being deleted because router.py,
reranker.py and intent_classifier.py import the names at module level, and
because the intent path is still the documented fallback if vector retrieval is
ever switched off. With empty lookups that fallback returns a graceful
"couldn't match" rather than a wrong answer.

INTENT_LOOKUP         — (intent, frozenset(entity_types)) -> query_id
INTENT_SLOTS          — per intent, which entity types to extract
INTENT_LIST           — all valid intent names (used to constrain LLM output)
INTENT_LIST_BY_DOMAIN — domain groupings for the two-step classifier
"""

INTENT_LOOKUP: dict[tuple[str, frozenset], str] = {}

INTENT_SLOTS: dict[str, list[str]] = {}

INTENT_LIST: list[str] = ["no_match"]

INTENT_LIST_BY_DOMAIN: dict[str, list[str]] = {}
