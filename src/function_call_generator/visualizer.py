from typing import ClassVar

from pydantic import BaseModel

from .abc import Tokenizer


class Visualizer(BaseModel):
    TOTAL_LINES: ClassVar[int] = 7
    GENERATED_LINE: ClassVar[int] = 0
    REJECTED_LINE: ClassVar[int] = 1
    TOP_TOKEN_START_LINE: ClassVar[int] = 2
    TOP_TOKEN_LIMIT: ClassVar[int] = 5

    tokenizer: Tokenizer
    is_initialized: bool = False

    def initialize(self) -> None:
        if self.is_initialized:
            return
        print("\n" * self.TOTAL_LINES, end="")
        self.is_initialized = True

    def show_generated_text(self, generated_text: str) -> None:
        self._write_line(
            self.GENERATED_LINE,
            f"generated_text: {repr(generated_text[-50:])}"
        )

    def show_rejected_token(self, rejected_token: str) -> None:
        self._write_line(
            self.REJECTED_LINE,
            f"rejected_token: {repr(rejected_token)}"
        )

    def show_top_tokens(self, logits: list[float]) -> None:
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
        self.initialize()
        move_up_count = self.TOTAL_LINES - line_index
        print(f"\033[{move_up_count}F", end="")
        print(f"\033[K{text}", end="")
        print(f"\033[{move_up_count}E", end="", flush=True)
