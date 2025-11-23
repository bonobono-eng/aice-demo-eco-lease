# システムアーキテクチャ

## 1. システム概要

本システムは、建築設備工事の仕様書PDFから見積書を自動生成するAIアプリケーションです。

### 目的

- 仕様書PDFを入力として、詳細な見積書を自動生成
- 過去の見積データを学習し、適切な単価を提案
- 法令要件を自動抽出し、見積項目に反映
- 見積作成業務の効率化と精度向上

### 対象工事区分

| 工事区分 | 対象設備例 |
|---------|-----------|
| 電気設備工事 | キュービクル、分電盤、照明器具、配線 |
| 機械設備工事 | 空調機、給排水設備、換気設備 |
| ガス設備工事 | ガス配管、ガス栓、安全機器 |

---

## 2. システム構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                      フロントエンド                               │
│                     Streamlit Web UI                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ 見積作成  │  │ 単価DB   │  │ 法令DB   │  │ 利用状況  │        │
│  │ pages/1  │  │ pages/2  │  │ pages/3  │  │ pages/4  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      バックエンド                                │
│                     pipelines/                                  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              estimate_generator_ai.py                   │    │
│  │              メイン見積生成エンジン                        │    │
│  │  ・建物情報抽出  ・見積項目生成  ・単価マッチング          │    │
│  └────────────────────────────────────────────────────────┘    │
│                              │                                  │
│          ┌──────────────────┼──────────────────┐               │
│          ▼                  ▼                  ▼               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ kb_builder  │    │ legal_req   │    │ cost_tracker│        │
│  │ 単価KB構築   │    │ 法令抽出     │    │ コスト追跡  │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│          │                  │                  │               │
│          ▼                  ▼                  ▼               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ ocr_extract │    │ pdf_gen     │    │ export      │        │
│  │ OCR処理     │    │ PDF生成     │    │ Excel出力   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   外部API     │    │   データ      │    │   出力       │
│              │    │              │    │              │
│ Anthropic    │    │ kb/          │    │ output/      │
│ Claude API   │    │ ├price_kb    │    │ ├PDF         │
│ (Sonnet 4)   │    │ └legal_kb    │    │ ├Excel       │
│              │    │              │    │ └JSON        │
│ Vision API   │    │ logs/        │    │              │
│ (図面解析)    │    │ └api_costs   │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 3. モジュール構成

### ディレクトリ構造

```
aice-demo-eco-lease/
├── app.py                   # メインエントリーポイント
├── pages/                   # Streamlit マルチページ
│   ├── 1.py                 # 見積作成ページ
│   ├── 2.py                 # 単価データベースページ
│   ├── 3.py                 # 法令データベースページ
│   └── 4.py                 # 利用状況ページ
├── pipelines/               # バックエンド処理モジュール
│   ├── schemas.py           # Pydanticスキーマ定義
│   ├── estimate_generator_ai.py  # メイン見積生成（AI自動）
│   ├── estimate_from_reference.py  # 参照見積ベース生成
│   ├── estimate_extractor.py     # LLM見積項目抽出
│   ├── estimate_extractor_v2.py  # 改善版抽出器
│   ├── estimate_generator.py     # RAG統合版生成
│   ├── estimate_generator_with_legal.py  # 法令統合版生成
│   ├── estimate_validator.py     # 見積精度検証
│   ├── kb_builder.py        # 単価KB構築
│   ├── legal_requirement_extractor.py  # 法令抽出
│   ├── inquiry_extractor.py # 質疑抽出器
│   ├── ocr_extractor.py     # OCR処理（Vision API）
│   ├── project_info_extractor.py  # プロジェクト情報抽出
│   ├── email_extractor.py   # メール情報抽出
│   ├── pdf_generator.py     # PDF生成
│   ├── export.py            # Excel/PDF出力
│   ├── cost_tracker.py      # APIコスト追跡
│   ├── logging_config.py    # ログ設定
│   ├── ingest.py            # データ取り込み
│   ├── normalize.py         # データ正規化
│   ├── classify.py          # 分類処理
│   └── rag_price.py         # RAG単価検索
├── kb/                      # ナレッジベース
│   ├── price_kb.json        # 単価データベース
│   └── legal_kb.json        # 法令データベース
├── logs/                    # ログファイル
│   ├── api_costs.json       # APIコスト履歴
│   ├── app_YYYYMMDD.log     # アプリログ
│   └── error_YYYYMMDD.log   # エラーログ
├── output/                  # 出力ファイル
├── test-files/              # テスト用ファイル
├── fonts/                   # 日本語フォント
└── docs/                    # ドキュメント
```

### 主要モジュール説明

