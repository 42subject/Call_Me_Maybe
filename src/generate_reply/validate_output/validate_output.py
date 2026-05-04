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
    LLM出力のJSON構造とパラメータ型を関数定義に照らして検証する。

    Args:
        output (dict[str, Any]): LLMが返したJSONオブジェクト。
        prompt (str): 元のユーザープロンプト。
        functions_map (dict[str, FunctionModel]): 関数名をキーにした定義辞書。

    Raises:
        ValueError: 必須キー不足、関数名不正、引数キー不一致、型不一致の場合。

    Returns:
        dict[str, Any]: 保存用に整形した検証済みオブジェクト。
    """
    try:
        validated_output = OutputModel(
            **output,
            functions_map=functions_map,
        )
    except ValidationError as error:
        raise ValueError(error) from error

    return {
        "prompt": prompt,
        "name": validated_output.name,
        "parameters": validated_output.parameters,
    }
