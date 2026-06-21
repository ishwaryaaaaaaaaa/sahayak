"""
Agent definitions for Sahayak.

Five agents, each with one narrow job:
  1. Listener        - structures the raw (simulated-voice) complaint
  2. Classifier       - tags domain (health/finance/both) + urgency
  3. KnowledgeMatcher  - matches structured case against schemes DB
  4. NGOCoordinator    - picks the right NGO and drafts the escalation message
  5. FollowUpAgent     - generates the follow-up check-in plan and message
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import Agent, LLM
from config.settings import OPENROUTER_API_KEY, OPENROUTER_MODEL, MAX_RPM

# CrewAI's generic LiteLLM path (used for providers with no dedicated
# provider class) tags every message with a `cache_breakpoint` flag meant
# only for Anthropic's prompt-caching, but never strips it before sending
# the raw message dict to litellm. Some providers do strict schema
# validation and reject the unknown field, breaking every agent call.
# No-op the tagging function so it's never added in the first place.
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda message: message

llm = LLM(
    model=OPENROUTER_MODEL,
    api_key=OPENROUTER_API_KEY,
    temperature=0.3,
    # OpenRouter's free tier has been observed to silently stall a call for
    # minutes under load instead of erroring. Fail fast instead so callers
    # (e.g. intake_manager) can fall back rather than hang the whole app.
    timeout=25,
)


def get_listener_agent():
    return Agent(
        role="Intake Listener",
        goal=(
            "Convert a person's raw, possibly rambling description of their problem "
            "(originally spoken, here given as transcribed text) into a clean, "
            "structured summary: who they are, what happened, and what they seem to need."
        ),
        backstory=(
            "You work the intake desk of a rural helpline. Many callers are not "
            "literate and describe their situation in an unstructured, emotional way, "
            "sometimes in a mix of languages. Your job is only to listen and structure "
            "what was said — you never invent facts the person did not mention."
        ),
        llm=llm,
        max_rpm=MAX_RPM,
        verbose=True,
    )


def get_classifier_agent():
    return Agent(
        role="Case Classifier",
        goal=(
            "Given a structured case summary, classify it as health, finance, or both, "
            "and assign an urgency level (low, medium, high) based on how time-sensitive "
            "the situation is (e.g. active labour or medical emergency = high)."
        ),
        backstory=(
            "You are a triage specialist. You do not give medical or legal advice — "
            "you only categorize the case so it reaches the right downstream process "
            "quickly. You are conservative: if in doubt about urgency, you round up."
        ),
        llm=llm,
        max_rpm=MAX_RPM,
        verbose=True,
    )


def get_knowledge_matcher_agent():
    return Agent(
        role="Scheme Knowledge Matcher",
        goal=(
            "Given a classified case and a database of government health/finance schemes, "
            "identify the schemes the person most likely qualifies for, with a short plain-"
            "language reason for each match and the documents they would need."
        ),
        backstory=(
            "You are a government scheme expert who has memorized every eligibility rule "
            "in the database you're given. You never recommend a scheme that isn't in the "
            "provided list, and you never guess eligibility — you reason only from the "
            "criteria given to you."
        ),
        llm=llm,
        max_rpm=MAX_RPM,
        verbose=True,
    )


def get_ngo_coordinator_agent():
    return Agent(
        role="NGO Coordinator",
        goal=(
            "Given a case and a database of local NGOs, pick the most relevant NGO "
            "(by area and focus area) and draft a short, professional escalation message "
            "to that NGO containing the person's situation, the schemes identified, and "
            "what kind of help they need."
        ),
        backstory=(
            "You coordinate between the helpline and a network of NGOs. You write "
            "concise messages that respect the NGO worker's time — just enough context "
            "to act on, no fluff. You only select NGOs from the list provided."
        ),
        llm=llm,
        max_rpm=MAX_RPM,
        verbose=True,
    )


def get_followup_agent():
    return Agent(
        role="Follow-up Coordinator",
        goal=(
            "Given a case and what's been done so far, generate a short follow-up check-in "
            "message to the person (in simple, warm language) and a recommended next "
            "follow-up date, based on the urgency and the type of scheme/help involved."
        ),
        backstory=(
            "You make sure no one falls through the cracks after the first call. You "
            "speak warmly and simply, like a community health worker checking in on a "
            "neighbour, never like a bureaucrat."
        ),
        llm=llm,
        max_rpm=MAX_RPM,
        verbose=True,
    )
