from abc import ABC, abstractmethod

from pydantic import BaseModel

from ..input_models import PromptModel

from .response_model import ResponseModel


class Tokenizer(BaseModel, ABC):
    """
    テキストとトークンIDの相互変換を行うインターフェース
    """

    @abstractmethod
    def encode(self, text: str) -> list[int]:
        """
        テキストをトークンIDのリストに変換する

        Args:
            text: 変換するテキスト

        Returns:
            list[int]: 変換されたトークンID
        """
        pass

    @abstractmethod
    def decode(self, token_ids: list[int]) -> str:
        """
        トークンIDのリストをテキストに変換する

        Args:
            token_ids: 変換するトークンID

        Returns:
            str: 変換されたテキスト
        """
        pass


class LLMClient(BaseModel, ABC):
    """
    プロンプトから関数呼び出し結果を生成するインターフェース
    """

    @abstractmethod
    def generate(
        self,
        prompts: list[PromptModel],
    ) -> list[ResponseModel] | str:
        """
        プロンプトから関数呼び出し結果を生成する

        Args:
            prompts: 関数呼び出しに変換するプロンプト

        Returns:
            list[ResponseModel] | str: 生成された関数呼び出し結果
        """
        pass