| モジュール | ファイル | 責務 |
|-----------|---------|------|
| **スキーマ定義** | schemas.py | Pydanticによるデータモデル定義（FMTDocument、EstimateItem等） |
| **AI見積生成** | estimate_generator_ai.py | AIによる見積項目生成、単価マッチング（メイン） |
| **参照見積生成** | estimate_from_reference.py | 過去見積をテンプレートとした生成 |
| **見積抽出** | estimate_extractor.py | LLMによる見積項目抽出 |
| **見積検証** | estimate_validator.py | 生成見積の精度検証 |
| **KB構築** | kb_builder.py | PDF/Excel見積書からの単価データ抽出 |
| **法令抽出** | legal_requirement_extractor.py | 法令要件の抽出・構造化 |
| **質疑抽出** | inquiry_extractor.py | 信頼度低の項目から質疑書生成 |
| **OCR** | ocr_extractor.py | スキャンPDFのOCR処理（Vision API） |
| **プロジェクト情報** | project_info_extractor.py | 仕様書からプロジェクト情報抽出 |
| **メール抽出** | email_extractor.py | メールからの情報抽出 |
| **PDF生成** | pdf_generator.py | 見積書PDFの生成（ReportLab） |
| **Excel出力** | export.py | Excel/PDF形式での出力 |
| **コスト追跡** | cost_tracker.py | LLM API利用料金の追跡（セッション別） |
| **ログ設定** | logging_config.py | Loguruによるログ設定 |
| **RAG検索** | rag_price.py | 単価のベクトル検索 |

---

## 4. データフロー

### 見積書生成フロー

```
[入力]                    [処理]                      [出力]
仕様書PDF ─────────────────────────────────────────▶ 見積書PDF
    │                                                   ▲
    ▼                                                   │
┌───────────────┐                              ┌───────────────┐
│ PyPDF2        │                              │ ReportLab     │
│ テキスト抽出   │                              │ PDF生成       │
└───────────────┘                              └───────────────┘
    │                                                   ▲
    ▼                                                   │
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│ Claude API    │ ───▶ │ 単価KB照合     │ ───▶ │ 金額計算      │
│ 建物情報抽出   │      │ キーワード     │      │ 数量×単価     │
│ 見積項目生成   │      │ マッチング     │      │ 合計計算      │
└───────────────┘      └───────────────┘      └───────────────┘
    │
    ▼
┌───────────────┐
│ Vision API    │
│ 諸元表・図面   │
│ 読み取り       │
└───────────────┘
```

### セッション別コスト追跡フロー

```
見積作成開始
    │
    ▼
┌───────────────┐
│ start_session │ ─────▶ session_id生成
└───────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ 各LLM呼び出し                          │
│  ├─ 建物情報抽出    → record_cost()   │
│  ├─ Vision抽出     → record_cost()   │
│  ├─ 見積項目生成    → record_cost()   │
│  └─ ...                              │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────┐
│ end_session   │ ─────▶ セッション合計計算
└───────────────┘              │
                               ▼
                        ┌───────────────┐
                        │ 利用状況表示   │
                        │ 見積別コスト   │
                        └───────────────┘
```

---

## 5. データモデル

### DisciplineType（工事区分）

```python
class DisciplineType(str, Enum):
    """工事区分"""
    ELECTRICAL = "電気設備工事"
    MECHANICAL = "機械設備工事"
    HVAC = "空調設備工事"
    PLUMBING = "衛生設備工事"
    GAS = "ガス設備工事"
    FIRE_PROTECTION = "消防設備工事"
    CONSTRUCTION = "建築工事"
```

### CostType（費用区分）

```python
class CostType(str, Enum):
    """費用区分"""
    MATERIAL = "材料費"       # 材料単価 × 数量
    LABOR = "労務費"          # 作業員単価 × 人数 × 日数
    CONSTRUCTION = "施工費"   # 工事範囲に応じた一式計上
    OVERHEAD = "諸経費"       # 法定福利費、現場管理費
    LUMP_SUM = "一式"         # 工種別一式金額
    EQUIPMENT = "機器費"      # キュービクル等の機器
    DEMOLITION = "解体費"     # 既存撤去・切断
    EXCAVATION = "掘削・埋戻し"
    RESTORATION = "復旧費"    # 舗装復旧等
```

### FMTDocument（見積書全体）

```python
class FMTDocument(BaseModel):
    """FMT統一フォーマット - メインドキュメント"""
    fmt_version: str = "1.0"            # FMTバージョン
    created_at: str                     # 作成日時
    project_info: ProjectInfo           # 案件情報
    facility_type: FacilityType         # 施設区分
    building_specs: List[BuildingSpec]  # 建物仕様
    disciplines: List[DisciplineType]   # 対象工事区分
    requirements: List[Requirement]     # 要求事項
    estimate_items: List[EstimateItem]  # 見積明細
    overhead_calculations: List[OverheadCalculation]  # 諸経費計算
    legal_references: List[LegalReference]  # 法令参照
    qa_items: List[QAItem]              # 質問事項
    raw_text: Optional[str]             # 抽出された生テキスト
    metadata: Dict[str, Any]            # メタデータ
```

