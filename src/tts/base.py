from abc import ABC, abstractmethod


class BaseTTS(ABC):
    name = "base"

    @abstractmethod
    def generate_to_file(self, text: str) -> str:
        """Genera audio y devuelve ruta a fichero temporal."""
        raise NotImplementedError
