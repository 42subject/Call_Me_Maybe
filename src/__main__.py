from typing import Any

from llm_sdk import Small_LLM_Model

from .config import FUNCTIONS_PATH, OUTPUT_PATH, PROMPTS_PATH
from .generate_reply import generate_reply
from .load_input_files import load_function_file, load_prompt_file
from .output_writer import save_results
from .validate_inputs import FunctionModel, PromptModel


def main() -> None:
    """
    入力JSONを読み込み、LLMで関数呼び出し情報を生成して保存する。
    """
    prompt_models: list[PromptModel] = load_prompt_file(PROMPTS_PATH)
    function_models: list[FunctionModel] = load_function_file(
        FUNCTIONS_PATH
    )
    function_map = {function.name: function for function in function_models}

    model = Small_LLM_Model()
    results: list[dict[str, Any]] = []
    for prompt_model in prompt_models:
        try:
            result = generate_reply(
                model=model,
                prompt=prompt_model.prompt,
                functions=function_models,
                functions_map=function_map,
            )
            results.append(result)
            print(result)
        except ValueError as error:
            print(f"Error: {error}")
    try:
        save_results(OUTPUT_PATH, results)
    except FileNotFoundError as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
