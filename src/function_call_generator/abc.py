from abc import ABC, abstractmethod

from ..input_models import PromptModel

from .response_model import ResponseModel


class Tokenizer(ABC):
    @abstractmethod
    def encode(self, text: str) -> list[int]:
        pass

    @abstractmethod
    def decode(self, token_ids: list[int]) -> str:
        pass


class LLMClient(ABC):
    @abstractmethod
    def generate(
        self,
        prompts: list[PromptModel],
    ) -> list[ResponseModel] | str:
        pass
