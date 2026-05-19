*このプロジェクトは smiyata によって 42 curriculum の一環として作成されました。*

# Call Me Maybe

## Description

Call Me Maybe は、小さなローカルLLMのための function calling パイプラインです。
自然言語のプロンプトと関数定義を読み込み、自由形式の回答ではなく、
構造化された JSON の関数呼び出しオブジェクトを生成します。

たとえば、次のようなプロンプトが与えられた場合:

```text
What is the sum of 2 and 3?
```

プログラムは、呼び出すべき関数と渡すべき引数を出力します:

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

このプロジェクトは、提供された `llm_sdk` パッケージ経由で
`Qwen/Qwen3-0.6B` を使用し、生成されるトークンが期待される JSON 構造と
利用可能な関数スキーマに適合し続けるように、制約付きデコーディングを実装しています。

## Instructions

### Requirements

- Python 3.10 以降
- `uv`
- 提供された `llm_sdk` パッケージ

### Installation

```bash
make install
```

これは次を実行します:

```bash
uv sync
```

### Run

```bash
uv run python -m src
```

デフォルトでは、プログラムは次のファイルを読み込みます:

- `data/input/functions_definition.json`
- `data/input/function_calling_tests.json`

そして次のファイルへ書き込みます:

- `data/output/function_calling_results.json`

カスタムパスは個別に指定できます:

```bash
uv run python -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calling_results.json
```

各オプションは任意です。省略されたオプションにはデフォルトパスが使われます。

### Makefile

```bash
make install
make run
make debug
make clean
make lint
make lint-strict
```

`make lint` は、プロジェクトで要求されるフラグ付きで `flake8` と `mypy` を実行します。

## Input Format

プロンプトファイルは、`prompt` フィールドを持つオブジェクトの JSON 配列である必要があります:

```json
[
  {
    "prompt": "What is the sum of 2 and 3?"
  }
]
```

関数定義ファイルは JSON 配列である必要があります。各関数は、名前、説明、
パラメータスキーマ、戻り値スキーマを持ちます:

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

サポートされるパラメータ型は次の通りです:

- `string`
- `number`
- `object`
- `array`

オブジェクトはネストした `properties` を使い、配列は `items` を使います。

## Output Format

出力ファイルは JSON 配列です。各要素は正確に次のキーを含みます:

- `prompt`: 元のプロンプト文字列
- `name`: 選択された関数名
- `parameters`: その関数のために生成された引数

例:

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

必要に応じて、出力ディレクトリは自動的に作成されます。

## Algorithm

生成ループはトークン単位で動作します:

1. `PromptBuilder` が、利用可能な関数とユーザープロンプトを単一の指示プロンプトへシリアライズします。
2. `QwenTokenizer` が SDK の tokenizer でプロンプトをエンコードします。
3. `QwenClient` が `Small_LLM_Model.get_logits_from_input_ids()` を呼び出します。
4. 追加しても `JsonValidator` によって出力が有効なままである場合のみ、最もスコアの高いトークンを選択します。
5. 無効なトークンは、その logits を負の無限大に設定することで拒否されます。
6. 選択されたトークンを入力トークン列へ追加します。
7. validator が JSON の完成を確認すると、生成を停止します。
8. 出力ファイルへ書き込む前に、Pydantic が最終 JSON を `ResponseModel` オブジェクトへ検証します。

### Constrained Decoding

制約付きデコーダは、prompting だけに依存しません。生成中、
`JsonValidator` は各候補トークンを JSON prefix として検査し、
要求される構造に違反するトークンを拒否します。

現在の validator は次を強制します:

- ルート出力は JSON 配列でなければならない。
- 各 response object は `prompt`, `name`, `parameters` をこの順番で含まなければならない。
- `name` は `functions_definition.json` にある名前のいずれかでなければならない。
- `parameters` は選択された `name` のパラメータスキーマと一致しなければならない。
- 未知の引数キーは拒否される。
- 必須引数キーが不足している場合、オブジェクトを閉じることはできない。
- 引数値の開始は、string, number, object, array の型によって制約される。
- ネストした object と array のスキーマは再帰的に検証される。

この手法は、無効なトークンが生成 JSON に入る前に防ぐことで、
小さなモデルでの信頼性を向上させます。

## Design Decisions

- **Pydantic models for validation**: 入力プロンプト、関数定義、CLI引数、
  出力レスポンスは Pydantic モデルで表現されています。
- **Explicit CLI parsing**: `src/__main__.py` は必要な optional 引数を受け付け、
  未知のオプションと重複したオプションを拒否します。
