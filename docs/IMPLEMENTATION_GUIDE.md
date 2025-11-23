# 実装ガイド

## 1. 環境構築

### 1.1 必要条件

| 項目 | 要件 |
|-----|------|
| Python | 3.10以上 |
| OS | macOS / Linux / Windows |
| メモリ | 8GB以上推奨 |
| ディスク | 1GB以上の空き容量 |

### 1.2 セットアップ手順

```bash
# 1. リポジトリクローン
git clone https://github.com/your-org/aice-demo-eco-lease.git
cd aice-demo-eco-lease

# 2. 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 依存関係インストール
pip install -r requirements.txt

# 4. 環境変数設定
export ANTHROPIC_API_KEY="your-api-key"
# または .env ファイルを作成
echo 'ANTHROPIC_API_KEY=your-api-key' > .env

# 5. 起動
streamlit run app.py
```

### 1.3 依存パッケージ

```txt
# requirements.txt
streamlit>=1.28.0
anthropic>=0.18.0
PyPDF2>=3.0.0
PyMuPDF>=1.23.0  # オプション（Vision機能用）
reportlab>=4.0.0
openpyxl>=3.1.0
pydantic>=2.0.0
loguru>=0.7.0
python-dotenv>=1.0.0
numpy>=1.24.0  # ベクトル計算用
```

### 1.4 ベクトル検索（オプション）

単価マッチングの精度向上のため、ベクトル検索機能が利用可能です：

```bash
# sentence-transformersをインストール（オプション）
pip install sentence-transformers
```

インストールされている場合、自動的にベクトル検索が有効になります。

---

## 2. プロジェクト構造

### 2.1 ディレクトリ構成

```
aice-demo-eco-lease/
├── app.py                   # エントリーポイント
├── pages/                   # Streamlitページ
│   ├── 1.py                 # 見積作成
│   ├── 2.py                 # 単価DB
│   ├── 3.py                 # 法令DB
│   └── 4.py                 # 利用状況
├── pipelines/               # バックエンド
│   ├── __init__.py
│   ├── schemas.py           # データモデル
│   ├── estimate_generator_ai.py
│   ├── kb_builder.py
│   ├── legal_requirement_extractor.py
│   ├── ocr_extractor.py
│   ├── pdf_generator.py
│   ├── export.py
│   └── cost_tracker.py
├── kb/                      # ナレッジベース
│   ├── price_kb.json
│   └── legal_kb.json
├── logs/                    # ログ
├── output/                  # 出力
├── docs/                    # ドキュメント
├── test-files/              # テストファイル
├── fonts/                   # 日本語フォント
│   └── ipaexg.ttf
├── requirements.txt
└── .env                     # 環境変数（gitignore）
```

### 2.2 命名規則

| 種類 | 規則 | 例 |
|-----|------|-----|
| ファイル | snake_case | `estimate_generator_ai.py` |
| クラス | PascalCase | `AIEstimateGenerator` |
| 関数 | snake_case | `extract_building_info()` |
| 定数 | UPPER_SNAKE | `SYNONYM_DICT` |
| 変数 | snake_case | `spec_text` |

---

## 3. 主要モジュールの実装詳細

### 3.1 schemas.py（データモデル）

#### 工事区分の定義

```python
from enum import Enum

class DisciplineType(str, Enum):
    """工事区分"""
    ELECTRICAL = "電気設備工事"
    MECHANICAL = "機械設備工事"
    GAS = "ガス設備工事"
    PLUMBING = "給排水設備工事"
    FIRE_PROTECTION = "消防設備工事"
    OTHER = "その他"
```

#### 見積項目モデル

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class EstimateItem(BaseModel):
    """見積項目"""
    item_number: str = ""
    name: str
    specification: str = ""
    quantity: Optional[float] = None
    unit: str = ""
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    level: int = Field(default=0, ge=0, le=3)
    discipline: DisciplineType
    confidence: float = Field(default=0.5, ge=0, le=1)
    source_reference: str = ""
    price_references: List[str] = Field(default_factory=list)
```

#### FMTDocument（見積書全体）

```python
class FMTDocument(BaseModel):
    """見積書ドキュメント"""
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "2.0"
    created_at: datetime = Field(default_factory=datetime.now)
    project_info: ProjectInfo
    items: List[EstimateItem] = Field(default_factory=list)
    total_amount: float = 0
    legal_references: List[LegalReference] = Field(default_factory=list)
