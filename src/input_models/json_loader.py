from pydantic import BaseModel

from abc import ABC, abstractmethod
from pathlib import Path
import json
from typing import Any

from .input_models import PromptModel, FunctionModel


class JsonLoader(BaseModel, ABC):
    json_path: Path

    def load_raw(self) -> Any:
        text = self.json_path.read_text(encoding="utf-8")
        return json.loads(text)
    
    @abstractmethod
    def load(self) -> Any:
        pass


class PromptLoader(JsonLoader):
    def load(self) -> list[PromptModel]:
        json = self.load_raw()
        return [PromptModel.model_validate(item) for item in json]


class FunctionLoader(JsonLoader):
    def load(self) -> list[FunctionModel]:
        json = self.load_raw()
        return [FunctionModel.model_validate(item) for item in json]
