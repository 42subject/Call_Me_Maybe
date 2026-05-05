from typing import Any

from pydantic import ValidationError

from ...validate_inputs import FunctionModel
from .output_model import OutputModel


def validate_output(
    output: dict[str, Any],
    prompt: str,
    functions_map: dict[str, FunctionModel],
) -> dict[str, Any]:
    """
    LLM出力のJSON構造を検証する。

    Args:
        output (dict[str, Any]): LLMが返したJSONオブジェクト。
        prompt (str): 元のユーザープロンプト。
        functions_map (dict[str, FunctionModel]): 互換性維持のために受け取る定義辞書。

    Raises:
        ValueError: 必須キー不足や型不一致の場合。

    Returns:
        dict[str, Any]: 保存用に整形した検証済みオブジェクト。
    """
    del functions_map
    try:
        validated_output = OutputModel(**output)
    except ValidationError as error:
        raise ValueError(error) from error

    return {
        "prompt": prompt,
        "fn_name": validated_output.fn_name,
        "args": validated_output.args,
    }
