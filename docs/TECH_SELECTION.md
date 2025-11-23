# 技術選定と選定理由

## 1. 技術スタック概要

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|-----------|------|
| **言語** | Python | 3.10+ | メイン開発言語 |
| **Web UI** | Streamlit | 1.x | インタラクティブUI |
| **LLM** | Claude Sonnet 4 | claude-sonnet-4-20250514 | テキスト/画像処理 |
| **PDF処理** | PyPDF2, PyMuPDF | - | テキスト抽出、画像変換 |
| **PDF生成** | ReportLab | - | 見積書PDF出力 |
| **Excel出力** | openpyxl | - | Excel形式出力 |
| **データ検証** | Pydantic | 2.x | スキーマ定義・検証 |
| **ログ** | Loguru | - | ログ出力 |

---

## 2. 各技術の選定理由

### 2.1 Web UI: Streamlit

#### 選定理由

| 観点 | Streamlit | 他の選択肢 | 判断 |
|------|-----------|-----------|------|
| **開発速度** | Pythonのみで完結 | Flask/Django + HTML/JS | Streamlit ◎ |
| **データサイエンス連携** | pandas/plotly統合済み | 追加実装が必要 | Streamlit ◎ |
| **ファイルアップロード** | 標準コンポーネント | 追加実装が必要 | Streamlit ◎ |
| **セッション管理** | st.session_state | サーバーサイド実装 | Streamlit ○ |
| **デプロイ** | Streamlit Cloud対応 | 独自インフラ | Streamlit ○ |

#### 採用の決め手

1. **高速プロトタイピング**: Python開発者がフロントエンドをすぐに構築可能
2. **データ可視化**: 精度レポートやコスト表示に最適
3. **ファイル操作**: PDFアップロード/ダウンロードが簡単
4. **マルチページ対応**: `pages/` ディレクトリで自動ルーティング

#### コード例

```python
# ファイルアップロード
uploaded_file = st.file_uploader("仕様書PDF", type=["pdf"])

# プログレスバー
with st.spinner("見積生成中..."):
    result = generate_estimate(uploaded_file)

# データ表示
st.dataframe(result.items)

# ダウンロードボタン
st.download_button("PDF", pdf_bytes, "見積書.pdf")
```

---

### 2.2 LLM: Anthropic Claude Sonnet 4

#### 選定理由

| 観点 | Claude Sonnet 4 | GPT-4 | Gemini Pro |
|------|----------------|-------|------------|
| **日本語精度** | ◎ 優秀 | ○ 良好 | ○ 良好 |
| **長文処理** | ◎ 200Kトークン | ○ 128Kトークン | ◎ 1Mトークン |
| **Vision機能** | ◎ 高精度 | ○ 良好 | ○ 良好 |
| **API料金** | ○ $3/$15 | △ $10/$30 | ◎ 低コスト |
| **レスポンス速度** | ○ 良好 | ○ 良好 | ◎ 高速 |
| **構造化出力** | ◎ JSON対応 | ◎ Function対応 | ○ 対応 |

#### 採用の決め手

1. **日本語の建築用語処理**: 専門用語（キュービクル、分電盤、白ガス管等）を正確に理解
2. **長文仕様書対応**: 50ページ超のPDFテキストを一度に処理可能
3. **Vision機能**: 諸元表や図面を画像として解析可能
4. **構造化出力**: JSON形式で見積項目を出力（パース不要）

#### コード例

```python
from anthropic import Anthropic

client = Anthropic()

# テキスト処理
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=8000,
    messages=[{"role": "user", "content": prompt}]
)

# Vision処理（画像解析）
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "data": image_base64}},
            {"type": "text", "text": "この諸元表から部屋情報を抽出してください"}
        ]
    }]
)
```

---

### 2.3 PDF処理: PyPDF2 + PyMuPDF

#### 選定理由