```

---

### 3.2 estimate_generator_ai.py（見積生成エンジン）

#### クラス構造

```python
class AIEstimateGenerator:
    """AI自動見積生成器"""

    def __init__(self):
        self.client = Anthropic()
        self.model = "claude-sonnet-4-20250514"
        self.kb_items = self._load_kb()

    def generate_estimate(
        self,
        spec_pdf_path: str,
        disciplines: List[DisciplineType]
    ) -> FMTDocument:
        """見積書を生成"""
        # 1. テキスト抽出
        spec_text = self.extract_text_from_pdf(spec_pdf_path)

        # 2. 建物情報抽出
        building_info = self.extract_building_info(spec_text)

        # 3. Vision抽出（オプション）
        if PYMUPDF_AVAILABLE:
            vision_data = self.extract_specification_table_with_vision(spec_pdf_path)
            building_info.update(vision_data)

        # 4. 見積項目生成（工事区分別）
        items = []
        for discipline in disciplines:
            discipline_items = self.generate_detailed_items(
                discipline, building_info, spec_text
            )
            items.extend(discipline_items)

        # 5. 単価マッチング
        items = self.enrich_with_prices(items)

        # 6. 金額計算
        items = self.calculate_amounts(items)

        # 7. FMTDocument生成
        return self._create_fmt_document(building_info, items)
```

#### テキスト抽出

```python
def extract_text_from_pdf(self, pdf_path: str) -> str:
    """PDFからテキストを抽出"""
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num, page in enumerate(pdf_reader.pages):
            text += f"\n[PAGE {page_num + 1}]\n"
            text += page.extract_text() or ""

    # 長すぎる場合は切り詰め（LLMトークン制限対策）
    if len(text) > 60000:
        text = text[:60000]
        logger.warning("Text truncated to 60000 characters")

    return text
```

#### 建物情報抽出（LLM使用）

```python
def extract_building_info(self, spec_text: str) -> Dict[str, Any]:
    """LLMで建物情報を抽出"""
    prompt = f"""
以下の仕様書テキストから建物情報を抽出してJSON形式で出力してください。

抽出項目:
- project_name: 工事名
- location: 工事場所
- floor_area_m2: 延床面積（㎡）
- num_floors: 階数
- building_type: 建物用途
- num_rooms: 部屋数
- contract_period: 工期

仕様書:
{spec_text[:30000]}

JSON形式で出力:
"""

    response = self.client.messages.create(
        model=self.model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    # コスト記録
    record_cost(
        operation="建物情報抽出",
        model_name=self.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens
    )

    return json.loads(response.content[0].text)
```

#### Vision抽出（諸元表）

```python
def extract_specification_table_with_vision(
    self,
    pdf_path: str,
    pages: List[int] = [39, 40]
) -> Dict[str, Any]:
    """Vision APIで諸元表を抽出"""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    images = []

    for page_num in pages:
        if page_num < len(doc):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            images.append(base64.b64encode(pix.tobytes("png")).decode())

    # Vision APIで解析
    content = []
    for img in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img}
        })
    content.append({
        "type": "text",
        "text": "この諸元表から部屋タイプ、ガス栓数、コンセント数を抽出してJSON形式で出力してください。"
    })

    response = self.client.messages.create(
        model=self.model,
        max_tokens=4000,
        messages=[{"role": "user", "content": content}]
    )

    record_cost(
        operation="諸元表Vision抽出",
        model_name=self.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens
    )

    return json.loads(response.content[0].text)
```

#### 単価マッチング

```python
def enrich_with_prices(self, items: List[EstimateItem]) -> List[EstimateItem]:
    """KBから単価をマッチング"""
    for item in items:
        if item.level == 0 or not item.quantity:
            continue  # 親項目・数量なしはスキップ

        best_match = None
        best_score = 0

        for kb in self.kb_items:
            # discipline互換性チェック
            if not self._is_discipline_compatible(kb['discipline'], item.discipline.value):
                continue

            # 単位互換性チェック
            if not self._is_unit_compatible(kb['unit'], item.unit):
                continue

            # スコア計算
            score = self._calculate_match_score(item, kb)

            if score > best_score:
                best_score = score
                best_match = kb

        # マッチング適用
        if best_match and best_score >= 1.0:
            # 単価妥当性チェック
            if self._validate_price(item.name, best_match['unit_price']):
                item.unit_price = best_match['unit_price']
                item.source_reference = f"KB:{best_match['item_id']}(score={best_score:.2f})"
                item.price_references.append(best_match['item_id'])

    return items
```

---

### 3.3 cost_tracker.py（コスト追跡）

#### セッション管理

```python
# グローバル変数
_current_session_id: Optional[str] = None
_current_session_name: Optional[str] = None

def start_session(session_name: str = "見積作成") -> str:
    """新しいセッションを開始"""
    global _current_session_id, _current_session_name
    _current_session_id = str(uuid.uuid4())[:8]
    _current_session_name = session_name
    logger.info(f"Session started: {_current_session_id} ({session_name})")
    return _current_session_id

def end_session() -> Optional[Dict[str, Any]]:
    """セッションを終了し合計を返す"""
    global _current_session_id, _current_session_name
    if _current_session_id is None:
        return None

    tracker = get_tracker()
    summary = tracker.get_session_summary(_current_session_id)

    if summary["total_cost_jpy"] > 0:
        tracker.record_session_complete(
            _current_session_id,
            _current_session_name or "見積作成",
            summary
        )

    _current_session_id = None
    _current_session_name = None
    return summary
