from typing import Any

from pydantic import (
    BaseModel,
    Field,
)


class OutputModel(BaseModel):
    """
    LLMが返す関数呼び出しJSONの基本構造を表すモデル。

    Args:
        fn_name (str): 呼び出す関数名。
        args (dict[str, Any]): 関数に渡す引数辞書。
    """

    fn_name: str = Field(...)
    args: dict[str, Any] = Field(...)
