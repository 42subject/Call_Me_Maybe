from math import inf

from llm_sdk import Small_LLM_Model

from ..input_models import PromptModel, FunctionModel

from .response_model import ResponseModel
from .json_validator import JsonValidator
from .visualizer import Visualizer
from .abc import Tokenizer, LLMClient


class PromptBuilder:
    def __init__(self, functions: list[FunctionModel]) -> None:
        self.functions_text = self._build_functions_text(functions)

    def _build_functions_text(self, functions: list[FunctionModel]) -> str:
        return "\n".join(function.model_dump_json() for function in functions)

    def build(self, prompts: list[PromptModel]) -> str:
        prompts_text = "\n".join(
            f"{index}. {prompt.prompt}"
            for index, prompt in enumerate(prompts, start=1)
        )

        return (
            "You are a function calling assistant.\n"
            "Choose the best function for each user prompt "
            f"Available functions:\n{self.functions_text}\n\n"
            f"User prompts:\n{prompts_text}\n\n"
            "Return format:\n"
            "[\n"
            '  {"prompt": "<exact original prompt text>",\n'
            '"fn_name": "<function name>",\n"args": {...}},\n'
            '  {"prompt": "<exact original prompt text>",\n'
            '"fn_name": "<function name>",\n"args": {...}}\n'
            "]\n"
            "Answer:\n"
        )


class QwenTokenizer(Tokenizer):
    def __init__(self, model: Small_LLM_Model) -> None:
        self.model = model

    def encode(self, text: str) -> list[int]:
        token_ids = self.model.encode(text)[0]
        return [int(token_id) for token_id in token_ids]

    def decode(self, token_ids: list[int]) -> str:
        text: str = self.model.decode(token_ids)
        return text


class QwenClient(LLMClient):
    def __init__(
        self,
        model_name: str,
        functions: list[FunctionModel],
    ) -> None:
        self.model = Small_LLM_Model(model_name)
        self.prompt_builder = PromptBuilder(functions)
        self.validator = JsonValidator()
        self.tokenizer = QwenTokenizer(self.model)
        self.visualizer = Visualizer(self.tokenizer)

    def _select_valid_text_from_logits(
        self,
        logits: list[float],
    ) -> tuple[str, int]:
        next_token_id = max(
            range(len(logits)),
            key=lambda token_id: logits[token_id]
        )
        next_str = self.tokenizer.decode([next_token_id])
        self.visualizer.show_top_tokens(logits)
        while not self.validator.is_valid_string(next_str):
            self.visualizer.show_rejected_token(next_str)
            logits[next_token_id] = -inf
            next_token_id = max(
                range(len(logits)),
                key=lambda token_id: logits[token_id]
            )
            next_str = self.tokenizer.decode([next_token_id])
            self.visualizer.show_top_tokens(logits)
        return next_str, next_token_id

    def _generate_response(self, token_ids: list[int]) -> str:
        generated_text: str = ""

        for _ in range(1000):
            logits = self.model.get_logits_from_input_ids(token_ids)
            next_str, next_token_id = self._select_valid_text_from_logits(
                logits
            )
            token_ids.append(next_token_id)
            next_str = self.tokenizer.decode([next_token_id])
            generated_text += next_str
            self.visualizer.show_generated_text(generated_text)

            if self.validator.is_complete():
                break

        return generated_text

    def generate(
        self,
        prompts: list[PromptModel],
    ) -> list[ResponseModel] | str:
        prompt_text: str = self.prompt_builder.build(prompts)
        input_ids = self.tokenizer.encode(prompt_text)
        response_text = self._generate_response(input_ids)
        return response_text
