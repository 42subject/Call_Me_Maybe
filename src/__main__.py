import sys
from pathlib import Path

from pydantic import BaseModel

from .paths import FUNCTIONS_DEFINITION, INPUT, OUTPUT
from .function_call_generator import QwenClient
from .json_io import JsonIO


class ArgvModel(BaseModel):
    functions_definition: Path
    input: Path
    output: Path

    @classmethod
    def parse_argv(cls, argv: list[str]) -> "ArgvModel":
        argc = len(argv)

        if argc == 1:
            parsed_default: ArgvModel = cls.model_validate({
                "functions_definition": FUNCTIONS_DEFINITION,
                "input": INPUT,
                "output": OUTPUT
            })
            return parsed_default
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

        parsed_args: ArgvModel = cls.model_validate(parsed_argv_dict)
        return parsed_args


def main() -> None:
    try:
        paths = ArgvModel.parse_argv(sys.argv)
    except ValueError as error:
        print(f"Error: {error}")
        return

    try:
        json_io = JsonIO(
            prompt_path=paths.input,
            functions_path=paths.functions_definition,
            output_path=paths.output,
        )
        prompts = json_io.load_prompts()
        functions = json_io.load_functions()
    except (
        ValueError,
        FileNotFoundError, IsADirectoryError, PermissionError
    ) as error:
        print(f"Error: {error}")
        return

    try:
        qwen_client = QwenClient("Qwen/Qwen3-0.6B", functions)
        response = qwen_client.generate(prompts)
    except ValueError as error:
        print(f"Error: {error}")
        return

    try:
        json_io.write_responses(response)
    except ValueError as error:
        print(f"Error: {error}")
        return

    return


if __name__ == "__main__":
    main()
