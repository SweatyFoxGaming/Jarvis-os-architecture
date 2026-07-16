import os
import logging
from typing import Optional

import requests

from src.voice.base import TTSProvider

logger = logging.getLogger(__name__)


class EdgeTTS(TTSProvider):
    def __init__(
        self,
        tts_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_voice: str = "alloy"
    ):
        self.tts_url = tts_url or os.getenv("TTS_URL", "http://localhost:5051/v1/audio/speech")
        self.api_key = api_key or os.getenv("TTS_API_KEY", "your_tts_key")
        self.default_voice = default_voice
        self._voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    def synthesize(self, text: str, voice: Optional[str] = None, **kwargs) -> bytes:
        voice = voice or self.default_voice
        response_format = kwargs.get("response_format", "mp3")
        speed = kwargs.get("speed", 1.0)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "input": text,
            "voice": voice,
            "response_format": response_format,
            "speed": speed,
        }

        resp = requests.post(self.tts_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content

    def get_voices(self) -> list[str]:
        return self._voices

    def get_default_voice(self) -> str:
        return self.default_voice
