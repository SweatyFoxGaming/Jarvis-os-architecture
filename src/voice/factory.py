import os
from src.voice.base import STTProvider, TTSProvider
from src.voice.providers.whisper_stt import WhisperSTT
from src.voice.providers.edge_tts import EdgeTTS


class VoiceFactory:
    @staticmethod
    def create_stt(provider: str = "whisper", **kwargs) -> STTProvider:
        if provider == "whisper":
            model_name = kwargs.get("model_name", os.getenv("WHISPER_MODEL", "tiny"))
            return WhisperSTT(model_name=model_name)
        raise ValueError(f"Unsupported STT provider: {provider}")

    @staticmethod
    def create_tts(provider: str = "edge_tts", **kwargs) -> TTSProvider:
        if provider == "edge_tts":
            tts_url = kwargs.get("tts_url", os.getenv("TTS_URL", "http://localhost:5051/v1/audio/speech"))
            api_key = kwargs.get("api_key", os.getenv("TTS_API_KEY", "your_tts_key"))
            default_voice = kwargs.get("default_voice", os.getenv("TTS_DEFAULT_VOICE", "alloy"))
            return EdgeTTS(tts_url=tts_url, api_key=api_key, default_voice=default_voice)
        raise ValueError(f"Unsupported TTS provider: {provider}")
