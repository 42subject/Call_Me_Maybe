from typing import Any

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from ...validate_inputs import FunctionModel


class OutputModel(BaseModel):
    """
    LLMが返す関数呼び出しJSONの基本構造を表すモデル。

    Args:
        name (str): 呼び出す関数名。
        parameters (dict[str, Any]): 関数に渡す引数辞書。
        functions_map (dict[str, FunctionModel]): 関数定義の辞書。
    """

    name: str = Field(...)
    parameters: dict[str, Any] = Field(...)
    functions_map: dict[str, FunctionModel] = Field(
        ...,
        repr=False,
        exclude=True,
    )

    @model_validator(mode="after")
    def validate_with_function_spec(self) -> "OutputModel":
        """
        関数定義に基づいて関数名・引数キー・引数型を検証する。

        Raises:
            ValueError: 関数名不正、引数キー不一致、型不一致の場合。

        Returns:
            OutputModel: 検証済みの自身。
        """
        function_spec = self.functions_map.get(self.name)
        if not isinstance(function_spec, FunctionModel):
            raise ValueError(f"Unknown function name: {self.name}")

        expected_params = function_spec.parameters
        if set(self.parameters.keys()) != set(expected_params.keys()):
            raise ValueError(
                "parameters keys do not match function definition"
            )

        for key, expected in expected_params.items():
            value = self.parameters[key]
            expected_type = expected.type.value
            if expected_type == "number":
                if (
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                ):
                    raise ValueError(f"parameter '{key}' must be a number")
            elif expected_type == "string":
                if not isinstance(value, str):
                    raise ValueError(f"parameter '{key}' must be a string")
            else:
                raise ValueError(
                    f"unsupported parameter type: {expected_type}"
                )
        return self
