from math import inf
from typing import ClassVar

from llm_sdk import Small_LLM_Model
from pydantic import BaseModel, ConfigDict, ValidationError

from ..input_models import PromptModel, FunctionModel

from .response_model import ResponseModel
from .json_validator import JsonValidator
from .visualizer import Visualizer
from .abc import Tokenizer, LLMClient


class PromptBuilder(BaseModel):
    """
    関数定義とプロンプトからLLMに渡すプロンプト文字列を組み立てる
    """

    functions_text: str

    def __init__(self, functions: list[FunctionModel]) -> None:
        """
        関数定義をプロンプト用の文字列に変換して初期化する

        Args:
            functions: 利用可能な関数定義
        """
        super().__init__(
            functions_text=self._build_functions_text(functions)
        )

    @staticmethod
    def _build_functions_text(functions: list[FunctionModel]) -> str:
        """
        関数定義のリストをプロンプトに埋め込むJSON文字列に変換する

        Args:
            functions: 利用可能な関数定義

        Returns:
            str: 関数定義を1行ずつJSONにした文字列
        """
        return "\n".join(function.model_dump_json() for function in functions)

    def build(
        self,
        prompts: list[PromptModel],
        feedbacks: list[str],
    ) -> str:
        """
        LLMに渡すプロンプト文字列を組み立てる

        Args:
            prompts: 関数呼び出しに変換するプロンプト
            feedbacks: 前回までの生成結果に対するバリデーションエラー

        Returns:
            str: LLMに渡すプロンプト文字列
        """
        prompts_text = "\n".join(
            f"{index}. {prompt.prompt}"
            for index, prompt in enumerate(prompts, start=1)
        )
        builded_prompt = ""

        builded_prompt += (
            "You are a function calling assistant.\n"
            "Choose the best function for each user prompt "
            f"Available functions:\n{self.functions_text}\n\n"
            f"User prompts:\n{prompts_text}\n\n"
            "You must return only valid json and chose "
            "prompt, name, parameters.\n"
            "For each result, the value of prompt must repeat the exact "
            "original user prompt text, not the function name.\n"
        )

        if feedbacks:
            feedback_text = "\n".join(
                f"{index}. {feedback}"
                for index, feedback in enumerate(feedbacks, start=1)
            )
            builded_prompt += (
                "Previous answers were invalid. "
                "Fix every issue listed below:\n"
                f"{feedback_text}\n"
                "Return only the corrected JSON answer.\n\n"
            )

        builded_prompt += "Answer:\n"
        return builded_prompt


