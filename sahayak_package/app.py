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

FOREST = "#1E3A2F"
TERRACOTTA = "#C2562D"
GOLD = "#D9A441"
OFFWHITE = "#FAFAF8"
CREAM = "#F5F0E4"
SAGE = "#3E8E5E"
OBSIDIAN = "#0A0F0D"
OBSIDIAN_2 = "#101713"
MALACHITE = "#1FB87C"

# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
    .stApp {{ background-color: {OFFWHITE}; }}
    h1, h2, h3, h4, .sahayak-serif {{
        font-family: 'Playfair Display', Cambria, Georgia, serif !important;
    }}
    body, p, div, span, li {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}
    .mono {{ font-family: 'JetBrains Mono', 'Courier New', monospace; }}

    /* ---------- Hero ---------- */
    .sahayak-hero {{
        position: relative;
        background:
            linear-gradient(120deg, rgba(10,15,13,0.94) 0%, rgba(16,23,19,0.85) 55%, rgba(16,23,19,0.6) 100%),
            radial-gradient(ellipse at 75% 85%, rgba(31,184,124,0.18), transparent 55%),
            linear-gradient(180deg, {OBSIDIAN_2} 0%, {OBSIDIAN} 100%);
        border-radius: 14px;
        padding: 28px 32px 22px 32px;
        margin-bottom: 14px;
        overflow: hidden;
        color: {OFFWHITE};
    }}
    .hero-motif {{
        position: absolute;
        right: 22px;
        bottom: 14px;
        font-size: 1.4rem;
        opacity: 0.22;
    }}
    .wordmark-row {{ display: flex; align-items: center; gap: 12px; }}
    .wordmark-badge {{
        width: 46px; height: 46px; border-radius: 50%;
        background: radial-gradient(circle at 35% 30%, #1A3527, {OBSIDIAN});
        border: 2px solid {MALACHITE};
        box-shadow: 0 0 10px rgba(31,184,124,0.35);
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem; flex-shrink: 0;
    }}
    .wordmark-text {{ display: flex; flex-direction: column; }}
    .wordmark {{ font-size: 1.7rem; font-weight: 700; letter-spacing: 0.01em; margin: 0; line-height: 1.1; }}
    .wordmark-sub {{ font-size: 0.85rem; color: {GOLD}; opacity: 0.9; line-height: 1.1; }}
    .hero-tagline {{ color: #D9D9D2; font-size: 1.0rem; margin: 10px 0 18px 0; max-width: 640px; }}
    .feature-row {{ display: flex; gap: 28px; flex-wrap: wrap; }}
    .feature-item {{ min-width: 150px; }}
    .feature-icon {{ font-size: 1.0rem; margin-bottom: 2px; }}
    .feature-label {{
        color: {GOLD}; font-weight: 700; font-size: 0.82rem;
        text-transform: uppercase; letter-spacing: 0.04em;
    }}
    .feature-caption {{ color: #C7CFC9; font-size: 0.80rem; margin-top: 2px; }}

    /* ---------- Pipeline strip ---------- */
    .pipeline-strip {{
        background: {CREAM};
        border: 1px solid #E8E0CC;
        border-radius: 14px;
        padding: 18px 22px 14px 22px;
        margin-bottom: 18px;
        position: relative;
        overflow: hidden;
    }}
    .pipeline-strip-header {{ margin-bottom: 12px; }}
    .pipeline-strip-title {{ font-weight: 700; font-size: 1.05rem; color: {FOREST}; }}
    .pipeline-strip-sub {{ font-size: 0.78rem; color: #8B8268; }}
    .pipeline-row {{ display: flex; align-items: flex-start; justify-content: space-between; }}
    .pipeline-node-wrap {{ display: flex; flex-direction: column; align-items: center; flex: 1; max-width: 130px; }}
    .pipeline-node {{
        width: 52px; height: 52px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.2rem; font-weight: 700; position: relative;
        border: 2px solid #D8CFB0; color: {FOREST}; background: #FFFFFF;
        transition: all 0.4s ease;
    }}
    .pipeline-node .badge {{
        position: absolute; top: -4px; right: -4px; width: 18px; height: 18px; border-radius: 50%;
        background: {OBSIDIAN}; color: #fff; font-size: 0.62rem; display: flex; align-items: center; justify-content: center;
        font-weight: 700;
    }}
    .pipeline-node.endpoint {{ border-color: {MALACHITE}; background: {OBSIDIAN}; color: #fff; }}
    .pipeline-node.completed {{
        background: {OBSIDIAN}; border-color: {MALACHITE}; color: {MALACHITE};
        box-shadow: 0 0 8px rgba(31,184,124,0.4);
    }}
    .pipeline-node.active {{
        background: #fff; border-color: {GOLD}; color: {FOREST};
        box-shadow: 0 0 0 4px rgba(217,164,65,0.25);
        animation: pulse-node 1.1s infinite;
    }}
    @keyframes pulse-node {{
        0% {{ box-shadow: 0 0 0 2px rgba(217,164,65,0.25); }}
        50% {{ box-shadow: 0 0 0 8px rgba(217,164,65,0.12); }}
        100% {{ box-shadow: 0 0 0 2px rgba(217,164,65,0.25); }}
    }}
    .pipeline-label {{ font-size: 0.78rem; font-weight: 700; margin-top: 8px; color: {FOREST}; text-align: center; }}
    .pipeline-desc {{ font-size: 0.68rem; color: #8B8268; text-align: center; margin-top: 2px; line-height: 1.3; }}
    .pipeline-connector {{
        display: flex; align-items: center; gap: 4px; flex: 0.5; justify-content: center; margin-top: 24px;
        position: relative; overflow: hidden;
    }}
    .pipeline-connector span {{
        width: 5px; height: 5px; border-radius: 50%; background: #D8CFB0; display: inline-block;
    }}
    .pipeline-connector.done span {{ background: {MALACHITE}; }}
    .pipeline-connector.live span {{ background: {GOLD}; animation: tick-pulse 1s infinite ease-in-out; }}
    .pipeline-connector.live::before {{
        content: ""; position: absolute; top: 0; left: -40%; width: 40%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(217,164,65,0.55), transparent);
        animation: glass-pulse 1.3s infinite linear;
    }}
    @keyframes glass-pulse {{ 0% {{ left: -40%; }} 100% {{ left: 100%; }} }}
    .pipeline-connector span:nth-child(2) {{ animation-delay: 0.15s; }}
    .pipeline-connector span:nth-child(3) {{ animation-delay: 0.3s; }}
    .pipeline-connector span:nth-child(4) {{ animation-delay: 0.45s; }}
    @keyframes tick-pulse {{ 0%, 100% {{ opacity: 0.5; transform: scale(0.8); }} 50% {{ opacity: 1; transform: scale(1.3); }} }}
    .pipeline-statusbar {{
        margin-top: 14px; padding: 7px 14px; border-radius: 999px; background: #E4ECDF;
        font-size: 0.78rem; color: #3F5C3F; display: inline-flex; align-items: center; gap: 6px;
    }}
    .status-dot-green {{
        width: 8px; height: 8px; border-radius: 50%; background: {SAGE}; display: inline-block;
    }}

    /* ---------- Phone panel ---------- */
    .phone-bezel {{
        background: #0E1814;
        border-radius: 30px;
        padding: 10px;
        max-width: 320px;
        margin: 0 auto;
        box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }}
    .phone-panel {{
        background:
            radial-gradient(ellipse at 80% 0%, rgba(31,184,124,0.12), transparent 60%),
            linear-gradient(160deg, {OBSIDIAN_2} 0%, {OBSIDIAN} 100%);
        border-radius: 22px;
        padding: 20px 18px;
        color: {OFFWHITE};
        min-height: 540px;
        position: relative;
    }}
    .phone-header {{ display: flex; justify-content: space-between; align-items: center; }}
    .phone-wordmark {{ display: flex; flex-direction: column; }}
    .phone-title {{ font-size: 1.05rem; font-weight: 700; }}
    .phone-title-sub {{ font-size: 0.68rem; color: {GOLD}; opacity: 0.9; }}
    .phone-status {{
        font-size: 0.66rem; color: {SAGE}; background: rgba(62,142,94,0.18);
        padding: 2px 8px; border-radius: 999px;
    }}
    .phone-timer {{ font-size: 0.85rem; color: #C7CFC9; font-variant-numeric: tabular-nums; margin-top: 4px; text-align: right; }}
    .waveform {{
        display: flex; align-items: center; justify-content: center;
        gap: 3px; height: 60px; margin: 18px 0 10px 0;
    }}
    .waveform span {{
        width: 4px; background: {MALACHITE}; border-radius: 3px; display: inline-block; height: 8px;
        box-shadow: 0 0 6px rgba(31,184,124,0.5);
    }}
    .waveform.live span {{ animation: bar-bounce 1s infinite ease-in-out; }}
    .waveform span:nth-child(odd) {{ animation-delay: 0.15s; }}
    .waveform span:nth-child(3n) {{ animation-delay: 0.3s; }}
    @keyframes bar-bounce {{ 0%, 100% {{ height: 8px; }} 50% {{ height: 44px; }} }}
    .call-quote-box {{
        background: rgba(255,255,255,0.07); border-radius: 10px; padding: 10px 14px;
        text-align: center; font-size: 0.92rem; color: #F1EFE6; margin: 4px 0 10px 0; min-height: 24px;
    }}
    .progress-line {{ font-size: 0.74rem; color: #B9C2BA; text-align: center; margin-bottom: 4px; }}
    .progress-track {{ height: 4px; background: rgba(255,255,255,0.12); border-radius: 4px; margin: 0 auto 14px auto; max-width: 220px; overflow: hidden; }}
    .progress-fill {{ height: 100%; background: {SAGE}; border-radius: 4px; animation: progress-grow 1.6s ease-in-out infinite; }}
    @keyframes progress-grow {{ 0% {{ width: 10%; }} 50% {{ width: 85%; }} 100% {{ width: 10%; }} }}
    .status-line {{ text-align: center; font-size: 0.95rem; color: #F1EFE6; font-weight: 600; margin-top: 6px; }}
    .extracted-box {{
        background: rgba(255,255,255,0.06); border-radius: 10px; padding: 12px 14px; margin-top: 10px;
    }}
    .extracted-title {{
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em;
        color: {GOLD}; font-weight: 700; margin-bottom: 6px;
    }}
    .extracted-box ul {{ margin: 0; padding-left: 0; list-style: none; font-size: 0.83rem; color: #E3E6DF; }}
    .extracted-box li {{ margin-bottom: 4px; }}
    .extracted-box li::before {{ content: "✓ "; color: {SAGE}; font-weight: 700; }}
    .end-call-row {{ display: flex; flex-direction: column; align-items: center; margin-top: 18px; }}
    .end-call-caption {{ font-size: 0.7rem; color: #9FAA9F; margin-top: 4px; }}

    /* ---------- Working cards ---------- */
    .work-card {{
        background: {CREAM}; border: 1px solid #E8E0CC; border-radius: 14px;
        padding: 16px 18px; margin-bottom: 14px; position: relative;
    }}
    .work-card.dark {{
        background:
            radial-gradient(ellipse at 90% 0%, rgba(31,184,124,0.10), transparent 60%),
            linear-gradient(160deg, {OBSIDIAN_2} 0%, {OBSIDIAN} 100%);
        color: {OFFWHITE}; border: none;
    }}
    .work-card-title {{
        font-weight: 700; color: {FOREST}; font-size: 0.95rem; margin-bottom: 4px;
        display: flex; align-items: center; gap: 6px;
    }}
    .work-card.dark .work-card-title {{ color: {OFFWHITE}; }}
    .work-card-sub {{ font-size: 0.74rem; color: #8B8268; margin-bottom: 10px; }}
    .work-card.dark .work-card-sub {{ color: #B9C2BA; }}
    .work-card .corner-motif {{ position: absolute; right: 10px; bottom: 8px; opacity: 0.18; font-size: 1.1rem; }}
    .scheme-card {{
        border: 1px solid #ECE6D4; border-radius: 10px; padding: 10px 12px; margin-bottom: 8px;
        background: #FCFAF2;
    }}
    .scheme-name {{ font-weight: 700; font-size: 0.86rem; color: {FOREST}; }}
    .scheme-bullets {{ font-size: 0.78rem; color: #5C5742; margin: 4px 0 2px 0; padding-left: 16px; }}
    .scheme-detail-link {{ font-size: 0.76rem; color: {FOREST}; font-weight: 600; }}
    .urgency-pill {{
        display: inline-block; font-size: 0.64rem; font-weight: 700; padding: 2px 9px;
        border-radius: 999px; margin-left: 6px; text-transform: uppercase; letter-spacing: 0.03em;
        float: right;
    }}
    .urgency-high {{ background: #E4ECDF; color: #2F6B47; }}
    .urgency-medium {{ background: #F1E7C8; color: #8A6A1F; }}
    .urgency-low {{ background: #EDE9DC; color: #6B6650; }}
    .amber-notice {{
        background: #FBEFD6; border-radius: 8px;
        padding: 9px 12px; font-size: 0.8rem; color: #6B4F1E; margin: 10px 0;
        display: flex; align-items: center; gap: 8px;
    }}
    .ngo-avatar {{
        width: 40px; height: 40px; border-radius: 50%; background: {FOREST}; color: #fff;
        display: flex; align-items: center; justify-content: center; font-size: 1.1rem; flex-shrink: 0;
    }}
    .ngo-header-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
    .ngo-tag {{
        font-size: 0.66rem; background: #E4ECDF; color: #2F6B47; padding: 1px 8px; border-radius: 999px;
        margin-right: 4px;
    }}
    .ngo-distance {{ font-size: 0.74rem; color: #8B8268; }}
    .status-tracker {{ display: flex; align-items: flex-start; margin: 10px 0 14px 0; }}
    .status-step {{ display: flex; flex-direction: column; align-items: center; flex: 1; position: relative; }}
    .status-dot {{
        width: 14px; height: 14px; border-radius: 50%; background: #E8E0CC; border: 2px solid #E8E0CC; z-index: 1;
    }}
    .status-dot.done {{ background: {SAGE}; border-color: {SAGE}; }}
    .status-dot.active {{ background: {GOLD}; border-color: {GOLD}; }}
    .status-step:not(:last-child)::after {{
        content: ""; position: absolute; top: 6px; left: 50%; width: 100%; height: 2px; background: #E8E0CC; z-index: 0;
    }}
    .status-step.done-track:not(:last-child)::after {{ background: {SAGE}; }}
    .status-step-label {{ font-size: 0.64rem; color: #6B6650; margin-top: 5px; text-align: center; }}
    .updates-feed {{ font-size: 0.80rem; color: #5C5742; margin-top: 4px; }}
    .updates-feed .update-row {{ padding: 5px 0; border-bottom: 1px solid #ECE6D4; display: flex; gap: 6px; }}
    .updates-feed .update-dot {{ color: {SAGE}; }}
    .updates-feed .update-time {{ color: #A69E80; font-size: 0.72rem; white-space: nowrap; }}
    /* dark working cards (e.g. Call in Progress) need light text + translucent
       chat-bubble rows instead of the light-card defaults above, which were
       unreadable (dark brown text) against the dark green background */
    .work-card.dark .updates-feed {{ color: {OFFWHITE}; }}
    .work-card.dark .updates-feed .update-row {{
        background: rgba(255,255,255,0.08); border-bottom: none; border-radius: 8px;
        padding: 8px 10px; margin-bottom: 6px;
    }}
    .work-card.dark .updates-feed .update-time {{ color: {GOLD}; }}
    .ngo-checklist {{ font-size: 0.82rem; color: #4E4A38; margin: 6px 0; padding-left: 0; list-style: none; }}
    .ngo-checklist li::before {{ content: "✓ "; color: {SAGE}; font-weight: 700; }}

    /* ---------- Audit Trail / Developer Console ---------- */
    .audit-row {{ border-left: 2px solid {MALACHITE}; padding: 4px 0 8px 12px; margin-bottom: 2px; }}
    .audit-time {{ color: {MALACHITE}; font-size: 0.74rem; }}
    .audit-stage {{ color: {OFFWHITE}; font-size: 0.8rem; font-weight: 600; margin-left: 6px; }}
    .audit-detail {{ color: #9FB0A6; font-size: 0.7rem; margin-top: 2px; line-height: 1.4; }}
    .dev-console {{
        background: {OBSIDIAN}; color: #8FE6BC; font-size: 0.72rem; padding: 14px 16px;
        border-radius: 8px; white-space: pre-wrap; max-height: 360px; overflow-y: auto; line-height: 1.5;
    }}

    /* ---------- Shimmer skeleton loaders ---------- */
    .shimmer-line {{ font-size: 0.74rem; color: {MALACHITE}; margin-bottom: 8px; }}
    .shimmer-bar {{
        height: 10px; border-radius: 4px; margin-bottom: 7px; width: 100%;
        background: linear-gradient(90deg, #ECE6D4 25%, #F8F4E8 37%, #ECE6D4 63%);
        background-size: 400% 100%; animation: shimmer-sweep 1.4s ease-in-out infinite;
    }}
    @keyframes shimmer-sweep {{ 0% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}

    /* ---------- Scrolling micro-log status (terminal feel) ---------- */
    .micro-log {{
        font-size: 0.72rem; color: {MALACHITE}; margin-top: 10px; white-space: nowrap;
        overflow: hidden;
    }}
    .micro-log .cursor {{ animation: blink-cursor 1s step-end infinite; }}
    @keyframes blink-cursor {{ 0%, 50% {{ opacity: 1; }} 50.01%, 100% {{ opacity: 0; }} }}

    /* ---------- Keyword highlight in transcript ---------- */
    .kw-highlight {{
        color: {MALACHITE}; font-weight: 700; border-bottom: 1px dotted {MALACHITE};
        text-shadow: 0 0 6px rgba(31,184,124,0.4);
    }}

    /* ---------- Dashboard ---------- */
    .dash-sidebar {{
        background: linear-gradient(160deg, {OBSIDIAN_2} 0%, {OBSIDIAN} 100%);
        border-radius: 14px; padding: 14px 10px; min-height: 480px;
    }}
    .dash-nav-title {{ color: {GOLD}; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; padding: 4px 10px 10px 10px; }}
    .kpi-card {{
        background: {CREAM}; border: 1px solid #E8E0CC; border-radius: 12px;
        padding: 14px 16px; text-align: left;
    }}
    .kpi-value {{ font-size: 1.7rem; font-weight: 700; color: {FOREST}; font-family: 'Playfair Display', serif; }}
    .kpi-label {{ font-size: 0.74rem; color: #8B8268; margin-top: 2px; }}
    .kpi-delta {{ font-size: 0.7rem; margin-top: 4px; font-weight: 600; }}
    .kpi-delta.up {{ color: {SAGE}; }}
    .kpi-delta.down {{ color: {TERRACOTTA}; }}
    .dash-chart-card {{
        background: {CREAM}; border: 1px solid #E8E0CC; border-radius: 14px; padding: 16px 18px; margin-bottom: 14px;
    }}
    .dash-chart-title {{ font-weight: 700; color: {FOREST}; font-size: 0.95rem; margin-bottom: 10px; }}
    .config-row {{
        display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid #ECE6D4; font-size: 0.84rem;
    }}
    .config-row span:first-child {{ color: #6B6650; }}
    .config-row span:last-child {{ color: {FOREST}; font-weight: 600; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }}

    /* secondary (default) buttons -> forest green action buttons; primary -> terracotta urgent accent (End Call, Start Call) */
    button[kind="secondary"] {{
        background: linear-gradient(160deg, {FOREST} 0%, #16281F 100%) !important;
        color: #fff !important; border: 1px solid rgba(31,184,124,0.35) !important;
        border-radius: 8px !important; transition: transform 0.08s ease, box-shadow 0.15s ease !important;
        box-shadow: 0 2px 0 rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.08) !important;
    }}
    button[kind="secondary"]:hover {{ box-shadow: 0 0 10px rgba(31,184,124,0.35) !important; }}
    button[kind="secondary"]:active {{ transform: scale(0.97) translateY(1px) !important; box-shadow: none !important; }}
    button[kind="primary"] {{
        border-radius: 999px !important; transition: transform 0.08s ease !important;
    }}
    button[kind="primary"]:active {{ transform: scale(0.93) !important; }}
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


def extracted_keywords(state) -> list:
    """Real keyword candidates to highlight in the transcript: the detail
    phrases the Intake Manager actually extracted, plus significant words
    from the stated problem - never invented."""
    words = []
    if state.problem:
        words.extend(w.strip(".,!?") for w in state.problem.split() if len(w.strip(".,!?")) > 4)
    return list(state.details) + words


def highlight_keywords(text: str, keywords: list) -> str:
    escaped = esc(text)
    for kw in sorted({k for k in keywords if k and k.strip()}, key=len, reverse=True):
        pattern = re.escape(esc(kw))
        if not pattern:
            continue
        escaped = re.sub(
            pattern,
            lambda m: f'<span class="kw-highlight">{m.group(0)}</span>',
            escaped,
            flags=re.IGNORECASE,
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
        f"""
        <div class="sahayak-hero">
          <div class="wordmark-row">
            <div class="wordmark-badge">👂</div>
            <div class="wordmark-text">
              <span class="wordmark sahayak-serif">Sahayak</span>
              <span class="wordmark-sub">সহায়ক</span>
            </div>
          </div>
          <div class="hero-tagline">
            A voice-first AI assistant that connects rural India to government
            health &amp; finance schemes, and to the NGOs who can help them apply.
          </div>
          <div class="feature-row">
            <div class="feature-item">
              <div class="feature-icon">🎤</div>
              <div class="feature-label">Voice First</div>
              <div class="feature-caption">Speak in your own language</div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">🧠</div>
              <div class="feature-label">Understands You</div>
              <div class="feature-caption">AI understands your situation</div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">🎯</div>
              <div class="feature-label">Finds Solutions</div>
              <div class="feature-caption">Matches relevant schemes &amp; support</div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">🤝</div>
              <div class="feature-label">Stays With You</div>
              <div class="feature-caption">Follows up till your problem is solved</div>
            </div>
          </div>
          <div class="hero-motif">🌾</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Pipeline strip — the signature live element
# ---------------------------------------------------------------------------
PIPELINE_STAGES = [
    {"label": "Voice Agent", "icon": "🎤", "desc": "Listens and transcribes speech", "log": "Structuring caller's situation"},
    {"label": "Intent Agent", "icon": "🎯", "desc": "Understands situation and extracts needs", "log": "Classifying domain and urgency"},
    {"label": "Matcher Agent", "icon": "🧩", "desc": "Matches with relevant schemes & criteria", "log": "Querying scheme database"},
    {"label": "NGO Agent", "icon": "🤝", "desc": "Finds and notifies local NGOs if help needed", "log": "Searching NGO directory"},
    {"label": "Follow-up Agent", "icon": "🔄", "desc": "Tracks progress and follows up regularly", "log": "Drafting follow-up plan"},
]


def render_pipeline_strip(completed=None, active=None) -> str:
    completed = completed or set()

    nodes_html = [
        '<div class="pipeline-node-wrap"><div class="pipeline-node endpoint">📞</div>'
        '<div class="pipeline-label">Caller</div>'
        '<div class="pipeline-desc">Any phone<br>Any network</div></div>'
    ]
    nodes_html.append(_connector_html(0 in completed or active == 0))

    for i, stage in enumerate(PIPELINE_STAGES):
        cls = "pending"
        if i in completed:
            cls = "completed"
        if i == active:
            cls = "active"
        nodes_html.append(
            f'<div class="pipeline-node-wrap"><div class="pipeline-node {cls}">{stage["icon"]}'
            f'<span class="badge">{i + 1}</span></div>'
            f'<div class="pipeline-label">{esc(stage["label"])}</div>'
            f'<div class="pipeline-desc">{esc(stage["desc"])}</div></div>'
        )
        is_live = (i == active)
        is_done = (i in completed)
        nodes_html.append(_connector_html(is_done, is_live))

    all_done = len(completed) == len(PIPELINE_STAGES)
    resolved_style = f"background: {OBSIDIAN}; border-color: {MALACHITE}; box-shadow: 0 0 8px rgba(31,184,124,0.4);" if all_done else ""
    nodes_html.append(
        f'<div class="pipeline-node-wrap"><div class="pipeline-node endpoint" style="{resolved_style}">✅</div>'
        f'<div class="pipeline-label">Resolution</div>'
        f'<div class="pipeline-desc">Problem solved.<br>Life improved.</div></div>'
    )

    if active is not None and active < len(PIPELINE_STAGES):
        log_line = f'Agent {active + 1}: {esc(PIPELINE_STAGES[active]["log"])}...<span class="cursor">_</span>'
        status_html = f'<div class="micro-log">{log_line}</div>'
    else:
        status_html = (
            '<div class="pipeline-statusbar"><span class="status-dot-green"></span>'
            "System Status: All agents operational</div>"
        )
    return (
        '<div class="pipeline-strip">'
        '<div class="pipeline-strip-header">'
        '<div class="pipeline-strip-title sahayak-serif">System Overview</div>'
        '<div class="pipeline-strip-sub">Five AI agents working together for every caller.</div>'
        "</div>"
        '<div class="pipeline-row">' + "".join(nodes_html) + "</div>"
        f"{status_html}"
        "</div>"
    )


def _connector_html(done: bool, live: bool = False) -> str:
    cls = "live" if live else ("done" if done else "")
    dots = "".join("<span></span>" for _ in range(4))
    return f'<div class="pipeline-connector {cls}">{dots}</div>'


# ---------------------------------------------------------------------------
# Render persistent header (hero + pipeline strip) once per script run
# ---------------------------------------------------------------------------
render_hero()
pipeline_placeholder = st.empty()
pipeline_placeholder.markdown(
    render_pipeline_strip(
        completed=st.session_state.get("pipeline_completed", set()),
        active=st.session_state.get("pipeline_active"),
    ),
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(["📞 Live Call", "🗂️ Case Log", "ℹ️ How It Works"])


# ---------------------------------------------------------------------------
# TAB 1: Live Call — the phone panel + working panels
# ---------------------------------------------------------------------------
def render_phone_panel(state, phase: str, elapsed: float):
    last_caller_line = ""
    for turn in reversed(state.history):
        if turn["role"] == "caller":
            last_caller_line = turn["text"]
            break

    if phase == "listening":
        status_text = "I'm listening..."
        wave_cls = "live"
    elif phase == "thinking":
        status_text = "Translating & understanding..."
        wave_cls = "live"
    elif phase == "running":
        status_text = "Finding the right help for you..."
        wave_cls = "live"
    else:
        status_text = "Call connected"
        wave_cls = ""

    bars = "".join(f"<span style='animation-delay:{i * 0.07:.2f}s'></span>" for i in range(18))

    extracted_items = []
    if state.name:
        extracted_items.append(f"Name: {esc(state.name)}")
    if state.location:
        extracted_items.append(f"Location: {esc(state.location)}")
    if state.problem:
        extracted_items.append(f"Situation: {esc(state.problem)}")
    for d in state.details:
        extracted_items.append(esc(d))
    extracted_html = "".join(f"<li>{item}</li>" for item in extracted_items) or "<li>Listening for details...</li>"

    progress_html = (
        f'<div class="progress-line">{esc(status_text)}</div>'
        '<div class="progress-track"><div class="progress-fill"></div></div>'
        if phase in ("thinking", "running")
        else f'<div class="status-line">{esc(status_text)}</div>'
    )

    st.markdown(
        f"""
        <div class="phone-bezel"><div class="phone-panel">
          <div class="phone-header">
            <div class="phone-wordmark">
              <div class="phone-title">Sahayak</div>
              <div class="phone-title-sub">সহায়ক</div>
            </div>
            <div>
              <div class="phone-status">● Connected</div>
              <div class="phone-timer">{format_timer(elapsed)}</div>
            </div>
          </div>
          <div class="waveform {wave_cls}">{bars}</div>
          <div class="call-quote-box">{f'&ldquo;{highlight_keywords(last_caller_line, extracted_keywords(state))}&rdquo;' if last_caller_line else ''}</div>
          {f'<div class="audit-detail mono" style="text-align:center; margin-bottom:8px;">Whisper STT &middot; {"Hindi" if state.language == "hi" else "English"}</div>' if last_caller_line else ''}
          {progress_html}
          <div class="extracted-box">
            <div class="extracted-title">Extracted information</div>
            <ul>{extracted_html}</ul>
          </div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="end-call-row">', unsafe_allow_html=True)
    end_call = st.button("🔴", key="end_call_btn", help="End call and start over", type="primary", use_container_width=False)
    st.markdown('<div class="end-call-caption">Tap to end call</div></div>', unsafe_allow_html=True)
    return end_call


def render_call_in_progress_card(state):
    keywords = extracted_keywords(state)
    rows = "".join(
        f'<div class="update-row"><b>{"Bot" if t["role"] == "bot" else "Caller"}:</b> '
        f'{highlight_keywords(t["text"], keywords) if t["role"] == "caller" else esc(t["text"])}</div>'
        for t in state.history[-6:]
    )
    st.markdown(
        f"""
        <div class="work-card dark">
          <div class="work-card-title">📋 Call in Progress</div>
          <div class="work-card-sub">Live ● {format_timer(time.time() - st.session_state.get('call_started_at', time.time()))}</div>
          <div class="updates-feed">{rows}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_placeholder_card(title: str, waiting_text: str):
    st.markdown(
        f"""
        <div class="work-card">
          <div class="work-card-title">{title}</div>
          <div style="color:#A6A698; font-size:0.85rem;">{esc(waiting_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_matching_results_card(matcher_output, urgency: str):
    matches = matcher_output.matches if matcher_output else []
    match_label = "High Match" if urgency == "high" else ("Medium Match" if urgency == "medium" else "Low Match")
    cards = ""
    for m in matches:
        docs_preview = ", ".join(m.documents_needed[:2]) if m.documents_needed else ""
        cards += f"""
        <div class="scheme-card">
          <span class="urgency-pill urgency-{urgency}">{esc(match_label)}</span>
          <span class="scheme-name">{esc(m.scheme_name)}</span>
          <ul class="scheme-bullets">
            <li>{esc(m.why_match)}</li>
            {f'<li>Documents: {esc(docs_preview)}</li>' if docs_preview else ''}
          </ul>
          <span class="scheme-detail-link">View details &gt;</span>
        </div>
        """
    if not cards:
        cards = '<div style="color:#8B8268; font-size:0.85rem;">No strong scheme match was found.</div>'
    st.markdown(
        f"""
        <div class="work-card">
          <div class="work-card-title">🎯 Matching Results</div>
          <div class="work-card-sub">{len(matches)} scheme{'s' if len(matches) != 1 else ''} found for you</div>
          {cards}
          <div class="corner-motif">🌾</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("Listen to all schemes", key="listen_schemes_btn", use_container_width=True)


def render_scheme_details_card(matcher_output, schemes_by_id: dict):
    matches = matcher_output.matches if matcher_output else []
    if not matches:
        render_placeholder_card("📑 Scheme Details", "No matched scheme to expand.")
        return
    st.markdown(
        '<div class="work-card"><div class="work-card-title">← Scheme Details</div>',
        unsafe_allow_html=True,
    )
    names = [m.scheme_name for m in matches]
    chosen = st.selectbox("View details for", names, key="scheme_detail_select", label_visibility="collapsed")
    match = next((m for m in matches if m.scheme_name == chosen), matches[0])
    full = schemes_by_id.get(match.scheme_id, {})
    st.markdown(f"**{esc(match.scheme_name)}**")
    st.caption(full.get("description", match.why_match))
    ov_tab, elig_tab, ben_tab, doc_tab = st.tabs(["Overview", "Eligibility", "Benefits", "Documents"])
    with ov_tab:
        st.write(full.get("description", match.why_match))
    with elig_tab:
        for e in full.get("eligibility", [match.why_match]):
            st.markdown(f"- {e}")
    with ben_tab:
        st.markdown("**Key Benefits**")
        benefit_icons = ["💰", "🛡️", "⚡", "🌾"]
        benefits = [full.get("description", "")] if full.get("description") else [match.why_match]
        for i, b in enumerate(benefits):
            st.markdown(f"{benefit_icons[i % len(benefit_icons)]} {b}")
    with doc_tab:
        for d in (full.get("documents_needed") or match.documents_needed):
            st.markdown(f"📄 {d}")
    st.button("I want to apply for this", key="apply_btn", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_ngo_card(ngo_output, ngos_by_id: dict):
    if not ngo_output:
        render_placeholder_card("🏠 NGO Assistance", "Waiting for an NGO match...")
        return
    full = ngos_by_id.get(ngo_output.ngo_id, {})
    checklist = "".join(f"<li>{esc(f.replace('_', ' ').title())}</li>" for f in full.get("focus", [])) or "<li>General assistance</li>"
    st.markdown(
        f"""
        <div class="work-card">
          <div class="work-card-title">🏠 NGO Assistance</div>
          <div class="work-card-sub">Local help available</div>
          <div class="ngo-header-row">
            <div class="ngo-avatar">🏠</div>
            <div>
              <div style="font-weight:700; color:{FOREST}; font-size:0.9rem;">{esc(ngo_output.ngo_name)}</div>
              <div><span class="ngo-tag">Local NGO</span><span class="ngo-distance">{esc(full.get('area', 'Local area'))}</span></div>
            </div>
          </div>
          <div style="font-size:0.8rem; color:#6B6650; margin-bottom:4px;">They can help you with:</div>
          <ul class="ngo-checklist">{checklist}</ul>
          <div class="amber-notice">⏰ NGO has been notified — they will contact you within 24 hours.</div>
          <div class="corner-motif">🌾</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("Call NGO now", key="call_ngo_btn", use_container_width=True, help=full.get("phone", "N/A"))


def render_followup_card(result: dict):
    stages = ["Applied", "Under Review", "Verified", "Approved", "Disbursed"]
    dots = ""
    for i, s in enumerate(stages):
        dot_cls = "done" if i == 0 else "pending"
        track_cls = "done-track" if i == 0 else ""
        dots += f'<div class="status-step {track_cls}"><div class="status-dot {dot_cls}"></div><div class="status-step-label">{s}</div></div>'
    st.markdown(
        f"""
        <div class="work-card">
          <div class="work-card-title">📅 Follow-up &amp; Status</div>
          <div class="work-card-sub">We stay with you</div>
          <div style="font-size:0.8rem; color:#6B6650; font-weight:600;">Application Status
            <span class="urgency-pill urgency-medium" style="float:right;">In Progress</span>
          </div>
          <div class="status-tracker">{dots}</div>
          <div style="font-size:0.78rem; color:#6B6650; font-weight:600; margin-bottom:2px;">Recent Updates</div>
          <div class="updates-feed">
            <div class="update-row"><span class="update-dot">●</span><span class="update-time">Just now</span> Case {esc(result['case_id'])} escalated to NGO.</div>
            <div class="update-row"><span class="update-dot">●</span><span class="update-time">Scheduled</span> {esc(result['followup_output'][:140])}</div>
          </div>
          <div class="corner-motif">🌾</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("I need more help", key="need_help_btn", use_container_width=True)


def stage_output_snippet(stage_index: int, output) -> str:
    """A short, real description of what a stage actually produced - used by
    the Audit Trail / Developer Console, never a fabricated/simulated line."""
    pyd = getattr(output, "pydantic", None)
    if stage_index == 2 and pyd is not None:
        names = ", ".join(m.scheme_name for m in pyd.matches) or "no matches"
        return f"Found {len(pyd.matches)} scheme match(es): {names}"
    if stage_index == 3 and pyd is not None:
        return f"Selected NGO: {pyd.ngo_name}"
    raw = getattr(output, "raw", "") or str(output)
    return raw[:140].replace("\n", " ")


def render_audit_trail_html(audit_log: list) -> str:
    if not audit_log:
        return (
            '<div class="work-card dark"><div class="work-card-title">🧾 Audit Trail — Chain of Thought</div>'
            '<div class="work-card-sub">Real per-agent completion log, not simulated.</div>'
            '<div class="audit-detail mono">Waiting for the first agent to finish...</div></div>'
        )
    rows = ""
    for entry in audit_log:
        ts = time.strftime("%H:%M:%S", time.localtime(entry["time"]))
        rows += (
            f'<div class="audit-row"><span class="audit-time mono">{ts}</span>'
            f'<span class="audit-stage">{esc(entry["stage"])}</span>'
            f'<div class="audit-detail mono">{esc(entry["detail"])}</div></div>'
        )
    return (
        '<div class="work-card dark"><div class="work-card-title">🧾 Audit Trail — Chain of Thought</div>'
        '<div class="work-card-sub">Real per-agent completion log, not simulated.</div>'
        f"{rows}</div>"
    )


def render_shimmer_card(title: str, loading_text: str):
    st.markdown(
        f"""
        <div class="work-card">
          <div class="work-card-title">{title}</div>
          <div class="shimmer-line mono">{esc(loading_text)}</div>
          <div class="shimmer-bar"></div>
          <div class="shimmer-bar" style="width:70%;"></div>
          <div class="shimmer-bar" style="width:45%;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def update_pipeline_strip(stage_index: int, output=None):
    completed = st.session_state.setdefault("pipeline_completed", set())
    completed.add(stage_index)
    st.session_state["pipeline_active"] = stage_index + 1 if stage_index + 1 < len(PIPELINE_STAGES) else None

    audit_log = st.session_state.setdefault("audit_log", [])
    audit_log.append(
        {
            "time": time.time(),
            "stage": PIPELINE_STAGES[stage_index]["label"],
            "detail": stage_output_snippet(stage_index, output) if output is not None else "",
        }
    )

    pipeline_placeholder.markdown(
        render_pipeline_strip(completed=completed, active=st.session_state["pipeline_active"]),
        unsafe_allow_html=True,
    )
    audit_trail_placeholder.markdown(render_audit_trail_html(audit_log), unsafe_allow_html=True)


def render_kpi_card(label: str, value):
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-value mono">{esc(str(value))}</div>
          <div class="kpi-label">{esc(label)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


DASH_NAV_ITEMS = ["Dashboard", "NGOs", "Schemes", "Settings"]


with tab1:
    if "intake_state" not in st.session_state:
        st.subheader("Start the call")
        st.caption(
            "The bot will ask the caller's name, location, and situation one "
            "question at a time, the way a real helpline call would go."
        )
        lang_choice = st.radio("Language / भाषा", ["English", "हिंदी (Hindi)"], horizontal=True)
        language = "hi" if lang_choice.startswith("हिंदी") else "en"
        caller_phone = st.text_input("Caller phone (optional, for the case log)", value="+91-98XXXXXXXX")
        st.session_state["caller_phone"] = caller_phone

        if st.button("📞 Start Call", type="primary"):
            st.session_state["intake_state"] = im.new_intake(language)
            st.session_state["call_started_at"] = time.time()
            st.session_state["pipeline_completed"] = set()
            st.session_state["pipeline_active"] = None
            st.rerun()

    else:
        state = st.session_state["intake_state"]
        elapsed = time.time() - st.session_state.get("call_started_at", time.time())
        col_phone, col_work = st.columns([1, 1.4])

        if not state.complete:
            with col_phone:
                end_call = render_phone_panel(state, phase="listening", elapsed=elapsed)
            with col_work:
                render_call_in_progress_card(state)
                render_placeholder_card("🎯 Matching Results", "Waiting for the call to finish...")
                render_placeholder_card("🏠 NGO Assistance", "Waiting for a scheme match...")
                render_placeholder_card("📅 Follow-up & Status", "Not started yet.")

            if end_call:
                for key in ("intake_state", "last_result", "caller_phone", "call_started_at", "pipeline_completed", "pipeline_active", "audit_log"):
                    st.session_state.pop(key, None)
                st.rerun()

            play_audio(state.current_question, state.language)
            audio_value = st.audio_input("🎙️ Record your reply", key=f"intake_audio_{state.turn_count}")
            typed_reply = st.text_input("Or type the reply instead", key=f"intake_text_{state.turn_count}")

            caller_reply = None
            if audio_value is not None:
                with st.spinner("Transcribing with Groq Whisper..."):
                    try:
                        whisper_language = "hi" if state.language == "hi" else None
                        caller_reply = transcribe_audio(audio_value.getvalue(), language=whisper_language)
                    except Exception as e:
                        st.error(f"Transcription failed: {e}")
            elif typed_reply:
                caller_reply = typed_reply

            if caller_reply:
                with st.spinner("Thinking..."):
                    play_hold_tune()
                    st.session_state["intake_state"] = im.next_turn(state, caller_reply)
                st.rerun()

        else:
            schemes_by_id = {s["id"]: s for s in load_schemes()}
            ngos_by_id = {n["id"]: n for n in load_ngos()}

            if "last_result" not in st.session_state:
                with col_phone:
                    render_phone_panel(state, phase="running", elapsed=elapsed)
                with col_work:
                    render_shimmer_card("🎯 Matching Results", "Querying scheme database...")
                    bento1, bento2 = st.columns(2)
                    with bento1:
                        render_shimmer_card("🏠 NGO Assistance", "Finding nearby NGOs...")
                    with bento2:
                        render_shimmer_card("📅 Follow-up & Status", "Building follow-up plan...")
                    audit_trail_placeholder = st.empty()
                    audit_trail_placeholder.markdown(render_audit_trail_html([]), unsafe_allow_html=True)

                play_hold_tune()
                st.session_state["pipeline_completed"] = set()
                st.session_state["pipeline_active"] = 0
                st.session_state["audit_log"] = []
                pipeline_placeholder.markdown(
                    render_pipeline_strip(completed=set(), active=0), unsafe_allow_html=True
                )
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

            else:
                result = st.session_state["last_result"]
                matcher_output = result.get("matcher_output_obj")
                ngo_output = result.get("ngo_output_obj")
                urgency = guess_urgency(result.get("classifier_output", ""))

                with col_phone:
                    end_call = render_phone_panel(state, phase="resolved", elapsed=elapsed)
                with col_work:
                    render_call_in_progress_card(state)
                    bento1, bento2 = st.columns(2)
                    with bento1:
                        render_matching_results_card(matcher_output, urgency)
                        render_ngo_card(ngo_output, ngos_by_id)
                    with bento2:
                        render_scheme_details_card(matcher_output, schemes_by_id)
                        render_followup_card(result)
                    st.markdown(
                        render_audit_trail_html(st.session_state.get("audit_log", [])),
                        unsafe_allow_html=True,
                    )

                if end_call:
                    for key in ("intake_state", "last_result", "caller_phone", "call_started_at", "pipeline_completed", "pipeline_active", "audit_log"):
                        st.session_state.pop(key, None)
                    st.rerun()

                st.markdown("#### 🔊 Spoken summary to caller")
                st.markdown(f'<div class="work-card">{esc(result["spoken_summary"])}</div>', unsafe_allow_html=True)
                play_audio(result["spoken_summary"], result.get("language", "en"))
                st.caption(
                    "Prototype note: the NGO is notified here via this escalation message. "
                    "In production this would be dispatched over a real channel (e.g. Twilio "
                    "SMS/voice) instead of being shown on screen."
                )

                with st.expander("🖥️ Developer Console — raw agent output"):
                    matcher_json = matcher_output.model_dump_json(indent=2) if matcher_output else "null"
                    ngo_json = ngo_output.model_dump_json(indent=2) if ngo_output else "null"
                    console_text = (
                        f"[1] LISTENER (raw text)\n{result['listener_output']}\n\n"
                        f"[2] CLASSIFIER (raw text)\n{result['classifier_output']}\n\n"
                        f"[3] MATCHER (structured Pydantic output)\n{matcher_json}\n\n"
                        f"[4] NGO COORDINATOR (structured Pydantic output)\n{ngo_json}\n\n"
                        f"[5] FOLLOW-UP (raw text)\n{result['followup_output']}"
                    )
                    st.markdown(f'<pre class="mono dev-console">{esc(console_text)}</pre>', unsafe_allow_html=True)
                    play_audio(result["followup_output"], result.get("language", "en"), autoplay=False)

                if st.button("📞 Start New Call"):
                    for key in ("intake_state", "last_result", "caller_phone", "call_started_at", "pipeline_completed", "pipeline_active", "audit_log"):
                        st.session_state.pop(key, None)
                    st.rerun()


# ---------------------------------------------------------------------------
# TAB 2: Case Log
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("Cases handled so far")
    st.caption("This is what an NGO worker or helpline supervisor would see — every case the agent pipeline has escalated.")

    cases = load_cases()
    if not cases:
        st.info("No cases yet — run a simulated call in the first tab.")
    else:
        for c in reversed(cases):
            with st.expander(f"{c['case_id']} — {c['caller_name']} ({c['created_at'][:19]} UTC)"):
                st.markdown(f"**Raw transcript:** {c['raw_text']}")
                st.markdown(f"**Status:** `{c['status']}`")
                st.markdown("**NGO escalation:**")
                st.text(c["ngo_output"])
                st.markdown("**Spoken summary:**")
                st.text(c.get("spoken_summary", ""))
                st.markdown("**Follow-up plan:**")
                st.text(c["followup_output"])

# ---------------------------------------------------------------------------
# TAB 3: Dashboard
# ---------------------------------------------------------------------------
with tab3:
    cases = load_cases()
    schemes = load_schemes()
    ngos = load_ngos()
    stats = compute_dashboard_stats(cases, schemes, ngos)

    nav_col, main_col = st.columns([0.18, 0.82])

    with nav_col:
        st.markdown('<div class="dash-sidebar">', unsafe_allow_html=True)
        st.markdown('<div class="dash-nav-title sahayak-serif">Sahayak</div>', unsafe_allow_html=True)
        active_view = st.session_state.get("dash_view", "Dashboard")
        for item in DASH_NAV_ITEMS:
            label = f"📍 {item}" if item == active_view else item
            if st.button(label, key=f"dashnav_{item}", use_container_width=True):
                st.session_state["dash_view"] = item
                active_view = item
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with main_col:
        if active_view == "Dashboard":
            st.markdown(
                f'<div class="sahayak-serif" style="font-size:1.4rem; font-weight:700; color:{FOREST};">Dashboard Overview</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Real-time overview computed from the actual case log (data/cases.json) - "
                "not synthetic numbers. It will look sparse until more calls are run."
            )

            kpi_cols = st.columns(4)
            with kpi_cols[0]:
                render_kpi_card("Total Calls Logged", stats["total_cases"])
            with kpi_cols[1]:
                render_kpi_card("Hindi Calls", stats["hindi_calls"])
            with kpi_cols[2]:
                render_kpi_card("English Calls", stats["english_calls"])
            with kpi_cols[3]:
                render_kpi_card("NGOs Engaged", f'{stats["ngos_engaged"]} / {len(ngos)}')

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.markdown(
                    '<div class="dash-chart-card"><div class="dash-chart-title">Calls Over Time</div>',
                    unsafe_allow_html=True,
                )
                if stats["calls_by_date"]:
                    df = pd.DataFrame(sorted(stats["calls_by_date"].items()), columns=["Date", "Calls"]).set_index("Date")
                    st.line_chart(df, height=220)
                else:
                    st.caption("No calls logged yet - run a simulated call in the Live Call tab.")
                st.markdown("</div>", unsafe_allow_html=True)
            with chart_col2:
                st.markdown(
                    '<div class="dash-chart-card"><div class="dash-chart-title">Top Schemes Matched</div>',
                    unsafe_allow_html=True,
                )
                if stats["top_schemes"]:
                    df = pd.DataFrame(stats["top_schemes"], columns=["Scheme", "Matches"]).set_index("Scheme")
                    st.bar_chart(df, height=220)
                else:
                    st.caption("No scheme matches logged yet.")
                st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("ℹ️ How the pipeline works"):
                st.markdown(
                    """
                    **An Intake Manager conversation loop runs in front of five agents, which then
                    run sequentially via CrewAI:**

                    0. **Intake Manager** — asks for name, location, and situation turn by turn,
                       extracting fields from however the caller answers (even out of order)
                    1. **Listener** — normalizes the completed intake into a structured summary
                    2. **Classifier** — tags the case as health / finance / both, and sets urgency
                    3. **Knowledge Matcher** — checks the case against a database of government schemes
                    4. **NGO Coordinator** — picks the right local NGO and drafts an escalation message
                    5. **Follow-up Coordinator** — generates a check-in message and a follow-up schedule

                    **What's real vs. simulated:** the intake conversation, the 5-agent reasoning,
                    and the spoken summary are all live LLM calls. Phone telephony (browser mic
                    stands in for a real call; production would connect via Twilio) and the NGO
                    directory (illustrative, fictional for the Kharagpur district demo) are
                    simulated for this prototype.
                    """
                )

        elif active_view == "NGOs":
            st.markdown(
                f'<div class="sahayak-serif" style="font-size:1.4rem; font-weight:700; color:{FOREST};">NGO Directory</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"{len(ngos)} NGOs - illustrative directory for the Kharagpur district demo.")
            st.dataframe(
                [
                    {
                        "Name": n["name"],
                        "Area": n["area"],
                        "Focus": ", ".join(n["focus"]),
                        "Times Engaged": stats["ngo_counts"].get(n["name"], 0),
                        "Phone": n["phone"],
                    }
                    for n in ngos
                ],
                use_container_width=True,
                hide_index=True,
            )

        elif active_view == "Schemes":
            st.markdown(
                f'<div class="sahayak-serif" style="font-size:1.4rem; font-weight:700; color:{FOREST};">Scheme Catalog</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"{len(schemes)} government schemes - real central + West Bengal state schemes.")
            st.dataframe(
                [
                    {
                        "Name": s["name"],
                        "Category": s["category"].title(),
                        "Eligibility": "; ".join(s["eligibility"][:2]),
                        "Times Matched": stats["scheme_counts"].get(s["name"], 0),
                    }
                    for s in schemes
                ],
                use_container_width=True,
                hide_index=True,
            )

        elif active_view == "Settings":
            st.markdown(
                f'<div class="sahayak-serif" style="font-size:1.4rem; font-weight:700; color:{FOREST};">Configuration</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Actual configured values from config/settings.py and the environment - "
                "read-only, since there's no settings backend to persist edits yet."
            )
            cfg_col1, cfg_col2 = st.columns(2)
            with cfg_col1:
                voice_rows = [
                    ("Whisper STT model", cfg.GROQ_WHISPER_MODEL),
                    ("English TTS", f"{cfg.GROQ_TTS_MODEL} ({cfg.GROQ_TTS_VOICE})"),
                    (
                        "Hindi TTS",
                        f"Sarvam {cfg.SARVAM_TTS_MODEL} ({cfg.SARVAM_TTS_SPEAKER})"
                        if cfg.SARVAM_API_KEY
                        else "gTTS fallback (no Sarvam key set)",
                    ),
                ]
                rows_html = "".join(f'<div class="config-row"><span>{esc(k)}</span><span>{esc(v)}</span></div>' for k, v in voice_rows)
                st.markdown(f'<div class="dash-chart-card"><div class="dash-chart-title">Voice</div>{rows_html}</div>', unsafe_allow_html=True)
            with cfg_col2:
                system_rows = [
                    ("LLM model", cfg.OPENROUTER_MODEL),
                    ("Max requests/min", str(cfg.MAX_RPM)),
                    ("Schemes loaded", str(len(schemes))),
                    ("NGOs loaded", str(len(ngos))),
                ]
                rows_html = "".join(f'<div class="config-row"><span>{esc(k)}</span><span>{esc(v)}</span></div>' for k, v in system_rows)
                st.markdown(f'<div class="dash-chart-card"><div class="dash-chart-title">System</div>{rows_html}</div>', unsafe_allow_html=True)
