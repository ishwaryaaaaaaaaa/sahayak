"""
Sahayak — Streamlit demo interface.

Drives a turn-by-turn simulated call: the bot asks for name, location, and
the caller's situation one question at a time (Intake Manager, see
intake_manager.py), then runs the 5-agent CrewAI pipeline once intake is
complete, speaks a summary back, and (if configured) actually emails the
matched NGO. Also includes a simple NGO dashboard view.
"""
import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import intake_manager as im
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
    <b>Prototype note:</b> This demo simulates a phone call as a turn-by-turn voice
    conversation in the browser (a production version would use real telephony via
    Twilio/Exotel). NGO contacts and some scheme details are illustrative for this
    prototype. The intake conversation, the 5-agent reasoning pipeline, the spoken
    summary, and (when enabled) the NGO email are all fully functional with live
    LLM calls.
    </div>
    """,
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(["📞 Simulated Call", "🗂️ Case Log / NGO Dashboard", "ℹ️ How It Works"])


def play_audio(text: str, language: str, autoplay: bool = True):
    try:
        audio_bytes, mime_type = synthesize_speech(text, language=language)
        st.audio(audio_bytes, format=mime_type, autoplay=autoplay)
    except Exception as e:
        st.warning(f"Could not synthesize audio: {e}")


# ---------------- TAB 1: Simulated Call ----------------
with tab1:
    if "intake_state" not in st.session_state:
        st.subheader("Step 1 — Start the call")
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
            st.rerun()

    else:
        state = st.session_state["intake_state"]

        st.subheader("Step 1 — Caller intake")
        for turn in state.history:
            role = "assistant" if turn["role"] == "bot" else "user"
            with st.chat_message(role):
                st.write(turn["text"])

        if not state.complete:
            play_audio(state.current_question, state.language)

            audio_value = st.audio_input(
                "🎙️ Record your reply", key=f"intake_audio_{state.turn_count}"
            )
            typed_reply = st.text_input(
                "Or type the reply instead", key=f"intake_text_{state.turn_count}"
            )

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
                    st.session_state["intake_state"] = im.next_turn(state, caller_reply)
                st.rerun()

        else:
            st.success("Intake complete — running the 5-agent pipeline.")

            if "last_result" not in st.session_state:
                with st.spinner("Running 5-agent pipeline (Listener → Classifier → Scheme Matcher → NGO Coordinator → Follow-up)..."):
                    try:
                        result = run_case(
                            im.build_case_brief(state),
                            im.build_raw_narrative(state),
                            caller_name=state.name or "Unknown Caller",
                            caller_phone=st.session_state.get("caller_phone", "N/A"),
                            language=state.language,
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

                st.markdown("#### 🔊 Spoken summary to caller")
                st.markdown(
                    f'<div class="stage-box">{result["spoken_summary"]}</div>',
                    unsafe_allow_html=True,
                )
                play_audio(result["spoken_summary"], result.get("language", "en"))

                if result.get("email_sent"):
                    st.success("NGO escalation email sent successfully.")
                elif result.get("email_error"):
                    st.info(f"NGO email not sent ({result['email_error']}).")

                st.markdown("#### Pipeline stage detail")
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
                stage_box("5. Follow-up Plan (generated natively in caller's language)", result["followup_output"])
                play_audio(result["followup_output"], result.get("language", "en"), autoplay=False)

            if st.button("📞 Start New Call"):
                for key in ("intake_state", "last_result", "caller_phone"):
                    st.session_state.pop(key, None)
                st.rerun()

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
                email_status = "✅ sent" if c.get("email_sent") else f"draft only ({c.get('email_error', 'n/a')})"
                st.markdown(f"**NGO email:** {email_status}")
                st.markdown("**NGO escalation:**")
                st.text(c["ngo_output"])
                st.markdown("**Spoken summary:**")
                st.text(c.get("spoken_summary", ""))
                st.markdown("**Follow-up plan:**")
                st.text(c["followup_output"])

# ---------------- TAB 3: How It Works ----------------
with tab3:
    st.subheader("Architecture")
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

        **LLM backend:** OpenRouter (LLaMA 3.3 70B) for all reasoning and the Intake
        Manager's turn-by-turn extraction; Groq for speech-to-text (Whisper) and
        English speech-to-speech (Orpheus); Sarvam AI for Hindi speech-to-speech
        (falling back to gTTS if no Sarvam key is configured).

        **What's real vs. simulated in this prototype:**
        """
    )
    real_col, sim_col = st.columns(2)
    with real_col:
        st.markdown("**✅ Real**")
        st.markdown(
            "- Multi-turn intake conversation, driven by the LLM turn-by-turn\n"
            "- CrewAI multi-agent orchestration\n"
            "- Live LLM reasoning at every stage, natively in Hindi when selected\n"
            "- Scheme eligibility matching logic\n"
            "- Spoken summary generated and read back to the caller\n"
            "- NGO escalation email (when SEND_REAL_EMAILS=true)\n"
            "- Case logging and dashboard"
        )
    with sim_col:
        st.markdown("**🔶 Simulated for demo**")
        st.markdown(
            "- Phone telephony (browser mic stands in for a real phone call)\n"
            "- NGO contact directory (illustrative, fictional for Kharagpur district)\n"
            "- Multi-day follow-up calling (a follow-up plan is produced, not auto-dialed)\n"
            "- Hindi speech defaults to gTTS if no SARVAM_API_KEY is configured"
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
