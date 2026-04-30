from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def analyse(self, formatted_transcript: str) -> dict:
        pass