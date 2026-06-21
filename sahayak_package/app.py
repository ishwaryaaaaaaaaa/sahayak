"""
Sahayak — Streamlit demo interface.

Simulates the voice call as a text input (clearly labeled as such), runs the
5-agent CrewAI pipeline, and displays each stage's output plus the final
escalation + follow-up plan. Also includes a simple NGO dashboard view.
"""
import os
import sys
import time
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools_data import load_cases, load_schemes, load_ngos
from crew_runner import run_case
from voice_tools import transcribe_audio, synthesize_speech

st.set_page_config(
    page_title="Sahayak — Rural Health & Finance Helpline Agent",
    page_icon="🤝",
    layout="wide",
)

# ---------- Minimal custom styling ----------
st.markdown(
    """
    <style>
    .stApp { background-color: #FAF7F2; }
    .sahayak-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A34;
        margin-bottom: 0;
    }
    .sahayak-sub {
        color: #5C6B66;
        font-size: 1.05rem;
        margin-top: 0.2rem;
    }
    .stage-box {
        background: #FFFFFF;
        border: 1px solid #E3DDD2;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .stage-label {
        font-weight: 600;
        color: #B5582E;
        text-transform: uppercase;
        font-size: 0.78rem;
        letter-spacing: 0.04em;
    }
    .disclaimer-box {
        background: #FFF4E5;
        border-left: 4px solid #D98C2B;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 0.88rem;
        color: #6B4A1E;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="sahayak-header">🤝 Sahayak</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sahayak-sub">A multi-agent helpline assistant connecting rural callers '
    'to government health &amp; finance schemes and local NGOs.</p>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="disclaimer-box">
    <b>Prototype note:</b> This demo simulates a voice call as text input (a production
    version would use real speech-to-text/text-to-speech in regional languages via
    Twilio/Exotel). NGO contacts and some scheme details are illustrative for this
    prototype. The 5-agent reasoning pipeline itself is fully functional and uses
    live LLM calls via Groq.
    </div>
    """,
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(["📞 Simulated Call", "🗂️ Case Log / NGO Dashboard", "ℹ️ How It Works"])

# ---------------- TAB 1: Simulated Call ----------------
with tab1:
    st.subheader("Step 1 — Caller describes their situation")
    st.caption(
        "Record real voice input below (transcribed live via Groq Whisper), or "
        "type the caller's situation directly."
    )

    lang_choice = st.radio(
        "Language / भाषा",
        ["English", "हिंदी (Hindi)"],
        horizontal=True,
    )
    language = "hi" if lang_choice.startswith("हिंदी") else "en"

    col1, col2 = st.columns(2)
    with col1:
        caller_name = st.text_input("Caller name (optional)", value="Ramesh")
    with col2:
        caller_phone = st.text_input("Caller phone (optional)", value="+91-98XXXXXXXX")

    audio_value = st.audio_input(
        "🎙️ Record the caller's situation (real voice input via Groq Whisper)"
    )

    example = (
        "I am Ramesh, a farmer in a village near Kharagpur. My wife is seven months "
        "pregnant and we don't have much money saved. I don't know what help we can "
        "get for the delivery or what schemes we might be eligible for. I also lost "
        "some crop this season due to rain."
    )

    if audio_value is not None:
        with st.spinner("Transcribing with Groq Whisper..."):
            try:
                whisper_language = "hi" if language == "hi" else None
                transcribed = transcribe_audio(audio_value.getvalue(), language=whisper_language)
                st.session_state["transcribed_text"] = transcribed
            except Exception as e:
                st.error(f"Transcription failed: {e}")

    raw_text = st.text_area(
        "Caller's situation (transcript — edit if needed)",
        value=st.session_state.get("transcribed_text", example),
        height=120,
    )

    run_btn = st.button("▶️ Run Sahayak Agent Pipeline", type="primary")

    HOLD_MESSAGE_HI = (
        "नमस्ते! कृपया थोड़ा रुकें, मैं आपकी बात समझ रहा हूं और सही मदद ढूंढ रहा हूं। "
        "कृपया लाइन पर बने रहें।"
    )

    if run_btn:
        if not raw_text.strip():
            st.warning("Please enter the caller's situation first.")
        else:
            if language == "hi":
                # Spoken/shown the instant the call is submitted, before the
                # 5-agent pipeline (10-20s) even starts, so the caller hears
                # something in Hindi right away instead of dead air.
                st.info(f"🤝 Sahayak: {HOLD_MESSAGE_HI}")
                try:
                    hold_audio = synthesize_speech(HOLD_MESSAGE_HI, language="hi")
                    st.audio(hold_audio, format="audio/mp3", autoplay=True)
                except Exception:
                    pass  # hold message is a nice-to-have; never block the call on it

            with st.spinner("Running 5-agent pipeline (Listener → Classifier → Scheme Matcher → NGO Coordinator → Follow-up)..."):
                try:
                    result = run_case(
                        raw_text,
                        caller_name=caller_name,
                        caller_phone=caller_phone,
                        language=language,
                    )
                    st.session_state["last_result"] = result
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")
                    result = None

    if "last_result" in st.session_state:
        result = st.session_state["last_result"]
        st.success(f"Case {result['case_id']} processed successfully.")

        def stage_box(label, english_text, hindi_text=None):
            shown = hindi_text if hindi_text else english_text
            st.markdown(
                f'<div class="stage-box"><span class="stage-label">{label}</span><br>'
                + shown.replace("\n", "<br>") + '</div>',
                unsafe_allow_html=True,
            )
            if hindi_text:
                with st.expander("Show English"):
                    st.write(english_text)

        stage_box(
            "1. Listener — structured intake",
            result["listener_output"],
            result.get("listener_output_hi"),
        )
        stage_box("2. Classifier — domain &amp; urgency", result["classifier_output"])
        stage_box(
            "3. Knowledge Matcher — matched schemes",
            result["matcher_output"],
            result.get("matcher_output_hi"),
        )
        stage_box("4. NGO Coordinator — escalation", result["ngo_output"])
        stage_box(
            "5. Follow-up Plan",
            result["followup_output"],
            result.get("followup_output_hi"),
        )

        followup_text = result.get("followup_output_hi") or result["followup_output"]
        with st.spinner("Synthesizing follow-up message audio..."):
            try:
                audio_bytes = synthesize_speech(followup_text, language=result.get("language", "en"))
                audio_format = "audio/mp3" if result.get("language") == "hi" else "audio/wav"
                st.audio(audio_bytes, format=audio_format)
            except Exception as e:
                st.warning(f"Could not synthesize follow-up audio: {e}")

# ---------------- TAB 2: Case Log / NGO Dashboard ----------------
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
                st.markdown("**Follow-up plan:**")
                st.text(c["followup_output"])

# ---------------- TAB 3: How It Works ----------------
with tab3:
    st.subheader("Architecture")
    st.markdown(
        """
        **Five agents, each with one job, run sequentially via CrewAI:**

        1. **Listener** — turns the raw (simulated voice) transcript into a structured summary
        2. **Classifier** — tags the case as health / finance / both, and sets urgency
        3. **Knowledge Matcher** — checks the case against a database of government schemes
        4. **NGO Coordinator** — picks the right local NGO and drafts an escalation message
        5. **Follow-up Coordinator** — generates a check-in message and a follow-up schedule

        **LLM backend:** Groq (LLaMA 3.3 70B) — fast, low-cost inference suited to a
        helpline-scale workload.

        **What's real vs. simulated in this prototype:**
        """
    )
    real_col, sim_col = st.columns(2)
    with real_col:
        st.markdown("**✅ Real**")
        st.markdown(
            "- CrewAI multi-agent orchestration\n"
            "- Live LLM reasoning at every stage\n"
            "- Scheme eligibility matching logic\n"
            "- NGO escalation message generation\n"
            "- Case logging and dashboard"
        )
    with sim_col:
        st.markdown("**🔶 Simulated for demo**")
        st.markdown(
            "- Voice input (text box stands in for transcribed speech)\n"
            "- NGO contact directory (illustrative, fictional for Kharagpur district)\n"
            "- Actual SMS/call dispatch (logged, not sent)\n"
            "- Multi-day follow-up calling (single-shot in this demo)"
        )

    st.subheader("Data this prototype runs on")
    schemes = load_schemes()
    ngos = load_ngos()
    st.markdown(f"**{len(schemes)} government schemes** (health + finance, real central schemes + WB state schemes)")
    st.dataframe(
        [{"ID": s["id"], "Name": s["name"], "Category": s["category"]} for s in schemes],
        use_container_width=True,
        hide_index=True,
    )
    st.markdown(f"**{len(ngos)} NGOs** (fictional, illustrative for Kharagpur district demo)")
    st.dataframe(
        [{"ID": n["id"], "Name": n["name"], "Focus": ", ".join(n["focus"])} for n in ngos],
        use_container_width=True,
        hide_index=True,
    )
