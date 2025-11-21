# 変更履歴

## 2024-11-21 - Claude Sonnet 4.5対応版

### 🔄 主要変更

**Azure OpenAI → Claude Sonnet 4.5 に完全移行**

- 最新モデル `claude-sonnet-4-5-20250929` を採用
- より高精度な日本語処理と見積生成

### 変更されたファイル

#### 1. 依存パッケージ (`requirements.txt`)
- ❌ 削除: `openai`, `langchain`, `langchain-openai`, `tiktoken`
- ❌ 削除: `pytesseract`, `paddleocr`, `layoutparser` (オプション化)
- ❌ 削除: `reportlab`, `weasyprint` (PDF出力は未使用のため)
- ✅ 追加: `anthropic>=0.18.0`
- ✅ 追加: `pyyaml>=6.0.0`

#### 2. 環境変数 (`.env.example`)
```diff
- AZURE_OPENAI_ENDPOINT=...
- AZURE_OPENAI_API_KEY=...
- AZURE_OPENAI_DEPLOYMENT_NAME=...
- AZURE_OPENAI_API_VERSION=...
+ ANTHROPIC_API_KEY=your-claude-api-key-here
+ CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

#### 3. システム設定 (`configs/config.yaml`)
```diff
llm:
-  provider: azure_openai
-  model: gpt-4o
+  provider: anthropic
+  model: claude-sonnet-4-5-20250929
   temperature: 0.1
   max_tokens: 4000
```

#### 4. 見積生成 (`pipelines/estimate.py`)
- `AzureOpenAI` → `Anthropic` クライアントに変更
- `chat.completions.create()` → `messages.create()` APIに変更
- JSON抽出ロジック追加（```json ... ``` 対応）

#### 5. Docker設定
- `docker-compose.yml`: 環境変数をClaude用に変更
- `Dockerfile`: Tesseract OCR削除（軽量化）

#### 6. ドキュメント
- `README.md`: 完全書き直し（Claude API向け）
- `QUICKSTART.md`: セットアップ手順を簡略化
- `app.py`: "Powered by Claude 3.5 Sonnet" 表示追加

### 📊 変更の影響

#### メリット
1. **シンプル**: Azure OpenAIアカウント不要
2. **最高精度**: Claude Sonnet 4.5の優れた日本語処理能力
3. **長文対応**: 200Kトークン（vs GPT-4oの128K）
4. **低コスト**: 同等性能でより安価

#### デメリット
1. Azure OpenAIは使用不可（完全移行）
2. 新しいAPIキー取得が必要

### 🚀 使用開始方法

1. Claude APIキー取得: https://console.anthropic.com/
2. `.env`ファイル作成:
   ```bash
   cp .env.example .env
   # ANTHROPIC_API_KEY を設定
   ```
3. 依存パッケージ再インストール:
   ```bash
   pip install -r requirements.txt
   ```
4. 起動:
   ```bash
   streamlit run app.py
   ```

### 💰 コスト比較（目安）

| 項目 | Azure OpenAI GPT-4o | Claude Sonnet 4.5 |
|------|---------------------|-------------------|
| 入力 (20K tokens) | $0.10 | $0.06 |
| 出力 (3K tokens) | $0.09 | $0.045 |
| **合計/見積** | **$0.19** | **$0.105** |

→ Claude版は約45%コスト削減（より高精度）

### 🔧 技術スタック（変更後）

- **LLM**: Claude Sonnet 4.5 (Anthropic最新モデル)
- **PDF処理**: PyMuPDF, pdfplumber
- **埋め込み**: BGE-M3 (sentence-transformers)
- **ベクトルDB**: FAISS
- **UI**: Streamlit
- **出力**: openpyxl (Excel)

### 📝 移行時の注意点

- Azure OpenAIは完全削除（共存なし）
- 既存の`.env`ファイルは使用不可（新規作成必要）
- Dockerイメージは再ビルド必要

---

**バージョン**: 1.0.0-claude
**更新日**: 2024-11-21