| 観点 | PyPDF2 | PyMuPDF (fitz) | pdfplumber |
|------|--------|----------------|------------|
| **テキスト抽出** | ○ 基本対応 | ◎ 高精度 | ◎ 高精度 |
| **画像抽出** | × 非対応 | ◎ 対応 | △ 制限あり |
| **依存関係** | ◎ 軽量 | △ バイナリ | ○ 中程度 |
| **処理速度** | ◎ 高速 | ◎ 高速 | ○ 中程度 |
| **ライセンス** | BSD | AGPL | MIT |

#### 採用の決め手

**PyPDF2を基本採用した理由**:
1. **軽量**: 依存関係が少なく、デプロイが容易
2. **高速**: 大きなPDFでも高速にテキスト抽出
3. **安定性**: 長年の実績があり、枯れた技術

**PyMuPDFをオプション採用した理由**:
1. **画像変換**: PDFページを画像に変換してVision APIに渡す
2. **Vision機能の前提**: 諸元表・図面解析に必須

#### コード例

```python
# PyPDF2: テキスト抽出
import PyPDF2

with open(pdf_path, 'rb') as f:
    reader = PyPDF2.PdfReader(f)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

# PyMuPDF: 画像変換（Vision用）
import fitz  # PyMuPDF

doc = fitz.open(pdf_path)
page = doc[page_num]
pix = page.get_pixmap(dpi=150)
image_bytes = pix.tobytes("png")
```

---

### 2.4 PDF生成: ReportLab

#### 選定理由

| 観点 | ReportLab | WeasyPrint | PyFPDF |
|------|-----------|------------|--------|
| **日本語対応** | ◎ フォント登録で対応 | ○ CSS指定 | ○ 対応 |
| **帳票レイアウト** | ◎ 精密制御可能 | △ HTML/CSS | ○ 基本対応 |
| **表組み** | ◎ Table機能 | ○ HTML table | △ 制限あり |
| **罫線・装飾** | ◎ 細かく制御 | ○ CSS | △ 制限あり |
| **処理速度** | ◎ 高速 | △ 遅い | ◎ 高速 |

#### 採用の決め手

1. **帳票レイアウト**: 見積書の厳密なレイアウト制御が可能
2. **表組み**: 見積明細の複雑な表を正確に描画
3. **日本語**: IPAexゴシックフォント登録で完全対応
4. **実績**: 業務系システムでの採用実績が豊富

#### コード例

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 日本語フォント登録
pdfmetrics.registerFont(TTFont('IPAexGothic', 'ipaexg.ttf'))

