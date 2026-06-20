"""
Voice I/O for Sahayak.

Speech-to-text: Groq Whisper (multilingual — same model handles English and
Hindi, we just pass the right ISO-639-1 language hint).

Speech-to-speech is split because Groq's hosted TTS only ships English/Arabic
voices: English output uses Groq's Orpheus TTS; Hindi output falls back to
gTTS (Google Text-to-Speech), since there is no Groq Hindi voice yet.
"""
import os
import sys
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from groq import Groq

from config.settings import (
    GROQ_API_KEY,
    GROQ_WHISPER_MODEL,
    GROQ_TTS_MODEL,
    GROQ_TTS_VOICE,
)

_client = Groq(api_key=GROQ_API_KEY)


def transcribe_audio(audio_bytes: bytes, language: str | None = None) -> str:
    """
    Transcribes audio (wav/mp3/m4a/webm/etc.) via Groq Whisper.

    `language` should be an ISO-639-1 code (e.g. "hi" for Hindi). Pass None
    to let Whisper auto-detect (used for the English toggle).
    """
    kwargs = {
        "model": GROQ_WHISPER_MODEL,
        "file": ("audio.wav", audio_bytes),
    }
    if language:
        kwargs["language"] = language

    transcript = _client.audio.transcriptions.create(**kwargs)
    return transcript.text


def synthesize_speech(text: str, language: str = "en") -> bytes:
    """
    Returns audio bytes for `text`.

    language="en" -> Groq Orpheus TTS (wav bytes).
    language="hi" -> gTTS (mp3 bytes), since Groq has no Hindi voice.
    """
    if language == "hi":
        from gtts import gTTS

        buf = BytesIO()
        gTTS(text=text, lang="hi").write_to_fp(buf)
        return buf.getvalue()

    response = _client.audio.speech.create(
        model=GROQ_TTS_MODEL,
        voice=GROQ_TTS_VOICE,
        input=text,
        response_format="wav",
    )
    return response.read()
