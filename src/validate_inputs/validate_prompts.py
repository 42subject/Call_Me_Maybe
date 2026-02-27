from pydantic import BaseModel, Field


class PromptModel(BaseModel):
    prompt: str = Field(...)


def validate_prompts(prompts: list[dict[str, str]]) -> list[PromptModel]:
    """
    プロンプト辞書配列をPromptModel配列へ変換して検証する。

    Args:
        prompts (list[dict[str, str]]): 読み込み済みのプロンプト辞書配列。

    Raises:
        ValidationError: プロンプト定義の必須項目不足や型不一致がある場合。

    Returns:
        list[PromptModel]: 検証済みのプロンプトモデル配列。
    """
    prompt_models = [
        PromptModel(**prompt)
        for prompt in prompts
    ]
    return prompt_models
