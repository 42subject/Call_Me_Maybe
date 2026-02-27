*This project has been created as part of the 42 curriculum by smiyata.*

# Call Me Maybe

## Description
Call Me Maybe is a function-calling pipeline built on top of a small local LLM (`Qwen/Qwen3-0.6B` through the provided `llm_sdk`).

The goal is to transform natural-language prompts into structured function-call JSON objects.
Instead of answering directly, the system outputs:
- `prompt`: original user prompt
- `name`: selected function name
- `parameters`: typed arguments for that function

Input comes from `data/input/` and output is written to `data/output/function_calls.json`.

## Project Structure
- `src/__main__.py`: pipeline entry point
- `src/load_input_files.py`: JSON loading + input validation
- `src/validate_inputs/`: Pydantic models for prompts/functions
- `src/generate_reply/`: prompt building, generation loop, JSON parsing, output validation
- `src/output_writer.py`: result serialization
- `llm_sdk/`: provided LLM wrapper
- `data/input/`: prompt/function definition files

## Instructions
### Requirements
- Python 3.10+
- `uv`

### Install
```bash
make install
```

### Run
```bash
make run
```

### Debug
```bash
make debug
```

### Lint
```bash
make lint
```

### Strict lint (optional)
```bash
make lint-strict
```

## Usage
Current implementation uses default paths from `src/config/paths.py`:
- Functions: `data/input/functions_definition.json`
- Prompts: `data/input/function_calling_tests.json`
- Output: `data/output/function_calls.json`

Main execution command:
```bash
uv run python -m src
```

## Constrained Decoding Approach (Current)
This repository currently uses a pragmatic constrained-generation strategy:
1. Build a strict instruction containing the function list and required JSON schema.
2. Generate deterministically (`do_sample=False`) to reduce format variance.
3. Block typical markdown fence patterns (` ``` ` and `'''`) via `bad_words_ids`.
4. Extract the first JSON object from the raw model text.
5. Validate schema and types with Pydantic (`OutputModel`) against the selected function definition.
6. Retry generation until a valid object is produced.

This ensures robust parseability in practice, while schema/type validity is guaranteed before writing output.

## Design Decisions
- **Pydantic-first validation**:
  - Input files are converted into `FunctionModel` and `PromptModel`.
  - Generated output is validated by `OutputModel` with `model_validator`.
- **Separation by responsibility**:
  - Load/validate/generate/write are isolated in dedicated modules.
- **Deterministic generation loop**:
  - Reduces randomness and improves reproducibility.
- **Fail-safe retry**:
  - Invalid generations are discarded without crashing the program.

## Output Format
Each output element has this structure:
```json
{
  "prompt": "What is the sum of 2 and 3?",
  "name": "fn_add_numbers",
  "parameters": {
    "a": 2.0,
    "b": 3.0
  }
}
```

## Performance Analysis
- **Accuracy**: strongly depends on prompt clarity and model behavior; schema/type mismatches are rejected and retried.
- **Speed**: small prompt sets complete quickly; retries increase latency when the model drifts from target format.
- **Reliability**: output file contains only validated JSON objects (invalid generations are not written).

## Challenges Faced
- Small-model instability on strict JSON formatting (extra prose/code fences).
- Frequent partial JSON or malformed tails.
- Dependency/import breakages during refactors.

### Solutions
- Added banned token patterns and deterministic decoding.
- Added first-object JSON extraction and retry loop.
- Centralized validation with Pydantic models.
- Cleaned package imports and module boundaries.

## Testing Strategy
- Static checks:
  - `flake8`
  - `mypy` (via Makefile rules)
- Runtime checks:
  - Execute full pipeline with provided input files.
  - Verify output file is valid JSON and schema-compliant.
- Edge cases tested manually:
  - malformed JSON input
  - unknown function names
  - wrong parameter keys/types
  - incomplete model output

## Example Usage
```bash
make install
make run
cat data/output/function_calls.json
```

## AI Usage
AI tools were used for:
- debugging strategy discussion
- refactoring suggestions
- documentation drafting/revision

All generated proposals were reviewed, adapted, and validated manually before integration.

## Resources
- 42 project subject (`call_en.subject.pdf`)
