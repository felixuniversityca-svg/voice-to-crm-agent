#!/usr/bin/env python3
"""
Unit checks for the reconciliation guardrail. Run:  python test_resolver.py
"""
from resolver_pattern import resolve, match_score, distinctive_tokens


def test_generic_overlap_does_not_match():
    # Shares only "capital"/"partners" (generic) with an existing record -> no match.
    d = resolve("Beta Capital Partners", ["Acme Capital Partners", "Northwind Trust"])
    assert d.action == "create_new", d


def test_single_clear_match():
    d = resolve("Zephyr Bank", ["Zephyr Bank", "Northwind Trust"])
    assert d.action == "match", d
    assert d.matches[0][0] == "Zephyr Bank"


def test_two_distinct_candidates_force_disambiguation():
    # Both share the distinctive token "riverstone" but are different records.
    d = resolve("Riverstone", ["Riverstone Holdings", "Riverstone Advisors"])
    assert d.action == "disambiguate", d
    assert len(d.matches) == 2


def test_duplicate_same_name_is_not_a_conflict():
    # The same name listed twice is one entity, not a disambiguation case.
    d = resolve("Zephyr Bank", ["Zephyr Bank", "Zephyr Bank"])
    assert d.action == "match", d


def test_garbled_mention_creates_new():
    d = resolve("Xqzzy", ["Zephyr Bank", "Acme Capital Partners"])
    assert d.action == "create_new", d


def test_accent_insensitive():
    # Accents must not block a match.
    assert match_score("Credit Mutuel", "Crédit Mutuel") == 1.0


def test_generic_tokens_are_dropped():
    assert distinctive_tokens("The Acme Capital Group") == {"acme"}


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
