#!/usr/bin/env python3
"""
Resolver eval: does the guardrail actually prevent wrong writes?

Each case is a transcript entity, a set of CRM candidates, and the decision a
careful human would make. We score two strategies:

  naive     pick the single highest-overlap candidate and write to it
  resolver  drop generic/geographic tokens, force disambiguation on ties,
            default to create-new when evidence is weak (resolver_pattern.py)

The metric that matters is not accuracy, it is "wrong writes": a confident
match to the wrong record, which silently corrupts the system of record. The
naive strategy is fast and dangerous; the resolver trades a few human taps for
zero wrong writes.

Run:  python eval_resolver.py
"""
from resolver_pattern import _normalize, resolve

# (mention, candidates, expected_action, expected_record)
CASES = [
    ("Zephyr Bank",            ["Zephyr Bank", "Northwind Trust"],                     "match",        "Zephyr Bank"),
    ("Beta Capital Partners",  ["Acme Capital Partners", "Northwind Trust"],           "create_new",   None),
    ("Riverstone",             ["Riverstone Holdings", "Riverstone Advisors"],         "disambiguate", None),
    ("Northwind Capital",      ["Acme Capital Partners", "Zephyr Bank"],               "create_new",   None),
    ("Credit Mutuel",          ["Credit Mutuel", "Banque Populaire"],                  "match",        "Credit Mutuel"),
    ("Parkside Family Office", ["Parkside Family Office (Geneva)",
                                "Parkside Family Office (London)"],                    "disambiguate", None),
    ("Xqzzy Holdings",         ["Apex Capital", "Helios Renewables"],                  "create_new",   None),
    ("Helios Renewables",      ["Helios Renewables", "Apex Capital"],                  "match",        "Helios Renewables"),
]

NAIVE_THRESHOLD = 0.5


def naive_score(mention: str, candidate: str) -> float:
    """All-token overlap, no token hygiene: the tempting wrong way to do it."""
    m = set(_normalize(mention))
    if not m:
        return 0.0
    return len(m & set(_normalize(candidate))) / len(m)


def naive_resolve(mention: str, candidates: list):
    """Pick the top candidate and write to it if it looks close enough."""
    ranked = sorted(candidates, key=lambda c: naive_score(mention, c), reverse=True)
    if ranked and naive_score(mention, ranked[0]) >= NAIVE_THRESHOLD:
        return ("match", ranked[0])
    return ("create_new", None)


def resolver_decide(mention: str, candidates: list):
    d = resolve(mention, candidates)
    record = d.matches[0][0] if d.action == "match" and d.matches else None
    return (d.action, record)


def is_wrong_write(got, expected_action, expected_record) -> bool:
    """A confident match to a record that is not the right one."""
    action, record = got
    return action == "match" and (expected_action != "match" or record != expected_record)


def main():
    methods = {"naive": naive_resolve, "resolver": resolver_decide}
    tally = {n: {"correct": 0, "wrong_writes": 0} for n in methods}

    print("Per-case decisions (! = confident wrong write):\n")
    print(f"  {'mention':<24} {'expected':<13} {'naive':<22} {'resolver':<22}")
    print("  " + "-" * 80)

    rows = []
    for mention, cands, exp_action, exp_record in CASES:
        cells = {}
        for name, fn in methods.items():
            got = fn(mention, cands)
            correct = (got[0] == exp_action) and (got[0] != "match" or got[1] == exp_record)
            wrong = is_wrong_write(got, exp_action, exp_record)
            tally[name]["correct"] += int(correct)
            tally[name]["wrong_writes"] += int(wrong)
            label = got[0] + (f"->{got[1]}" if got[0] == "match" else "")
            cells[name] = ("! " if wrong else "  ") + label
        rows.append((mention, exp_action, cells["naive"], cells["resolver"]))

    for mention, exp, n, r in rows:
        print(f"  {mention:<24} {exp:<13} {n:<22} {r:<22}")

    n = len(CASES)
    print(f"\nAggregate over {n} cases:\n")
    print(f"  {'method':<10} {'correct':>9} {'wrong writes':>14}")
    print("  " + "-" * 36)
    for name in methods:
        print(f"  {name:<10} {tally[name]['correct']}/{n:<7} {tally[name]['wrong_writes']:>14}")
    print("\nWrong writes are the ones that matter: a silent match to the wrong record.")


if __name__ == "__main__":
    main()
