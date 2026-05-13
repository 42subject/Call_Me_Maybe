from pydantic import BaseModel

from ..input_models import PromptModel, FunctionParametersModel


class ResponseModel(BaseModel):
    prompt: PromptModel
    fn_name: str
    args: dict[str, FunctionParametersModel]