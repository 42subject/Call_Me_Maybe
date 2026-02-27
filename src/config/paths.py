from pathlib import Path


BASE_PATH = Path(__file__).resolve().parents[2]
INPUT_PATH = BASE_PATH / "data" / "input"
OUTPUT_PATH = BASE_PATH / "data" / "output" / "function_calls.json"
PROMPTS_PATH = INPUT_PATH / "function_calling_tests.json"
FUNCTIONS_PATH = INPUT_PATH / "functions_definition.json"
