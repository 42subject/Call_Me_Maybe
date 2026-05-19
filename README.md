*This project has been created as part of the 42 curriculum by smiyata.*

# Call Me Maybe

## Description

Call Me Maybe is a function-calling pipeline for a small local LLM. It reads
natural-language prompts and function definitions, then produces structured
JSON function-call objects instead of free-form answers.

For example, given a prompt such as:

```text
What is the sum of 2 and 3?
```

the program should output the function to call and the arguments to pass:

```json
{
  "prompt": "What is the sum of 2 and 3?",
  "name": "fn_add_numbers",
  "parameters": {
    "a": 2,
    "b": 3
  }
}
```

The project uses `Qwen/Qwen3-0.6B` through the provided `llm_sdk` package and
implements constrained decoding so that generated tokens stay compatible with
the expected JSON structure and the available function schemas.

## Instructions

### Requirements

- Python 3.10 or later
- `uv`
- The provided `llm_sdk` package

### Installation

```bash
make install
```

This runs:

```bash
uv sync
```

### Run

```bash
uv run python -m src
```

By default, the program reads:

- `data/input/functions_definition.json`
- `data/input/function_calling_tests.json`

and writes:

- `data/output/function_calling_results.json`

Custom paths can be provided independently:

```bash
uv run python -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calling_results.json
```

Each option is optional. If an option is omitted, its default path is used.

### Makefile

```bash
make install
make run
make debug
make clean
make lint
make lint-strict
```

`make lint` runs `flake8` and `mypy` with the required project flags.

## Input Format

The prompt file must be a JSON array of objects with a `prompt` field:

```json
[
  {
    "prompt": "What is the sum of 2 and 3?"
  }
]
```

The function definition file must be a JSON array. Each function has a name,
description, parameter schema, and return schema:

```json
[
  {
    "name": "fn_add_numbers",
    "description": "Add two numbers together and return their sum.",
    "parameters": {
      "a": {
        "type": "number"
      },
      "b": {
        "type": "number"
      }
    },
    "returns": {
      "type": "number"
    }
  }
]
```

Supported parameter types are:

- `string`
- `number`
- `object`
- `array`

Objects use nested `properties`, and arrays use `items`.

## Output Format

The output file is a JSON array. Each element contains exactly:

- `prompt`: the original prompt text
- `name`: the selected function name
- `parameters`: the generated arguments for that function

Example:

```json
[
  {
    "prompt": "What is the sum of 2 and 3?",
    "name": "fn_add_numbers",
    "parameters": {
      "a": 2,
      "b": 3
    }
  }
]
```

The output directory is created automatically when needed.

## Algorithm

The generation loop works token by token:

1. `PromptBuilder` serializes the available functions and user prompts into a
   single instruction prompt.
2. `QwenTokenizer` encodes the prompt with the SDK tokenizer.
3. `QwenClient` calls `Small_LLM_Model.get_logits_from_input_ids()`.
4. The highest-scoring token is selected only if appending it keeps the output
   valid according to `JsonValidator`.
5. Invalid tokens are rejected by setting their logits to negative infinity.
6. The selected token is appended to the input token list.
7. Generation stops when the validator confirms that the JSON is complete.
8. Pydantic validates the final JSON into `ResponseModel` objects before
   writing the output file.

### Constrained Decoding

The constrained decoder does not rely only on prompting. During generation,
`JsonValidator` checks each candidate token as a JSON prefix and rejects tokens
that would violate the required structure.

The validator currently enforces:

- The root output must be a JSON array.
- Each response object must contain `prompt`, `name`, and `parameters` in that
  order.
- `name` must be one of the names from `functions_definition.json`.
- `parameters` must match the parameter schema of the selected `name`.
- Unknown argument keys are rejected.
- Missing required argument keys prevent an object from closing.
- Argument value starts are constrained by type: string, number, object, or
  array.
- Nested object and array schemas are validated recursively.

This approach improves reliability with a small model by preventing invalid
tokens from entering the generated JSON in the first place.

## Design Decisions

