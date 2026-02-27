*このプロジェクトは 42 カリキュラムの一環として smiyata により作成されました。*

# Call Me Maybe

## 概要
Call Me Maybe は、提供された `llm_sdk` 経由で小型ローカルLLM（`Qwen/Qwen3-0.6B`）を使い、自然言語プロンプトを構造化された関数呼び出しJSONに変換するパイプラインです。

目的は「質問に直接答える」ことではなく、以下を返すことです。
- `prompt`: 元の入力文
- `name`: 選択された関数名
- `parameters`: その関数へ渡す型付き引数

入力は `data/input/`、出力は `data/output/function_calls.json` に保存されます。

## ディレクトリ構成
- `src/__main__.py`: パイプラインのエントリポイント
- `src/load_input_files.py`: JSON読み込み + 入力バリデーション
- `src/validate_inputs/`: prompts/functions 用 Pydantic モデル
- `src/generate_reply/`: 指示文生成、推論ループ、JSON抽出、出力バリデーション
- `src/output_writer.py`: 結果の書き込み
- `llm_sdk/`: 課題提供のLLMラッパー
- `data/input/`: テスト用入力ファイル

## 実行方法
### 必要環境
- Python 3.10+
- `uv`

### インストール
```bash
make install
```

### 実行
```bash
make run
```

### デバッグ
```bash
make debug
```

### Lint
```bash
make lint
```

### 厳密Lint（任意）
```bash
make lint-strict
```

## 使い方
現在の実装は `src/config/paths.py` のデフォルトパスを使用します。
- 関数定義: `data/input/functions_definition.json`
- プロンプト: `data/input/function_calling_tests.json`
- 出力先: `data/output/function_calls.json`

実行コマンド:
```bash
uv run python -m src
```

## 制約付きデコード方針（現実装）
このリポジトリでは、次の実用的な制約付き生成戦略を使っています。
1. 関数一覧と厳密なJSONスキーマを含む指示文を構築
2. `do_sample=False` の決定的生成で出力ぶれを抑制
3. `bad_words_ids` で ` ``` ` と `'''`（コードフェンス）を禁止
4. 生テキストから先頭のJSONオブジェクトだけ抽出
5. `OutputModel`（Pydantic）でスキーマ・型を関数定義に照らして検証
6. 不正なら再生成

この流れにより、実用上の高いJSON復元性を維持しつつ、保存前にスキーマ・型の整合性を保証しています。

## 設計判断
- **Pydantic中心の検証**:
  - 入力は `FunctionModel` / `PromptModel` に変換して検証
  - 出力は `OutputModel` + `model_validator` で検証
- **責務分離**:
  - 読み込み / 検証 / 生成 / 書き込みをモジュール分割
- **決定的生成ループ**:
  - 再現性を上げるためランダム性を抑制
- **安全なリトライ**:
  - 不正出力は破棄し、クラッシュせず再試行

## 出力フォーマット
各要素は次の構造です。
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

## パフォーマンス分析
- **精度**: プロンプト品質とモデル挙動に依存。スキーマ不一致は検証で弾いて再試行。
- **速度**: 通常の入力件数なら短時間で完了。再試行が増えると遅延が増える。
- **信頼性**: 出力ファイルには検証済みオブジェクトのみを書き込む。

## 直面した課題
- 小型モデルでのJSONフォーマット不安定性（余計な説明・コードフェンス）
- JSONの途中切れや末尾崩れ

### 解決策
- 禁止トークン設定
- 先頭JSON抽出 + 成功するまでループ
- Pydanticモデルによる検証

## テスト戦略
- 静的検査:
  - `flake8`
  - `mypy`（Makefileのルール）
- 実行検証:
  - 提供入力でパイプラインを通し実行
  - 出力JSONの妥当性とスキーマ適合を確認
- 手動エッジケース:
  - 壊れたJSON入力
  - 未定義関数名
  - 引数キー/型の不一致
  - 途中で切れたLLM出力

## 実行例
```bash
make install
make run
cat data/output/function_calls.json
```

## AI利用について
AIは以下に利用しました。
- デバッグ方針の検討
- リファクタ案の比較
- ドキュメントの下書きと改善

生成内容はすべて手動で確認・修正し、理解したうえで採用しています。

## 参考資料
- 42課題資料（`call_en.subject.pdf`）
