"""
Crew orchestration for Sahayak.

Pipeline: Listener -> Classifier -> KnowledgeMatcher -> NGOCoordinator -> FollowUp
Each stage's output is passed as context to later stages (CrewAI's `context=`
mechanism), so later agents see earlier structured outputs without us having
to manually thread strings around.
"""
import os
import sys
import re
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import Crew, Process

from agents.definitions import (
    llm,
    get_listener_agent,
    get_classifier_agent,
    get_knowledge_matcher_agent,
    get_ngo_coordinator_agent,
    get_followup_agent,
)
from tasks.definitions import (
    make_listener_task,
    make_classifier_task,
    make_knowledge_matcher_task,
    make_ngo_coordinator_task,
    make_followup_task,
)
from tools_data import schemes_as_text, ngos_as_text, save_case


def translate_text(text: str, target_language: str = "hi") -> str:
    """
    Translates `text` using the same LLM that powers the agent pipeline
    (no separate translation dependency). The agents themselves always
    reason in English since the schemes/NGO data is in English — this is
    only for presenting results to a Hindi-speaking caller.
    """
    language_name = "Hindi" if target_language == "hi" else "English"
    prompt = (
        f"Translate the following text into natural, simple {language_name}. "
        "Keep person names, scheme names, and currency amounts unchanged. "
        "Return only the translation, with no preamble or explanation.\n\n"
        f"{text}"
    )
    return llm.call(messages=prompt)


def run_case(
    raw_text: str,
    caller_name: str = "Unknown Caller",
    caller_phone: str = "N/A",
    language: str = "en",
) -> dict:
    """
    Runs the full 5-agent pipeline on one case and returns a structured result
    dict, also persisting it to the local case log (data/cases.json).

    `language` controls only the presentation layer: agents always reason in
    English; when language="hi", the transcript summary, matched-schemes
    summary, and follow-up message are additionally translated to Hindi and
    stored under "*_hi" keys, alongside the original English output.
    """
    listener = get_listener_agent()
    classifier = get_classifier_agent()
    matcher = get_knowledge_matcher_agent()
    coordinator = get_ngo_coordinator_agent()
    follower = get_followup_agent()

    t1 = make_listener_task(listener, raw_text)
    t2 = make_classifier_task(classifier, t1)
    t3 = make_knowledge_matcher_task(matcher, [t1, t2], schemes_as_text())
    t4 = make_ngo_coordinator_task(coordinator, [t1, t2, t3], ngos_as_text())
    t5 = make_followup_task(follower, [t1, t2, t3, t4])

    crew = Crew(
        agents=[listener, classifier, matcher, coordinator, follower],
        tasks=[t1, t2, t3, t4, t5],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    case_record = {
        "case_id": f"CASE-{uuid.uuid4().hex[:8].upper()}",
        "created_at": datetime.utcnow().isoformat(),
        "caller_name": caller_name,
        "caller_phone": caller_phone,
        "language": language,
        "raw_text": raw_text,
        "listener_output": str(t1.output) if t1.output else "",
        "classifier_output": str(t2.output) if t2.output else "",
        "matcher_output": str(t3.output) if t3.output else "",
        "ngo_output": str(t4.output) if t4.output else "",
        "followup_output": str(t5.output) if t5.output else "",
        "final_output": str(result),
        "status": "escalated",
    }

    if language == "hi":
        case_record["listener_output_hi"] = translate_text(case_record["listener_output"], "hi")
        case_record["matcher_output_hi"] = translate_text(case_record["matcher_output"], "hi")
        case_record["followup_output_hi"] = translate_text(case_record["followup_output"], "hi")

    save_case(case_record)
    return case_record


if __name__ == "__main__":
    sample = (
        "I am Ramesh, I am a farmer in a village near Kharagpur. My wife is "
        "seven months pregnant and we don't have much money saved. I don't "
        "know what help we can get for the delivery or what schemes we might "
        "be eligible for. I also lost some crop this season due to rain."
    )
    res = run_case(sample, caller_name="Ramesh", caller_phone="+91-98XXXXXXXX")
    print("\n\n=== FINAL CASE RECORD ===")
    for k, v in res.items():
        print(f"\n--- {k} ---\n{v}")
