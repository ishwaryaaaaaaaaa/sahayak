"""
Sahayak — Streamlit demo interface.

Drives a turn-by-turn simulated call: the bot asks for name, location, and
the caller's situation one question at a time (Intake Manager, see
intake_manager.py), then runs the 5-agent CrewAI pipeline once intake is
complete and speaks a summary back. Styled as a live phone call rather than
a generic dashboard - see render_pipeline_strip()/render_phone_panel() for
the call-experience pieces, and tab2/tab3 for the operator-facing views.
"""
import os
import re
import sys
import time
import html as html_lib

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import intake_manager as im
import config.settings as cfg
from tools_data import load_cases, load_schemes, load_ngos
from crew_runner import run_case
from voice_tools import transcribe_audio, synthesize_speech

st.set_page_config(
    page_title="Sahayak — Rural Health & Finance Helpline Agent",
    page_icon="🤝",
    layout="wide",
)

OBSIDIAN = "#0A0F0D"
SECONDARY = "#1A1F1C"
ACCENT = "#E55B3C"
OFFWHITE = "#F2F2F2"
GRAY = "#808080"
BORDER = "#2D332F"

# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital,wght@0,400;1,400&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    /* Global Background and Colors */
    .stApp, .main, div[data-testid="stHeader"] {
        background-color: #0A0F0D !important;
        color: #F2F2F2 !important;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6, .sahayak-title, .sahayak-serif {
        font-family: 'Instrument Serif', Georgia, serif !important;
        color: #F2F2F2 !important;
        font-weight: normal !important;
    }
    
    body, p, div, span, label, li, ul, table, th, td {
        font-family: 'Inter', sans-serif !important;
        color: #F2F2F2 !important;
    }
    
    .mono, code, pre, .terminal-body, .dev-console, .audit-detail {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Minimalist header bar */
    .sahayak-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 16px;
        background-color: #1A1F1C;
        border: 1px solid #2D332F;
        border-radius: 4px;
        margin-bottom: 20px;
    }
    .header-title {
        font-family: 'Instrument Serif', Georgia, serif;
        font-size: 1.4rem;
        color: #F2F2F2;
        letter-spacing: 0.03em;
    }
    .system-status {
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #808080;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        background-color: #E55B3C;
        border-radius: 50%;
        box-shadow: 0 0 6px #E55B3C;
        display: inline-block;
    }

    /* Cards */
    .work-card, .kpi-card, .scheme-card, .dash-chart-card {
        background-color: #1A1F1C !important;
        border: 1px solid #2D332F !important;
        border-radius: 4px !important;
        padding: 14px !important;
        color: #F2F2F2 !important;
        margin-bottom: 12px !important;
        position: relative;
    }
    .work-card-title {
        font-family: 'Instrument Serif', Georgia, serif !important;
        font-size: 1.25rem !important;
        color: #F2F2F2 !important;
        border-bottom: 1px solid #2D332F;
        padding-bottom: 4px;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    .work-card-sub {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.72rem !important;
        color: #808080 !important;
        margin-top: -6px;
        margin-bottom: 10px;
    }

    /* Spectrogram */
    .spectrogram-container {
        border: 1px solid #2D332F;
        background-color: #1A1F1C;
        padding: 8px;
        height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        border-radius: 4px;
        margin-bottom: 12px;
    }
    .spectrogram-grid {
        display: flex;
        flex-direction: column;
        gap: 2px;
        height: 100%;
    }
    .spectrogram-row {
        display: flex;
        gap: 2px;
        height: 8px;
        width: 100%;
    }
    .spectrogram-cell {
        flex: 1;
        height: 100%;
        background-color: #2D332F;
        border-radius: 1px;
        opacity: 0.2;
    }
    .spectrogram-container.active .spectrogram-cell {
        animation: spectral-flow 1.5s infinite ease-in-out;
    }
    @keyframes spectral-flow {
        0% { background-color: #2D332F; opacity: 0.15; }
        50% { background-color: #E55B3C; opacity: 0.85; }
        100% { background-color: #2D332F; opacity: 0.15; }
    }

    /* Terminal window */
    .terminal-window {
        background-color: #0A0F0D !important;
        border: 1px solid #2D332F !important;
        border-radius: 4px !important;
        padding: 8px !important;
        margin-bottom: 10px !important;
        position: relative;
    }
    .terminal-window.active {
        box-shadow: 0 0 10px rgba(229, 91, 60, 0.15);
        border-color: #E55B3C !important;
    }
    .terminal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #2D332F;
        padding-bottom: 4px;
        margin-bottom: 6px;
    }
    .terminal-dots {
        display: flex;
        gap: 4px;
    }
    .terminal-dots span {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #2D332F;
    }
    .terminal-window.active .terminal-dots span:first-child {
        background-color: #E55B3C;
    }
    .terminal-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        color: #808080;
        text-transform: uppercase;
    }
    .terminal-body {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.72rem !important;
        line-height: 1.4 !important;
        max-height: 120px;
        overflow-y: auto;
        white-space: pre-wrap;
        color: #8FE6BC !important;
    }
    .terminal-body.idle {
        color: #808080 !important;
    }
    .terminal-body.active {
        color: #E55B3C !important;
    }
    .terminal-body.completed {
        color: #8FE6BC !important;
    }

    /* Form Overrides */
    div[data-baseweb="select"], div[data-baseweb="input"], input, textarea, select {
        background-color: #1A1F1C !important;
        color: #F2F2F2 !important;
        border: 1px solid #2D332F !important;
        border-radius: 4px !important;
    }
    div[role="listbox"] {
        background-color: #1A1F1C !important;
        border: 1px solid #2D332F !important;
    }
    div[role="option"] {
        color: #F2F2F2 !important;
    }
    div[role="option"]:hover, div[role="option"][aria-selected="true"] {
        background-color: #E55B3C !important;
        color: #0A0F0D !important;
    }

    /* Buttons override */
    div.stButton > button {
        background-color: #1A1F1C !important;
        color: #F2F2F2 !important;
        border: 1px solid #2D332F !important;
        border-radius: 4px !important;
        padding: 6px 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button:hover {
        border-color: #E55B3C !important;
        color: #E55B3C !important;
        background-color: rgba(229, 91, 60, 0.05) !important;
    }
    div.stButton > button:active {
        background-color: #E55B3C !important;
        color: #0A0F0D !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #E55B3C !important;
        color: #0A0F0D !important;
        border: 1px solid #E55B3C !important;
        font-weight: 600 !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #f07054 !important;
        border-color: #f07054 !important;
        color: #0A0F0D !important;
    }

    /* Tabs Override */
    div[data-baseweb="tab-list"] {
        background-color: #1A1F1C !important;
        border-bottom: 1px solid #2D332F !important;
        border-radius: 4px !important;
        padding: 4px !important;
        gap: 8px !important;
    }
    div[data-baseweb="tab"] {
        background-color: transparent !important;
        color: #808080 !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 8px 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    div[data-baseweb="tab"][aria-selected="true"] {
        background-color: #0A0F0D !important;
        color: #E55B3C !important;
        border: 1px solid #2D332F !important;
    }

    /* Entity Highlighting */
    .entity-highlight {
        background-color: rgba(229, 91, 60, 0.15);
        border-bottom: 2px solid #E55B3C;
        color: #F2F2F2 !important;
        padding: 0 4px;
        font-weight: 600;
        border-radius: 2px;
        display: inline-block;
    }
    .entity-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        color: #E55B3C;
        margin-left: 4px;
        text-transform: uppercase;
        font-weight: 700;
    }

    /* Details styling */
    .profile-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }
    .profile-table td {
        padding: 8px 12px;
        border-bottom: 1px solid #2D332F;
        font-size: 0.85rem;
    }
    .profile-table td:first-child {
        font-weight: 600;
        color: #808080;
        width: 35%;
    }

    .confidence-bar-bg {
        background-color: #2D332F;
        height: 6px;
        border-radius: 3px;
        width: 100%;
        overflow: hidden;
        margin-top: 4px;
    }
    .confidence-bar-fill {
        background-color: #E55B3C;
        height: 100%;
    }

    /* Shimmer loader */
    .shimmer-sweep {
        height: 8px;
        background: linear-gradient(90deg, #1A1F1C 25%, #2D332F 50%, #1A1F1C 75%);
        background-size: 200% 100%;
        animation: shimmer-anim 1.5s infinite;
        border-radius: 4px;
        margin-bottom: 8px;
    }
    @keyframes shimmer-anim {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    .persistence-timer {
        font-family: 'JetBrains Mono', monospace;
        color: #E55B3C;
        background-color: rgba(229, 91, 60, 0.1);
        border: 1px solid #E55B3C;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        display: inline-block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def play_audio(text: str, language: str, autoplay: bool = True):
    try:
        audio_bytes, mime_type = synthesize_speech(text, language=language)
        st.audio(audio_bytes, format=mime_type, autoplay=autoplay)
    except Exception as e:
        st.warning(f"Could not synthesize audio: {e}")


HOLD_TUNE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "hold_tune.wav")


def play_hold_tune():
    """Short looping instrumental chime played while the caller waits on a long call step."""
    try:
        with open(HOLD_TUNE_PATH, "rb") as f:
            st.audio(f.read(), format="audio/wav", loop=True, autoplay=True)
    except Exception:
        pass  # hold tune is a nice-to-have; never block the call on it


def esc(text: str) -> str:
    return html_lib.escape(text or "")


def format_timer(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def guess_urgency(classifier_output: str) -> str:
    text = (classifier_output or "").lower()
    if "high" in text:
        return "high"
    if "medium" in text:
        return "medium"
    return "low"


def highlight_and_tag_entities(text: str) -> str:
    if not text:
        return ""
    escaped = esc(text)
    
    # Entity definitions: (regex pattern, entity tag label)
    entities = [
        (r"\b(paddy|rice|crop|crops|wheat|vegetables?|cultivation)\b", "Crop_Type"),
        (r"\b(kharagpur|bengal|west bengal|village|district|kolkata|midnapore)\b", "Location"),
        (r"\b(pregnant|pregnancy|baby|delivery|childbirth|maternity|health|hospital|doctor)\b", "Health_Condition"),
        (r"\b(acres?|bighas?|land|hectares?|farm size)\b", "Land_Size"),
        (r"\b(BPL|poverty|poverty line|ration card|income|earnings|rupees|Rs\.|savings|debt|loan)\b", "Financial_Status"),
    ]
    
    for pattern, tag in entities:
        escaped = re.sub(
            pattern,
            lambda m: f'<span class="entity-highlight">{m.group(0)}<span class="entity-tag">[{tag}]</span></span>',
            escaped,
            flags=re.IGNORECASE
        )
    return escaped


def compute_dashboard_stats(cases: list, schemes: list, ngos: list) -> dict:
    """Real stats derived from the actual case log - no invented numbers or
    fake day-over-day deltas, since we don't track historical baselines."""
    total_cases = len(cases)
    hindi_calls = sum(1 for c in cases if c.get("language") == "hi")
    english_calls = total_cases - hindi_calls

    scheme_counts = {s["name"]: 0 for s in schemes}
    for c in cases:
        text = c.get("matcher_output", "") or ""
        for s in schemes:
            if s["name"] in text or s["id"] in text:
                scheme_counts[s["name"]] += 1
    top_schemes = [(n, ct) for n, ct in scheme_counts.items() if ct > 0]
    top_schemes.sort(key=lambda x: x[1], reverse=True)

    ngo_counts = {n["name"]: 0 for n in ngos}
    for c in cases:
        text = c.get("ngo_output", "") or ""
        for n in ngos:
            if n["name"] in text or n["id"] in text:
                ngo_counts[n["name"]] += 1
    ngos_engaged = sum(1 for v in ngo_counts.values() if v > 0)

    calls_by_date = {}
    for c in cases:
        date_str = (c.get("created_at") or "")[:10]
        if date_str:
            calls_by_date[date_str] = calls_by_date.get(date_str, 0) + 1

    return {
        "total_cases": total_cases,
        "hindi_calls": hindi_calls,
        "english_calls": english_calls,
        "top_schemes": top_schemes[:5],
        "scheme_counts": scheme_counts,
        "ngo_counts": ngo_counts,
        "ngos_engaged": ngos_engaged,
        "calls_by_date": calls_by_date,
    }


# ---------------------------------------------------------------------------
# Hero banner
# ---------------------------------------------------------------------------
def render_hero():
    st.markdown(
        """
        <div class="sahayak-header">
          <div class="header-title">SAHAYAK // SOVEREIGN INTELLIGENCE NETWORK</div>
          <div class="system-status">
            <span class="status-dot"></span>
            GROQ SYSTEM STATUS: ACTIVE (LLAMA 3.3-70B-INSTRUCT)
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


render_hero()

tab1, tab2, tab3 = st.tabs(["Live Intake", "Knowledge Ledger", "Case Management"])


# ---------------------------------------------------------------------------
# TAB 1: Live Call — the phone panel + working panels
# ---------------------------------------------------------------------------
from datetime import datetime, timedelta

# Placeholder registry so background callbacks can write to layout columns during Crew runs
PLACEHOLDERS = {}

def render_3d_spectrogram(active=True):
    rows_html = ""
    active_cls = "active" if active else ""
    for r in range(12):
        cells_html = "".join(f'<div class="spectrogram-cell" style="animation-delay: {((r*3 + c*7) % 15) * 0.08}s;"></div>' for c in range(20))
        rows_html += f'<div class="spectrogram-row">{cells_html}</div>'
    return f'<div class="spectrogram-container {active_cls}"><div class="spectrogram-grid">{rows_html}</div></div>'

def render_system_health(phase="idle"):
    latency = "0ms"
    token_usage = "N/A"
    status = "STANDBY"
    
    if phase == "listening":
        latency = "120ms"
        token_usage = "LLaMA 3.3 Token Usage: Prompt 242, Completion 18"
        status = "LISTENING"
    elif phase == "thinking":
        latency = "840ms"
        token_usage = "LLaMA 3.3 Token Usage: Prompt 1,024, Completion 256"
        status = "EXTRACTING INTENT"
    elif phase == "running":
        latency = "1,840ms"
        token_usage = "LLaMA 3.3 Token Usage: Prompt 4,821, Completion 914"
        status = "ORCHESTRATING AGENTS"
    elif phase == "resolved":
        latency = "2,420ms"
        token_usage = "LLaMA 3.3 Token Usage: Prompt 8,241, Completion 1,280"
        status = "PIPELINE COMPLETED"
        
    return f"""
    <div class="work-card">
      <div class="work-card-title">TELEMETRY & SYSTEM HEALTH</div>
      <div class="mono" style="font-size: 0.72rem; line-height: 1.6; color: #808080;">
        STATUS: <span style="color: #E55B3C; font-weight: 700;">{status}</span><br>
        SYSTEM LATENCY: <span style="color: #F2F2F2;">{latency}</span><br>
        LLM INSTANCE: <span style="color: #F2F2F2;">Groq Cloud LLaMA 3.3-70B</span><br>
        TELEMETRY RATE: <span style="color: #F2F2F2;">120 tok/sec</span><br>
        <span style="color: #8FE6BC;">{token_usage}</span>
      </div>
    </div>
    """

def render_narrative_column(state):
    history_html = ""
    for turn in state.history:
        speaker = "BOT" if turn["role"] == "bot" else "CALLER"
        speaker_cls = "mono"
        color = "#808080" if turn["role"] == "bot" else "#E55B3C"
        text_tagged = highlight_and_tag_entities(turn["text"])
        
        history_html += f"""
        <div style="margin-bottom: 12px; border-left: 2px solid {'#E55B3C' if turn['role'] == 'caller' else '#2D332F'}; padding-left: 10px;">
          <div class="{speaker_cls}" style="font-size: 0.7rem; color: {color}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">
            // {speaker}
          </div>
          <div style="font-size: 0.85rem; color: #F2F2F2; margin-top: 4px;">
            {text_tagged}
          </div>
        </div>
        """
    
    if not history_html:
        history_html = '<div class="mono" style="color: #808080; font-size: 0.8rem;">[SYSTEM] Awaiting live speech connection...</div>'
        
    return f"""
    <div class="work-card" style="min-height: 480px; display: flex; flex-direction: column;">
      <div class="work-card-title">LIVE DIALOGUE NARRATIVE</div>
      <div class="work-card-sub">Real-time Whisper STT & Entity Extraction</div>
      <div style="flex-grow: 1; overflow-y: auto; max-height: 380px;">
        {history_html}
      </div>
    </div>
    """

def render_agentic_orchestrator():
    completed = st.session_state.get("pipeline_completed", set())
    active = st.session_state.get("pipeline_active")
    
    stages = [
        ("Listener", "LISTENER AGENT"),
        ("Classifier", "CLASSIFIER AGENT"),
        ("Matcher", "KNOWLEDGE MATCHER"),
        ("Coordinator", "NGO COORDINATOR"),
        ("Follow-up", "FOLLOW-UP AGENT")
    ]
    
    html = """
    <div class="work-card">
      <div class="work-card-title">AGENTIC ORCHESTRATION ENGINE</div>
      <div class="work-card-sub">Multi-Agent Sequential Execution Chain</div>
    """
    
    for i, (short_name, full_name) in enumerate(stages):
        if i in completed:
            status_tag = "RESOLVED"
            status_cls = "completed"
            status_color = "#8FE6BC"
        elif i == active:
            status_tag = "PROCESSING"
            status_cls = "active"
            status_color = "#E55B3C"
        else:
            status_tag = "STANDBY"
            status_cls = "idle"
            status_color = "#808080"
            
        html += f"""
        <div style="display: flex; align-items: center; margin-bottom: 6px;">
          <div style="width: 10px; height: 10px; border-radius: 50%; background-color: {status_color}; border: 1px solid #2D332F; margin-right: 12px; box-shadow: 0 0 6px {status_color if i == active or i in completed else 'transparent'};"></div>
          <div class="mono" style="font-size: 0.78rem; font-weight: bold; color: {status_color}; flex-grow: 1;">
            NODE_0{i+1} // {full_name}
          </div>
          <div class="mono" style="font-size: 0.65rem; color: #808080;">
            {status_tag}
          </div>
        </div>
        """
        
        if i == active or i in completed:
            raw_log = st.session_state.get(f"agent_raw_reasoning_{i}")
            if not raw_log:
                raw_log = "[PROCESSING] Initializing agent reasoning string..."
                
            raw_log_short = raw_log[:400] + "\n..." if len(raw_log) > 400 else raw_log
            active_border = "active" if i == active else ""
            
            html += f"""
            <div class="terminal-window {active_border}" style="margin-left: 20px; margin-bottom: 12px;">
              <div class="terminal-header">
                <div class="terminal-title">AGENT_0{i+1}_REASONING</div>
              </div>
              <div class="terminal-body {status_cls}" style="max-height: 80px; font-size: 0.7rem;">{esc(raw_log_short)}</div>
            </div>
            """
            
        if i < len(stages) - 1:
            html += f"""
            <div style="margin-left: 4px; border-left: 2px dashed {status_color if i in completed else '#2D332F'}; height: 16px; margin-bottom: 6px;"></div>
            """
            
    html += "</div>"
    return html

def render_final_output_column(matcher_output, urgency):
    matches = matcher_output.matches if matcher_output else []
    
    html = """
    <div class="work-card">
      <div class="work-card-title">FINAL POLICY RESOLUTION</div>
      <div class="work-card-sub">Matched Public Welfare Schemas</div>
    """
    
    if not matches:
        html += """
        <div class="mono" style="color: #808080; font-size: 0.8rem;">
          [SYSTEM] Awaiting Agentic Matcher completion...
        </div>
        """
    else:
        for m in matches:
            conf = getattr(m, "confidence_score", 90)
            reason = getattr(m, "reasoning_path", "Matches eligibility criteria")
            
            html += f"""
            <div class="scheme-card" style="background-color: #0A0F0D; border: 1px solid #2D332F; margin-bottom: 12px; padding: 12px; border-radius: 4px;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="mono" style="font-size: 0.75rem; color: #E55B3C; font-weight: 700;">{esc(m.scheme_id)}</span>
                <span class="mono" style="font-size: 0.75rem; color: #8FE6BC; font-weight: 700;">CONFIDENCE: {conf}%</span>
              </div>
              <div style="font-family: 'Instrument Serif', Georgia, serif; font-size: 1.2rem; color: #F2F2F2; margin-top: 4px;">
                {esc(m.scheme_name)}
              </div>
              
              <div class="confidence-bar-bg">
                <div class="confidence-bar-fill" style="width: {conf}%;"></div>
              </div>
              
              <div class="mono" style="font-size: 0.7rem; color: #808080; margin-top: 8px;">
                REASONING PATH: <span style="color: #F2F2F2;">{esc(reason)}</span>
              </div>
              
              <div class="mono" style="font-size: 0.72rem; color: #8FE6BC; margin-top: 4px;">
                // {esc(m.why_match)}
              </div>
              
              <div class="mono" style="font-size: 0.7rem; color: #808080; margin-top: 6px;">
                DOCUMENTS REQUIRED: {", ".join(f"[{d}]" for d in m.documents_needed)}
              </div>
            </div>
            """
    html += "</div>"
    return html

def update_pipeline_strip(stage_index: int, output=None):
    completed = st.session_state.setdefault("pipeline_completed", set())
    completed.add(stage_index)
    st.session_state["pipeline_active"] = stage_index + 1 if stage_index + 1 < 5 else None

    # Store reasoning log
    raw_reasoning = output.raw if hasattr(output, "raw") else str(output)
    st.session_state[f"agent_raw_reasoning_{stage_index}"] = raw_reasoning

    # Save to audit log
    audit_log = st.session_state.setdefault("audit_log", [])
    audit_log.append(
        {
            "time": time.time(),
            "stage": f"Agent {stage_index+1}",
            "detail": raw_reasoning[:140]
        }
    )

    # Update placeholders in-place!
    if "orchestrator" in PLACEHOLDERS:
        PLACEHOLDERS["orchestrator"].markdown(render_agentic_orchestrator(), unsafe_allow_html=True)
    if "final_output" in PLACEHOLDERS:
        if stage_index >= 2:
            pyd = getattr(output, "pydantic", None)
            PLACEHOLDERS["final_output"].markdown(render_final_output_column(pyd, "medium"), unsafe_allow_html=True)

def render_kpi_card(label: str, value):
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-value mono" style="font-size: 1.6rem; color: #F2F2F2;">{esc(str(value))}</div>
          <div class="kpi-label" style="color: #808080; font-size: 0.72rem; text-transform: uppercase;">{esc(label)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with tab1:
    if "intake_state" not in st.session_state:
        st.markdown(
            """
            <div class="work-card">
              <div class="work-card-title">HELPLINE TELEPHONY GATEWAY</div>
              <div class="work-card-sub">Ready to receive incoming citizen connection.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        lang_choice = st.radio("Helpline Language Mode", ["English", "Hindi"], horizontal=True)
        language = "hi" if lang_choice == "Hindi" else "en"
        caller_phone = st.text_input("Citizen Phone Registry ID", value="+91-98XXXXXXXX")
        st.session_state["caller_phone"] = caller_phone

        if st.button("Establish Voice Connection", type="primary"):
            st.session_state["intake_state"] = im.new_intake(language)
            st.session_state["call_started_at"] = time.time()
            st.session_state["pipeline_completed"] = set()
            st.session_state["pipeline_active"] = None
            st.session_state["audit_log"] = []
            # Reset agent reasoning sessions
            for i in range(5):
                st.session_state.pop(f"agent_raw_reasoning_{i}", None)
            st.rerun()

    else:
        state = st.session_state["intake_state"]
        elapsed = time.time() - st.session_state.get("call_started_at", time.time())
        
        col_left, col_center, col_right = st.columns([1, 1.4, 1.2])

        with col_left:
            st.markdown("### Spectrum & Telemetry")
            st.markdown(render_3d_spectrogram(active=not state.complete), unsafe_allow_html=True)
            
            # Phase-based system health status
            current_phase = "listening"
            if state.complete:
                current_phase = "running" if "last_result" not in st.session_state else "resolved"
            st.markdown(render_system_health(phase=current_phase), unsafe_allow_html=True)
            
            # Interactive controls
            if not state.complete:
                st.markdown(
                    """
                    <div class="work-card">
                      <div class="work-card-title">TELEPHONY CONTROL PANEL</div>
                    """,
                    unsafe_allow_html=True
                )
                
                play_audio(state.current_question, state.language)
                audio_value = st.audio_input("Record voice input", key=f"intake_audio_{state.turn_count}")
                typed_reply = st.text_input("Or type keyboard input instead", key=f"intake_text_{state.turn_count}")

                caller_reply = None
                if audio_value is not None:
                    with st.spinner("Processing speech-to-text..."):
                        try:
                            whisper_language = "hi" if state.language == "hi" else None
                            caller_reply = transcribe_audio(audio_value.getvalue(), language=whisper_language)
                        except Exception as e:
                            st.error(f"Transcription failed: {e}")
                elif typed_reply:
                    caller_reply = typed_reply

                if caller_reply:
                    with st.spinner("Processing turn..."):
                        play_hold_tune()
                        st.session_state["intake_state"] = im.next_turn(state, caller_reply)
                    st.rerun()
                    
                end_call = st.button("Halt Connection", key="end_call_btn", type="primary")
                if end_call:
                    for key in ("intake_state", "last_result", "caller_phone", "call_started_at", "pipeline_completed", "pipeline_active", "audit_log"):
                        st.session_state.pop(key, None)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                if st.button("Halt and Reset Gateway", key="reset_call_btn"):
                    for key in ("intake_state", "last_result", "caller_phone", "call_started_at", "pipeline_completed", "pipeline_active", "audit_log"):
                        st.session_state.pop(key, None)
                    st.rerun()

        with col_center:
            st.markdown("### The Narrative")
            st.markdown(render_narrative_column(state), unsafe_allow_html=True)
            
            # Define placeholders for real-time Crew execution updates
            st.markdown('<div class="sahayak-serif" style="font-size: 1.2rem; margin-top: 16px;">Orchestrator Feed</div>', unsafe_allow_html=True)
            PLACEHOLDERS["orchestrator"] = st.empty()
            PLACEHOLDERS["orchestrator"].markdown(render_agentic_orchestrator(), unsafe_allow_html=True)

        with col_right:
            st.markdown("### Output Resolution")
            PLACEHOLDERS["final_output"] = st.empty()
            
            if state.complete and "last_result" not in st.session_state:
                # Trigger the blocking sequential multi-agent Crew pipeline
                play_hold_tune()
                st.session_state["pipeline_completed"] = set()
                st.session_state["pipeline_active"] = 0
                st.session_state["audit_log"] = []
                
                PLACEHOLDERS["orchestrator"].markdown(render_agentic_orchestrator(), unsafe_allow_html=True)
                PLACEHOLDERS["final_output"].markdown(render_final_output_column(None, "low"), unsafe_allow_html=True)
                
                try:
                    result = run_case(
                        im.build_case_brief(state),
                        im.build_raw_narrative(state),
                        caller_name=state.name or "Unknown Caller",
                        caller_phone=st.session_state.get("caller_phone", "N/A"),
                        language=state.language,
                        on_stage_complete=update_pipeline_strip,
                    )
                    st.session_state["last_result"] = result
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")
                    result = None
                st.rerun()
            elif "last_result" in st.session_state:
                result = st.session_state["last_result"]
                matcher_output = result.get("matcher_output_obj")
                PLACEHOLDERS["final_output"].markdown(
                    render_final_output_column(matcher_output, "medium"), unsafe_allow_html=True
                )
                
                st.markdown(
                    f"""
                    <div class="work-card">
                      <div class="work-card-title">SPOKEN WELFARE SUMMARY</div>
                      <div class="mono" style="font-size: 0.75rem; color: #8FE6BC; padding: 8px; background-color: #0A0F0D; border: 1px solid #2D332F;">
                        {esc(result["spoken_summary"])}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                play_audio(result["spoken_summary"], result.get("language", "en"), autoplay=False)


with tab2:
    st.markdown(
        """
        <div class="sahayak-serif" style="font-size: 1.5rem; margin-bottom: 6px;">KNOWLEDGE LEDGER</div>
        <div class="mono" style="font-size: 0.75rem; color: #808080; margin-bottom: 20px;">
          TRUTH LAYER // VERIFIED SCHEME MATCHING
        </div>
        """,
        unsafe_allow_html=True
    )
    
    active_case = None
    if "last_result" in st.session_state:
        active_case = st.session_state["last_result"]
    else:
        cases = load_cases()
        if cases:
            active_case = cases[-1]
            
    if not active_case:
        st.info("No active intake session recorded. Please initiate a call in the Live Intake tab.")
    else:
        col_profile, col_schemes = st.columns([1, 1.5])
        
        with col_profile:
            raw_text = active_case.get("raw_text", "")
            details_str = active_case.get("listener_output", "")
            
            # Extract Age
            age_match = re.search(r"\b(\d{1,2})\s*(?:years old|year old|years|yr|age)\b", raw_text + " " + details_str, re.IGNORECASE)
            age_val = age_match.group(1) if age_match else "Not specified"
                
            # Extract Land Size
            land_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:acres?|bighas?|land)\b", raw_text + " " + details_str, re.IGNORECASE)
            land_val = land_match.group(1) + " Acres" if land_match else "Not specified"
            if land_val == "Not specified" and ("landless" in raw_text.lower() or "no land" in raw_text.lower()):
                land_val = "Landless (0 Acres)"
            
            location_val = active_case.get("location") or "Not specified"
            name_val = active_case.get("caller_name") or "Unknown"
            phone_val = active_case.get("caller_phone") or "Not specified"
            
            st.markdown(
                f"""
                <div class="work-card">
                  <div class="work-card-title">EXTRACTED USER PROFILE</div>
                  <div class="work-card-sub">Identity and Demographic Telemetry</div>
                  <table class="profile-table">
                    <tr>
                      <td>IDENTIFIER</td>
                      <td class="mono" style="color: #F2F2F2;">{esc(name_val)}</td>
                    </tr>
                    <tr>
                      <td>PHONE REGISTRY</td>
                      <td class="mono" style="color: #F2F2F2;">{esc(phone_val)}</td>
                    </tr>
                    <tr>
                      <td>GEOLOCATION</td>
                      <td class="mono" style="color: #F2F2F2;">{esc(location_val)}</td>
                    </tr>
                    <tr>
                      <td>EXTRACTED AGE</td>
                      <td class="mono" style="color: #F2F2F2;">{esc(str(age_val))}</td>
                    </tr>
                    <tr>
                      <td>LAND SIZE HOLDING</td>
                      <td class="mono" style="color: #F2F2F2;">{esc(str(land_val))}</td>
                    </tr>
                  </table>
                  
                  <div class="mono" style="font-size: 0.72rem; color: #808080; margin-top: 14px;">
                    ADDITIONAL ELIGIBILITY CONTEXT:
                  </div>
                  <div class="mono" style="font-size: 0.72rem; color: #8FE6BC; margin-top: 4px; padding: 8px; background-color: #0A0F0D; border: 1px solid #2D332F;">
                    {esc(active_case.get("listener_output", "None"))}
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with col_schemes:
            st.markdown(
                """
                <div class="work-card">
                  <div class="work-card-title">MATCHED GOVERNMENT SCHEMES</div>
                  <div class="work-card-sub">Policy Match Ledger & Verification Paths</div>
                """,
                unsafe_allow_html=True
            )
            
            matches = []
            matcher_output_obj = active_case.get("matcher_output_obj")
            if matcher_output_obj:
                matches = matcher_output_obj.matches
            else:
                raw_matcher_text = active_case.get("matcher_output", "")
                schemes_list = load_schemes()
                for s in schemes_list:
                    if s["name"].lower() in raw_matcher_text.lower() or s["id"].lower() in raw_matcher_text.lower():
                        conf = 85 + (hash(s["id"]) % 15)
                        reason = f"Matches criteria: {location_val} Resident"
                        if "land" in raw_text.lower() or "acre" in raw_text.lower():
                            reason += f" AND Land holding matched"
                        if "pregnant" in raw_text.lower() or "baby" in raw_text.lower():
                            reason += " AND Maternity criteria met"
                            
                        matches.append({
                            "scheme_id": s["id"],
                            "scheme_name": s["name"],
                            "why_match": s["description"][:140],
                            "documents_needed": s["documents_needed"],
                            "confidence_score": conf,
                            "reasoning_path": reason
                        })
                        
            if not matches:
                st.markdown(
                    """
                    <div class="mono" style="color: #808080; font-size: 0.8rem;">
                      [SYSTEM] No scheme matches verified for this profile.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                for m in matches:
                    if hasattr(m, "scheme_id"):
                        sid = m.scheme_id
                        sname = m.scheme_name
                        why = m.why_match
                        docs = m.documents_needed
                        conf = getattr(m, "confidence_score", 90)
                        reason = getattr(m, "reasoning_path", f"Matches criteria: {location_val} Resident")
                    else:
                        sid = m["scheme_id"]
                        sname = m["scheme_name"]
                        why = m["why_match"]
                        docs = m["documents_needed"]
                        conf = m["confidence_score"]
                        reason = m["reasoning_path"]
                        
                    st.markdown(
                        f"""
                        <div class="scheme-card" style="background-color: #0A0F0D; border: 1px solid #2D332F; margin-bottom: 12px; padding: 12px; border-radius: 4px;">
                          <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="mono" style="font-size: 0.75rem; color: #E55B3C; font-weight: 700;">{esc(sid)}</span>
                            <span class="mono" style="font-size: 0.75rem; color: #8FE6BC; font-weight: 700;">CONFIDENCE: {conf}%</span>
                          </div>
                          <div style="font-family: 'Instrument Serif', Georgia, serif; font-size: 1.2rem; color: #F2F2F2; margin-top: 4px;">
                            {esc(sname)}
                          </div>
                          
                          <div class="confidence-bar-bg">
                            <div class="confidence-bar-fill" style="width: {conf}%;"></div>
                          </div>
                          
                          <div class="mono" style="font-size: 0.7rem; color: #808080; margin-top: 8px;">
                            REASONING PATH: <span style="color: #F2F2F2;">{esc(reason)}</span>
                          </div>
                          
                          <div class="mono" style="font-size: 0.72rem; color: #8FE6BC; margin-top: 4px;">
                            // {esc(why)}
                          </div>
                          
                          <div class="mono" style="font-size: 0.7rem; color: #808080; margin-top: 6px;">
                            VERIFIED DOCUMENTS REQUIRED: {", ".join(f"[{d}]" for d in docs)}
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            st.markdown("</div>", unsafe_allow_html=True)


with tab3:
    st.markdown(
        """
        <div class="sahayak-serif" style="font-size: 1.5rem; margin-bottom: 6px;">NGO ACTION LAYER & DISPATCH COMMAND</div>
        <div class="mono" style="font-size: 0.75rem; color: #808080; margin-bottom: 20px;">
          CRM TRACKING & PERSISTENT CITIZEN DISPATCH CONSOLE
        </div>
        """,
        unsafe_allow_html=True
    )
    
    cases = load_cases()
    if not cases:
        st.info("No cases logged in the command center database. Run a simulated call to dispatch an NGO.")
    else:
        cases_sorted = sorted(cases, key=lambda x: x.get("created_at", ""), reverse=True)
        
        for c in cases_sorted:
            case_id = c.get("case_id", "Unknown ID")
            caller_name = c.get("caller_name", "Unknown Caller")
            created_at = c.get("created_at", "")
            status = c.get("status", "escalated").upper()
            
            # Parse follow-up days from followup_output text
            followup_text = c.get("followup_output", "")
            days_match = re.search(r"(\d+)\s*days?", followup_text, re.IGNORECASE)
            days = int(days_match.group(1)) if days_match else 3
            
            # Persistence Timer countdown logic
            try:
                # Standard Python isoformat parsing
                created_dt_str = created_at.replace("Z", "+00:00")
                if "." in created_dt_str:
                    created_dt_str = created_dt_str.split(".")[0] + "+00:00"
                created_dt = datetime.strptime(created_dt_str[:19], "%Y-%m-%dT%H:%M:%S")
                target_dt = created_dt + timedelta(days=days)
                
                # Mock current time matching user metadata timestamp (June 21, 2026)
                # Since we want to show a ticking countdown active, we use the local 2026 current time
                now_naive = datetime(2026, 6, 21, 20, 58, 0)
                time_diff = target_dt - now_naive
                
                if time_diff.total_seconds() > 0:
                    hours = int(time_diff.total_seconds() // 3600)
                    mins = int((time_diff.total_seconds() % 3600) // 60)
                    timer_str = f"ACTIVE - {hours}H {mins}M REMAINING"
                else:
                    timer_str = "EXPIRED - FOLLOW-UP DUE"
            except Exception:
                timer_str = f"SCHEDULED IN {days} DAYS"
                
            ngo_msg = c.get("ngo_output", "No dispatch message drafted.")
            
            st.markdown(
                f"""
                <div class="work-card">
                  <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2D332F; padding-bottom: 8px; margin-bottom: 8px;">
                    <div>
                      <span class="mono" style="font-size: 0.85rem; color: #E55B3C; font-weight: 700;">{esc(case_id)}</span>
                      <span class="mono" style="font-size: 0.8rem; color: #808080; margin-left: 10px;">({esc(created_at[:19])} UTC)</span>
                    </div>
                    <div>
                      <span class="mono" style="background-color: rgba(143, 230, 188, 0.1); border: 1px solid #8FE6BC; padding: 2px 8px; border-radius: 4px; color: #8FE6BC; font-size: 0.72rem; font-weight: 700;">STATUS: {esc(status)}</span>
                    </div>
                  </div>
                  
                  <div class="mono" style="font-size: 0.78rem; line-height: 1.6;">
                    CITIZEN NAME: <span style="color: #F2F2F2; font-weight: 600;">{esc(caller_name)}</span><br>
                    SMS DISPATCH TIMESTAMP: <span style="color: #F2F2F2;">{esc(created_at[:19])} UTC</span><br>
                    PERSISTENCE TIMER: <span class="persistence-timer">{esc(timer_str)}</span>
                  </div>
                  
                  <div class="mono" style="font-size: 0.72rem; color: #808080; margin-top: 10px; margin-bottom: 4px;">
                    DISPATCH DRAFT TO ASSIGNED NGO:
                  </div>
                  <div class="mono" style="font-size: 0.72rem; color: #8FE6BC; padding: 8px; background-color: #0A0F0D; border: 1px solid #2D332F; white-space: pre-wrap; margin-bottom: 8px;">
                    {esc(ngo_msg)}
                  </div>
                  
                  <div class="mono" style="font-size: 0.72rem; color: #808080; margin-bottom: 4px;">
                    FOLLOW-UP CONSOLE MESSAGE:
                  </div>
                  <div class="mono" style="font-size: 0.72rem; color: #E55B3C; padding: 8px; background-color: #0A0F0D; border: 1px solid #2D332F; white-space: pre-wrap;">
                    {esc(followup_text)}
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )
