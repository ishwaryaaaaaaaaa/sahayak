"""
Voice I/O for Sahayak.

Speech-to-text: Groq Whisper (multilingual — same model handles English and
Hindi, we just pass the right ISO-639-1 language hint).

Speech-to-speech is split because Groq's hosted TTS only ships English/Arabic
voices: English output uses Groq's Orpheus TTS; Hindi output uses Sarvam AI
(a TTS provider purpose-built for Indian languages), falling back to gTTS
(Google Text-to-Speech) if no Sarvam key is configured or the Sarvam call
fails, so Hindi speech never breaks even without a Sarvam account.
"""
import base64
import logging
import os
import sys
from io import BytesIO

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from groq import Groq

from config.settings import (
    GROQ_API_KEY,
    GROQ_WHISPER_MODEL,
    GROQ_TTS_MODEL,
    GROQ_TTS_VOICE,
    SARVAM_API_KEY,
    SARVAM_TTS_MODEL,
    SARVAM_TTS_SPEAKER,
)

_client = Groq(api_key=GROQ_API_KEY)
logger = logging.getLogger("sahayak.voice")

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


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


def _synthesize_hindi_sarvam(text: str) -> bytes:
    """Raises on any failure - caller is responsible for falling back to gTTS."""
    response = requests.post(
        SARVAM_TTS_URL,
        headers={"api-subscription-key": SARVAM_API_KEY},
        json={
            "text": text,
            "target_language_code": "hi-IN",
            "speaker": SARVAM_TTS_SPEAKER,
            "model": SARVAM_TTS_MODEL,
        },
        timeout=15,
    )
    response.raise_for_status()
    audio_b64 = response.json()["audios"][0]
    return base64.b64decode(audio_b64)


def _synthesize_hindi_gtts(text: str) -> bytes:
    from gtts import gTTS

    buf = BytesIO()
    gTTS(text=text, lang="hi").write_to_fp(buf)
    return buf.getvalue()


def synthesize_speech(text: str, language: str = "en") -> tuple[bytes, str]:
    """
    Returns (audio_bytes, mime_type) for `text`.

    language="en" -> Groq Orpheus TTS (wav).
    language="hi" -> Sarvam AI (wav) if SARVAM_API_KEY is set, since Groq has
    no Hindi voice; falls back to gTTS (mp3) if no key is configured or the
    Sarvam call fails, so Hindi speech is never blocked on having a Sarvam
    account.
    """
    if language == "hi":
        if SARVAM_API_KEY:
            try:
                return _synthesize_hindi_sarvam(text), "audio/wav"
            except Exception as e:
                logger.warning(f"Sarvam TTS failed, falling back to gTTS: {e}")
        return _synthesize_hindi_gtts(text), "audio/mp3"

    response = _client.audio.speech.create(
        model=GROQ_TTS_MODEL,
        voice=GROQ_TTS_VOICE,
        input=text,
        response_format="wav",
    )
    return response.read(), "audio/wav"
