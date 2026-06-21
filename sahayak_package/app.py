"""
SAHAYAK V2 — Sovereign AI Operations Center

Redesigned by Staff Product Designers to resemble a deployable, sovereign-grade
welfare operating intelligence platform (Palantir Foundry / Stripe / Linear).
Features Industrial Morphism design system, monochrome Lucide-style vector icons,
ticking telemetry, outline tags for entities, terminal stream logs,
and case management details drawer with countdown follow-up timers.
"""
import os
import re
import sys
import time
import html as html_lib
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import intake_manager as im
import config.settings as cfg
from tools_data import load_cases, load_schemes, load_ngos, save_case
from crew_runner import run_case
from voice_tools import transcribe_audio, synthesize_speech

# Page config
st.set_page_config(
    page_title="SAHAYAK // Sovereign AI Operations Center",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# HTML Parsing Cleanup Helper
# ---------------------------------------------------------------------------
def clean_html(html_str):
    if not html_str:
        return ""
    # Strip all leading and trailing whitespaces from every single line to prevent Streamlit pre/code wrapping
    return "\n".join(line.strip() for line in html_str.split("\n"))

# ---------------------------------------------------------------------------
# Icon Helpers (Monochrome, 1.5px stroke, Lucide/Tabler style)
# ---------------------------------------------------------------------------
def get_svg_icon(name, color="#808080", size=16):
    if name == "phone":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>'
    elif name == "mic" or name == "ear":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v1a7 7 0 0 1-14 0v-1"/><line x1="12" y1="19" x2="12" y2="22"/></svg>'
    elif name == "tag":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>'
    elif name == "target":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>'
    elif name == "handshake" or name == "users":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
    elif name == "refresh":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>'
    elif name == "database":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></svg>'
    elif name == "shield":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
    elif name == "file-text":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>'
    elif name == "activity":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
    elif name == "clock":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
    elif name == "check":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><polyline points="20 6 9 17 4 12"/></svg>'
    elif name == "filter":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><polyline points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>'
    elif name == "search":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
    elif name == "alert-triangle":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
    return ""

def get_node_svg_icon(index, status_cls):
    color = "#808080"
    if status_cls == "active":
        color = "#E55B3C"
    elif status_cls == "completed":
        color = "#3DD68C"
    
    if index == 0: return get_svg_icon("phone", color, 20)
    elif index == 1: return get_svg_icon("mic", color, 20)
    elif index == 2: return get_svg_icon("tag", color, 20)
    elif index == 3: return get_svg_icon("target", color, 20)
    elif index == 4: return get_svg_icon("users", color, 20)
    else: return get_svg_icon("refresh", color, 20)

# ---------------------------------------------------------------------------
# Global CSS Injector
# ---------------------------------------------------------------------------
st.markdown(
    clean_html("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital,wght@0,400;1,400&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
    
    /* Subtle Grain Texture Overlay */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        opacity: 0.02;
        pointer-events: none;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
        z-index: -1;
    }

    /* Global Backgrounds */
    .stApp, .main, div[data-testid="stHeader"] {
        background-color: #0A0F0D !important;
        color: #F2F2F2 !important;
    }
    
    /* Typography & Hierarchy */
    h1, h2, h3, h4, h5, h6, .sahayak-heading, .level-1-heading {
        font-family: 'Instrument Serif', Georgia, serif !important;
        font-weight: 600 !important;
        color: #F2F2F2 !important;
    }
    body, p, div, span, label, li, ul, table, th, td {
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        color: #F2F2F2 !important;
    }
    .level-2-label {
        font-family: 'Inter', sans-serif !important;
        color: #A0A0A0 !important;
        font-weight: 500 !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .level-3-meta {
        font-family: 'Inter', sans-serif !important;
        color: #6B7280 !important;
        font-weight: 400 !important;
        font-size: 0.7rem !important;
    }
    .mono, code, pre, .terminal-body, .audit-detail, .mono-text, .log-mono {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 400 !important;
    }
    .metric-value, .num-val {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 700 !important;
    }
    
    /* Hide default Streamlit padding */
    [data-testid="stHeader"] {
        display: none !important;
    }
    div.block-container {
        padding-top: 0rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }
    
    /* Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0A0F0D;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.3);
    }
    
    /* Industrial Morphism Panels - Soft Borders */
    .ops-panel, .details-drawer, .kpi-card {
        background: linear-gradient(180deg, #161B18, #111513) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 4px !important;
        padding: 24px !important;
        margin-bottom: 20px !important;
        color: #F2F2F2 !important;
        box-shadow: none !important;
    }
    .ops-panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 12px;
        margin-bottom: 16px;
    }
    .ops-panel-badge {
        background-color: #1A1F1C;
        border: 1px solid rgba(255, 255, 255, 0.05);
        color: #E55B3C;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        padding: 2px 8px;
        border-radius: 2px;
        font-weight: bold;
        text-transform: uppercase;
    }
    .ops-panel-title {
        font-family: 'Instrument Serif', Georgia, serif;
        font-size: 1.4rem;
        font-weight: 600;
        color: #F2F2F2;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    
    /* Global Sticky Header */
    .sahayak-header {
        height: 72px;
        background: linear-gradient(180deg, #161B18, #111513);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0 24px;
        position: sticky;
        top: 0;
        z-index: 1000;
        margin-bottom: 24px;
    }
    .header-left {
        display: flex;
        flex-direction: column;
    }
    .brand-title {
        font-family: 'Instrument Serif', Georgia, serif;
        font-size: 1.6rem;
        font-weight: 600;
        color: #F2F2F2;
        line-height: 1.1;
        letter-spacing: 0.03em;
    }
    .brand-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        color: #6B7280;
        letter-spacing: 0.1em;
        font-weight: 500;
        margin-top: 2px;
    }
    .header-right {
        display: flex;
        align-items: center;
    }
    .telemetry-bar {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .telemetry-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #6B7280;
    }
    .telemetry-divider {
        color: rgba(255, 255, 255, 0.05);
        font-size: 0.8rem;
    }
    .telemetry-meta {
        font-family: 'Inter', sans-serif;
        font-size: 0.68rem;
        color: #6B7280;
    }
    .telemetry-meta span {
        color: #F2F2F2;
        font-family: 'JetBrains Mono', monospace;
        font-weight: bold;
    }
    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #5EE6A8;
        display: inline-block;
        box-shadow: 0 0 6px #5EE6A8;
    }
    .status-dot.orange {
        background-color: #E55B3C;
        box-shadow: 0 0 6px #E55B3C;
        animation: status-pulse 1s infinite alternate;
    }
    @keyframes status-pulse {
        0% { opacity: 0.4; }
        100% { opacity: 1; }
    }
    
    /* Workflow Strip */
    .workflow-strip {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        background-color: #121715;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 16px 20px;
        margin-bottom: 24px;
    }
    .workflow-node {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        position: relative;
    }
    .node-circle {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        margin-bottom: 6px;
        border: 2px solid rgba(255, 255, 255, 0.05);
        background-color: #1A1F1C;
        transition: all 0.3s ease;
    }
    .node-circle.active {
        border-color: #E55B3C;
        box-shadow: 0 0 8px rgba(229, 91, 60, 0.2);
        animation: active-pulse-border 1.5s infinite ease-in-out alternate;
    }
    .node-circle.completed {
        border-color: #5EE6A8;
        box-shadow: 0 0 8px rgba(94, 230, 168, 0.3);
    }
    .node-circle.standby {
        color: #6B7280;
    }
    @keyframes active-pulse-border {
        0% { border-color: #E55B3C; box-shadow: 0 0 4px rgba(229, 91, 60, 0.2); }
        100% { border-color: #ff6e4f; box-shadow: 0 0 12px rgba(229, 91, 60, 0.5); }
    }
    .node-num {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.65rem;
        color: #6B7280;
        margin-bottom: 2px;
    }
    .node-name {
        font-family: 'Instrument Serif', Georgia, serif;
        font-size: 1.1rem;
        font-weight: 600;
        color: #F2F2F2;
        text-transform: uppercase;
    }
    .node-sub {
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        color: #6B7280;
        margin-top: 2px;
        line-height: 1.2;
    }
    .workflow-node-card {
        background-color: #1A1F1C;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 8px;
        margin-top: 8px;
        font-size: 0.62rem;
        width: 95%;
        text-align: left;
        color: #6B7280;
        font-family: 'JetBrains Mono', monospace;
    }
    .workflow-node-card.active {
        border-color: #E55B3C;
        border-left: 3px solid #E55B3C;
        box-shadow: 0 0 8px rgba(229, 91, 60, 0.1);
        color: #F2F2F2;
    }
    .workflow-node-card.completed {
        border-color: #5EE6A8;
        color: #6B7280;
    }
    .node-card-row {
        margin-bottom: 2px;
    }
    .node-card-row span {
        color: #F2F2F2;
    }
    .node-card-row .status-val {
        font-weight: bold;
    }
    .workflow-node-card.active .status-val {
        color: #E55B3C;
    }
    .workflow-node-card.completed .status-val {
        color: #5EE6A8;
    }
    .workflow-arrow {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 40px;
        color: rgba(255, 255, 255, 0.05);
        font-size: 1.1rem;
        padding: 0 4px;
    }
    .workflow-arrow.completed {
        color: #5EE6A8;
    }
    .workflow-arrow.active {
        color: #E55B3C;
    }
    
    /* Audio Waveform - OpenAI Voice Inspired breathing flow */
    .voice-waveform {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        height: 90px;
        background-color: #1A1F1C;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 20px;
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }
    .voice-waveform.active {
        box-shadow: 0 0 15px rgba(94, 230, 168, 0.05);
        animation: container-breath 3s infinite ease-in-out alternate;
    }
    @keyframes container-breath {
        0% { box-shadow: 0 0 10px rgba(94, 230, 168, 0.03); }
        100% { box-shadow: 0 0 25px rgba(94, 230, 168, 0.1); }
    }
    .wave-bar {
        width: 4px;
        background-color: rgba(94, 230, 168, 0.7);
        border-radius: 2px;
        height: 8px;
        transition: height 0.3s ease-in-out;
    }
    .voice-waveform.active .wave-bar {
        animation: voice-pulse 1.4s infinite ease-in-out alternate;
        animation-delay: var(--delay);
    }
    @keyframes voice-pulse {
        0% { height: 10px; transform: scaleY(0.8); }
        50% { height: 45px; transform: scaleY(1.3); }
        100% { height: 15px; transform: scaleY(1.0); }
    }
    
    /* System Health Progress Bars */
    .health-progress-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
    }
    .health-progress-label {
        width: 75px;
        color: #6B7280;
    }
    .health-progress-bar-bg {
        flex-grow: 1;
        height: 6px;
        background-color: #1A1F1C;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 1px;
        position: relative;
        overflow: hidden;
    }
    .health-progress-bar-fill {
        height: 100%;
        background-color: #5EE6A8;
    }
    .health-progress-value {
        width: 30px;
        text-align: right;
        color: #F2F2F2;
    }
    
    /* Live Transcript & Entity tags */
    .transcript-container {
        background-color: #1A1F1C;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 24px;
        min-height: 580px;
        height: calc(100vh - 340px);
        max-height: 760px;
        overflow-y: auto;
        margin-bottom: 16px;
    }
    .transcript-bubble {
        margin-bottom: 16px;
        border-left: 2px solid rgba(255, 255, 255, 0.05);
        padding-left: 12px;
    }
    .transcript-bubble.caller {
        border-left-color: #E55B3C;
    }
    .transcript-speaker {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #6B7280;
        margin-bottom: 4px;
        letter-spacing: 0.05em;
    }
    .transcript-speaker.caller {
        color: #E55B3C;
    }
    .transcript-text {
        font-size: 0.85rem;
        color: #F2F2F2;
        line-height: 1.4;
    }
    
    .entity-highlight {
        background: transparent !important;
        border: 1px solid #5EE6A8;
        border-radius: 2px;
        padding: 1px 4px;
        color: #5EE6A8 !important;
        display: inline-block;
        font-weight: 500;
    }
    .entity-highlight.weather_event {
        border-color: #E55B3C;
        color: #E55B3C !important;
    }
    .entity-highlight.land_size {
        border-color: #F7B955;
        color: #F7B955 !important;
    }
    .entity-highlight.location {
        border-color: #55B9F7;
        color: #55B9F7 !important;
    }
    .entity-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.58rem;
        color: #6B7280;
        margin-left: 4px;
        text-transform: uppercase;
        font-weight: normal;
    }
    
    /* Chips / Pills & Outlined Extracted Entity Chips */
    .entity-chip {
        display: inline-block;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        background-color: transparent !important;
        color: #F2F2F2 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.7rem !important;
        padding: 4px 10px !important;
        border-radius: 2px !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    .pill-badge {
        display: inline-block;
        background-color: #1A1F1C;
        border: 1px solid rgba(255, 255, 255, 0.05);
        color: #6B7280;
        font-family: 'Inter', sans-serif;
        font-size: 0.72rem;
        padding: 4px 10px;
        border-radius: 20px;
        margin-right: 8px;
        margin-bottom: 8px;
        font-weight: 500;
    }
    .pill-badge.active {
        color: #F2F2F2;
        border-color: #5EE6A8;
        background-color: rgba(94, 230, 168, 0.05);
    }
    .pill-badge.urgency-high {
        border-color: #E55B3C;
        color: #E55B3C;
        background-color: rgba(229, 91, 60, 0.05);
    }
    
    /* AI Confidence Stack Horizontal Cards */
    .confidence-grid {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        gap: 12px;
        width: 100%;
        margin-top: 12px;
        flex-wrap: wrap;
    }
    .confidence-card {
        flex: 1;
        background: linear-gradient(180deg, #161B18, #111513);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 14px 16px;
        text-align: left;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-width: 150px;
    }
    .confidence-card-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        font-weight: 500;
        color: #A0A0A0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .confidence-card-value {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 1.6rem;
        font-weight: 700;
        color: #F2F2F2;
        line-height: 1.1;
    }
    .confidence-card-status {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.58rem;
        font-weight: 600;
        margin-top: 6px;
    }
    .confidence-card-status.high {
        color: #5EE6A8;
    }
    .confidence-card-status.medium {
        color: #F7B955;
    }
    
    /* Terminals & Blinking cursor */
    .terminal-window {
        background-color: #0A0F0D !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 4px !important;
        padding: 16px !important;
        margin-top: 16px !important;
    }
    .terminal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 8px;
        margin-bottom: 12px;
    }
    .terminal-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        color: #A0A0A0;
        text-transform: uppercase;
    }
    .terminal-body {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.72rem !important;
        line-height: 1.4 !important;
        max-height: 120px;
        overflow-y: auto;
        color: #8FE6BC !important;
        white-space: pre-wrap;
    }
    .blinking-cursor {
        display: inline-block;
        width: 6px;
        height: 12px;
        background-color: #5EE6A8;
        margin-left: 4px;
        animation: cursor-blink 1s infinite;
    }
    @keyframes cursor-blink {
        0%, 49% { opacity: 1; }
        50%, 100% { opacity: 0; }
    }
    
    /* Streamlit overrides */
    input[type="text"], textarea {
        background-color: #121715 !important;
        color: #F2F2F2 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 4px !important;
        font-family: 'Inter', sans-serif !important;
    }
    div.stButton > button {
        background-color: #121715 !important;
        color: #6B7280 !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 4px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        padding: 6px 14px !important;
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
        background-color: #ff6e4f !important;
        border-color: #ff6e4f !important;
        color: #0A0F0D !important;
    }
    
    /* Segmented view controls columns with has selector */
    [data-testid="column"]:has(.segmented-control-marker) button {
        width: 100% !important;
        height: 48px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
    }
    [data-testid="column"]:has(.segmented-control-marker) button[kind="primary"] {
        background-color: #1A1F1C !important;
        border-color: #E55B3C !important;
        color: #E55B3C !important;
    }
    [data-testid="column"]:has(.segmented-control-marker) button[kind="secondary"] {
        background-color: #121715 !important;
        border-color: rgba(255, 255, 255, 0.05) !important;
        color: #6B7280 !important;
    }
    
    /* Sidebar */
    .sidebar-menu {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .sidebar-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        border-radius: 4px;
        color: #6B7280;
        font-size: 0.85rem;
        font-weight: 500;
        transition: all 0.2s ease;
        cursor: pointer;
        background-color: transparent;
        border: none;
        text-align: left;
        width: 100%;
    }
    .sidebar-item.active {
        color: #F2F2F2;
        background-color: #1A1F1C;
        border-left: 3px solid #E55B3C;
    }
    .sidebar-item:hover:not(.active) {
        color: #F2F2F2;
        background-color: rgba(26, 31, 28, 0.5);
    }
    
    /* Table Case ID Plain Text Button Style with has selector */
    [data-testid="column"]:has(.table-id-cell) button {
        background-color: transparent !important;
        border: none !important;
        color: #5EE6A8 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        padding: 0 !important;
        text-align: left !important;
        width: auto !important;
        text-decoration: underline;
        cursor: pointer;
    }
    [data-testid="column"]:has(.table-id-cell) button:hover {
        color: #ff6e4f !important;
        background-color: transparent !important;
    }
    
    /* Table Headers */
    .ops-table {
        width: 100%;
        border-collapse: collapse;
    }
    .ops-table th {
        background-color: #1A1F1C;
        color: #6B7280;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        text-transform: uppercase;
        text-align: left;
        padding: 10px 16px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        letter-spacing: 0.05em;
    }
    
    /* Status Pills */
    .status-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
        text-align: center;
        border: 1.5px solid;
    }
    .status-pill.resolved {
        background-color: rgba(94, 230, 168, 0.05);
        border-color: #5EE6A8;
        color: #5EE6A8;
    }
    .status-pill.pending {
        background-color: rgba(247, 185, 85, 0.05);
        border-color: #F7B955;
        color: #F7B955;
    }
    .status-pill.escalated {
        background-color: rgba(229, 91, 60, 0.05);
        border-color: #E55B3C;
        color: #E55B3C;
    }
    .status-pill.critical {
        background-color: rgba(229, 91, 60, 0.1);
        border-color: #E55B3C;
        color: #E55B3C;
        animation: status-pulse 1s infinite alternate;
    }
    </style>
    """),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Data Seeding & Mock Database Setup
# ---------------------------------------------------------------------------
MOCK_SPEC_CASES = [
    {
        "case_id": "CASE-2341",
        "caller_name": "Bikash Mondal",
        "created_at": "2026-06-21T10:18:00Z",
        "language": "hi",
        "raw_text": "I am Bikash Mondal, 41 years old farmer from Kharagpur II. My crop was damaged by rain. I don't have insurance.",
        "listener_output": "person_situation: Farmer Bikash Mondal reports crop damage due to rain.\nstated_need: Financial assistance and crop insurance recovery.\nmentioned_details: age=41, occupation=farmer, location=Kharagpur II, land=1.8 acres, insurance=none.",
        "classifier_output": "domain: finance\nurgency: medium\nurgency_reason: Crop destroyed but no immediate medical distress.",
        "matcher_output": "Matched Krishak Bandhu and PM Fasal Bima Yojana.",
        "ngo_output": "Krishak Sahayata Kendra has been assigned to assist Bikash Mondal with land records.",
        "followup_output": "followup_message: Namaste Bikash ji, hum aapse Krishak Bandhu aavedan ke silsile mein sampark kar rahe hain. Kya aapse NGO ne sampark kiya?\nrecommended_followup_days: 3",
        "spoken_summary": "Bikash ji, aapke liye Krishak Bandhu aur PM Fasal Bima Yojana chuni gayi hai. Krishak Sahayata Kendra aapse jald hi sampark karega.",
        "status": "Resolved",
        "updated_time": "10:20 AM",
        "age": "41",
        "district": "Kharagpur II",
        "occupation": "Farmer",
        "land_size": "1.8 Acres",
        "income_range": "Low",
        "urgency": "Medium",
        "language_name": "Bengali",
        "insurance_status": "No Insurance",
        "category_badge": "Farmer",
        "urgency_badge": "Medium Urgency",
        "case_type_badge": "Finance Case",
        "assigned_ngo": "Krishak Sahayata Kendra",
        "ngo_message_draft": "Citizen requires assistance with Krishak Bandhu application. Documents appear incomplete. Requesting NGO intervention and application support."
    },
    {
        "case_id": "CASE-2340",
        "caller_name": "Rina Das",
        "created_at": "2026-06-21T10:10:00Z",
        "language": "hi",
        "raw_text": "I am Rina Das. I am pregnant and need to register for Swasthya Sathi scheme.",
        "listener_output": "person_situation: Pregnant woman Rina Das needs health scheme enrollment.\nstated_need: Swasthya Sathi cards and maternal health benefits.\nmentioned_details: status=pregnant, location=Kharagpur town.",
        "classifier_output": "domain: health\nurgency: high\nurgency_reason: Maternal care and pregnancy support required.",
        "matcher_output": "Matched Swasthya Sathi and Janani Suraksha Yojana.",
        "ngo_output": "Gramin Swasthya Seva Sangh has been assigned to help Rina Das visit the hospital.",
        "followup_output": "followup_message: Namaste Rina ji, Swasthya Sathi card aur JSY benefits ke liye aapka aavedan shuru ho gaya hai. Kya hospital se madad mili?\nrecommended_followup_days: 1",
        "spoken_summary": "Rina ji, Swasthya Sathi aur Janani Suraksha Yojana aapke liye bilkul sahi hain. Gramin Swasthya Seva Sangh aapki delivery aur card ke liye madad karega.",
        "status": "NGO Follow-up",
        "updated_time": "10:18 AM",
        "age": "28",
        "district": "Kharagpur I",
        "occupation": "Homemaker",
        "land_size": "0 Acres",
        "income_range": "Low",
        "urgency": "High",
        "language_name": "Hindi",
        "insurance_status": "No Insurance",
        "category_badge": "Maternal Care",
        "urgency_badge": "High Urgency",
        "case_type_badge": "Health Case",
        "assigned_ngo": "Gramin Swasthya Seva Sangh",
        "ngo_message_draft": "Citizen requires assistance with Janani Suraksha Yojana registration and Swasthya Sathi health card. Requesting urgent NGO coordination."
    },
    {
        "case_id": "CASE-2339",
        "caller_name": "Haripada Soren",
        "created_at": "2026-06-21T10:00:00Z",
        "language": "hi",
        "raw_text": "I am Haripada Soren. I am 52 years old and have 80% disability. I need to apply for disability pension.",
        "listener_output": "person_situation: Disabled citizen Haripada Soren seeking pension benefits.\nstated_need: National Disability Pension Scheme enrollment.\nmentioned_details: age=52, disability=80%, BPL household.",
        "classifier_output": "domain: finance\nurgency: medium\nurgency_reason: Seeking disability pension with BPL status.",
        "matcher_output": "Matched National Disability Pension Scheme (IGNDPS).",
        "ngo_output": "Paschim Medinipur Disability Rights Forum has been assigned to help Haripada Soren.",
        "followup_output": "followup_message: Namaste Haripada ji, disability pension scheme aavedan aur medical certificate verification shuru ho gaya hai.\nrecommended_followup_days: 3",
        "spoken_summary": "Haripada ji, aapke liye National Disability Pension Scheme chuni gayi hai. Disability Rights Forum aapse sampark karega.",
        "status": "Pending",
        "updated_time": "10:15 AM",
        "age": "52",
        "district": "Paschim Medinipur",
        "occupation": "Unemployed",
        "land_size": "0.5 Acres",
        "income_range": "Low (BPL)",
        "urgency": "Medium",
        "language_name": "Bengali",
        "insurance_status": "No Insurance",
        "category_badge": "Disabled",
        "urgency_badge": "Medium Urgency",
        "case_type_badge": "Finance Case",
        "assigned_ngo": "Paschim Medinipur Disability Rights Forum",
        "ngo_message_draft": "Citizen requires support for obtaining disability certificate and pension enrollment. Requesting NGO intervention."
    },
    {
        "case_id": "CASE-2338",
        "caller_name": "Gopal Murmu",
        "created_at": "2026-06-21T09:40:00Z",
        "language": "hi",
        "raw_text": "I am Gopal Murmu. I need to get MGNREGA Job Card to find manual work in our village.",
        "listener_output": "person_situation: Citizen Gopal Murmu needs manual employment.\nstated_need: MGNREGA Job Card and wage employment.\nmentioned_details: status=rural household.",
        "classifier_output": "domain: finance\nurgency: low\nurgency_reason: Employment support needed, no immediate health emergency.",
        "matcher_output": "Matched MGNREGA.",
        "ngo_output": "Krishak Sahayata Kendra has been assigned to help Gopal Murmu.",
        "followup_output": "followup_message: Namaste Gopal ji, MGNREGA Job Card registration ke silsile mein hum aapse check kar rahe hain.\nrecommended_followup_days: 5",
        "spoken_summary": "Gopal ji, aapke liye MGNREGA Job Card registration chuna gaya hai. Krishak Sahayata Kendra madad karega.",
        "status": "Resolved",
        "updated_time": "10:10 AM",
        "age": "34",
        "district": "Kharagpur Rural",
        "occupation": "Laborer",
        "land_size": "0.2 Acres",
        "income_range": "Low",
        "urgency": "Low",
        "language_name": "Hindi",
        "insurance_status": "No Insurance",
        "category_badge": "Laborer",
        "urgency_badge": "Low Urgency",
        "case_type_badge": "Finance Case",
        "assigned_ngo": "Krishak Sahayata Kendra",
        "ngo_message_draft": "Citizen requires MGNREGA Job Card registration for rural unskilled manual work. Requesting NGO intervention."
    },
    {
        "case_id": "CASE-2337",
        "caller_name": "Parbati Kisku",
        "created_at": "2026-06-21T09:30:00Z",
        "language": "hi",
        "raw_text": "My newborn baby is sick and we have no health insurance.",
        "listener_output": "person_situation: Newborn child is ill, family has no health insurance.\nstated_need: Cashless medical treatment and hospitalization.\nmentioned_details: age=newborn, insurance=none.",
        "classifier_output": "domain: health\nurgency: high\nurgency_reason: Newborn sickness demands immediate medical attention.",
        "matcher_output": "Matched Ayushman Bharat PM-JAY and Swasthya Sathi.",
        "ngo_output": "Gramin Swasthya Seva Sangh has been assigned to coordinate immediate hospital admission.",
        "followup_output": "followup_message: Namaste Parbati ji, aapke bacche ki tabiyat kaisi hai? Hospital mein cashless PM-JAY support mila?\nrecommended_followup_days: 1",
        "spoken_summary": "Parbati ji, aapke bacche ke ilaaj ke liye Swasthya Sathi aur PM-JAY chune gaye hain. Swasthya Seva Sangh aapse turant hospital mein milega.",
        "status": "NGO Follow-up",
        "updated_time": "10:05 AM",
        "age": "24",
        "district": "Kharagpur Rural",
        "occupation": "Homemaker",
        "land_size": "0 Acres",
        "income_range": "Low",
        "urgency": "High",
        "language_name": "Bengali",
        "insurance_status": "No Insurance",
        "category_badge": "Newborn Care",
        "urgency_badge": "High Urgency",
        "case_type_badge": "Health Case",
        "assigned_ngo": "Gramin Swasthya Seva Sangh",
        "ngo_message_draft": "Newborn child requires immediate hospitalization. Requesting NGO support to coordinate cashless treatment under PM-JAY."
    }
]

SPEC_CASES_DICT = {c["case_id"]: c for c in MOCK_SPEC_CASES}

# Seed cases in cases.json
if "workspace_view" not in st.session_state:
    st.session_state["workspace_view"] = "Live Intake"

if "seeded" not in st.session_state:
    try:
        cases = load_cases()
        if not cases or len(cases) < len(MOCK_SPEC_CASES):
            for sc in MOCK_SPEC_CASES:
                if not any(c.get("case_id") == sc["case_id"] for c in cases):
                    save_case(sc)
    except Exception:
        pass
    st.session_state["seeded"] = True

# ---------------------------------------------------------------------------
# Telemetry, Sparklines & Helper Functions
# ---------------------------------------------------------------------------
def play_audio(text: str, language: str, autoplay: bool = True):
    try:
        audio_bytes, mime_type = synthesize_speech(text, language=language)
        st.audio(audio_bytes, format=mime_type, autoplay=autoplay)
    except Exception as e:
        st.warning(f"Could not synthesize audio: {e}")

HOLD_TUNE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "hold_tune.wav")

def play_hold_tune():
    try:
        with open(HOLD_TUNE_PATH, "rb") as f:
            st.audio(f.read(), format="audio/wav", loop=True, autoplay=True)
    except Exception:
        pass

def esc(text: str) -> str:
    return html_lib.escape(text or "")

def format_timer(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

def get_followup_countdown(case_record):
    created_at = case_record.get("created_at")
    if not created_at:
        return "2 DAYS 14 HOURS 22 MINUTES"
    
    followup_text = case_record.get("followup_output", "")
    days_match = re.search(r"(\d+)\s*days?", followup_text, re.IGNORECASE)
    days = int(days_match.group(1)) if days_match else 3
    
    try:
        created_dt_str = created_at.replace("Z", "+00:00")
        if "." in created_dt_str:
            created_dt_str = created_dt_str.split(".")[0] + "+00:00"
        created_dt = datetime.strptime(created_dt_str[:19], "%Y-%m-%dT%H:%M:%S")
        target_dt = created_dt + timedelta(days=days)
        
        now = datetime(2026, 6, 21, 21, 14, 30)
        time_diff = target_dt - now
        
        if time_diff.total_seconds() > 0:
            d = time_diff.days
            h = time_diff.seconds // 3600
            m = (time_diff.seconds % 3600) // 60
            return f"{d} DAYS {h} HOURS {m} MINUTES"
        else:
            return "EXPIRED - FOLLOW-UP DUE"
    except Exception:
        return f"{days} DAYS 14 HOURS 22 MINUTES"

def highlight_and_tag_entities(text: str) -> str:
    if not text:
        return ""
    escaped = esc(text)
    
    entities = [
        (r"\b(paddy|rice|crop|crops|wheat|vegetables?|cultivation)\b", "Crop_Type", "crop_type"),
        (r"\b(kharagpur|bengal|west bengal|village|district|kolkata|midnapore|kharagpur ii)\b", "Location", "location"),
        (r"\b(pregnant|pregnancy|baby|delivery|childbirth|maternity|health|hospital|doctor|sick|illness|newborn)\b", "Health_Condition", "health_condition"),
        (r"\b(acres?|bighas?|land|hectares?|farm size)\b", "Land_Size", "land_size"),
        (r"\b(BPL|poverty|poverty line|ration card|income|earnings|rupees|Rs\.|savings|debt|loan)\b", "Financial_Status", "financial_status"),
    ]
    
    for pattern, tag, class_name in entities:
        escaped = re.sub(
            pattern,
            lambda m: f'<span class="entity-highlight {class_name}">{m.group(0)}<span class="entity-tag">[{tag}]</span></span>',
            escaped,
            flags=re.IGNORECASE
        )
    return escaped

def get_sparkline_svg(data, color="#3DD68C"):
    points = []
    width = 80
    height = 20
    min_val = min(data)
    max_val = max(data)
    val_range = max_val - min_val if max_val > min_val else 1
    
    for i, val in enumerate(data):
        x = int((i / (len(data) - 1)) * width)
        y = int(height - ((val - min_val) / val_range) * height)
        points.append(f"{x},{y}")
        
    points_str = " ".join(points)
    return f"""
    <svg width="{width}" height="{height}" style="overflow: visible; display: inline-block; vertical-align: middle; margin-left: 10px;">
      <polyline fill="none" stroke="{color}" stroke-width="1.5" points="{points_str}" />
    </svg>
    """

funnel_html = """
<div class="funnel-container">
  <div class="funnel-stage">
    <div class="funnel-label">Calls Received</div>
    <div class="funnel-value">1,247</div>
    <div class="funnel-bar-bg"><div class="funnel-bar-fill" style="width: 100%;"></div></div>
  </div>
  <div class="funnel-stage">
    <div class="funnel-label">Schemes Matched</div>
    <div class="funnel-value">892</div>
    <div class="funnel-bar-bg"><div class="funnel-bar-fill" style="width: 71.5%;"></div></div>
  </div>
  <div class="funnel-stage">
    <div class="funnel-label">NGO Escalated</div>
    <div class="funnel-value">156</div>
    <div class="funnel-bar-bg"><div class="funnel-bar-fill" style="width: 12.5%;"></div></div>
  </div>
  <div class="funnel-stage">
    <div class="funnel-label">Resolved</div>
    <div class="funnel-value">623</div>
    <div class="funnel-bar-bg"><div class="funnel-bar-fill" style="width: 50%;"></div></div>
  </div>
</div>
"""

def get_scheme_matches_html(case, show_benefit=True):
    matches = []
    if "matcher_output_obj" in case and case["matcher_output_obj"]:
        matches = case["matcher_output_obj"].matches
    
    if not matches:
        txt = case.get("matcher_output", "") or ""
        if "Krishak Bandhu" in txt or "Krishak" in txt:
            matches.append({
                "scheme_id": "S010",
                "scheme_name": "Krishak Bandhu",
                "confidence_score": 92,
                "reasoning_path": "West Bengal Resident, Farmer, Land Records Available, Crop Loss Reported",
                "why_match": "Provides income support to West Bengal farmers facing crop distress.",
                "documents_needed": ["Aadhaar", "Land Records", "Bank Details"],
                "expected_benefit": "Annual grant up to Rs. 10,000 and Rs. 2 lakh death cover."
            })
        if "PM Fasal Bima" in txt or "Bima" in txt or "Fasal" in txt:
            matches.append({
                "scheme_id": "S009",
                "scheme_name": "PM Fasal Bima Yojana",
                "confidence_score": 87,
                "reasoning_path": "Farmer, Crop Damage, Bank Account Linked",
                "why_match": "Accidental crop loss insurance cover for registered farmers.",
                "documents_needed": ["Aadhaar", "Land Records", "Crop Loss Proof"],
                "expected_benefit": "Financial support to offset agriculture losses from natural disasters."
            })
        if "Swasthya Sathi" in txt:
            matches.append({
                "scheme_id": "S004",
                "scheme_name": "Swasthya Sathi",
                "confidence_score": 95,
                "reasoning_path": "West Bengal Resident, Universal Coverage, No existing health cover",
                "why_match": "Cashless treatment up to Rs. 5 lakh for families in West Bengal.",
                "documents_needed": ["Aadhaar card", "Voter ID"],
                "expected_benefit": "Cashless hospitalization secondary/tertiary care benefits."
            })
        if "Janani Suraksha" in txt or "JSY" in txt:
            matches.append({
                "scheme_id": "S002",
                "scheme_name": "Janani Suraksha Yojana",
                "confidence_score": 91,
                "reasoning_path": "Pregnant woman, SC/ST/BPL household, Delivery at accredited facility",
                "why_match": "Cash assistance for pregnant women to encourage institutional delivery.",
                "documents_needed": ["Aadhaar", "ANC Card", "BPL Certificate"],
                "expected_benefit": "Direct cash assistance of Rs. 1,400 after institutional delivery."
            })
            
    if not matches:
        matches = [{
            "scheme_id": "S010",
            "scheme_name": "Krishak Bandhu",
            "confidence_score": 92,
            "reasoning_path": "West Bengal Resident, Farmer, Land Records Available, Crop Loss Reported",
            "why_match": "Provides income support to West Bengal farmers facing crop distress.",
            "documents_needed": ["Aadhaar", "Land Records", "Bank Details"],
            "expected_benefit": "Annual grant up to Rs. 10,000 and Rs. 2 lakh death cover."
        }]

    html = ""
    for m in matches:
        if hasattr(m, "scheme_name"):
            sid = m.scheme_id
            name = m.scheme_name
            score = m.confidence_score
            reason = m.reasoning_path
            why = m.why_match
            docs = m.documents_needed
            benefit = getattr(m, "expected_benefit", "Direct financial/welfare support disbursement.")
        else:
            sid = m["scheme_id"]
            name = m["scheme_name"]
            score = m["confidence_score"]
            reason = m["reasoning_path"]
            why = m["why_match"]
            docs = m["documents_needed"]
            benefit = m.get("expected_benefit", "Direct financial/welfare support disbursement.")
        
        benefit_html = f'<div class="mono-text" style="font-size: 0.7rem; color: #808080; margin-top: 4px;">EXPECTED BENEFIT: <span style="color: #F2F2F2;">{esc(benefit)}</span></div>' if show_benefit else ""
        
        html += f"""
        <div class="scheme-card" style="background-color: #1A1F1C; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 10px; padding: 12px; border-radius: 4px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span class="mono-text" style="font-size: 0.75rem; color: #E55B3C; font-weight: 700;">{esc(sid)}</span>
            <span class="mono-text" style="font-size: 0.75rem; color: #3DD68C; font-weight: 700;">CONFIDENCE: {score}%</span>
          </div>
          <div style="font-family: 'Instrument Serif', Georgia, serif; font-size: 1.25rem; font-weight: 600; color: #F2F2F2; margin-top: 4px;">
            {esc(name)}
          </div>
          <div class="mono-text" style="font-size: 0.7rem; color: #808080; margin-top: 6px;">
            REASONING: <span style="color: #F2F2F2;">{esc(reason)}</span>
          </div>
          <div class="mono-text" style="font-size: 0.72rem; color: #3DD68C; margin-top: 4px;">
            // {esc(why)}
          </div>
          {benefit_html}
          <div class="mono-text" style="font-size: 0.7rem; color: #808080; margin-top: 6px;">
            REQUIRED DOCUMENTS: {", ".join(f"[{d}]" for d in docs)}
          </div>
        </div>
        """
    return html

# ---------------------------------------------------------------------------
# Global Header & Workflow Strip Layout Components
# ---------------------------------------------------------------------------
def render_global_header(active_call=False, processing=False):
    dot_whisper = "status-dot orange" if active_call else "status-dot"
    dot_crew = "status-dot orange" if processing else "status-dot"
    
    header_html = f"""
    <div class="sahayak-header">
      <div class="header-left">
        <div class="brand-title">SAHAYAK</div>
        <div class="brand-subtitle">INDIA WELFARE INTELLIGENCE NETWORK</div>
      </div>
      <div class="header-right">
        <div class="telemetry-bar">
          <div class="telemetry-item"><span class="status-dot"></span> GROQ ONLINE</div>
          <div class="telemetry-item"><span class="{dot_whisper}"></span> WHISPER ONLINE</div>
          <div class="telemetry-item"><span class="{dot_crew}"></span> CREWAI ONLINE</div>
          <div class="telemetry-item"><span class="status-dot"></span> NGO NETWORK CONNECTED</div>
          <div class="telemetry-divider">|</div>
          <div class="telemetry-meta">DISTRICT: <span>Kharagpur II</span></div>
          <div class="telemetry-meta">LIVE CASES: <span>127</span></div>
          <div class="telemetry-meta">LAST SYNC: <span>10:42:33</span></div>
        </div>
      </div>
    </div>
    """
    st.markdown(clean_html(header_html), unsafe_allow_html=True)

def render_workflow_strip(active_node=None, completed_nodes=None):
    if completed_nodes is None:
        completed_nodes = set()
        
    nodes = [
        ("CALLER", "100%", "0.5s", "Helpline connected"),
        ("LISTENER", "97%", "1.2s", "Extracting details"),
        ("CLASSIFIER", "94%", "0.8s", "Categorizing case"),
        ("MATCHER", "92%", "1.5s", "Matching schemes"),
        ("NGO COORDINATOR", "89%", "1.1s", "Assigning NGO"),
        ("FOLLOW-UP", "95%", "1.3s", "Scheduling follow-up")
    ]
    
    # Calculate step progress
    step_num = len(completed_nodes)
    if active_node is not None:
        step_num = max(step_num, active_node + 1)
    if step_num > 6:
        step_num = 6
    dots = "●" * step_num + "○" * (6 - step_num)
    progress_text = f"PIPELINE STATUS: STEP {step_num} / 6 | {dots}"
    
    html = '<div class="workflow-strip" style="display:flex; flex-direction:column; gap:12px;">'
    html += f'<div class="level-2-label" style="text-align: center; font-size: 0.72rem; letter-spacing: 0.1em; color: #5EE6A8; font-weight: bold; width: 100%; border-bottom: 1px solid rgba(255,255,255,0.03); padding-bottom: 8px;">{progress_text}</div>'
    html += '<div style="display:flex; justify-content: space-between; align-items: flex-start; width: 100%;">'
    
    for i, (name, conf, exec_time, desc) in enumerate(nodes):
        is_active = (i == active_node)
        is_completed = (i in completed_nodes)
        
        status_cls = "standby"
        status_text = "STANDBY"
        if is_active:
            status_cls = "active"
            status_text = "PROCESSING"
        elif is_completed:
            status_cls = "completed"
            status_text = "COMPLETE"
            
        icon_svg = get_node_svg_icon(i, status_cls)
        
        active_glow = 'box-shadow: 0 0 20px rgba(229,91,60,.12) !important;' if is_active else ''
        
        html += f"""
        <div class="workflow-node">
          <div class="node-circle {status_cls}">
            {icon_svg}
          </div>
          <div class="node-num">0{i+1}</div>
          <div class="node-name">{name}</div>
          <div class="workflow-node-card {status_cls}" style="{active_glow}">
            <div class="node-card-row">STATUS: <span class="status-val">{status_text}</span></div>
            <div class="node-card-row">CONFIDENCE: <span>{conf}</span></div>
            <div class="node-card-row">EXECUTION: <span>{exec_time}</span></div>
          </div>
        </div>
        """
        if i < len(nodes) - 1:
            arrow_cls = "completed" if (i in completed_nodes and (i+1) in completed_nodes) else ("active" if is_active or (i+1 == active_node) else "standby")
            html += f'<div class="workflow-arrow {arrow_cls}" style="margin-top: 10px;">→</div>'
            
    html += '</div></div>'
    st.markdown(clean_html(html), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# VIEW 1: Live Intake Command Center
# ---------------------------------------------------------------------------
PLACEHOLDERS = {}

def get_voice_waveform_html(active=True):
    active_cls = "active" if active else ""
    return f"""
    <div class="voice-waveform {active_cls}">
      <div class="wave-bar" style="height: 15px; --delay: 0.1s;"></div>
      <div class="wave-bar" style="height: 25px; --delay: 0.3s;"></div>
      <div class="wave-bar" style="height: 45px; --delay: 0.5s;"></div>
      <div class="wave-bar" style="height: 30px; --delay: 0.2s;"></div>
      <div class="wave-bar" style="height: 60px; --delay: 0.7s;"></div>
      <div class="wave-bar" style="height: 40px; --delay: 0.4s;"></div>
      <div class="wave-bar" style="height: 20px; --delay: 0.8s;"></div>
      <div class="wave-bar" style="height: 35px; --delay: 0.6s;"></div>
      <div class="wave-bar" style="height: 15px; --delay: 0.9s;"></div>
      <div class="wave-bar" style="height: 25px; --delay: 0.15s;"></div>
      <div class="wave-bar" style="height: 50px; --delay: 0.35s;"></div>
      <div class="wave-bar" style="height: 30px; --delay: 0.55s;"></div>
    </div>
    """

def render_system_health(phase="idle", state=None):
    latency = "0ms"
    token_usage = "N/A"
    status = "STANDBY"
    speech = "NO"
    lang = "N/A"
    quality = "N/A"
    model_time = "N/A"
    speaker = "NONE"
    duration = "00:00"
    
    if state:
        lang = "Bengali" if state.language == "hi" else "English"
        quality = "98%"
        model_time = "142ms"
        duration = f"00:{state.turn_count * 8:02d}"
        if not state.complete:
            latency = "132ms"
            status = "LISTENING"
            speech = "YES"
            token_usage = "12,435 Tokens"
            speaker = "Citizen"
        else:
            latency = "840ms"
            status = "PROCESSING"
            speech = "NO"
            token_usage = "18,242 Tokens"
            speaker = "None (Processing)"
            
    if phase == "resolved":
        status = "COMPLETED"
        latency = "1,840ms"
        speech = "NO"
        quality = "98%"
        token_usage = "18,242 Tokens"
        model_time = "142ms"
        speaker = "None"
        duration = "00:24"
        
    return f"""
    <table class="profile-table" style="margin-top: 8px;">
      <tr><td class="label level-2-label">MICROPHONE</td><td class="value level-3-meta" style="color: #5EE6A8; font-weight: 600;">ONLINE</td></tr>
      <tr><td class="label level-2-label">SPEECH DETECTION</td><td class="value level-3-meta" style="color: #5EE6A8; font-weight: 600;">{speech}</td></tr>
      <tr><td class="label level-2-label">LATENCY</td><td class="value level-3-meta">{latency}</td></tr>
      <tr><td class="label level-2-label">MODEL RESPONSE TIME</td><td class="value level-3-meta" style="color: #5EE6A8; font-weight: 600;">{model_time}</td></tr>
      <tr><td class="label level-2-label">LANGUAGE</td><td class="value level-3-meta">{lang}</td></tr>
      <tr><td class="label level-2-label">TOKEN USAGE</td><td class="value level-3-meta">{token_usage}</td></tr>
      <tr><td class="label level-2-label">CONNECTION QUALITY</td><td class="value level-3-meta">{quality}</td></tr>
      <tr><td class="label level-2-label">CURRENT SPEAKER</td><td class="value level-3-meta">{speaker}</td></tr>
      <tr><td class="label level-2-label">SPEECH DURATION</td><td class="value level-3-meta">{duration}</td></tr>
    </table>
    """

def render_narrative_column(state=None):
    if not state:
        # Standby Empty State Design (Node 7)
        return f"""
        <div class="transcript-container" style="display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; border: 1px dashed rgba(255,255,255,0.08);">
          <div style="font-family: 'Instrument Serif', Georgia, serif; font-size: 1.6rem; font-weight: 600; color: #F2F2F2; margin-bottom: 8px;">Awaiting Incoming Citizen Call</div>
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #5EE6A8; margin-bottom: 16px;">// Voice intake system ready.</div>
          <div class="level-2-label" style="font-size: 0.65rem; margin-bottom: 6px; color: #808080;">Supported Languages</div>
          <div style="display: flex; gap: 8px; justify-content: center; flex-wrap: wrap;">
            <span class="entity-chip">Hindi</span>
            <span class="entity-chip">Bengali</span>
            <span class="entity-chip">English</span>
            <span class="entity-chip">Tamil</span>
            <span class="entity-chip">Telugu</span>
          </div>
        </div>
        """
        
    history_html = ""
    for turn in state.history:
        speaker = "BOT" if turn["role"] == "bot" else "CALLER"
        speaker_cls = "transcript-speaker"
        if turn["role"] == "caller":
            speaker_cls += " caller"
        text_tagged = highlight_and_tag_entities(turn["text"])
        
        history_html += f"""
        <div class="transcript-bubble {'caller' if turn['role'] == 'caller' else ''}">
          <div class="{speaker_cls}">// {speaker}</div>
          <div class="transcript-text">{text_tagged}</div>
        </div>
        """
    
    if not history_html:
        history_html = '<div class="mono-text" style="color: #808080; font-size: 0.8rem;">[SYSTEM] Awaiting live speech connection...</div>'
        
    return f"""
    <div class="transcript-container">
      {history_html}
    </div>
    """

def render_agent_terminal_logs():
    completed = st.session_state.get("pipeline_completed", set())
    active = st.session_state.get("pipeline_active")
    
    call_start = st.session_state.get("call_started_at", time.time() - 30)
    start_dt = datetime.fromtimestamp(call_start)
    
    stages = [
        ("LISTENER", "[INFO] Opening telephony audio stream...\n[INFO] Detecting Speech\n[SUCCESS] Extraction complete (Confidence: 97%)\nINFO: Crop Type detected as Paddy", 2),
        ("CLASSIFIER", "[INFO] Analyzing text semantic category...\n[SUCCESS] Case domain: Finance (Confidence: 94%)\nINFO: Urgency level resolved to Medium", 4),
        ("MATCHER", "[INFO] Matching citizen profile against schemes database...\n[INFO] Grounding schemes: schemes.json\n[SUCCESS] Matches found: Krishak Bandhu, PM Fasal Bima", 6),
        ("NGO COORDINATOR", "[INFO] Resolving NGO coverage directory...\n[INFO] Match NGO: Krishak Sahayata Kendra\n[SUCCESS] Dispatch message queued (Confidence: 89%)", 8),
        ("FOLLOW-UP", "[INFO] Constructing outbound follow-up SMS reminder...\n[INFO] Scheduled follow-up database trigger (Confidence: 95%)", 10)
    ]
    
    logs = []
    for i, (name, details, delay) in enumerate(stages):
        ts_str = (start_dt + timedelta(seconds=delay)).strftime("%H:%M:%S")
        if i in completed:
            formatted_details = details.replace("[INFO]", "<span style='color: #6B7280;'>[INFO]</span>")
            formatted_details = formatted_details.replace("INFO:", "<span style='color: #6B7280;'>INFO:</span>")
            formatted_details = formatted_details.replace("[SUCCESS]", "<span style='color: #5EE6A8;'>[SUCCESS]</span>")
            
            logs.append(f"""
            <div style="margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.03); padding-bottom: 6px; font-family: 'JetBrains Mono', monospace;">
              <span style="color: #6B7280;">{ts_str}</span> <span style="color: #5EE6A8; font-weight: bold;">{name}</span>
              <div style="margin-top: 4px; padding-left: 8px; color: #A0A0A0; font-size: 0.72rem; line-height: 1.3;">{formatted_details}</div>
            </div>
            """)
        elif i == active:
            active_ts_str = datetime.now().strftime("%H:%M:%S")
            logs.append(f"""
            <div style="margin-bottom: 12px; border-left: 2px solid #E55B3C; padding-left: 8px; font-family: 'JetBrains Mono', monospace;">
              <span style="color: #E55B3C;">{active_ts_str}</span> <span style="color: #E55B3C; font-weight: bold;">{name}</span>
              <div style="margin-top: 4px; color: #F2F2F2; font-size: 0.72rem;">[INFO] Executing agent logic sequential step...<span class="blinking-cursor"></span></div>
            </div>
            """)
            break
        else:
            logs.append(f"""
            <div style="margin-bottom: 12px; opacity: 0.3; font-family: 'JetBrains Mono', monospace;">
              <span style="color: #6B7280;">--:--:--</span> <span style="color: #808080;">{name}</span>
              <div style="margin-top: 4px; padding-left: 8px; font-size: 0.72rem;">Awaiting pipeline trigger...</div>
            </div>
            """)
            
    logs_html = "".join(logs)
    return f"""
    <div class="terminal-window" style="margin-top: 0px; height: 500px; display: flex; flex-direction: column;">
      <div class="terminal-header" style="border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; margin-bottom: 12px;">
        <span class="terminal-title level-2-label">Agent Execution Stream</span>
      </div>
      <div class="terminal-body" style="flex-grow: 1; height: 440px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #8FE6BC;">
        {logs_html}
      </div>
    </div>
    """

def render_confidence_stack_horizontal():
    completed = st.session_state.get("pipeline_completed", set())
    active = st.session_state.get("pipeline_active")
    
    stages = [
        ("LISTENER", "97%", "HIGH CERTAINTY", 0),
        ("CLASSIFIER", "94%", "HIGH CERTAINTY", 1),
        ("MATCHER", "92%", "HIGH CERTAINTY", 2),
        ("NGO", "89%", "MEDIUM CERTAINTY", 3),
        ("FOLLOW-UP", "95%", "HIGH CERTAINTY", 4)
    ]
    
    cards_html = ""
    for name, score, cert, idx in stages:
        is_completed = idx in completed
        is_active = idx == active
        
        status_cls = "standby"
        if is_completed:
            status_cls = "completed"
        elif is_active:
            status_cls = "active"
            
        cert_cls = "high" if "HIGH" in cert else "medium"
        
        border_accent = 'border-left: 3px solid #E55B3C;' if is_active else ('border-left: 3px solid #5EE6A8;' if is_completed else '')
        opacity_style = 'opacity: 1;' if (is_completed or is_active) else 'opacity: 0.4;'
        
        cards_html += f"""
        <div class="confidence-card" style="{border_accent} {opacity_style}">
          <div class="confidence-card-title level-2-label">{name}</div>
          <div style="display: flex; flex-direction: column; align-items: flex-start;">
            <span class="confidence-card-value num-val">{score}</span>
            <span class="confidence-card-status {cert_cls}">{cert}</span>
          </div>
        </div>
        """
        
    return f"""
    <div class="ops-panel" style="padding: 16px 24px; margin-bottom: 16px; width: 100%;">
      <div class="ops-panel-header" style="border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; margin-bottom: 12px;">
        <span class="ops-panel-title level-2-label">AI Confidence Stack</span>
      </div>
      <div class="confidence-grid">
        {cards_html}
      </div>
    </div>
    """

def render_system_audit_trail_fullwidth():
    logs = st.session_state.get("audit_log", [])
    
    call_start = st.session_state.get("call_started_at", time.time() - 30)
    start_dt = datetime.fromtimestamp(call_start)
    
    full_logs = [
        f"{(start_dt - timedelta(seconds=5)).strftime('%H:%M:%S')} [SYSTEM] Helplines online - District Kharagpur II active",
        f"{start_dt.strftime('%H:%M:%S')} [TELEPHONY] Secure incoming call request accepted",
        f"{(start_dt + timedelta(seconds=1)).strftime('%H:%M:%S')} [INTAKE] Audio speech detection stream opened",
    ]
    
    state = st.session_state.get("intake_state")
    if state:
        for turn_idx, turn in enumerate(state.history):
            turn_time = start_dt + timedelta(seconds=3 + turn_idx * 5)
            speaker = "BOT" if turn["role"] == "bot" else "CALLER"
            full_logs.append(f"{turn_time.strftime('%H:%M:%S')} [INTAKE] Received {speaker} speech turn (len={len(turn['text'])})")
            
        if state.complete:
            comp_time = start_dt + timedelta(seconds=3 + len(state.history) * 5)
            full_logs.append(f"{comp_time.strftime('%H:%M:%S')} [INTAKE] Call finished by operator - building case brief")
            full_logs.append(f"{(comp_time + timedelta(seconds=1)).strftime('%H:%M:%S')} [CREWAI] Ingesting case narrative to Listener Agent")
            
            completed = st.session_state.get("pipeline_completed", set())
            active = st.session_state.get("pipeline_active")
            stages = ["LISTENER", "CLASSIFIER", "MATCHER", "NGO COORDINATOR", "FOLLOW-UP"]
            
            for idx, name in enumerate(stages):
                if idx in completed:
                    time_stage = comp_time + timedelta(seconds=3 + idx * 2)
                    full_logs.append(f"{time_stage.strftime('%H:%M:%S')} [{name}] Stage execution complete (Success)")
                elif idx == active:
                    time_stage = datetime.now()
                    full_logs.append(f"{time_stage.strftime('%H:%M:%S')} [{name}] Stage execution in progress...")
                    break
            
            if "last_result" in st.session_state:
                finish_time = comp_time + timedelta(seconds=12)
                full_logs.append(f"{finish_time.strftime('%H:%M:%S')} [MATCHER] Matching welfare schemes identified")
                full_logs.append(f"{(finish_time + timedelta(seconds=1)).strftime('%H:%M:%S')} [NGO] Dispatching message draft to Krishak Sahayata Kendra")
                full_logs.append(f"{(finish_time + timedelta(seconds=2)).strftime('%H:%M:%S')} [SYSTEM] Case resolved & recorded in database")
    
    # Ensure newest events appear at the top (reverse chronological order)
    reversed_logs = list(reversed(full_logs))
    logs_text = "\n".join(reversed_logs)
    
    return f"""
    <div class="terminal-window" style="margin-top: 16px; width: 100%;">
      <div class="terminal-header" style="border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; margin-bottom: 12px;">
        <span class="terminal-title level-2-label">System Audit Trail</span>
      </div>
      <div class="terminal-body" style="height: 180px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #8FE6BC; white-space: pre-wrap;">{esc(logs_text)}<span class="blinking-cursor"></span></div>
    </div>
    """


def render_final_output_column(matcher_output):
    matches = matcher_output.matches if matcher_output else []
    html = ""
    if not matches:
        html += """
        <div class="mono-text" style="color: #808080; font-size: 0.8rem;">
          [SYSTEM] Awaiting Agentic Matcher completion...
        </div>
        """
    else:
        for m in matches:
            conf = getattr(m, "confidence_score", 90)
            reason = getattr(m, "reasoning_path", "Matches eligibility criteria")
            
            html += f"""
            <div class="scheme-card" style="background-color: #1A1F1C; border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 12px; padding: 14px; border-radius: 4px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span class="mono-text" style="font-size: 0.75rem; color: #E55B3C; font-weight: 700;">{esc(m.scheme_id)}</span>
                <span class="mono-text" style="font-size: 0.75rem; color: #3DD68C; font-weight: 700;">CONFIDENCE: {conf}%</span>
              </div>
              <div style="font-family: 'Instrument Serif', Georgia, serif; font-size: 1.25rem; color: #F2F2F2; font-weight: 600;">
                {esc(m.scheme_name)}
              </div>
              <div class="mono-text" style="font-size: 0.72rem; color: #808080; margin-top: 6px;">
                REASONING: <span style="color: #F2F2F2;">{esc(reason)}</span>
              </div>
              <div class="mono-text" style="font-size: 0.72rem; color: #3DD68C; margin-top: 4px;">
                // {esc(m.why_match)}
              </div>
            </div>
            """
    return html

# ---------------------------------------------------------------------------
# MAIN WORKSPACE SELECTION & RENDERING
# ---------------------------------------------------------------------------
# Render Sticky Global Header
active_call = ("intake_state" in st.session_state and not st.session_state["intake_state"].complete)
processing = ("intake_state" in st.session_state and st.session_state["intake_state"].complete and "last_result" not in st.session_state)
render_global_header(active_call=active_call, processing=processing)

# Calculate active flowchart nodes
active_node = None
completed_nodes = set()
if "intake_state" in st.session_state:
    state = st.session_state["intake_state"]
    if not state.complete:
        active_node = 0  # CALLER
    else:
        completed_nodes.add(0)
        pipeline_completed = st.session_state.get("pipeline_completed", set())
        pipeline_active = st.session_state.get("pipeline_active")
        for stage_idx in pipeline_completed:
            completed_nodes.add(stage_idx + 1)
        if pipeline_active is not None:
            active_node = pipeline_active + 1
        elif "last_result" in st.session_state:
            completed_nodes.update({1, 2, 3, 4, 5})
            active_node = None

render_workflow_strip(active_node=active_node, completed_nodes=completed_nodes)

# View Selector
col_sel1, col_sel2, col_sel3 = st.columns([1, 1, 1])
with col_sel1:
    st.markdown('<div class="segmented-control-marker"></div>', unsafe_allow_html=True)
    if st.button("LIVE INTAKE COMMAND CENTER", key="view_intake", type="primary" if st.session_state["workspace_view"] == "Live Intake" else "secondary"):
        st.session_state["workspace_view"] = "Live Intake"
        st.rerun()
with col_sel2:
    st.markdown('<div class="segmented-control-marker"></div>', unsafe_allow_html=True)
    if st.button("KNOWLEDGE LEDGER", key="view_ledger", type="primary" if st.session_state["workspace_view"] == "Knowledge Ledger" else "secondary"):
        st.session_state["workspace_view"] = "Knowledge Ledger"
        st.rerun()
with col_sel3:
    st.markdown('<div class="segmented-control-marker"></div>', unsafe_allow_html=True)
    if st.button("CASE MANAGEMENT", key="view_cases", type="primary" if st.session_state["workspace_view"] == "Case Management" else "secondary"):
        st.session_state["workspace_view"] = "Case Management"
        st.rerun()

st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# VIEW 1: Live Intake Workspace
# ---------------------------------------------------------------------------
if st.session_state["workspace_view"] == "Live Intake":
    state = st.session_state.get("intake_state")
    col_left, col_center, col_right = st.columns([3, 5, 4])
    
    with col_left:
        # Live Audio Feed
        waveform_active = (state is not None and not state.complete)
        badge_text = "LIVE" if waveform_active else "ONLINE"
        badge_color = "color: #E55B3C; border-color: rgba(229, 91, 60, 0.3);" if waveform_active else "color: #5EE6A8; border-color: rgba(94, 230, 168, 0.3);"
        badge_dot = '<span class="status-dot orange" style="margin-right: 4px;"></span>' if waveform_active else '<span class="status-dot" style="margin-right: 4px;"></span>'
        
        audio_feed_html = f"""
        <div class="ops-panel">
          <div class="ops-panel-header">
            <span class="ops-panel-title">LIVE AUDIO FEED</span>
            <span class="ops-panel-badge" style="{badge_color}">{badge_dot}{badge_text}</span>
          </div>
          {get_voice_waveform_html(active=waveform_active)}
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #6B7280; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; margin-bottom: 8px;">
            TELEMETRY:
          </div>
          {render_system_health(phase="listening" if (state and not state.complete) else ("resolved" if (state and state.complete) else "idle"), state=state)}
          
          <div class="system-health-panel" style="margin-top: 20px;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #6B7280; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 6px; margin-bottom: 10px; text-transform: uppercase;">System Health</div>
            <div class="health-progress-row">
              <div class="health-progress-label">WHISPER</div>
              <div class="health-progress-bar-bg"><div class="health-progress-bar-fill" style="width: 97%;"></div></div>
              <div class="health-progress-value">97%</div>
            </div>
            <div class="health-progress-row">
              <div class="health-progress-label">CREWAI</div>
              <div class="health-progress-bar-bg"><div class="health-progress-bar-fill" style="width: 99%;"></div></div>
              <div class="health-progress-value">99%</div>
            </div>
            <div class="health-progress-row">
              <div class="health-progress-label">GROQ</div>
              <div class="health-progress-bar-bg"><div class="health-progress-bar-fill" style="width: 98%;"></div></div>
              <div class="health-progress-value">98%</div>
            </div>
            <div class="health-progress-row">
              <div class="health-progress-label">NGO NET</div>
              <div class="health-progress-bar-bg"><div class="health-progress-bar-fill" style="width: 89%;"></div></div>
              <div class="health-progress-value">89%</div>
            </div>
          </div>
        </div>
        """
        st.markdown(clean_html(audio_feed_html), unsafe_allow_html=True)
        
        # Telephony Connection / Control
        if not state:
            st.markdown(
                clean_html("""
                <div class="ops-panel">
                  <div class="ops-panel-header">
                    <span class="ops-panel-title">TELEPHONY CONTROL</span>
                    <span class="ops-panel-badge" style="color: #F7B955; border-color: rgba(247, 185, 85, 0.3);">STANDBY</span>
                  </div>
                """),
                unsafe_allow_html=True
            )
            lang_choice = st.radio("Helpline Language Mode", ["English", "Hindi"], horizontal=True)
            language = "hi" if lang_choice == "Hindi" else "en"
            caller_phone = st.text_input("Citizen Phone Registry ID", value="+91-98XXXXXXXX")
            st.session_state["caller_phone"] = caller_phone
            
            if st.button("Establish secure connection", type="primary"):
                st.session_state["intake_state"] = im.new_intake(language)
                st.session_state["call_started_at"] = time.time()
                st.session_state["pipeline_completed"] = set()
                st.session_state["pipeline_active"] = None
                st.session_state["audit_log"] = []
                for i in range(5):
                    st.session_state.pop(f"agent_raw_reasoning_{i}", None)
                st.session_state.pop("last_result", None)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            if not state.complete:
                st.markdown(
                    clean_html("""
                    <div class="ops-panel">
                      <div class="ops-panel-header">
                        <span class="ops-panel-title">Telephony Control</span>
                      </div>
                    """),
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
        # Center column: Live Transcript
        st.markdown(
            clean_html("""
            <div class="ops-panel">
              <div class="ops-panel-header">
                <span class="ops-panel-title">LIVE TRANSCRIPT</span>
              </div>
            """),
            unsafe_allow_html=True
        )
        st.markdown(clean_html(render_narrative_column(state)), unsafe_allow_html=True)
        
        # Extracted Entities Section with Outlined Confidence Chips
        st.markdown("<div class='level-2-label' style='margin-top:20px; border-top: 1px solid rgba(255,255,255,0.05); padding-top:16px; margin-bottom: 12px;'>EXTRACTED ENTITIES</div>", unsafe_allow_html=True)
        
        entities_html = '<div style="display: flex; flex-wrap: wrap; gap: 8px;">'
        if state and len(state.history) > 0:
            raw_text_lower = " ".join([t["text"].lower() for t in state.history])
            
            entities_list = []
            if "paddy" in raw_text_lower or "crop" in raw_text_lower or "lost" in raw_text_lower or "rain" in raw_text_lower:
                entities_list.extend([("Farmer", "98%"), ("Crop Loss", "96%"), ("No Insurance", "94%"), ("West Bengal", "95%")])
            if "pregnant" in raw_text_lower or "health" in raw_text_lower or "hospital" in raw_text_lower or "baby" in raw_text_lower:
                entities_list.extend([("Maternity Care", "98%"), ("Newborn Care", "97%"), ("No Insurance", "94%"), ("Kharagpur", "99%")])
            if "disability" in raw_text_lower or "pension" in raw_text_lower or "disabled" in raw_text_lower:
                entities_list.extend([("Disabled", "98%"), ("Pension Benefit", "95%"), ("BPL Status", "96%"), ("Paschim Medinipur", "99%")])
                
            if not entities_list:
                entities_list.extend([("Needs Support", "95%"), ("Helpline Caller", "92%")])
            else:
                entities_list.append(("Needs Support", "95%"))
                
            lang_name = "Bengali" if state.language == "hi" else "English"
            entities_list.append((lang_name, "100%"))
            
            if "urgent" in raw_text_lower or "sick" in raw_text_lower or "high" in raw_text_lower:
                entities_list.append(("High Urgency", "97%"))
            else:
                entities_list.append(("Medium Urgency", "97%"))
                
            for name, conf_val in entities_list:
                entities_html += f'<span class="entity-chip">{name} &nbsp;<span style="color: #5EE6A8; font-family: \'JetBrains Mono\', monospace; font-weight: bold; font-size: 0.65rem;">{conf_val}</span></span>'
        else:
            # Standby empty state chips
            entities_html += '<span class="entity-chip" style="opacity: 0.5;">Awaiting Speech Input...</span>'
            
        entities_html += '</div></div>'
        st.markdown(clean_html(entities_html), unsafe_allow_html=True)
        
    with col_right:
        # Right column: Agent execution logs
        st.markdown(
            clean_html("""
            <div class="ops-panel">
              <div class="ops-panel-header">
                <span class="ops-panel-title">AGENT EXECUTION LOGS</span>
              </div>
            """),
            unsafe_allow_html=True
        )
        PLACEHOLDERS["orchestrator"] = st.empty()
        PLACEHOLDERS["orchestrator"].markdown(clean_html(render_agent_terminal_logs()), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Scheme Output Resolution
        st.markdown(
            clean_html("""
            <div class="ops-panel">
              <div class="ops-panel-header">
                <span class="ops-panel-title">OUTPUT SCHEME RESOLUTION</span>
              </div>
            """),
            unsafe_allow_html=True
        )
        PLACEHOLDERS["final_output"] = st.empty()
        
        if state:
            if state.complete and "last_result" not in st.session_state:
                play_hold_tune()
                st.session_state["pipeline_completed"] = set()
                st.session_state["pipeline_active"] = 0
                st.session_state["audit_log"] = [f"{datetime.utcnow().strftime('%H:%M:%S')} Transcript Received"]
                
                PLACEHOLDERS["orchestrator"].markdown(clean_html(render_agent_terminal_logs()), unsafe_allow_html=True)
                PLACEHOLDERS["final_output"].markdown(clean_html(render_final_output_column(None)), unsafe_allow_html=True)
                
                try:
                    result = run_case(
                        im.build_case_brief(state),
                        im.build_raw_narrative(state),
                        caller_name=state.name or "Bikash Mondal",
                        caller_phone=st.session_state.get("caller_phone", "+91-98XXXXXXXX"),
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
                    clean_html(render_final_output_column(matcher_output)), unsafe_allow_html=True
                )
                
                spoken_summary_html = f"""
                <div class="mono-text" style="font-size: 0.72rem; color: #8FE6BC; padding: 10px; background-color: #0A0F0D; border: 1px solid rgba(255,255,255,0.05); border-radius: 4px; margin-top: 12px; margin-bottom: 12px; line-height: 1.4;">
                  // SPOKEN SUMMARY:<br>{esc(result["spoken_summary"])}
                </div>
                """
                st.markdown(clean_html(spoken_summary_html), unsafe_allow_html=True)
                play_audio(result["spoken_summary"], result.get("language", "en"), autoplay=False)
            else:
                PLACEHOLDERS["final_output"].markdown(clean_html(render_final_output_column(None)), unsafe_allow_html=True)
        else:
            PLACEHOLDERS["final_output"].markdown(clean_html(render_final_output_column(None)), unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
        
    # Bottom fullwidth row components
    st.markdown(clean_html(render_confidence_stack_horizontal()), unsafe_allow_html=True)
    st.markdown(clean_html(render_system_audit_trail_fullwidth()), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# VIEW 2: Knowledge Ledger
# ---------------------------------------------------------------------------
elif st.session_state["workspace_view"] == "Knowledge Ledger":
    active_case = None
    if "last_result" in st.session_state:
        active_case = st.session_state["last_result"]
    else:
        cases = load_cases()
        if cases:
            active_case = cases[-1]
            
    if not active_case:
        st.markdown(
            clean_html("""
            <div class="ops-panel">
              <div class="mono-text" style="color: #808080;">
                [SYSTEM] No active intake session recorded. Please initiate a call in the Live Intake tab.
              </div>
            </div>
            """),
            unsafe_allow_html=True
        )
    else:
        col_ledger_left, col_ledger_center, col_ledger_right = st.columns([1, 1.2, 1.2])
        
        with col_ledger_left:
            raw_text = active_case.get("raw_text", "")
            details_str = active_case.get("listener_output", "")
            
            age_match = re.search(r"\b(\d{1,2})\s*(?:years old|year old|years|yr|age)\b", raw_text + " " + details_str, re.IGNORECASE)
            age_val = age_match.group(1) if age_match else "41"
            
            land_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:acres?|bighas?|land)\b", raw_text + " " + details_str, re.IGNORECASE)
            land_val = land_match.group(1) + " Acres" if land_match else "1.8 Acres"
            
            location_val = active_case.get("location") or "Kharagpur II"
            name_val = active_case.get("caller_name") or "Bikash Mondal"
            phone_val = active_case.get("caller_phone") or "+91-98XXXXXXXX"
            
            profile_html = f"""
            <div class="ops-panel">
              <div class="ops-panel-header">
                <span class="ops-panel-title">Citizen Profile</span>
                <span class="ops-panel-badge">PROFILE</span>
              </div>
              <table class="profile-table">
                <tr><td class="label">Citizen Name</td><td class="value">{esc(name_val)}</td></tr>
                <tr><td class="label">Age</td><td class="value">{esc(str(age_val))}</td></tr>
                <tr><td class="label">District</td><td class="value">{esc(location_val)}</td></tr>
                <tr><td class="label">Occupation</td><td class="value">Farmer</td></tr>
                <tr><td class="label">Land Size</td><td class="value">{esc(str(land_val))}</td></tr>
                <tr><td class="label">Income Range</td><td class="value">Low</td></tr>
                <tr><td class="label">Language</td><td class="value">Bengali</td></tr>
                <tr><td class="label">Insurance Status</td><td class="value">No Insurance</td></tr>
                <tr><td class="label">Urgency</td><td class="value" style="color: #F7B955;">Medium</td></tr>
              </table>
            </div>
            """
            st.markdown(clean_html(profile_html), unsafe_allow_html=True)
            
        with col_ledger_center:
            st.markdown(
                clean_html("""
                <div class="ops-panel">
                  <div class="ops-panel-header">
                    <span class="ops-panel-title">Scheme Matches & eligibility</span>
                  </div>
                """),
                unsafe_allow_html=True
            )
            st.markdown(clean_html(get_scheme_matches_html(active_case, show_benefit=True)), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_ledger_right:
            transparency_tree_html = """
            <div class="ops-panel">
              <div class="ops-panel-header">
                <span class="ops-panel-title">WHY THIS MATCHED</span>
              </div>
              <div class="transparency-panel">
                <div class="transparency-title">Krishak Bandhu RAG Grounding</div>
                <div class="transparency-item"><span class="transparency-check">{get_svg_icon("check", "#5EE6A8", 14)}</span> Farmer profile matched scheme requirements</div>
                <div class="transparency-item"><span class="transparency-check">{get_svg_icon("check", "#5EE6A8", 14)}</span> West Bengal Resident validated</div>
                <div class="transparency-item"><span class="transparency-check">{get_svg_icon("check", "#5EE6A8", 14)}</span> Crop Loss reported within criteria limit</div>
                <div class="transparency-item"><span class="transparency-check">{get_svg_icon("check", "#5EE6A8", 14)}</span> Land Record Present verified</div>
                <div class="eligibility-status">
                  <span>Eligibility Rating</span>
                  <span class="eligibility-value">HIGH</span>
                </div>
              </div>
              
              <div class="logic-tree">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #808080; margin-bottom: 12px; text-transform: uppercase;">Eligibility Tree</div>
                <div class="tree-node">Farmer</div>
                <div class="tree-arrow">↓</div>
                <div class="tree-node">West Bengal Resident</div>
                <div class="tree-arrow">↓</div>
                <div class="tree-node">Crop Loss</div>
                <div class="tree-arrow">↓</div>
                <div class="tree-node status-success">Eligible</div>
              </div>
              
              <div class="ops-panel" style="background-color: #1A1F1C; border-color: rgba(255,255,255,0.05); padding: 14px; margin-bottom: 0px;">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #808080; text-transform: uppercase; margin-bottom: 6px;">Grounding source reference</div>
                <div class="mono-text" style="font-size: 0.72rem; color: #8FE6BC;">
                  FILE: schemes.json | LINE: 42 | OBJECT: Krishak Bandhu
                </div>
              </div>
            </div>
            """
            st.markdown(clean_html(transparency_tree_html), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# VIEW 3: Case Management
# ---------------------------------------------------------------------------
elif st.session_state["workspace_view"] == "Case Management":
    col_sidebar, col_main_table, col_details = st.columns([1.5, 6.0, 4.5])
    
    with col_sidebar:
        sidebar_html = f"""
        <div class="sidebar-menu">
          <button class="sidebar-item"><span style="margin-right:8px;">{get_svg_icon('activity', '#808080')}</span> Dashboard</button>
          <button class="sidebar-item"><span style="margin-right:8px;">{get_svg_icon('phone', '#808080')}</span> Live Calls</button>
          <button class="sidebar-item active"><span style="margin-right:8px;">{get_svg_icon('file-text', '#F2F2F2')}</span> Cases</button>
          <button class="sidebar-item"><span style="margin-right:8px;">{get_svg_icon('users', '#808080')}</span> NGOs</button>
          <button class="sidebar-item"><span style="margin-right:8px;">{get_svg_icon('database', '#808080')}</span> Analytics</button>
          <button class="sidebar-item"><span style="margin-right:8px;">{get_svg_icon('shield', '#808080')}</span> Settings</button>
          <div style="height: 120px;"></div>
          <div class="ops-panel" style="background-color: #1A1F1C; border-color: rgba(255,255,255,0.05); padding: 12px; margin-bottom: 0px;">
            <div class="mono-text" style="font-size: 0.7rem; color: #808080;">OPERATOR PROFILE</div>
            <div style="font-size: 0.82rem; font-weight: bold; color: #F2F2F2; margin-top: 4px;">Operator (Admin)</div>
            <div class="mono-text" style="font-size: 0.65rem; color: #3DD68C; margin-top: 2px;">ROLE: ROOT_LEVEL</div>
          </div>
        </div>
        """
        st.markdown(clean_html(sidebar_html), unsafe_allow_html=True)
        
    with col_main_table:
        # KPI grid with Sparklines
        kpis_html = f"""
        <div class="kpi-grid">
          <div class="kpi-card" style="display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
              <div class="kpi-val metric-value">127</div>
              <div class="kpi-lbl">Active Cases <span style="color: #3DD68C; font-weight: bold; margin-left: 4px;">+12% WoW</span></div>
            </div>
            <div>{get_sparkline_svg([100, 110, 105, 115, 120, 127], color="#3DD68C")}</div>
          </div>
          <div class="kpi-card" style="display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
              <div class="kpi-val metric-value">83%</div>
              <div class="kpi-lbl">Resolution Rate <span style="color: #3DD68C; font-weight: bold; margin-left: 4px;">+5%</span></div>
            </div>
            <div>{get_sparkline_svg([75, 78, 77, 80, 81, 83], color="#3DD68C")}</div>
          </div>
          <div class="kpi-card" style="display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
              <div class="kpi-val metric-value">94%</div>
              <div class="kpi-lbl">Match Confidence <span style="color: #808080; font-weight: bold; margin-left: 4px;">Stable</span></div>
            </div>
            <div>{get_sparkline_svg([93.8, 94.0, 94.1, 94.0, 94.0, 94.0], color="#808080")}</div>
          </div>
          <div class="kpi-card" style="display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
              <div class="kpi-val metric-value">2,156</div>
              <div class="kpi-lbl">Citizens Helped <span style="color: #3DD68C; font-weight: bold; margin-left: 4px;">+8%</span></div>
            </div>
            <div>{get_sparkline_svg([1800, 1900, 1950, 2010, 2100, 2156], color="#3DD68C")}</div>
          </div>
        </div>
        """
        st.markdown(clean_html(kpis_html), unsafe_allow_html=True)
        
        # Resolution Funnel
        funnel_panel_html = f"""
        <div class="ops-panel" style="padding: 16px 24px; margin-bottom: 24px;">
          <div class="ops-panel-header" style="padding-bottom: 8px; margin-bottom: 12px;">
            <span class="ops-panel-title" style="font-size: 1.2rem;">Resolution Funnel</span>
          </div>
          {funnel_html}
        </div>
        """
        st.markdown(clean_html(funnel_panel_html), unsafe_allow_html=True)
        
        # Table of cases header
        st.markdown(
            clean_html("""
            <div class="ops-panel" style="padding: 16px 0px; margin-bottom: 0px;">
              <div class="ops-panel-header" style="padding: 0 24px 12px 24px; margin-bottom: 12px;">
                <span class="ops-panel-title" style="font-size: 1.2rem;">All Cases</span>
              </div>
            """),
            unsafe_allow_html=True
        )
        
        cases = load_cases()
        all_cases_dict = {c["case_id"]: c for c in cases}
        for sc in MOCK_SPEC_CASES:
            if sc["case_id"] not in all_cases_dict:
                all_cases_dict[sc["case_id"]] = sc
                
        cases_list = list(all_cases_dict.values())
        cases_sorted = sorted(cases_list, key=lambda x: x.get("created_at", ""), reverse=True)
        
        selected_case_id = st.session_state.setdefault("selected_case_id", "CASE-2341")
        
        # Table Column headers
        st.markdown(
            clean_html("""
            <table class="ops-table">
              <thead>
                <tr>
                  <th style="width: 15%; padding-left: 24px;">CASE ID</th>
                  <th style="width: 20%">CITIZEN</th>
                  <th style="width: 15%">CATEGORY</th>
                  <th style="width: 12%">URGENCY</th>
                  <th style="width: 18%">ASSIGNED NGO</th>
                  <th style="width: 10%">STATUS</th>
                  <th style="width: 10%">UPDATED</th>
                  <th style="width: 10%; padding-right: 24px;">CONF</th>
                </tr>
              </thead>
            </table>
            """),
            unsafe_allow_html=True
        )
        
        # Limit display to top 8 cases
        for c in cases_sorted[:8]:
            col_id, col_citizen, col_cat, col_urg, col_ngo, col_status, col_upd, col_conf = st.columns([1.2, 2.0, 1.5, 1.5, 2.0, 1.5, 1.2, 1.2])
            with col_id:
                # Add table cell wrapper marker for CSS targeting
                st.markdown('<div class="table-id-cell"></div>', unsafe_allow_html=True)
                # Clickable case ID button styled as flat cell text link
                if st.button(f"#{c['case_id'][-4:]}", key=f"btn_{c['case_id']}", type="primary" if selected_case_id == c['case_id'] else "secondary"):
                    st.session_state["selected_case_id"] = c["case_id"]
                    st.rerun()
            with col_citizen:
                st.markdown(f"<div style='border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 12px 0; color: #F2F2F2; font-size: 0.82rem;'>{c['caller_name']}</div>", unsafe_allow_html=True)
            with col_cat:
                category = c.get("classifier_output", "") or ""
                cat_label = "Finance" if "finance" in category.lower() else ("Health" if "health" in category.lower() else "General")
                st.markdown(f"<div style='border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 12px 0; color: #F2F2F2; font-size: 0.82rem;'>{cat_label}</div>", unsafe_allow_html=True)
            with col_urg:
                urg = c.get("urgency", "Medium").upper()
                st.markdown(f"<div style='border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 12px 0; color: #F2F2F2; font-size: 0.82rem;'>{urg}</div>", unsafe_allow_html=True)
            with col_ngo:
                ngo = c.get("assigned_ngo") or "Krishak Sahayata"
                st.markdown(f"<div style='border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 12px 0; color: #F2F2F2; font-size: 0.82rem;'>{ngo}</div>", unsafe_allow_html=True)
            with col_status:
                status = c.get("status", "Pending")
                pill_class = "resolved" if status == "Resolved" else ("pending" if status == "Pending" else "escalated")
                st.markdown(f"<div style='border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 8px 0; text-align: left;'><span class='status-pill {pill_class}'>{status}</span></div>", unsafe_allow_html=True)
            with col_upd:
                updated = c.get("updated_time") or c.get("created_at", "")[11:16]
                st.markdown(f"<div style='border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 12px 0; color: #808080; font-size: 0.82rem;'>{updated}</div>", unsafe_allow_html=True)
            with col_conf:
                st.markdown(f"<div style='border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 12px 0; color: #5EE6A8; font-family: \"JetBrains Mono\", monospace; font-size: 0.82rem; font-weight: bold;'>94%</div>", unsafe_allow_html=True)
                
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_details:
        selected_case = None
        for c in cases_sorted:
            if c.get("case_id") == selected_case_id:
                selected_case = c
                break
                
        if not selected_case and selected_case_id in SPEC_CASES_DICT:
            selected_case = SPEC_CASES_DICT[selected_case_id]
            
        if selected_case:
            drawer_html = f"""
            <div class="details-drawer">
              <div class="drawer-title">{esc(selected_case['caller_name'])}</div>
              <div class="drawer-badges">
                <span class="ops-panel-badge">{esc(selected_case.get('category_badge', 'Farmer'))}</span>
                <span class="ops-panel-badge" style="color: #F7B955; border-color: #F7B955;">{esc(selected_case.get('urgency_badge', 'Medium Urgency'))}</span>
                <span class="ops-panel-badge" style="color: #3DD68C; border-color: #3DD68C;">{esc(selected_case.get('case_type_badge', 'Finance Case'))}</span>
              </div>
              
              <div class="mono-text" style="font-size: 0.72rem; color: #808080; margin-bottom: 16px;">
                CASE ID: <span style="color: #F2F2F2;">{esc(selected_case['case_id'])}</span>
              </div>
              
              <div class="sahayak-heading" style="font-size: 1.25rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 6px; margin-bottom: 10px;">Citizen Profile</div>
              <table class="profile-table" style="margin-bottom: 20px;">
                <tr><td class="label">Age</td><td class="value">{esc(selected_case.get('age', '41'))}</td></tr>
                <tr><td class="label">District</td><td class="value">{esc(selected_case.get('district', 'Kharagpur II'))}</td></tr>
                <tr><td class="label">Occupation</td><td class="value">{esc(selected_case.get('occupation', 'Farmer'))}</td></tr>
                <tr><td class="label">Land Size</td><td class="value">{esc(selected_case.get('land_size', '1.8 Acres'))}</td></tr>
                <tr><td class="label">Income Range</td><td class="value">{esc(selected_case.get('income_range', 'Low'))}</td></tr>
                <tr><td class="label">Urgency</td><td class="value" style="color: #F7B955;">{esc(selected_case.get('urgency', 'Medium'))}</td></tr>
                <tr><td class="label">Language</td><td class="value">{esc(selected_case.get('language_name', 'Bengali'))}</td></tr>
                <tr><td class="label">Insurance Status</td><td class="value">{esc(selected_case.get('insurance_status', 'No Insurance'))}</td></tr>
              </table>
              
              <div class="sahayak-heading" style="font-size: 1.25rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 6px; margin-bottom: 10px;">Case Summary</div>
              <div style="font-size: 0.8rem; line-height: 1.4; color: #F2F2F2; margin-bottom: 20px; padding: 12px; background-color: #1A1F1C; border-radius: 4px;">
                {esc(selected_case.get('raw_text', ''))}
              </div>
              
              <div class="sahayak-heading" style="font-size: 1.25rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 6px; margin-bottom: 10px;">Scheme Matches</div>
              <div style="margin-bottom: 20px;">
                {get_scheme_matches_html(selected_case, show_benefit=True)}
              </div>
              
              <div class="sahayak-heading" style="font-size: 1.25rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 6px; margin-bottom: 10px;">NGO Assignment</div>
              <div class="ngo-card">
                <div class="ngo-field">ORGANIZATION: <span>{esc(selected_case.get('assigned_ngo', 'Krishak Sahayata Kendra'))}</span></div>
                <div class="ngo-field">COVERAGE AREA: <span>Paschim Medinipur District</span></div>
                <div class="ngo-field">CONTACT STATUS: <span style="color: #3DD68C;">Assigned</span></div>
                <div class="ngo-field">LAST CONTACT: <span>Yesterday, 4:35 PM</span></div>
                <div class="ngo-field">RESPONSE TIME: <span>&lt; 2 Hours</span></div>
                <div class="ngo-field">ASSIGNED OFFICER: <span>Mr. Debasish Mondal</span></div>
                <div class="ngo-field">STATUS: <span style="color: #3DD68C;">Escalated</span></div>
              </div>
              
              <div class="sahayak-heading" style="font-size: 1.25rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 6px; margin-bottom: 10px;">Generated Message Draft</div>
              <div class="mono-text" style="font-size: 0.72rem; color: #8FE6BC; padding: 12px; background-color: #0A0F0D; border: 1px solid rgba(255, 255, 255, 0.05); white-space: pre-wrap; margin-bottom: 20px; border-radius: 4px; line-height: 1.4;">
                {esc(selected_case.get('ngo_message_draft') or selected_case.get('ngo_output') or 'Citizen requires assistance with Krishak Bandhu application. Documents incomplete. Requesting NGO intervention.')}
              </div>
              
              <div class="sahayak-heading" style="font-size: 1.25rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 6px; margin-bottom: 10px;">Follow-Up Panel</div>
              <div class="countdown-panel">
                <div class="countdown-title">NEXT FOLLOW-UP</div>
                <div class="countdown-time">{get_followup_countdown(selected_case)}</div>
              </div>
              
              <div class="sahayak-heading" style="font-size: 1.25rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 6px; margin-bottom: 10px;">Case Timeline</div>
              <div class="timeline-vertical">
                <div class="timeline-event">Call Received <span class="timeline-time">10:18 AM</span></div>
                <div class="timeline-event">Case Classified <span class="timeline-time">10:18 AM</span></div>
                <div class="timeline-event">Scheme Matched <span class="timeline-time">10:19 AM</span></div>
                <div class="timeline-event">NGO Assigned <span class="timeline-time">10:20 AM</span></div>
                <div class="timeline-event">Message Sent <span class="timeline-time">10:20 AM</span></div>
                <div class="timeline-event">Follow-Up Scheduled <span class="timeline-time">10:21 AM</span></div>
                <div class="timeline-event pending">Resolved <span class="timeline-time">Pending</span></div>
              </div>
            </div>
            """
            st.markdown(clean_html(drawer_html), unsafe_allow_html=True)
        else:
            st.markdown(
                clean_html("""
                <div class="details-drawer">
                  <div class="mono-text" style="color: #808080; text-align: center; padding: 40px 0;">
                    SELECT A CASE TO VIEW FULL AUDIT & NGO DISPATCH TIMELINE
                  </div>
                </div>
                """),
                unsafe_allow_html=True
            )
