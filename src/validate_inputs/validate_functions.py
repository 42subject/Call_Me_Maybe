from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ParameterType(str, Enum):
    """
    関数パラメータとして許可される型名を表す列挙型。
    """

    number = "number"
    string = "string"


class ParameterModel(BaseModel):
    """
    関数パラメータまたは戻り値の型定義を表すモデル。

    Args:
        type (ParameterType): パラメータまたは戻り値の型。
    """

    type: ParameterType = Field(...)


class FunctionModel(BaseModel):
    """
    LLMが選択できる関数定義1件分のJSON構造を表すモデル。

    Args:
        name (str): 関数名。
        description (str): 関数の説明文。
        parameters (dict[str, ParameterModel]): 引数名と型定義の辞書。
        returns (ParameterModel): 戻り値の型定義。
    """

    name: str = Field(...)
    description: str = Field(...)
    parameters: dict[str, ParameterModel] = Field(...)
    returns: ParameterModel = Field(...)


def validate_functions(
    functions: list[dict[str, Any]]
) -> list[FunctionModel]:
    """
    関数定義の辞書配列をFunctionModel配列へ変換して検証する。

    Args:
        functions (list[dict[str, Any]]):
            読み込み済みの関数定義辞書配列。

    Raises:
        pydantic.ValidationError: 関数定義の必須項目不足や型不一致がある場合。

    Returns:
        list[FunctionModel]: 検証済みの関数モデル配列。
    """
    functions_models = [
        FunctionModel(**function_dict)
        for function_dict in functions
    ]
    return functions_models