### EstimateItem（見積項目）

```python
class EstimateItem(BaseModel):
    """見積明細項目"""
    item_no: str                        # 項番
    name: str                           # 名称
    specification: Optional[str]        # 仕様
    quantity: Optional[float]           # 数量
    unit: Optional[str]                 # 単位
    unit_price: Optional[float]         # 単価
    amount: Optional[float]             # 金額
    remarks: Optional[str]              # 摘要
    parent_item_no: Optional[str]       # 親項番
    level: int = 0                      # 階層レベル（0-3）
    discipline: Optional[DisciplineType]  # 工事区分
    cost_type: Optional[CostType]       # 費用区分

    # 計算ロジック
    calculation_formula: Optional[str]  # 計算式
    labor_unit_price: Optional[float]   # 労務単価
    labor_days: Optional[float]         # 人工数
    overhead_rate: Optional[float]      # 諸経費率
    overhead_base_amount: Optional[float]  # 諸経費基礎額

    # RAG/根拠情報
    source_type: Optional[str]          # 出典タイプ(rag|rule|manual)
    source_reference: Optional[str]     # 出典参照(KB ID/式/条文)
    confidence: Optional[float]         # 信頼度スコア(0-1)
    price_references: List[str]         # 価格参照ID一覧
```

### PriceReference（単価KB項目）

```python
class PriceReference(BaseModel):
    """過去価格参照（単価KB）"""
    item_id: str                        # 項目ID
    description: str                    # 項目説明
    discipline: DisciplineType          # 工事区分
    unit: str                           # 単位
    unit_price: float                   # 単価
    vendor: Optional[str]               # 業者
    valid_from: date                    # 有効期間開始
    valid_to: Optional[date]            # 有効期間終了
    source_project: str                 # 出典案件
    context_tags: List[str]             # コンテキストタグ
    features: Dict[str, Any]            # 特徴量
    similarity_score: float = 0.0       # 類似度スコア
```

---

## 6. 外部連携

### Anthropic Claude API

| 用途 | モデル | 機能 |
|-----|-------|------|
| テキスト処理 | claude-sonnet-4-20250514 | 建物情報抽出、見積項目生成 |
| 画像処理 | claude-sonnet-4-20250514 (Vision) | 諸元表・図面の読み取り |

### API料金

| 項目 | 料金 |
|-----|------|
| 入力トークン | $3.00 / 1Mトークン |
| 出力トークン | $15.00 / 1Mトークン |
| 為替レート | ¥150 / $1（固定） |

---

## 7. 設計原則

### 1. モジュラー設計

各機能を独立したモジュールに分離し、疎結合を維持。

```
estimate_generator_ai.py  # 見積生成（コア機能）
    └── kb_builder.py     # KB構築（独立モジュール）
    └── cost_tracker.py   # コスト追跡（横断機能）
```

### 2. 型安全性

Pydanticによる厳密な型定義でデータ整合性を保証。

```python
class EstimateItem(BaseModel):
    quantity: float = Field(..., ge=0)  # 0以上
    confidence: float = Field(..., ge=0, le=1)  # 0-1
```

### 3. トレーサビリティ

全ての見積項目に根拠情報を記録。

```python
item.source_reference = "KB:GAS_002[exact](score=3.50)"
item.price_references = ["GAS_002", "GAS_003"]
```

### 4. コスト透明性

LLM API呼び出しごとにコストを記録・表示。

```python
record_cost(
    operation="見積項目生成",
    model_name="claude-sonnet-4-20250514",
    input_tokens=8000,
    output_tokens=5000
)
```

---

## 8. セキュリティ考慮事項

### APIキー管理

- 環境変数 `ANTHROPIC_API_KEY` で管理
- コードにハードコーディングしない
- `.env` ファイルは `.gitignore` に追加

### データ保護

- 顧客情報を含むPDFは `output/` に一時保存
- 長期保存が必要な場合は暗号化を検討
- ログファイルに機密情報を含めない

---

## 9. パフォーマンス考慮事項

### LLM呼び出しの最適化

| 最適化手法 | 効果 |
|-----------|------|
| テキスト長制限（60,000文字） | トークン数削減 |
| 工事区分別処理 | 並列化可能 |
| KBキャッシュ | 起動時に一度だけ読み込み |

### 処理時間目安

| 処理 | 時間 |
|-----|------|
| 見積生成（AI自動・3区分） | 2-3分 |
| 見積生成（参照ベース） | 30秒-1分 |
| 単価KB構築（30ページPDF） | 1-2分 |

---

*最終更新: 2025年11月*
