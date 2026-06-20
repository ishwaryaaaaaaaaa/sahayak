"""
Simple data access helpers. Kept dependency-free (no DB) for prototype speed —
swapping these for a real database later only touches this one file.
"""
import json
import os
import sys

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
    with open(CASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_case(case: dict):
    cases = load_cases()
    cases.append(case)
    with open(CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    return case


def update_case(case_id: str, updates: dict):
    cases = load_cases()
    for c in cases:
        if c["case_id"] == case_id:
            c.update(updates)
            break
    with open(CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    return cases


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
            f"focus={', '.join(n['focus'])} | contact={n['contact_person']} ({n['phone']})"
        )
    return "\n".join(lines)
