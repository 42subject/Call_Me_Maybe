from enum import Enum

from pydantic import BaseModel, Field


class ParameterType(str, Enum):
    number = "number"
    string = "string"


class ParameterModel(BaseModel):
    type: ParameterType = Field(...)


class FunctionModel(BaseModel):
    name: str = Field(...)
    description: str = Field(...)
    parameters: dict[str, ParameterModel] = Field(...)
    returns: ParameterModel = Field(...)


def validate_functions(
    functions: list[dict[str, str | dict[str, dict[str, str]]]]
) -> list[FunctionModel]:
    """
    関数定義の辞書配列をFunctionModel配列へ変換して検証する。

    Args:
        functions (list[dict[str, str | dict[str, dict[str, str]]]]):
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
