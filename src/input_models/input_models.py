from pydantic import BaseModel, model_validator, ConfigDict

from enum import Enum
from typing import Optional


class PromptModel(BaseModel):
    """
    入力プロンプトを表す
    """

    model_config = ConfigDict(extra="forbid")

    prompt: str


class ParameterType(str, Enum):
    """
    関数パラメータで利用できる型を表す
    """

    STR = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"


class FunctionParametersModel(BaseModel):
    """
    関数の引数または戻り値の型定義を表す
    """

    model_config = ConfigDict(extra="forbid")

    type: ParameterType
    properties: Optional[dict[str, "FunctionParametersModel"]] = None
    items: Optional["FunctionParametersModel"] = None

    @model_validator(mode="after")
    def validate_nested_schema(self) -> "FunctionParametersModel":
        """
        typeが配列などの場合に、正しく変数を持っているかどうかをバリデートする

        Raises:
            ValueError: オブジェクトだがプロパティがない時
            ValueError: 配列だがアイテムがない時
            ValueError: オブジェクトではないのにプロパティがある時
            ValueError: 配列ではないのにアイテムがある時

        Returns:
            FunctionParametersModel: self
        """
        if self.type == ParameterType.OBJECT and self.properties is None:
            raise ValueError("object type requires properties")

        if self.type == ParameterType.ARRAY and self.items is None:
            raise ValueError("array type requires items")

        if self.type != ParameterType.OBJECT and self.properties is not None:
            raise ValueError("properties is only allowed for object type")

        if self.type != ParameterType.ARRAY and self.items is not None:
            raise ValueError("items is only allowed for array type")

        return self


class FunctionModel(BaseModel):
    """
    LLMが呼び出し候補として利用する関数定義を表す
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    parameters: dict[str, FunctionParametersModel]
    returns: FunctionParametersModel
