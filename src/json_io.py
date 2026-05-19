import json
from pathlib import Path

from pydantic import BaseModel

from .function_call_generator import ResponseModel
from .input_models import FunctionModel, PromptModel


class JsonIO(BaseModel):
    """
    入力JSONの読み込みと出力JSONの書き込みを行う
    """

    prompt_path: Path
    functions_path: Path
    output_path: Path

    def _load_raw(self, json_path: Path) -> object:
        """
        JSONファイルを読み込んでPythonオブジェクトに変換する

        Args:
            json_path: 読み込むJSONファイルのパス

        Raises:
            FileNotFoundError: ファイルが存在しない時
            IsADirectoryError: パスがディレクトリの時
            PermissionError: ファイルを読み込む権限がない時
            UnicodeDecodeError: UTF-8として読み込めない時
            ValueError: JSONとして不正な時

        Returns:
            object: 読み込まれたJSONオブジェクト
        """
        text = json_path.read_text(encoding="utf-8")
        loaded_json: object = json.loads(text)
        return loaded_json

    def load_prompts(self) -> list[PromptModel]:
        """
        プロンプト定義JSONを読み込んでPromptModelのリストに変換する

        Raises:
            FileNotFoundError: ファイルが存在しない時
            IsADirectoryError: パスがディレクトリの時
            PermissionError: ファイルを読み込む権限がない時
            UnicodeDecodeError: UTF-8として読み込めない時
            ValueError: JSONのルートがリストではない時
            ValueError: プロンプト定義の形式が不正な時

        Returns:
            list[PromptModel]: 読み込まれたプロンプト定義
        """
        loaded_json = self._load_raw(self.prompt_path)
        if not isinstance(loaded_json, list):
            raise ValueError("prompt json must be a list")
        return [
            PromptModel.model_validate(item)
            for item in loaded_json
        ]

    def load_functions(self) -> list[FunctionModel]:
        """
        関数定義JSONを読み込んでFunctionModelのリストに変換する

        Raises:
            FileNotFoundError: ファイルが存在しない時
            IsADirectoryError: パスがディレクトリの時
            PermissionError: ファイルを読み込む権限がない時
            UnicodeDecodeError: UTF-8として読み込めない時
            ValueError: JSONのルートがリストではない時
            ValueError: 関数定義の形式が不正な時

        Returns:
            list[FunctionModel]: 読み込まれた関数定義
        """
        loaded_json = self._load_raw(self.functions_path)
        if not isinstance(loaded_json, list):
            raise ValueError("function json must be a list")
        return [
            FunctionModel.model_validate(item)
            for item in loaded_json
        ]

    def write_responses(self, responses: list[ResponseModel]) -> None:
        """
        生成された関数呼び出し結果をJSONファイルに書き込む

        Args:
            responses: 書き込む関数呼び出し結果

        Raises:
            FileExistsError: 出力先の親ディレクトリと同名のファイルが存在する時
            PermissionError: ファイルを書き込む権限がない時
            IsADirectoryError: 出力先がディレクトリの時
            TypeError: JSONに変換できない値が含まれている時
            UnicodeEncodeError: UTF-8として書き込めない時
            ValueError: JSONへの変換が不正な時
        """
        output_text = json.dumps(
            [response.model_dump() for response in responses],
            ensure_ascii=False,
            indent=2,
        )
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(output_text, encoding="utf-8")
