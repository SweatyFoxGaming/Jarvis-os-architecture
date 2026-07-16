from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_data: bytes, **kwargs) -> str:
        pass

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        pass


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: Optional[str] = None, **kwargs) -> bytes:
        pass

    @abstractmethod
    def get_voices(self) -> list[str]:
        pass

    @abstractmethod
    def get_default_voice(self) -> str:
        pass
