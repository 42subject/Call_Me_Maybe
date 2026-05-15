from math import inf

from llm_sdk import Small_LLM_Model
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from ..input_models import PromptModel, FunctionModel

from .response_model import ResponseModel
from .json_validator import JsonValidator
from .visualizer import Visualizer
from .abc import Tokenizer, LLMClient


class PromptBuilder(BaseModel):
    functions_text: str

    def __init__(self, functions: list[FunctionModel]) -> None:
        super().__init__(
            functions_text=self._build_functions_text(functions)
        )

    @staticmethod
    def _build_functions_text(functions: list[FunctionModel]) -> str:
        return "\n".join(function.model_dump_json() for function in functions)

    def build(
        self,
        prompts: list[PromptModel],
        feedbacks: list[str],
    ) -> str:
        prompts_text = "\n".join(
            f"{index}. {prompt.prompt}"
            for index, prompt in enumerate(prompts, start=1)
        )

        builded_prompt = (
            "You are a function calling assistant.\n"
            "Choose the best function for each user prompt "
            f"Available functions:\n{self.functions_text}\n\n"
            f"User prompts:\n{prompts_text}\n\n"
            # "You must return only valid json and chose "
            # "prompt, fn_name, args.\n"
            # "For each result, the value of prompt must repeat the exact "
            # "original user prompt text, not the function name.\n"
        )

        if feedbacks:
            feedback_text = "\n".join(
                f"{index}. {feedback}"
                for index, feedback in enumerate(feedbacks, start=1)
            )
            builded_prompt += (
                "Previous answers were invalid. "
                "Fix every issue listed below:\n"
                f"{feedback_text}\n"
                "Return only the corrected JSON answer.\n\n"
            )

        builded_prompt += "Answer:\n"
        return builded_prompt


class QwenTokenizer(Tokenizer):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: Small_LLM_Model

    def encode(self, text: str) -> list[int]:
        token_ids = self.model.encode(text)[0]
        return [int(token_id) for token_id in token_ids]

    def decode(self, token_ids: list[int]) -> str:
        text: str = self.model.decode(token_ids)
        return text


class QwenClient(LLMClient):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: Small_LLM_Model
    prompt_builder: PromptBuilder
    validator: JsonValidator
    tokenizer: QwenTokenizer
    visualizer: Visualizer

    def __init__(
        self,
        model_name: str,
        functions: list[FunctionModel],
    ) -> None:
        model = Small_LLM_Model(model_name)
        tokenizer = QwenTokenizer(model=model)
        BaseModel.__init__(
            self,
            model=model,
            prompt_builder=PromptBuilder(functions),
            validator=JsonValidator(),
            tokenizer=tokenizer,
            visualizer=Visualizer(tokenizer=tokenizer),
        )

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
    ) -> list[ResponseModel]:
        max_retries = 3
        adapter = TypeAdapter(list[ResponseModel])
        feedbacks: list[str] = []

        for retry in range(max_retries):
            self.validator.reset()
            prompt_text: str = self.prompt_builder.build(prompts, feedbacks)
            input_ids = self.tokenizer.encode(prompt_text)
            response_text = self._generate_response(input_ids)

            try:
                response_models: list[ResponseModel] = adapter.validate_json(
                    response_text
                )
                return response_models
            except ValidationError as error:
                print(
                    f"response validation failed. ({retry + 1}/{max_retries})"
                )
                feedback = str(error)
                if feedback not in feedbacks:
                    feedbacks.append(feedback)
                continue

        raise ValueError("failed to generate valid response")