class QwenTokenizer(Tokenizer):
    """
    Qwenモデルのトークナイズ処理をTokenizerインターフェースに合わせる
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: Small_LLM_Model

    def encode(self, text: str) -> list[int]:
        """
        テキストをQwenモデルのトークンIDに変換する

        Args:
            text: 変換するテキスト

        Returns:
            list[int]: 変換されたトークンID
        """
        token_ids = self.model.encode(text)[0]
        return [int(token_id) for token_id in token_ids]

    def decode(self, token_ids: list[int]) -> str:
        """
        QwenモデルのトークンIDをテキストに変換する

        Args:
            token_ids: 変換するトークンID

        Returns:
            str: 変換されたテキスト
        """
        text: str = self.model.decode(token_ids)
        return text


class QwenClient(LLMClient):
    """
    Qwenモデルを使ってプロンプトから関数呼び出し結果を生成する
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: Small_LLM_Model
    prompt_builder: PromptBuilder
    validator: JsonValidator
    tokenizer: QwenTokenizer
    visualizer: Visualizer

    MAX_TOKENS: ClassVar[int] = 1000
    MAX_RETRIES: ClassVar[int] = 3

    def __init__(
        self,
        model_name: str,
        functions: list[FunctionModel],
    ) -> None:
        """
        Qwenモデルと生成に必要な補助オブジェクトを初期化する

        Args:
            model_name: 使用するQwenモデル名
            functions: 利用可能な関数定義
        """
        model = Small_LLM_Model(model_name)
        tokenizer = QwenTokenizer(model=model)
        BaseModel.__init__(
            self,
            model=model,
            prompt_builder=PromptBuilder(functions),
            validator=JsonValidator(
                function_names=tuple(function.name for function in functions),
                function_parameters={
                    function.name: function.parameters
                    for function in functions
                },
            ),
            tokenizer=tokenizer,
            visualizer=Visualizer(tokenizer=tokenizer),
        )

    def _select_valid_text_from_logits(
        self,
        logits: list[float],
    ) -> tuple[str, int]:
        """
        JSON制約を満たす次トークンをlogitsから選択する

        Args:
            logits: 次トークンごとのスコア

        Returns:
            tuple[str, int]: 選択された文字列とトークンID
        """
        next_token_id = max(
            range(len(logits)),
            key=lambda token_id: logits[token_id]
        )
        next_str = self.tokenizer.decode([next_token_id])
        self.visualizer.show_top_tokens(logits)
        while not self.validator.is_valid_string(next_str):
            self.visualizer.show_rejected_token(next_str)
            logits[next_token_id] = -inf
            next_token_id = max(
                range(len(logits)),
                key=lambda token_id: logits[token_id]
            )
            next_str = self.tokenizer.decode([next_token_id])
            self.visualizer.show_top_tokens(logits)
        return next_str, next_token_id

    def _generate_response(self, token_ids: list[int]) -> str:
        """
        入力トークンからJSON文字列の応答を生成する

        Args:
            token_ids: プロンプトをトークン化したID

        Returns:
            str: 生成されたJSON文字列
        """
        generated_text: str = ""

        for _ in range(self.MAX_TOKENS):
            logits = self.model.get_logits_from_input_ids(token_ids)
            next_str, next_token_id = self._select_valid_text_from_logits(
                logits
            )
            token_ids.append(next_token_id)
            next_str = self.tokenizer.decode([next_token_id])
            generated_text += next_str
            self.visualizer.show_generated_text(generated_text)

            if self.validator.is_complete():
                break

        return generated_text

    def generate(
        self,
        prompts: list[PromptModel],
    ) -> list[ResponseModel]:
        """
        プロンプトを関数呼び出し結果に変換する

        Args:
            prompts: 関数呼び出しに変換するプロンプト

        Raises:
            ValueError: 最大リトライ回数までに有効な応答を生成できない時

        Returns:
            list[ResponseModel]: 生成された関数呼び出し結果
        """
        return [self._generate_one(prompt) for prompt in prompts]

    def _generate_one(self, prompt: PromptModel) -> ResponseModel:
        """
        1つのプロンプトを関数呼び出し結果に変換する

        Args:
            prompt: 関数呼び出しに変換するプロンプト

        Raises:
            ValueError: 最大リトライ回数までに有効な応答を生成できない時

        Returns:
            ResponseModel: 生成された関数呼び出し結果
        """
        feedbacks: list[str] = []

        for retry in range(self.MAX_RETRIES):
            self.visualizer.initialize()
            self.validator.expected_prompt = prompt.prompt
            self.validator.reset()
            prompt_text: str = self.prompt_builder.build([prompt], feedbacks)
            input_ids = self.tokenizer.encode(prompt_text)
            response_text = self._generate_response(input_ids)

            try:
                response_model: ResponseModel = (
                    ResponseModel.model_validate_json(response_text)
                )
                if response_model.prompt != prompt.prompt:
                    raise ValueError(
                        "response prompt must match the original prompt "
                        f"exactly. Expected: {prompt.prompt!r}. "
                        f"Got: {response_model.prompt!r}."
                    )
                print(f"Answer: \n{response_model.model_dump_json()}")
                return response_model
            except (ValidationError, ValueError) as error:
                print(
                    f"response validation failed. "
                    f"({retry + 1}/{self.MAX_RETRIES})\n"
                    f"response: {response_text}"
                )
                feedback = str(error)
                if feedback not in feedbacks:
                    feedbacks.append(feedback)
                continue

        raise ValueError("failed to generate valid response")
