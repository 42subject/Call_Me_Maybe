import json
from typing import Any


def extract_first_json_object(text: str) -> dict[str, Any]:
    """
    文字列から先頭のJSONオブジェクトを抽出して辞書として返す。

    Args:
        text (str): LLMの生出力文字列。

    Raises:
        ValueError: JSON開始位置が見つからない、またはJSONがオブジェクトでない場合。
        json.JSONDecodeError: JSON構文が不正でデコードできない場合。

    Returns:
        dict[str, Any]: 抽出した先頭JSONオブジェクト。
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("JSON object not found in reply")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("Decoded JSON is not an object")
    return obj
