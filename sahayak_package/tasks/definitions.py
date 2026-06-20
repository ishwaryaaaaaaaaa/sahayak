"""
Task definitions for Sahayak. Each task is tied to one agent and produces
a structured output that feeds into the next stage of the pipeline.
"""
from crewai import Task


def make_listener_task(agent, raw_text: str):
    return Task(
        description=(
            f"Here is a transcript of what a caller said (originally spoken, "
            f"transcribed to text):\n\n\"{raw_text}\"\n\n"
            "Produce a structured summary with these fields ONLY, based strictly on "
            "what was said (do not invent details):\n"
            "- person_situation: 1-2 sentence plain summary\n"
            "- stated_need: what the person seems to want help with\n"
            "- mentioned_details: any specific facts mentioned (age, occupation, "
            "family status, location, health condition, income situation, etc.)\n"
            "Return as plain text with these three labeled fields."
        ),
        expected_output=(
            "A structured summary with person_situation, stated_need, and "
            "mentioned_details clearly labeled."
        ),
        agent=agent,
    )


def make_classifier_task(agent, context_task):
    return Task(
        description=(
            "Using the structured case summary from the previous step, classify this case.\n"
            "Output exactly these fields:\n"
            "- domain: one of [health, finance, both]\n"
            "- urgency: one of [low, medium, high]\n"
            "- urgency_reason: one short sentence justifying the urgency level"
        ),
        expected_output="domain, urgency, and urgency_reason clearly labeled.",
        agent=agent,
        context=[context_task],
    )


def make_knowledge_matcher_task(agent, context_tasks, schemes_text: str):
    return Task(
        description=(
            "Using the case summary and classification from previous steps, and ONLY "
            "the schemes listed below, identify up to 3 schemes the person likely "
            "qualifies for.\n\n"
            f"AVAILABLE SCHEMES:\n{schemes_text}\n\n"
            "For each matched scheme, output:\n"
            "- scheme_id and scheme_name\n"
            "- why_match: one sentence on why this person likely qualifies\n"
            "- documents_needed: from the scheme data\n"
            "If no scheme is a strong match, say so honestly rather than forcing a match."
        ),
        expected_output="A list of matched schemes, each with scheme_id, scheme_name, why_match, and documents_needed.",
        agent=agent,
        context=context_tasks,
    )


def make_ngo_coordinator_task(agent, context_tasks, ngos_text: str):
    return Task(
        description=(
            "Using the case summary, classification, and matched schemes from previous "
            "steps, and ONLY the NGOs listed below, pick the single best-matching NGO "
            "(by focus area; area/location is illustrative for this prototype) and draft "
            "a short escalation message to them.\n\n"
            f"AVAILABLE NGOs:\n{ngos_text}\n\n"
            "Output exactly:\n"
            "- ngo_id and ngo_name\n"
            "- escalation_message: a short, professional message (3-5 sentences) summarizing "
            "the person's situation, the schemes they may qualify for, and what kind of "
            "help is being requested from the NGO"
        ),
        expected_output="ngo_id, ngo_name, and escalation_message clearly labeled.",
        agent=agent,
        context=context_tasks,
    )


def make_followup_task(agent, context_tasks):
    return Task(
        description=(
            "Using everything established in previous steps, write a short follow-up "
            "plan. Output exactly:\n"
            "- followup_message: a warm, simple check-in message (2-3 sentences) that "
            "could be read out to the person on a follow-up call\n"
            "- recommended_followup_days: a single integer, number of days from now to "
            "follow up, based on urgency (high urgency = sooner, e.g. 1-2 days; "
            "low urgency = 5-7 days)"
        ),
        expected_output="followup_message and recommended_followup_days clearly labeled.",
        agent=agent,
        context=context_tasks,
    )
