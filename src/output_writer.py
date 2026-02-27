import json
from pathlib import Path
from typing import Any


def save_results(output_path: Path, results: list[dict[str, Any]]) -> None:
    """
    関数呼び出し結果の配列をJSONファイルとして保存する。

    Args:
        output_path (Path): 出力先ファイルパス。
        results (list[dict[str, Any]]): 保存対象の結果配列。

    Raises:
        OSError: ディレクトリ作成やファイル書き込みに失敗した場合。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
