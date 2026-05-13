import sys
from pathlib import Path

from pydantic import BaseModel

from .paths import FUNCTIONS_DEFINITION, INPUT, OUTPUT
from .input_models import PromptLoader, FunctionLoader
from .function_call_generator import QwenClient


class ArgvModel(BaseModel):
    functions_definition: Path
    input: Path
    output: Path

    @classmethod
    def parse_argv(cls, argv: list[str]) -> "ArgvModel":
        argc = len(argv)

        if argc == 1:
            return cls.model_validate({
                "functions_definition": FUNCTIONS_DEFINITION,
                "input": INPUT,
                "output": OUTPUT
            })
        if argc == 7:
            parsed_argv_dict: dict[str, str] = {}
            for key, value in zip(argv[1::2], argv[2::2]):
                if not key.startswith("--"):
                    raise ValueError("argv must be starts with \"--\"")
                removed_prefix_key = key.removeprefix("--")
                if removed_prefix_key in parsed_argv_dict:
                    raise ValueError(f"duplicate argv \"{key}\"")
                parsed_argv_dict[removed_prefix_key] = value
        else:
            raise ValueError("Invalid argv")

        return cls.model_validate(parsed_argv_dict)


def main():
    try:
        paths = ArgvModel.parse_argv(sys.argv)
    except ValueError as error:
        print(f"Error: {error}")
        return
    
    try:
        prompts = PromptLoader(json_path=paths.input)
        prompts = prompts.load()
        functions = FunctionLoader(json_path=paths.functions_definition)
        functions = functions.load()
    except (
        ValueError, 
        FileNotFoundError, IsADirectoryError, PermissionError
    ) as error:
        print(f"Error: {error}")
        return
    
    try:
        qwen_client = QwenClient("Qwen/Qwen3-0.6B", functions)
        response = qwen_client.generate(prompts)
        print(response)
    except ValueError as error:
        print(f"Error: {error}")
        return


if __name__ == "__main__":
    main()