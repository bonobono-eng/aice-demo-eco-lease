# 見積生成デモ - AI見積書自動生成システム

入札仕様書PDFから見積書を自動生成するデモシステムです。

## 概要

- 仕様書PDFをアップロードするだけで見積書を自動生成
- 過去見積の単価データベース（KB）から単価を自動マッチング
- PDF/Excel形式で見積書を出力

## クイックスタート

### 1. 環境構築

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
```

`.env`ファイルを編集してAPIキーを設定:

```env
ANTHROPIC_API_KEY=your-api-key-here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

### 2. アプリ起動

```bash
streamlit run app.py
```

ブラウザで http://localhost:8501 にアクセス

## 機能一覧

### 見積書作成

仕様書PDFから見積書を自動生成します。

1. 仕様書PDFをアップロード
2. 生成モードを選択（AI自動生成 / 参照見積ベース）
3. 「生成開始」をクリック
4. PDF/Excelをダウンロード

### 単価データベース

過去の見積書から単価を抽出してナレッジベース（KB）を構築します。

- Excel/PDF見積書のアップロード
- 単価の自動抽出・カテゴリ分類
- KBの閲覧・編集・エクスポート

### 法令データベース

関係法令の管理機能です（準備中）。

### 利用状況

API利用状況とコストの確認ができます。

## ディレクトリ構成

```
aice-demo-eco-lease/
├── app.py                 # エントリーポイント
├── pages/
│   ├── 1.py               # 見積書作成
│   ├── 2.py               # 単価データベース
│   ├── 3.py               # 法令データベース
│   └── 4.py               # 利用状況
├── pipelines/
│   ├── schemas.py         # データスキーマ
│   ├── kb_builder.py      # KB構築
│   ├── estimate_generator_ai.py  # AI見積生成
│   ├── export.py          # PDF/Excel出力
│   └── ...
├── kb/
│   └── price_kb.json      # 単価KB
├── output/                # 生成ファイル出力先
└── test-files/            # テスト用ファイル
```

## 技術仕様

### 使用技術

| 項目 | 技術 |
|------|------|
| LLM | Claude Sonnet 4.5 |
| PDF処理 | PyPDF2, pdf2image |
| OCR | Claude Vision API |
| UI | Streamlit |
| 出力 | ReportLab (PDF), openpyxl (Excel) |

### 処理フロー

```
仕様書PDF
    │
    ├─ テキスト抽出（PyPDF2）
    │      └─ 失敗時: OCR（Claude Vision）
    │
    ├─ 建物情報抽出（Claude API）
    │      └─ 面積、階数、部屋数、ガス栓数等
    │
    ├─ 見積項目生成（Claude API）
    │      └─ 工事区分別に詳細項目を設計
    │
    ├─ KB単価照合
    │      ├─ 類似度計算
    │      ├─ 単位互換性チェック
    │      └─ 単価妥当性チェック
    │
    └─ 見積書出力（PDF/Excel）
```

### KB単価マッチング

詳細は `docs/KB_MATCHING_FLOW.md` を参照してください。

## 設定

### 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| ANTHROPIC_API_KEY | Claude APIキー | Yes |
| CLAUDE_MODEL | 使用モデル名 | No (default: claude-sonnet-4-5-20250929) |

### APIキーの取得

1. https://console.anthropic.com/ にアクセス
2. アカウント作成
3. API Keysセクションでキーを生成

## テスト

テスト用の仕様書が含まれています:

```
test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】.pdf
```

## トラブルシューティング

### アプリが起動しない

```bash
# ポートが使用中の場合
lsof -ti:8501 | xargs kill -9
streamlit run app.py
```

### KBが読み込めない

`kb/price_kb.json`が空または破損している場合:

```bash
echo "[]" > kb/price_kb.json
```

### APIエラー

- APIキーが正しく設定されているか確認
- API利用制限に達していないか確認

## ライセンス

社内使用のみ

## サポート

問題が発生した場合は開発チームまでお問い合わせください。