```

#### コスト記録

```python
def record_cost(
    operation: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """API呼び出しのコストを記録"""
    return get_tracker().record(
        operation=operation,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        metadata=metadata
    )
```

#### 料金計算

```python
class CostTracker:
    # Claude API料金
    PRICING = {
        "claude-sonnet-4-20250514": {
            "input": 3.00,   # $3/1Mトークン
            "output": 15.00  # $15/1Mトークン
        }
    }
    USD_JPY_RATE = 150.0

    def calculate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, float]:
        pricing = self.get_pricing(model_name)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_usd = input_cost + output_cost
        total_jpy = total_usd * self.USD_JPY_RATE

        return {
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": total_usd,
            "total_cost_jpy": total_jpy
        }
```

---

### 3.4 pdf_generator.py（PDF生成）

#### 初期化

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class EcoleasePDFGenerator:
    def __init__(self):
        # 日本語フォント登録
        font_path = Path(__file__).parent.parent / "fonts" / "ipaexg.ttf"
        if font_path.exists():
            pdfmetrics.registerFont(TTFont('IPAexGothic', str(font_path)))
            self.font_name = 'IPAexGothic'
        else:
            self.font_name = 'Helvetica'
```

#### 見積書生成

```python
def generate_pdf(
    self,
    fmt_doc: FMTDocument,
    output_path: str
) -> str:
    """見積書PDFを生成"""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm
    )

    elements = []

    # 1. 御見積書ページ
    elements.extend(self._create_quotation_page(fmt_doc))

    # 2. 見積内訳明細書
    elements.extend(self._create_detail_pages(fmt_doc))

    doc.build(elements)
    return output_path
```

---

## 4. 新機能の追加方法

### 4.1 新しい工事区分を追加

```python
# 1. schemas.py: DisciplineType に追加
class DisciplineType(str, Enum):
    # ...既存...
    ELEVATOR = "エレベーター設備工事"  # 新規追加

# 2. estimate_generator_ai.py: 生成メソッド追加
def generate_detailed_items_for_elevator(
    self,
    building_info: Dict,
    spec_text: str
) -> List[EstimateItem]:
    """エレベーター設備の見積項目を生成"""
    # 実装

# 3. kb/price_kb.json: KB項目追加
{
    "item_id": "ELEV_001",
    "description": "乗用エレベーター",
    "discipline": "エレベーター設備工事",
    "unit": "台",
    "unit_price": 5000000
}
```

### 4.2 新しいLLM操作を追加

```python
# 1. 操作を実装
def new_llm_operation(self, input_data):
    response = self.client.messages.create(
        model=self.model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    # 2. コスト記録を必ず追加
    record_cost(
        operation="新規操作名",  # 利用状況に表示される
        model_name=self.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        metadata={"key": "value"}  # オプション
    )

    return response.content[0].text
```

### 4.3 新しいページを追加

```python
# pages/5.py として作成
import streamlit as st

st.set_page_config(page_title="新機能", page_icon="🆕")

def main():
    st.title("新機能")
    # 実装

if __name__ == "__main__":
    main()
```

---

## 5. テスト

### 5.1 ユニットテスト

```python
# tests/test_estimate_generator.py
import pytest
from pipelines.estimate_generator_ai import AIEstimateGenerator
from pipelines.schemas import DisciplineType

def test_extract_building_info():
    generator = AIEstimateGenerator()
    spec_text = "工事名: テスト工事\n工事場所: 東京都..."

    info = generator.extract_building_info(spec_text)

    assert "project_name" in info
    assert info["project_name"] == "テスト工事"

def test_match_price():
    generator = AIEstimateGenerator()
    item = EstimateItem(
        name="白ガス管",
        specification="15A",
        unit="m",
        discipline=DisciplineType.GAS
    )

    generator.enrich_with_prices([item])

    assert item.unit_price is not None
```

### 5.2 実行

```bash
# 全テスト実行
pytest tests/

# 特定テスト
pytest tests/test_estimate_generator.py -v
```

---

## 6. トラブルシューティング

### 6.1 よくある問題

| 問題 | 原因 | 解決策 |
|-----|------|--------|
| `ANTHROPIC_API_KEY not set` | 環境変数未設定 | `.env`ファイル確認 |
| PDF生成で文字化け | フォント未登録 | `fonts/ipaexg.ttf`を配置 |
| Vision機能エラー | PyMuPDF未インストール | `pip install PyMuPDF` |
| 単価マッチング0% | discipline不一致 | schemas.pyとKBを確認 |

### 6.2 ログ確認

```python
# loguru設定
from loguru import logger

logger.add("logs/app.log", rotation="1 day")
logger.info("処理開始")
logger.error("エラー発生")
```

```bash
# ログ確認
tail -f logs/app.log
```

---

## 7. デプロイ

### 7.1 Streamlit Cloud

```bash
# 1. GitHubにプッシュ
git push origin main

# 2. Streamlit Cloudでアプリ作成
# - https://share.streamlit.io/
# - リポジトリを選択
# - Secrets にAPIキーを設定
```

### 7.2 Docker

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

```bash
docker build -t eco-lease .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=xxx eco-lease
```

---

*最終更新: 2025年11月*
