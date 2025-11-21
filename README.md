# Ecolease PoC - 入札見積自動化システム

入札書類から自動的に見積書を生成するPoC（概念実証）システムです。

## 🎯 目標

- **処理時間**: 5分以内
- **完成度**: 70%以上
- **対応工事区分**: 電気、機械、空調、衛生、ガス、消防

## 🏗️ システム構成

```
入札仕様書PDF → 解析 → FMT正規化 → 分類 → RAG検索 → 見積生成 → Excel出力
```

### 主要コンポーネント

1. **Document Ingestor** - PDF/DOCXからテキスト・テーブルを抽出
2. **FMT Normalizer** - 社内統一フォーマット（FMT）に変換
3. **Classifier** - 施設区分・工事区分を自動分類
4. **Price RAG** - 過去見積から類似価格を検索（FAISS + BGE-M3）
5. **Estimate Generator** - **Claude Sonnet 4.5**で見積項目を生成
6. **Exporter** - Excel形式で見積書を出力（送付状・御見積書・明細書）

## 📋 必要要件

- Python 3.10+
- **Anthropic API キー**（Claude API）
- 8GB以上のメモリ推奨

## 🚀 セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. Claude API キーの設定

`.env`ファイルを作成:

```bash
cp .env.example .env
```

`.env`ファイルを編集してClaude APIキーを設定:

```env
ANTHROPIC_API_KEY=your-claude-api-key-here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

**Claude APIキーの取得方法**:
1. https://console.anthropic.com/ にアクセス
2. アカウントを作成
3. API Keysセクションでキーを生成

### 3. Streamlitアプリの起動

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` にアクセス

## 📖 使い方

### Webインターフェース（推奨）

1. Streamlitアプリを起動
2. 入札仕様書PDFをアップロード
3. 「処理開始」ボタンをクリック
4. 見積内容を確認
5. Excel形式でダウンロード

### サンプルで試す

テストファイルが含まれています:

```
test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】.pdf
```

期待される出力:
- 施設区分: 学校
- 工事区分: 電気、空調、衛生など
- 見積項目: 40-60項目程度
- 処理時間: 1-3分

## 📁 プロジェクト構成

```
ecolease-poc/
├── app.py                  # Streamlit UI
├── requirements.txt        # 依存パッケージ
├── .env.example           # 環境変数サンプル
├── README.md              # このファイル
├── configs/
│   └── config.yaml        # システム設定
├── pipelines/
│   ├── schemas.py         # データスキーマ
│   ├── ingest.py          # PDF解析
│   ├── normalize.py       # FMT正規化
│   ├── classify.py        # 分類
│   ├── rag_price.py       # 価格RAG
│   ├── estimate.py        # 見積生成（Claude使用）
│   └── export.py          # Excel出力
├── kb/                    # 過去見積データ
├── output/                # 生成ファイル
└── test-files/           # テストファイル
```

## 🔧 Dockerで実行

```bash
# ビルド & 起動
docker-compose up

# ブラウザで http://localhost:8501 にアクセス
```

## 💡 技術スタック

- **LLM**: Claude Sonnet 4.5（Anthropic最新モデル）
- **PDF処理**: PyMuPDF, pdfplumber
- **埋め込み**: BGE-M3
- **ベクトルDB**: FAISS
- **UI**: Streamlit
- **出力**: openpyxl (Excel)

## 📊 データフロー

```
入札仕様書PDF
    ↓
[PDF解析] テキスト・テーブル抽出
    ↓
[FMT正規化] 案件情報・建物仕様を構造化
    ↓
[分類] 施設区分・工事区分を判定
    ↓
[Claude + RAG] 見積項目生成・価格推定
    ↓
[Excel出力] 送付状・御見積書・明細書
```

## 🔧 カスタマイズ

### 過去見積データの追加

`kb/past_estimates/`にExcelファイルを配置:

| 項目名 | 仕様 | 単価 | 単位 | 案件名 | 日付 | 工事区分 |
|--------|------|------|------|--------|------|----------|
| LED照明 | 40W | 15000 | 台 | 〇〇学校 | 2024-01-15 | 電気 |

### LLMモデルの変更

`.env`ファイルで変更可能:

```env
CLAUDE_MODEL=claude-sonnet-4-5-20250929  # 最新モデル（推奨）
# または
CLAUDE_MODEL=claude-3-5-sonnet-20241022  # 前バージョン
```

## 📝 ライセンス

Proprietary - Ecolease社内使用のみ

## 🤝 サポート

問題が発生した場合は開発チームまでお問い合わせください。
