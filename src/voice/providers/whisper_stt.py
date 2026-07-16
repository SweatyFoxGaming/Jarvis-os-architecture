import os
import tempfile
import logging
import whisper

from src.voice.base import STTProvider

logger = logging.getLogger(__name__)


class WhisperSTT(STTProvider):
    def __init__(self, model_name: str = "tiny"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            logger.info(f"[WhisperSTT] Loading model '{self.model_name}'...")
            self._model = whisper.load_model(self.model_name)
            logger.info("[WhisperSTT] Model loaded.")
        return self._model

    def transcribe(self, audio_data: bytes, **kwargs) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        try:
            result = self.model.transcribe(tmp_path)
            return result["text"].strip()
        finally:
            os.unlink(tmp_path)

    def get_supported_formats(self) -> list[str]:
        return ["audio/webm", "audio/wav", "audio/mpeg", "audio/mp4", "audio/flac", "audio/ogg"]
