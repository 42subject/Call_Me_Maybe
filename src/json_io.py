import json
from pathlib import Path

from pydantic import BaseModel

from .function_call_generator import ResponseModel
from .input_models import FunctionModel, PromptModel


class JsonIO(BaseModel):
    prompt_path: Path
    functions_path: Path
    output_path: Path

    def _load_raw(self, json_path: Path) -> object:
        text = json_path.read_text(encoding="utf-8")
        loaded_json: object = json.loads(text)
        return loaded_json

    def load_prompts(self) -> list[PromptModel]:
        loaded_json = self._load_raw(self.prompt_path)
        if not isinstance(loaded_json, list):
            raise ValueError("prompt json must be a list")
        return [
            PromptModel.model_validate(item)
            for item in loaded_json
        ]

    def load_functions(self) -> list[FunctionModel]:
        loaded_json = self._load_raw(self.functions_path)
        if not isinstance(loaded_json, list):
            raise ValueError("function json must be a list")
        return [
            FunctionModel.model_validate(item)
            for item in loaded_json
        ]

    def write_responses(self, responses: list[ResponseModel]) -> None:
        output_text = json.dumps(
            [response.model_dump() for response in responses],
            ensure_ascii=False,
            indent=2,
        )
        self.output_path.write_text(output_text, encoding="utf-8")
