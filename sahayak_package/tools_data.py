"""
Simple data access helpers. Kept dependency-free (no DB) for prototype speed —
swapping these for a real database later only touches this one file.
"""
import json
import os
import sys

import portalocker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SCHEMES_PATH, NGOS_PATH, CASES_PATH


def load_schemes():
    with open(SCHEMES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_ngos():
    with open(NGOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cases():
    if not os.path.exists(CASES_PATH):
        return []
    with portalocker.Lock(CASES_PATH, mode="r", encoding="utf-8", timeout=10) as f:
        content = f.read()
    return json.loads(content) if content.strip() else []


def _update_cases_file(mutate_fn):
    """
    Reads, mutates, and rewrites cases.json under a single exclusive file
    lock, so two concurrent callers (e.g. two browser tabs running the
    pipeline at once) can't interleave their writes and tear the file —
    each save_case/update_case waits its turn instead of racing.
    """
    with portalocker.Lock(CASES_PATH, mode="a+", encoding="utf-8", timeout=10) as f:
        f.seek(0)
        content = f.read()
        cases = json.loads(content) if content.strip() else []
        cases = mutate_fn(cases)
        f.seek(0)
        f.truncate()
        json.dump(cases, f, indent=2, ensure_ascii=False)
    return cases


def save_case(case: dict):
    _update_cases_file(lambda cases: cases + [case])
    return case


def update_case(case_id: str, updates: dict):
    def mutate(cases):
        for c in cases:
            if c["case_id"] == case_id:
                c.update(updates)
                break
        return cases

    return _update_cases_file(mutate)


def schemes_as_text():
    """Flatten schemes into a compact text block for LLM context."""
    schemes = load_schemes()
    lines = []
    for s in schemes:
        lines.append(
            f"[{s['id']}] {s['name']} | category={s['category']} | "
            f"eligibility={'; '.join(s['eligibility'])} | "
            f"benefit={s['description']}"
        )
    return "\n".join(lines)


def ngos_as_text():
    ngos = load_ngos()
    lines = []
    for n in ngos:
        lines.append(
            f"[{n['id']}] {n['name']} | area={n['area']} | "
            f"focus={', '.join(n['focus'])} | contact={n['contact_person']} ({n['phone']}) | "
            f"email={n['email']}"
        )
    return "\n".join(lines)
