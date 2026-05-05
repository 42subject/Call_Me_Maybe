import json
from typing import Any, cast

from llm_sdk import Small_LLM_Model

from .validate_output import validate_output
from ..validate_inputs import FunctionModel


def extract_first_json_object(text: str) -> dict[str, Any]:
    """
    文字列から最初にデコード可能なJSONオブジェクトを抽出して返す。

    Args:
        text (str): LLMの生出力文字列。

    Raises:
        ValueError: JSONオブジェクトが見つからない場合。
        json.JSONDecodeError: JSON構文が不正でデコードできない場合。

    Returns:
        dict[str, Any]: 抽出したJSONオブジェクト。
    """
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return cast(dict[str, Any], obj)
    raise ValueError("JSON object not found in reply")


def build_instruction(prompt: str, functions: list[FunctionModel]) -> str:
    """
    LLMへ渡す関数選択用の指示文を組み立てる。

    Args:
        prompt (str): ユーザー入力プロンプト。
        functions (list[FunctionModel]): 関数定義一覧。

    Returns:
        str: 関数一覧と出力制約を含んだ最終プロンプト文字列。
    """
    functions_json = json.dumps(
        [function.model_dump() for function in functions],
        ensure_ascii=False,
        indent=2,
    )
    return (
        f"User prompt:\n{prompt}\n\n"
        "Use the function list below as reference information.\n"
        f"{functions_json}\n\n"
        "Return ONLY one raw JSON object with this schema:\n"
        '{"prompt":"<original prompt>",'
        '"fn_name":"<function name>","args":{...}}\n'
        "fn_name must be a string and args must be an object. "
        "No examples. No quoted JSON. No markdown. No explanation."
    )


def encode_token_ids(model: Small_LLM_Model, text: str) -> list[int]:
    """
    LLM SDKのencode結果を1次元のトークンID配列へ変換する。

    Args:
        model (Small_LLM_Model): エンコードに使用するLLMモデル。
        text (str): トークンIDへ変換する文字列。

    Returns:
        list[int]: 入力文字列に対応するトークンID配列。
    """
    encoded: Any = model.encode(text)
    token_rows: list[list[int]] = encoded.tolist()
    return token_rows[0]


def greedy_json_decode(
    model: Small_LLM_Model,
    instruction: str,
    max_new_tokens: int = 128,
) -> dict[str, Any]:
    """
    LLMの次トークンlogitsを貪欲に選択してJSONオブジェクトを生成する。

    Args:
        model (Small_LLM_Model): 生成に使用するLLMモデル。
        instruction (str): 生成前に渡す指示文。
        max_new_tokens (int): 生成する最大トークン数。

    Raises:
        ValueError: 最大トークン数内にJSONオブジェクトを抽出できない場合。

    Returns:
        dict[str, Any]: 生成テキストから抽出したJSONオブジェクト。
    """
    context = encode_token_ids(model, instruction + "\n")
    generated_ids: list[int] = []

    for _ in range(max_new_tokens):
        logits = model.get_logits_from_input_ids(context)
        next_token_id = max(
            range(len(logits)),
            key=lambda index: logits[index],
        )
        context.append(next_token_id)
        generated_ids.append(next_token_id)

        reply = model.decode(generated_ids).strip()
        try:
            return extract_first_json_object(reply)
        except ValueError:
            continue

    raise ValueError("JSON object not found in generated reply")


def generate_reply(
    model: Small_LLM_Model,
    prompt: str,
    functions: list[FunctionModel],
    functions_map: dict[str, FunctionModel],
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    1つのプロンプトに対して、検証済みの関数呼び出しJSONを生成する。

    Args:
        model (Small_LLM_Model): 推論に使用するLLMモデルラッパー。
        prompt (str): ユーザー入力プロンプト。
        functions (list[FunctionModel]): 選択対象となる関数定義一覧。
        functions_map (dict[str, FunctionModel]): 関数名をキーにした関数定義辞書。
        max_retries (int): 互換性維持のために受け取る再試行回数。

    Raises:
        ValueError: 有効なJSONが抽出できない、または定義に一致しない場合。

    Returns:
        dict[str, Any]: 検証済みの関数呼び出し情報。
    """
    instruction = build_instruction(prompt, functions)
    last_error: ValueError | None = None

    for _ in range(max_retries):
        try:
            output_obj = greedy_json_decode(model, instruction)
            return validate_output(output_obj, prompt, functions_map)
        except ValueError as error:
            last_error = error
            instruction += (
                "\nPrevious output was invalid. Return one valid JSON object "
                "with fn_name as a string and args as an object."
            )

    raise ValueError(
        f"Failed to generate valid JSON for prompt: {prompt}"
    ) from last_error