# PDF生成
doc = SimpleDocTemplate("見積書.pdf", pagesize=A4)
table = Table(data)
table.setStyle(TableStyle([
    ('FONT', (0,0), (-1,-1), 'IPAexGothic'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
]))
doc.build([table])
```

---

### 2.5 データ検証: Pydantic

#### 選定理由

| 観点 | Pydantic | dataclasses | attrs |
|------|----------|-------------|-------|
| **型検証** | ◎ 実行時検証 | × なし | △ 制限あり |
| **JSON変換** | ◎ 標準対応 | △ 追加実装 | △ 追加実装 |
| **バリデーション** | ◎ 詳細なルール | × なし | △ 制限あり |
| **ネスト構造** | ◎ 自然に対応 | ○ 対応 | ○ 対応 |
| **IDE補完** | ◎ 優秀 | ◎ 優秀 | ○ 良好 |

#### 採用の決め手

1. **データ整合性**: 見積データの整合性を自動検証
2. **JSON互換**: LLM出力のJSONを直接パース可能
3. **型安全性**: 開発時のミスを早期発見
4. **ドキュメント生成**: スキーマから自動ドキュメント

#### コード例

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class EstimateItem(BaseModel):
    name: str = Field(..., min_length=1)
    quantity: float = Field(..., ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    confidence: float = Field(..., ge=0, le=1)

# LLM出力をパース
data = json.loads(llm_response)
item = EstimateItem(**data)  # 自動検証
```

---

### 2.6 単価マッチング: ハイブリッド方式

#### 選定理由（ベクトル検索 + キーワードマッチング）

| 観点 | ベクトル検索のみ | キーワードのみ | ハイブリッド（採用） |
|------|----------------|--------------|-------------------|
| **検索速度** | ◎ 高速 | △ 全件スキャン | ◎ 高速 |
| **仕様の厳密性** | △ 誤マッチの恐れ | ◎ 明確に区別 | ◎ 両方の利点 |
| **未知項目対応** | ◎ 類似検索可能 | × マッチしない | ◎ 対応可能 |
| **マッチング率** | ○ 50%程度 | △ 30%程度 | ◎ **67%+** |
| **コスト** | △ 外部API | ◎ なし | ◎ ローカル実行 |

#### 採用の決め手

1. **sentence-transformers** をローカルで実行（API費用なし）
2. ベクトル検索で候補を絞り込み → キーワードで精密マッチング
3. 単位・仕様の厳密チェックで誤マッチを防止

**実績**:
```
Price matching: 72/107 items (67.3%)
  - Vector search matches: 50
  - String matching matches: 23
```

#### コード例

```python
def match_price(item, kb_items):
    # Step 1: ベクトル検索で候補抽出
    if self.embedder:
        vector_match = self._vector_search_match(item.name, item.specification)
        if vector_match and vector_match['score'] >= 0.85:
            # 単位互換性チェック
            if self._is_unit_compatible(vector_match['unit'], item.unit):
                return vector_match

    # Step 2: キーワードマッチング
    best_match = None
    best_score = 0

    for kb in kb_items:
        # discipline/単位の互換性チェック
        if not self._is_discipline_compatible(kb['discipline'], item.discipline):
            continue
        if not self._is_unit_compatible(kb['unit'], item.unit):
            continue

        score = self._calculate_match_score(item, kb)
        if score > best_score:
            best_score = score
            best_match = kb

    return best_match if best_score >= 1.0 else None
```

---

## 3. 不採用技術と理由

### 3.1 LangChain

| 理由 | 詳細 |
|-----|------|
| **過剰な抽象化** | シンプルなAPI呼び出しには不要 |
| **学習コスト** | 独自の概念（Chain, Agent等）の理解が必要 |
| **デバッグ困難** | 抽象化層が多くトラブルシュートが難しい |

**代替**: Anthropic SDKを直接使用

### 3.2 ベクトルDB (FAISS, Pinecone等)

| 理由 | 詳細 |
|-----|------|
| **精度問題** | 建築設備の仕様違いを区別できない |
| **コスト** | Embedding APIの追加コスト |
| **複雑性** | インデックス管理が必要 |

**代替**: キーワードマッチング + 類義語辞書

### 3.3 Django/FastAPI

| 理由 | 詳細 |
|-----|------|
| **開発速度** | フロントエンド別途開発が必要 |
| **用途** | デモ/POC段階では過剰 |
| **学習コスト** | チーム全員がフルスタック必要 |

**代替**: Streamlit（Pythonのみで完結）

---

## 4. 将来の技術検討

### 検討中の技術

| 技術 | 用途 | 検討理由 |
|-----|------|---------|
| **FastAPI** | 本番API化 | スケーラビリティ |
| **PostgreSQL** | KB永続化 | 大規模データ対応 |
| **Redis** | キャッシュ | レスポンス高速化 |
| **AWS Bedrock** | マルチLLM | コスト最適化 |

### 移行シナリオ

```
現在（POC）           →    将来（本番）
Streamlit            →    FastAPI + React
JSONファイル          →    PostgreSQL
ローカル実行          →    AWS/GCP

※ pipelinesモジュールは変更不要（疎結合設計）
```

---

*最終更新: 2025年11月*
