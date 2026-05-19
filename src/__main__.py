import sys
from json import JSONDecodeError
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from .paths import FUNCTIONS_DEFINITION, INPUT, OUTPUT
from .function_call_generator import QwenClient
from .json_io import JsonIO


class ArgvModel(BaseModel):
    """
    コマンドライン引数から受け取る入出力ファイルのパスを表す
    """

    model_config = ConfigDict(extra="forbid")

    functions_definition: Path
    input: Path
    output: Path

    @classmethod
    def parse_argv(cls, argv: list[str]) -> "ArgvModel":
        """
        コマンドライン引数を解析してArgvModelに変換する

        Args:
            argv: コマンドライン引数

        Raises:
            ValueError: 引数の数や形式が不正な時
            ValueError: 同じ引数が複数指定された時

        Returns:
            ArgvModel: 解析されたコマンドライン引数
        """
        if len(argv) % 2 == 0:
            raise ValueError("Invalid argv")

        parsed_argv_dict: dict[str, str | Path] = {
            "functions_definition": FUNCTIONS_DEFINITION,
            "input": INPUT,
            "output": OUTPUT,
        }
        specified_keys: set[str] = set()
        for key, value in zip(argv[1::2], argv[2::2]):
            if not key.startswith("--"):
                raise ValueError("argv must be starts with \"--\"")
            removed_prefix_key = key.removeprefix("--")
            if removed_prefix_key in specified_keys:
                raise ValueError(f"duplicate argv \"{key}\"")
            specified_keys.add(removed_prefix_key)
            parsed_argv_dict[removed_prefix_key] = value

        parsed_args: ArgvModel = cls.model_validate(parsed_argv_dict)
        return parsed_args


def main() -> None:
    try:
        paths = ArgvModel.parse_argv(sys.argv)
    except (ValueError, ValidationError) as error:
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
        FileNotFoundError, IsADirectoryError, PermissionError,
        JSONDecodeError,
        UnicodeDecodeError,
        ValidationError,
        ValueError,
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
    except (
        FileExistsError,
        IsADirectoryError,
        PermissionError,
        TypeError,
        UnicodeEncodeError,
        ValueError,
    ) as error:
        print(f"Error: {error}")
        return

    print("Generation succeeded.")
    print("Result:")
    print(response)

    return


if __name__ == "__main__":
    main()
