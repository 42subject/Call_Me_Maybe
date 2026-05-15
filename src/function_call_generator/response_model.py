from pydantic import BaseModel


class ResponseModel(BaseModel):
    prompt: str
    fn_name: str
    args: dict[str, object]
