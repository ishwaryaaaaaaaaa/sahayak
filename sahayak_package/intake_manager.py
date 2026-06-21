"""
Multi-turn intake conversation manager for Sahayak.

This intentionally does NOT use a CrewAI Agent/Task. CrewAI's Crew/Task
abstraction is built for one-shot sequential pipelines with context passed
between tasks - it has no natural model for a stateful, turn-by-turn loop
that needs to persist partial state across Streamlit reruns and decide what
to ask next. Re-invoking a full Crew.kickoff() every turn just to ask one
question would be slow and awkward. Instead this makes one direct llm.call()
per turn, reusing the same `llm` object the 5-agent pipeline uses.

Once intake is complete, build_case_brief() hands a structured case off to
the existing Listener task (see tasks/definitions.py / crew_runner.py) -
the 5-agent pipeline itself is unchanged.
"""
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional

from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.definitions import llm

logger = logging.getLogger("sahayak.intake")

MAX_TURNS = 6


class _TurnExtraction(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    problem: Optional[str] = None
    new_details: List[str] = []
    next_question: Optional[str] = None
    complete: bool = False


@dataclass
class IntakeState:
    language: str = "en"
    history: List[dict] = field(default_factory=list)
    name: Optional[str] = None
    location: Optional[str] = None
    problem: Optional[str] = None
    details: List[str] = field(default_factory=list)
    turn_count: int = 0
    complete: bool = False
    current_question: str = ""


_OPENING_GREETING_EN = (
    "Hello, I'm Sahayak. I'm here to help you.\n"
    "You can tell me what's going on — about your health, your money, or "
    "anything you're struggling with. Just speak normally, the way you'd "
    "talk to a person.\n"
    "I'll listen, and I'll tell you about government help you might be able "
    "to get. If you need more help after that, I can connect you to someone "
    "nearby who can walk you through it.\n"
    "So, go ahead. What's happening?"
)

_OPENING_GREETING_HI = (
    "नमस्ते, मैं सहायक हूं। मैं आपकी मदद के लिए यहां हूं।\n"
    "आप मुझे अपनी सेहत, पैसों, या किसी भी परेशानी के बारे में बता सकते हैं। "
    "बस सामान्य तरीके से बोलिए, जैसे आप किसी इंसान से बात करते हैं।\n"
    "मैं सुनूंगा, और आपको बताऊंगा कि आपको कौन सी सरकारी मदद मिल सकती है। अगर "
    "आपको इसके बाद और मदद चाहिए, तो मैं आपको पास के किसी ऐसे व्यक्ति से जोड़ "
    "सकता हूं जो आपकी पूरी मदद कर सके।\n"
    "तो बताइए, क्या हो रहा है?"
)


def opening_question(language: str = "en") -> str:
    return _OPENING_GREETING_HI if language == "hi" else _OPENING_GREETING_EN


def new_intake(language: str = "en") -> IntakeState:
    state = IntakeState(language=language)
    state.current_question = opening_question(language)
    state.history.append({"role": "bot", "text": state.current_question})
    return state


def _transcript_text(state: IntakeState) -> str:
    lines = []
    for turn in state.history:
        speaker = "Bot" if turn["role"] == "bot" else "Caller"
        lines.append(f"{speaker}: {turn['text']}")
    return "\n".join(lines)


def _fallback_question(state: IntakeState) -> str:
    if state.language == "hi":
        if not state.name:
            return "आपका नाम क्या है?"
        if not state.location:
            return "आप किस गाँव या जिले से हैं?"
        if not state.problem:
            return "आपकी क्या समस्या है? कृपया बताएं।"
        return "क्या आप कुछ और बताना चाहेंगे?"
    if not state.name:
        return "What is your name?"
    if not state.location:
        return "Which village or district are you calling from?"
    if not state.problem:
        return "What problem or situation are you facing?"
    return "Is there anything else you'd like to add?"


def next_turn(state: IntakeState, caller_reply: str) -> IntakeState:
    """
    Advances the conversation by one turn: records the caller's reply,
    extracts whatever fields it contains (re-scanning the whole transcript
    so out-of-order or unprompted detail is still picked up), and decides
    the next question or marks the intake complete.
    """
    state.history.append({"role": "caller", "text": caller_reply})
    state.turn_count += 1

    language_name = "Hindi (Devanagari script)" if state.language == "hi" else "English"
    known_parts = []
    if state.name:
        known_parts.append(f"name={state.name}")
    if state.location:
        known_parts.append(f"location={state.location}")
    if state.problem:
        known_parts.append(f"problem={state.problem}")
    if state.details:
        known_parts.append(f"details={'; '.join(state.details)}")
    known_text = "; ".join(known_parts) if known_parts else "(nothing yet)"

    force_complete = state.turn_count >= MAX_TURNS

    prompt = (
        "You are the intake conversation manager for a rural welfare helpline. "
        "You are having a turn-by-turn voice conversation with a caller. "
        "Here is the conversation transcript so far:\n\n"
        f"{_transcript_text(state)}\n\n"
        f"Already collected fields: {known_text}\n\n"
        "From the caller's LATEST reply (and the transcript overall), extract any of: "
        "name, location (village/district), problem (their situation/need), and any "
        "additional eligibility-relevant details (age, family status, pregnancy, "
        "disability, occupation, income, etc., as separate short strings in "
        "new_details). The caller may answer out of order or volunteer extra "
        "information unprompted - extract whatever is present, don't just answer "
        "the field you most recently asked about.\n\n"
        "Decide what to ask next:\n"
        "- If name is still missing, ask for it first.\n"
        "- Else if location is still missing, ask for it.\n"
        "- Else if problem is still missing, ask what situation/problem they're facing.\n"
        "- Else, ask at most one short clarifying question about eligibility-relevant "
        "details still missing (age, family status, pregnancy/disability/occupation, "
        "income) ONLY if something important and relevant to their stated problem is "
        "still unclear. If you already have enough to proceed, set complete=true and "
        "leave next_question empty.\n"
        "- If the caller's LATEST reply indicates they have nothing more to add or "
        "declines to elaborate further (e.g. \"that's everything\", \"no\", \"nothing "
        "else\", \"I don't know\"), you MUST respect that and set complete=true now, "
        "even if some eligibility details are still missing - never ask the same or a "
        "similar question again after the caller has already declined to answer it.\n"
        + (
            "You MUST set complete=true now and leave next_question empty - the "
            "conversation has reached its turn limit.\n"
            if force_complete
            else ""
        )
        + f"Write next_question in natural, simple {language_name} - never in another "
        "language."
    )

    try:
        result = llm.call(messages=prompt, response_model=_TurnExtraction)
    except Exception as e:
        # If the LLM call times out or errors (seen with the OpenRouter free
        # tier under load), don't hang the conversation - fall back to the
        # deterministic next question with no field extraction this turn.
        # The caller's reply already accepted into state.history above, so
        # nothing is lost; the next turn's extraction will re-scan it.
        logger.warning(f"Intake turn LLM call failed, using fallback question: {e}")
        state.current_question = _fallback_question(state)
        if force_complete:
            state.complete = True
            state.current_question = ""
        else:
            state.history.append({"role": "bot", "text": state.current_question})
        return state

    if result.name:
        state.name = result.name
    if result.location:
        state.location = result.location
    if result.problem:
        state.problem = result.problem
    if result.new_details:
        for detail in result.new_details:
            if detail not in state.details:
                state.details.append(detail)

    if force_complete or result.complete:
        state.complete = True
        state.current_question = ""
    else:
        question = result.next_question or _fallback_question(state)
        state.current_question = question
        state.history.append({"role": "bot", "text": question})

    return state


def build_case_brief(state: IntakeState) -> str:
    """Structured intake handed to the Listener task (see tasks.definitions.make_listener_task)."""
    lines = [
        f"Caller name: {state.name or 'Unknown'}",
        f"Location: {state.location or 'Unknown'}",
        f"Stated problem: {state.problem or 'Unknown'}",
    ]
    if state.details:
        lines.append("Additional details: " + "; ".join(state.details))
    return "\n".join(lines)


def build_raw_narrative(state: IntakeState) -> str:
    """Plain-prose version kept for the case log's raw_text field."""
    parts = [
        f"{state.name or 'The caller'} is calling from "
        f"{state.location or 'an unspecified location'}."
    ]
    if state.problem:
        parts.append(state.problem)
    if state.details:
        parts.append(" ".join(state.details))
    return " ".join(parts)
