#!/usr/bin/env python3
"""
Illustrative reconciliation guardrail from a voice-to-CRM agent.

This is a sanitized teaching example, not the production code. It shows the idea
that keeps the agent honest about identity:

  1. Drop generic and geographic tokens so they cannot create false matches.
  2. Score candidates only on the remaining distinctive tokens.
  3. If two or more distinct candidates both match strongly, force a human
     disambiguation gate instead of guessing.
  4. When evidence is weak, default to creating a new record.

A wrong new record is trivially merged later. A wrong attachment silently
corrupts an existing record, so the resolver never guesses identity.

    python resolver_pattern.py   # run the worked examples
"""
import re
import unicodedata
from dataclasses import dataclass, field

# Words that say nothing about identity: legal forms, sector filler, etc.
GENERIC_TOKENS = {
    "the", "group", "holding", "holdings", "partners", "partner", "capital",
    "fund", "funds", "bank", "banque", "trust", "company", "co", "corp",
    "inc", "ltd", "llc", "plc", "sa", "sas", "sarl", "gmbh", "ag",
    "private", "investment", "investments", "management", "asset", "assets",
    "advisors", "advisory", "ventures", "global", "international",
}

# Place names also never establish identity (illustrative shortlist).
GEO_TOKENS = {
    "paris", "london", "brussels", "geneva", "zurich", "york", "new",
    "luxembourg", "munich", "madrid", "amsterdam",
}

STRONG = 0.6  # a candidate at or above this share of matched distinctive tokens


def _normalize(text: str) -> list[str]:
    """Lowercase, strip accents, return alphanumeric word tokens."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", text.lower())


def _full_name(name: str) -> str:
    """Normalized full name, used to tell two strong candidates apart."""
    return " ".join(_normalize(name))


def distinctive_tokens(name: str) -> set:
    """Identity-bearing tokens only: drop generic, geographic, and one-char tokens."""
    return {
        t for t in _normalize(name)
        if t not in GENERIC_TOKENS and t not in GEO_TOKENS and len(t) > 1
    }


def match_score(mention: str, candidate: str) -> float:
    """Share of the mention's distinctive tokens found in the candidate (0..1)."""
    m = distinctive_tokens(mention)
    if not m:
        return 0.0
    c = distinctive_tokens(candidate)
    return len(m & c) / len(m)


@dataclass
class Decision:
    action: str                      # "match" | "disambiguate" | "create_new"
    matches: list = field(default_factory=list)  # [(candidate, score), ...]


def resolve(mention: str, candidates: list, strong: float = STRONG) -> Decision:
    """Classify a transcript entity against existing CRM records, without guessing."""
    scored = sorted(
        ((c, match_score(mention, c)) for c in candidates),
        key=lambda x: x[1], reverse=True,
    )
    strong_matches = [(c, s) for c, s in scored if s >= strong]
    distinct_names = {_full_name(c) for c, _ in strong_matches}

    if len(distinct_names) >= 2:
        # Two genuinely different records both match: a human must choose.
        return Decision("disambiguate", strong_matches)
    if strong_matches:
        return Decision("match", strong_matches[:1])
    return Decision("create_new", [])


def demo():
    crm = [
        "Riverstone Holdings", "Riverstone Advisors", "Zephyr Bank",
        "Northwind Trust", "Acme Capital Partners",
    ]
    examples = [
        ("Zephyr Bank", crm),               # one clear match
        ("Riverstone", crm),                # two distinct strong candidates
        ("Beta Capital Partners", crm),     # overlaps only on generic tokens
        ("Xqzzy", crm),                     # garbled, matches nothing
    ]
    for mention, candidates in examples:
        d = resolve(mention, candidates)
        shown = ", ".join(f"{c} ({s:.2f})" for c, s in d.matches) or "-"
        print(f"  {mention:<24} -> {d.action:<12} [{shown}]")


if __name__ == "__main__":
    print("Reconciliation decisions:\n")
    demo()
