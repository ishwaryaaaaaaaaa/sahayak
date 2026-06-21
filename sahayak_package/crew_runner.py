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
from typing import Optional

from pydantic import BaseModel

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
from email_tools import send_ngo_escalation_email


def translate_text(text: str, target_language: str = "hi") -> str:
    """
    Translates `text` using the same LLM that powers the agent pipeline
    (no separate translation dependency). The agents themselves always
    reason in English since the schemes/NGO data is in English — this is
    only used for the intermediate debug display of Listener/Matcher output
    in the Streamlit stage boxes. Anything actually spoken aloud (the intake
    questions, the spoken summary, the follow-up message) is generated
    natively in the target language instead - see generate_spoken_summary()
    and the `language` param on make_followup_task.
    """
    language_name = "Hindi" if target_language == "hi" else "English"
    prompt = (
        f"Translate the following text into natural, simple {language_name}. "
        "Keep person names, scheme names, and currency amounts unchanged. "
        "Return only the translation, with no preamble or explanation.\n\n"
        f"{text}"
    )
    return llm.call(messages=prompt)


def generate_spoken_summary(matcher_output, ngo_output, language: str = "en") -> str:
    """
    Composes a short, natural spoken paragraph directly in the target
    language from the structured Knowledge Matcher + NGO Coordinator output
    (Pydantic objects, not prose) - e.g. "Yahan hum aapke liye yeh kar rahe
    hain...". This is facts-in, natural-paragraph-out, not a translation of
    an English paragraph.
    """
    matches = matcher_output.matches if matcher_output else []
    scheme_lines = "\n".join(f"- {m.scheme_name}: {m.why_match}" for m in matches) or "- No strong scheme match was found."
    ngo_name = ngo_output.ngo_name if ngo_output else "a local NGO"

    language_instruction = (
        "Write this in natural, warm, simple spoken Hindi (Devanagari script), "
        "the way a helpline worker would say it out loud on a call - not a "
        "literal translation of English, and not a list read aloud."
        if language == "hi"
        else "Write this in natural, warm, simple spoken English, the way a "
        "helpline worker would say it out loud on a call - not a list read aloud."
    )

    prompt = (
        "Compose a short spoken summary (3-5 sentences) for a caller, based on "
        "these facts:\n\n"
        f"Matched schemes:\n{scheme_lines}\n\n"
        f"We are contacting this NGO on their behalf: {ngo_name}\n\n"
        f"{language_instruction} Mention the scheme names and confirm the NGO "
        "is being contacted. Return only the spoken paragraph, no preamble."
    )
    return llm.call(messages=prompt)


def run_case(
    case_brief: str,
    raw_narrative: str,
    caller_name: str = "Unknown Caller",
    caller_phone: str = "N/A",
    language: str = "en",
) -> dict:
    """
    Runs the full 5-agent pipeline on one case and returns a structured result
    dict, also persisting it to the local case log (data/cases.json).

    `case_brief` is the structured intake collected turn-by-turn by
    intake_manager.build_case_brief() (name/location/problem/details) - this
    replaces the old single rambling transcript as the Listener task's input.
    `raw_narrative` (intake_manager.build_raw_narrative()) is a plain-prose
    version kept only for the case log's `raw_text` field.

    `language` controls generation language for caller-facing text: the
    Follow-up Coordinator writes its message directly in Hindi when
    language="hi" (see make_followup_task), and the spoken summary is
    generated natively in that language too (generate_spoken_summary).
    Classifier/Matcher/NGOCoordinator still reason in English internally
    since the schemes/NGO data is English; their stage output is additionally
    translated for the Streamlit debug display only (see translate_text).
    """
    listener = get_listener_agent()
    classifier = get_classifier_agent()
    matcher = get_knowledge_matcher_agent()
    coordinator = get_ngo_coordinator_agent()
    follower = get_followup_agent()

    t1 = make_listener_task(listener, case_brief)
    t2 = make_classifier_task(classifier, t1)
    t3 = make_knowledge_matcher_task(matcher, [t1, t2], schemes_as_text())
    t4 = make_ngo_coordinator_task(coordinator, [t1, t2, t3], ngos_as_text())
    t5 = make_followup_task(follower, [t1, t2, t3, t4], language=language)

    crew = Crew(
        agents=[listener, classifier, matcher, coordinator, follower],
        tasks=[t1, t2, t3, t4, t5],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    matcher_output = t3.output.pydantic if t3.output else None
    ngo_output = t4.output.pydantic if t4.output else None

    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    email_sent, email_error = False, None
    if ngo_output:
        email_sent, email_error = send_ngo_escalation_email(
            to_email=ngo_output.ngo_email,
            ngo_name=ngo_output.ngo_name,
            case_id=case_id,
            message_body=ngo_output.escalation_message,
        )

    case_record = {
        "case_id": case_id,
        "created_at": datetime.utcnow().isoformat(),
        "caller_name": caller_name,
        "caller_phone": caller_phone,
        "language": language,
        "raw_text": raw_narrative,
        "listener_output": str(t1.output) if t1.output else "",
        "classifier_output": str(t2.output) if t2.output else "",
        "matcher_output": str(t3.output) if t3.output else "",
        "ngo_output": str(t4.output) if t4.output else "",
        "followup_output": str(t5.output) if t5.output else "",
        "final_output": str(result),
        "email_sent": email_sent,
        "email_error": email_error,
        "status": "escalated",
    }

    case_record["spoken_summary"] = generate_spoken_summary(matcher_output, ngo_output, language)

    if language == "hi":
        case_record["listener_output_hi"] = translate_text(case_record["listener_output"], "hi")
        case_record["matcher_output_hi"] = translate_text(case_record["matcher_output"], "hi")

    save_case(case_record)
    return case_record


if __name__ == "__main__":
    import intake_manager as im

    state = im.new_intake("en")
    state = im.next_turn(state, "I am Ramesh, a farmer in a village near Kharagpur.")
    state = im.next_turn(
        state,
        "My wife is seven months pregnant and we don't have much money saved. "
        "I also lost some crop this season due to rain.",
    )
    while not state.complete:
        state = im.next_turn(state, "No, that's everything.")

    res = run_case(
        im.build_case_brief(state),
        im.build_raw_narrative(state),
        caller_name="Ramesh",
        caller_phone="+91-98XXXXXXXX",
    )
    print("\n\n=== FINAL CASE RECORD ===")
    for k, v in res.items():
        print(f"\n--- {k} ---\n{v}")
