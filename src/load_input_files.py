import json
from typing import Any

from .validate_inputs import (
    validate_functions, FunctionModel, validate_prompts, PromptModel
)


def load_json(file_path: str) -> Any:
    """
    指定パスのJSONファイルを読み込み、Pythonオブジェクトとして返す。

    Args:
        file_path (str): 読み込み対象のJSONファイルパス。

    Raises:
        FileNotFoundError: 指定ファイルが存在しない場合。
        JSONDecodeError: ファイル内容がJSONとして不正な場合。

    Returns:
        Any: 読み込んだJSONをPythonオブジェクトへ変換した結果。
    """
    with open(file_path, encoding="utf-8") as file:
        json_data = json.load(file)
    return json_data


def load_prompt_file(file_path: str) -> list[PromptModel]:
    """
    プロンプト定義JSONを読み込み、PromptModel配列に変換する。

    Args:
        file_path (str): プロンプト定義JSONファイルパス。

    Raises:
        ValidationError: プロンプト形式がモデル定義に一致しない場合。

    Returns:
        list[PromptModel]: 検証済みのプロンプトモデル配列。
    """
    prompts = load_json(file_path)
    prompt_model_list: list[PromptModel] = validate_prompts(prompts)
    return prompt_model_list


def load_function_file(file_path: str) -> list[FunctionModel]:
    """
    関数定義JSONを読み込み、FunctionModel配列に変換する。

    Args:
        file_path (str): 関数定義JSONファイルパス。

    Raises:
        ValidationError: 関数定義形式がモデル定義に一致しない場合。

    Returns:
        list[FunctionModel]: 検証済みの関数モデル配列。
    """
    functions: list[dict[str, Any]] = load_json(file_path)
    function_model_list: list[FunctionModel] = validate_functions(functions)
    return function_model_list
