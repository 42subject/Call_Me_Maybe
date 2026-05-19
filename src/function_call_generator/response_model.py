from pydantic import BaseModel, ConfigDict


class ResponseModel(BaseModel):
    """
    生成された関数呼び出し結果を表す
    """

    model_config = ConfigDict(extra="forbid")

    prompt: str
    name: str
    parameters: dict[str, object]
