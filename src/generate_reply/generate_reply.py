from json import JSONDecodeError
import json
from typing import Any

from llm_sdk import Small_LLM_Model

from .validate_output import validate_output
from ..validate_inputs import FunctionModel


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
        "Select exactly one function from the function list below.\n"
        f"{functions_json}\n\n"
        "Return ONLY raw JSON with this exact schema:\n"
        '{"prompt":"<original prompt>",'
        '"name":"<function name>","parameters":{...}}\n'
        "No markdown. No code fences. No extra text."
    )


def build_bad_words_ids(model: Small_LLM_Model) -> list[list[int]]:
    """
    生成時に禁止する文字列のトークンIDリストを作成する。

    Args:
        model (Small_LLM_Model): トークナイザーを保持するLLMモデルラッパー。

    Returns:
        list[list[int]]: `bad_words_ids` に渡す禁止トークンIDの二次元配列。
    """
    return [
        model._tokenizer.encode("```", add_special_tokens=False),
        model._tokenizer.encode("'''", add_special_tokens=False),
    ]


def generate_reply(
    model: Small_LLM_Model,
    prompt: str,
    functions: list[FunctionModel],
    functions_map: dict[str, FunctionModel],
) -> dict[str, Any]:
    """
    1つのプロンプトに対して、検証済みの関数呼び出しJSONを生成する。

    Args:
        model (Small_LLM_Model): 推論に使用するLLMモデルラッパー。
        prompt (str): ユーザー入力プロンプト。
        functions (list[FunctionModel]): 選択対象となる関数定義一覧。
        functions_map (dict[str, FunctionModel]): 関数名をキーにした関数定義辞書。

    Raises:
        ValueError: 有効なJSONが抽出できない、または定義に一致しない場合。

    Returns:
        dict[str, Any]: 検証済みの関数呼び出し情報。
    """
    instruction = build_instruction(prompt, functions)
    input_ids = model.encode(instruction)
    bad_words_ids = build_bad_words_ids(model)
    raw_model: Any = model._model

    while True:
        output_ids = raw_model.generate(
            input_ids=input_ids,
            do_sample=False,
            max_new_tokens=128,
            eos_token_id=model._tokenizer.eos_token_id,
            pad_token_id=model._tokenizer.eos_token_id,
            bad_words_ids=bad_words_ids,
            repetition_penalty=1.1,
        )
        new_ids = output_ids[0][input_ids.shape[1]:]
        reply = model.decode(new_ids).strip()
        try:
            output_obj = extract_first_json_object(reply)
            return validate_output(output_obj, prompt, functions_map)
        except (ValueError, JSONDecodeError):
            print("Generate failed. Try again...")
            continue
    raise ValueError(f"Failed to generate valid JSON for prompt: {prompt}")
