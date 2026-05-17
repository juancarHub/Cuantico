from abc import ABC, abstractmethod


class BaseSTT(ABC):
    name = "base"

    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        """Transcribe un fichero WAV y devuelve texto."""
        raise NotImplementedError
