from abc import ABC, abstractmethod

from llm_sdk import Small_LLM_Model

from ..input_models import PromptModel, FunctionModel

from .response_model import ResponseModel


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
            "Choose the best function for each user prompt and return only JSON.\n\n"
            f"Available functions:\n{self.functions_text}\n\n"
            f"User prompts:\n{prompts_text}\n\n"
            "Return format:\n"
            "[\n"
            '  {"prompt": "...", "fn_name": "...", "args": {...}},\n'
            '  {"prompt": "...", "fn_name": "...", "args": {...}}\n'
            "]"
        )


class Tokenizer(ABC):
    @abstractmethod
    def encode(self, text: str) -> list[int]:
        pass

    @abstractmethod
    def decode(self, token_ids: list[int]) -> str:
        pass


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompts: list[PromptModel]) -> list[ResponseModel] | str:
        pass


class QwenTokenizer(Tokenizer):
    def __init__(self, model: Small_LLM_Model) -> None:
        self.model = model
    
    def encode(self, text: str) -> list[int]:
        token_ids = self.model.encode(text)[0]
        return [int(token_id) for token_id in token_ids]
    
    def decode(self, token_ids: list[int]) -> str:
        text = self.model.decode(token_ids)
        return text

class QwenClient(LLMClient):
    def __init__(self, model_name: str, functions: list[FunctionModel]) -> None:
        self.model = Small_LLM_Model(model_name)
        self.prompt_builder = PromptBuilder(functions)
        self.tokenizer = QwenTokenizer(self.model)
    
    def _generate_response(self, token_ids: list[int]) -> str:
        generated_text: str = ""

        for _ in range(1000):
            logits = self.model.get_logits_from_input_ids(token_ids)
            next_token_id = max(
                range(len(logits)),
                key=lambda token_id: logits[token_id]
            )
            token_ids.append(next_token_id)
            next_str = self.model.decode([next_token_id])
            generated_text += next_str
            print(next_str, end="", flush=True)
            
            if "]" in next_str:
                break
        
        return generated_text

    def generate(self, prompts: list[PromptModel]) -> list[ResponseModel] | str:
        prompt_text: str = self.prompt_builder.build(prompts)
        input_ids = self.tokenizer.encode(prompt_text)
        response_text = self._generate_response(input_ids)
        return response_text

        