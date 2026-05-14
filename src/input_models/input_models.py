from pydantic import BaseModel, model_validator

from enum import Enum
from typing import Optional


class PromptModel(BaseModel):
    prompt: str


class ParameterType(str, Enum):
    STR = "string"
    NUMBER = "number"
    OBJECT = "object"
    ARRAY = "array"


class FunctionParametersModel(BaseModel):
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
    name: str
    description: str
    parameters: dict[str, FunctionParametersModel]
    returns: FunctionParametersModel