- **Pydantic models for validation**: input prompts, function definitions, CLI
  arguments, and output responses are represented with Pydantic models.
- **Explicit CLI parsing**: `src/__main__.py` accepts the required optional
  arguments while rejecting unknown and duplicate options.
- **Schema-aware constrained decoding**: the decoder uses function definitions
  to restrict `name` and `parameters` during generation.
- **Retry loop**: if the generated JSON parses but fails response validation,
  the error is fed back into the prompt and generation is retried.
- **Output safety**: output directories are created automatically, and file and
  JSON errors are reported without crashing.
- **Terminal visualization**: generation progress, rejected tokens, and top
  candidate tokens are displayed while decoding.

## Performance Analysis

The implementation targets the project requirements:

- **JSON validity**: constrained decoding is designed to keep every generated
  response parseable as JSON.
- **Schema reliability**: function names and argument schemas are constrained
  during token selection.
- **Accuracy**: function selection and argument extraction still depend on the
  small LLM's understanding of the prompt, but invalid function names and
  incompatible argument structures are blocked.
- **Speed**: generation is token-by-token and can be slower than unconstrained
  decoding, but the default input size is intended to complete within the
  project time limit.

## Challenges Faced

- **Small-model JSON instability**: the model can produce malformed or partial
  JSON without constraints. This was addressed with prefix validation during
  decoding.
- **Function-aware validation**: `parameters` cannot be validated correctly until
  `name` is known. The validator stores the selected function name and then
  switches to that function's parameter schema.
- **Nested schemas**: object and array arguments require recursive validation.
  The validator tracks schema frames for nested objects and arrays.
- **Terminal output state**: repeated generation attempts can disturb cursor
  positioning. The visualizer resets its display block between retries.

## Testing Strategy

Static checks:

```bash
make lint
make lint-strict
```

Manual runtime checks:

- Run the full pipeline with the default input files.
- Validate that `data/output/function_calling_results.json` is valid JSON.
- Try missing input files.
- Try malformed JSON input files.
- Try custom `--input`, `--output`, and `--functions_definition` paths.
- Check that unknown CLI options and duplicate options fail gracefully.
- Check that output directories are created automatically.
- Check that extra output keys are rejected by `ResponseModel`.
- Check that invalid function names and invalid argument schemas are rejected
  by constrained decoding.

## Project Structure

```text
src/
  __main__.py
  json_io.py
  paths.py
  input_models/
    input_models.py
  function_call_generator/
    abc.py
    function_call_generator.py
    json_validator.py
    response_model.py
    visualizer.py
```

Key files:

- `src/__main__.py`: CLI entry point and top-level error handling
- `src/json_io.py`: JSON input loading and output writing
- `src/input_models/input_models.py`: prompt and function definition models
- `src/function_call_generator/function_call_generator.py`: prompt building,
  token generation, retries, and SDK integration
- `src/function_call_generator/json_validator.py`: constrained JSON and schema
  prefix validation
- `src/function_call_generator/response_model.py`: output response model
- `src/function_call_generator/visualizer.py`: terminal generation display

## Example Usage

Install dependencies:

```bash
make install
```

Run with defaults:

```bash
uv run python -m src
```

Run with explicit paths:

```bash
uv run python -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calling_results.json
```

Read the result:

```bash
cat data/output/function_calling_results.json
```

## Resources

- Project subject: `call_me_maybe.pdf`
- Pydantic documentation: https://docs.pydantic.dev/
- Python `json` documentation: https://docs.python.org/3/library/json.html
- Python `pathlib` documentation: https://docs.python.org/3/library/pathlib.html
- Qwen model family: https://qwenlm.github.io/
- Constrained decoding background: JSON/schema-constrained generation and
  token filtering concepts described in the project subject

## AI Usage

AI assistance was used for:

- discussing implementation approaches for constrained decoding
- enumerating and cross-checking the conditional branches required for
  schema-aware constrained decoding
- identifying validation gaps against the project subject
- drafting and refining documentation
- debugging terminal visualization and CLI behavior

All code and documentation changes were reviewed, adapted, and tested manually
before being kept in the repository.