- **Schema-aware constrained decoding**: デコーダは関数定義を使い、
  生成中の `name` と `parameters` を制限します。
- **Retry loop**: 生成された JSON が parse できても response validation に失敗した場合、
  エラーをプロンプトへフィードバックして再生成します。
- **Output safety**: 出力ディレクトリは自動作成され、ファイルや JSON のエラーは
  クラッシュせずに報告されます。
- **Terminal visualization**: デコード中に、生成の進行状況、拒否されたトークン、
  上位候補トークンがターミナルに表示されます。

## Performance Analysis

この実装はプロジェクト要件を満たすことを目標にしています:

- **JSON validity**: 制約付きデコーディングは、生成されるすべての response が
  JSON として parse 可能であるように設計されています。
- **Schema reliability**: 関数名と引数スキーマは、トークン選択中に制約されます。
- **Accuracy**: 関数選択と引数抽出は、依然として小さな LLM のプロンプト理解に依存しますが、
  無効な関数名や互換性のない引数構造はブロックされます。
- **Speed**: 生成はトークン単位で行われるため、制約なしのデコーディングより遅くなる可能性がありますが、
  デフォルトの入力サイズはプロジェクトの時間制限内に完了することを想定しています。

## Challenges Faced

- **Small-model JSON instability**: 制約がない場合、モデルは壊れた JSON や途中で切れた JSON を
  生成することがあります。これはデコード中の prefix validation によって対応しました。
- **Function-aware validation**: `parameters` は `name` が分かるまで正しく検証できません。
  validator は選択された関数名を保持し、その関数のパラメータスキーマへ切り替えます。
- **Nested schemas**: object と array の引数には再帰的な検証が必要です。
  validator はネストした object と array のために schema frame を追跡します。
- **Terminal output state**: 生成の再試行が繰り返されると、カーソル位置が乱れることがあります。
  visualizer は retry の間に表示ブロックをリセットします。

## Testing Strategy

静的チェック:

```bash
make lint
make lint-strict
```

手動での実行時チェック:

- デフォルト入力ファイルでパイプライン全体を実行する。
- `data/output/function_calling_results.json` が有効な JSON であることを確認する。
- 入力ファイルが存在しない場合を試す。
- 壊れた JSON 入力ファイルを試す。
- カスタムの `--input`, `--output`, `--functions_definition` パスを試す。
- 未知の CLI オプションと重複したオプションが graceful に失敗することを確認する。
- 出力ディレクトリが自動作成されることを確認する。
- 余分な出力キーが `ResponseModel` によって拒否されることを確認する。
- 無効な関数名と無効な引数スキーマが制約付きデコーディングによって拒否されることを確認する。

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

主要ファイル:

- `src/__main__.py`: CLI エントリポイントとトップレベルのエラーハンドリング
- `src/json_io.py`: JSON 入力の読み込みと出力の書き込み
- `src/input_models/input_models.py`: プロンプトと関数定義のモデル
- `src/function_call_generator/function_call_generator.py`: プロンプト構築、
  トークン生成、retry、SDK連携
- `src/function_call_generator/json_validator.py`: 制約付き JSON と schema の
  prefix validation
- `src/function_call_generator/response_model.py`: 出力 response モデル
- `src/function_call_generator/visualizer.py`: ターミナル上の生成表示

## Example Usage

依存関係をインストール:

```bash
make install
```

デフォルト設定で実行:

```bash
uv run python -m src
```

明示的なパスで実行:

```bash
uv run python -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calling_results.json
```

結果を読む:

```bash
cat data/output/function_calling_results.json
```

## Resources

- Project subject: `call_me_maybe.pdf`
- Pydantic documentation: https://docs.pydantic.dev/
- Python `json` documentation: https://docs.python.org/3/library/json.html
- Python `pathlib` documentation: https://docs.python.org/3/library/pathlib.html
- Qwen model family: https://qwenlm.github.io/
- Constrained decoding background: プロジェクト subject で説明されている
  JSON/schema-constrained generation と token filtering の概念

## AI Usage

AI assistance was used for:

- 制約付きデコーディングの実装方針の相談
- schema-aware な制約付きデコーディングに必要な条件分岐の洗い出しと
  網羅確認
- プロジェクト subject に対する validation gap の特定
- ドキュメントのドラフト作成と改善
- ターミナル表示と CLI 挙動のデバッグ

すべてのコードとドキュメントの変更は、リポジトリに残す前に手動で確認、
調整、テストされています。
