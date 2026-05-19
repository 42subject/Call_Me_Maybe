from typing import ClassVar

from pydantic import BaseModel

from .abc import Tokenizer


class Visualizer(BaseModel):
    """
    生成中のテキストや候補トークンをターミナルに表示する
    """

    TOTAL_LINES: ClassVar[int] = 7
    GENERATED_LINE: ClassVar[int] = 0
    REJECTED_LINE: ClassVar[int] = 1
    TOP_TOKEN_START_LINE: ClassVar[int] = 2
    TOP_TOKEN_LIMIT: ClassVar[int] = 5

    tokenizer: Tokenizer
    is_initialized: bool = False

    def initialize(self) -> None:
        """
        表示用の行を確保する
        """
        if self.is_initialized:
            return
        print("\n" * self.TOTAL_LINES, end="")
        self.is_initialized = True

    def reset(self) -> None:
        """
        次の生成で新しい表示ブロックを作るように状態をリセットする
        """
        self.is_initialized = False

    def show_generated_text(self, generated_text: str) -> None:
        """
        現在までに生成されたテキストを表示する

        Args:
            generated_text: 現在までに生成されたテキスト
        """
        self._write_line(
            self.GENERATED_LINE,
            f"generated_text: {repr(generated_text[-50:])}"
        )

    def show_rejected_token(self, rejected_token: str) -> None:
        """
        JSON制約により拒否されたトークンを表示する

        Args:
            rejected_token: 拒否されたトークン文字列
        """
        self._write_line(
            self.REJECTED_LINE,
            f"rejected_token: {repr(rejected_token)}"
        )

    def show_top_tokens(self, logits: list[float]) -> None:
        """
        次トークン候補の上位を表示する

        Args:
            logits: 次トークンごとのスコア
        """
        top_token_ids = sorted(
            range(len(logits)),
            key=lambda token_id: logits[token_id],
            reverse=True
        )[:self.TOP_TOKEN_LIMIT]
        candidate_texts = [
            self.tokenizer.decode([token_id])
            for token_id in top_token_ids
        ]
        lines = [
            f"top_token[{index}]: {token_id} {repr(text)}"
            for index, (token_id, text)
            in enumerate(zip(top_token_ids, candidate_texts), start=1)
        ]

        for index in range(self.TOP_TOKEN_LIMIT):
            line = lines[index] if index < len(lines) else ""
            self._write_line(self.TOP_TOKEN_START_LINE + index, line)

    def _write_line(self, line_index: int, text: str) -> None:
        """
        表示ブロック内の指定行を上書きする

        Args:
            line_index: 表示ブロック内の行番号
            text: 表示する文字列
        """
        self.initialize()
        move_up_count = self.TOTAL_LINES - line_index
        print(f"\033[{move_up_count}F", end="")
        print(f"\033[K{text}", end="")
        print(f"\033[{move_up_count}E", end="", flush=True)
