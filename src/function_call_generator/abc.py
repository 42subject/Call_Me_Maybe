from abc import ABC, abstractmethod

from pydantic import BaseModel

from ..input_models import PromptModel

from .response_model import ResponseModel


class Tokenizer(BaseModel, ABC):
    @abstractmethod
    def encode(self, text: str) -> list[int]:
        pass

    @abstractmethod
    def decode(self, token_ids: list[int]) -> str:
        pass


class LLMClient(BaseModel, ABC):
    @abstractmethod
    def generate(
        self,
        prompts: list[PromptModel],
    ) -> list[ResponseModel] | str:
        pass
