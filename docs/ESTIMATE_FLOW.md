# 見積書作成フロー

## 1. システム概要

仕様書PDFから見積書を自動生成するAIシステム。

```
【入力】          【AI処理】           【KB照合】         【出力】

 仕様書PDF    →   Claude API     →    単価KB      →    見積書PDF
 ・本文            ・建物情報抽出        ・単価マッチング     ・御見積書
 ・図面            ・見積項目生成        ・妥当性チェック     ・内訳明細
 ・諸元表     →   Vision API     →    法令KB      →    Excel/JSON
                   ・表の読み取り        ・要件抽出          ・構造化データ
                   ・図面解析            ・遵守検証          ・精度レポート
```

### 入出力

| 種別 | 内容 |
|-----|------|
| **入力** | 仕様書PDF（図面・諸元表含む） |
| **出力** | 見積書PDF、Excel、JSON、精度レポート |

---

## 2. 処理フロー

```
仕様書PDF
    │
    ▼
┌──────────────────────────────────────┐
│ Step 1: テキスト抽出                  │
│ PyPDF2（全ページ）                    │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ Step 2: 建物情報抽出                  │
│ ・Claude API（テキスト→構造化）       │
│ ・Vision API（諸元表・図面）          │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ Step 3: 見積項目生成                  │
│ Claude API（工事区分別に詳細設計）    │
└──────────────────────────────────────┘
    │
    ├──────────────────────┐
    ▼                      ▼
┌────────────────┐   ┌────────────────┐
│ Step 4:        │   │ Step 5:        │
│ 単価KB照合     │   │ 法令KB照合     │
│ キーワード     │   │ 要件抽出       │
│ マッチング     │   │ 遵守検証       │
└────────────────┘   └────────────────┘
    │                      │
    └──────────┬───────────┘
               ▼
┌──────────────────────────────────────┐
│ Step 6: 金額計算                      │
│ ・数量×単価                          │
│ ・親項目の合計計算                    │
│ ・法定福利費（16.07%）                │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ Step 7: 出力                          │
│ PDF / Excel / JSON                    │
└──────────────────────────────────────┘
```

---

### Step 1: テキスト抽出

| 項目 | 内容 |
|-----|------|
| ツール | PyPDF2 |
| 処理 | PDFの全ページからテキスト抽出 |
| 出力 | テキスト（最大60,000文字をLLMへ送信） |

```python
# pipelines/estimate_generator_ai.py
def extract_text_from_pdf(self, pdf_path: str) -> str:
    pdf_reader = PyPDF2.PdfReader(file)
    for page_num in range(len(pdf_reader.pages)):
        text += f"[PAGE {page_num + 1}]\n"
        text += pdf_reader.pages[page_num].extract_text()
```

---

### Step 2: 建物情報抽出

2種類の抽出方法を併用。

| 方法 | 対象 | 抽出内容 |
|-----|------|---------|
| **Claude API（テキスト）** | 仕様書本文 | 工事名、場所、面積、階数、期間 |
| **Vision API** | 諸元表（39-40ページ） | 部屋数、ガス栓数、コンセント数 |
| **Vision API** | 図面（41-49ページ） | 設備配置、配管ルート |

```python
# テキストベース抽出
building_info = self.extract_building_info(spec_text)

# Vision抽出（諸元表）
vision_data = self.extract_specification_table_with_vision(pdf_path)

# Vision抽出（図面）
drawing_info = self.extract_drawing_info(pdf_path)
```

**Vision API使用条件**: PyMuPDFがインストールされている場合のみ有効

---

### Step 3: 見積項目生成

Claude APIが建物情報をもとに、工事区分別の詳細項目を設計。

| 工事区分 | 生成メソッド | 生成項目例 |
|---------|------------|-----------|
| ガス設備 | `generate_detailed_items_for_gas()` | 白ガス管15A/20A、ガスコンセント、撤去工事 |
| 電気設備 | `generate_detailed_items_for_electrical()` | キュービクル、分電盤、LED照明、配線 |
| 機械設備 | `generate_detailed_items_for_mechanical()` | 空調機、給水ポンプ、換気扇、衛生器具 |

**この時点では単価は空（null）**

---

### Step 4: 単価KB照合

詳細は「3. 単価KBマッチング」を参照。

---

### Step 5: 法令KB照合

詳細は「4. 法令KBフロー」を参照。

---

### Step 6: 金額計算

```python
# 1. 各項目の金額計算
item.amount = item.quantity * item.unit_price

# 2. 親項目は子項目の合計
for parent in parents:
    parent.amount = sum(child.amount for child in children)

# 3. 法定福利費（労務費の16.07%）
statutory_welfare = labor_cost * 0.1607
```

---

### Step 7: 出力

| 形式 | 内容 | 用途 |
|-----|------|------|
| PDF | 御見積書、見積内訳明細書 | 提出用 |
| Excel | 見積データ（根拠情報付き） | 編集・分析用 |
| JSON | FMTDocument構造化データ | システム連携 |

---

## 3. 単価KBマッチング

### ハイブリッドマッチング方式

本システムでは **ベクトル検索 + キーワードマッチング** のハイブリッド方式を採用。

| 方式 | 用途 | 特徴 |
|-----|------|------|
| **ベクトル検索** | 候補の初期絞り込み | 類似項目を高速に検索（sentence-transformers） |
| **キーワードマッチング** | 精密なスコアリング | 仕様・単位の厳密チェック |

### なぜハイブリッドか？

| 観点 | ベクトル検索のみ | キーワードのみ | ハイブリッド |
|-----|----------------|--------------|-------------|
| **検索速度** | ◎ 高速 | △ 全件スキャン | ◎ 高速 |
| **仕様の厳密性** | △ 誤マッチの恐れ | ◎ 明確に区別 | ◎ 両方の利点 |
| **未知項目対応** | ◎ 類似検索可能 | × マッチしない | ◎ 対応可能 |
| **マッチング率** | ○ 67% | △ 30% | ◎ 67%+ |

**実績（最新ログより）**:
```
Price matching: 72/107 items (67.3%)
  - Vector search matches: 50
  - String matching matches: 23
```

---

### マッチング処理フロー

```
見積項目
   │
   ├─ level==0 or 数量なし → スキップ
   │
   ▼
テキスト正規化（全角→半角、記号除去）
   │
   ▼
┌─────────────────────────────────────┐
│ Step 1: ベクトル検索（候補抽出）     │
│ sentence-transformers で類似度計算   │
│ score >= 0.85 で候補を抽出           │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│ Step 2: キーワードマッチング         │
│ ├─ discipline互換性チェック          │
│ ├─ 単位互換性チェック                │
│ ├─ 類義語展開（SYNONYM_DICT）        │
│ └─ スコア計算（項目名/仕様/単位）     │
└─────────────────────────────────────┘
   │
   ▼
単価妥当性チェック（HIGH_VALUE_ITEMS）
   │
   ├─ OK → 単価適用、金額計算
   └─ NG → 単価適用せず、信頼度低下
```

---

### スコア計算

| マッチ条件 | スコア | 説明 |
|-----------|--------|------|
| 項目名 完全一致 | **+2.0** | 正規化後の名前が一致 |
| 項目名 類義語一致 | **+1.8** | SYNONYM_DICT経由 |
| 項目名 部分一致 | +1.5 | 片方が他方を含む |
| カテゴリ一致 | +1.0 | 白ガス管、PE管等 |
| 仕様 完全一致 | +1.5 | 15A == 15A |
| サイズ一致 | +1.2 | 数値+単位が一致 |
| 単位 一致 | +0.5 | m, 式, 個 等 |

**適用条件**: `best_score >= 1.0` または `normalized_score >= 0.50`

---

### 類義語辞書

```python
SYNONYM_DICT = {
    "気中開閉器": ["PAS", "高圧気中負荷開閉器"],
    "キュービクル": ["高圧受電設備", "受変電設備"],
    "白ガス管": ["鋼管", "ガス管", "SGP"],
    "空冷ヒートポンプ": ["エアコン", "空調機"],
    # ...
}
```

---

### 単価妥当性チェック

高額機器に異常に低い単価がマッチしないよう検証。

```python
HIGH_VALUE_ITEMS = {
    "キュービクル": 1_000_000,    # 最低100万円
    "変圧器": 500_000,            # 最低50万円
    "発電機": 2_000_000,          # 最低200万円
    "エレベーター": 5_000_000,    # 最低500万円
}
```

---

## 4. 法令KBフロー

### 概要

仕様書から法令要件を抽出し、見積項目に反映すべき法令遵守事項を特定する。

```
仕様書テキスト
      │
      ▼
┌──────────────────────────────────┐
│ 法令要件抽出                      │
│ LegalRequirementExtractor        │
│ ・工事区分別の重要法令を特定      │
│ ・Claude APIで要件を構造化        │
└──────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────┐
│ 法令対応項目の追加                │
│ ・高信頼度（0.9以上）の要件のみ   │
│ ・見積項目として自動追加          │
└──────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────┐
│ 法令遵守検証                      │
│ ・見積項目が法令要件を満たすか    │
│ ・違反リスクを検出               │
└──────────────────────────────────┘
```

---

### 重要法令リスト

| カテゴリ | 法令名 |
|---------|-------|
| **共通** | 内線規程（JEAC 8001）、消防法、学校施設設備基準、東京都工事標準仕様書 |
| **電気設備** | 電気設備技術基準の解釈、公共建築工事標準仕様書(電気設備工事編) |
| **機械設備** | 建築設備設計基準、公共建築設備工事標準図（機械設備編） |
| **ガス設備** | ガス事業法、都市ガス事業法、液化石油ガス法 |

---

### 法令要件の抽出形式

```json
{
  "law_code": "JEAC8001",
  "law_name": "内線規程（JEAC 8001）",
  "requirement_type": "技術基準",
  "topic": "低圧屋内配線の保護",
  "description": "低圧屋内配線には適切な過電流保護装置を設置すること",
  "target_value": "定格電流の1.25倍以下",
  "applicable_items": ["分電盤", "配線用遮断器", "幹線"],
  "confidence": 0.9
}
```

---

### 法令遵守検証

```python
# 法令要件ごとに該当する見積項目が存在するかチェック
for legal_ref in legal_refs:
    matching_items = [
        item for item in estimate_items
        if any(keyword in item.name for keyword in legal_ref.applicable_items)
    ]

    if not matching_items:
        violations.append({
            "law": legal_ref.title,
            "message": "法令要件に該当する見積項目が見つかりません"
        })
```

---

## 5. KB管理

### ファイル構成

```
kb/
├── price_kb.json    # 単価KB（メイン）
└── legal_kb.json    # 法令KB
```

### 単価KBのデータ構造

```json
{
  "item_id": "GAS_001",
  "description": "白ガス管（ネジ接合）",
  "discipline": "ガス設備工事",
  "unit": "m",
  "unit_price": 8990.0,
  "features": {
    "specification": "15A",
    "quantity": 93
  },
  "context_tags": ["学校", "仮設"],
  "vendor": "株式会社エコリース",
  "valid_from": "2025-09-18",
  "source_project": "都立山崎高校仮設校舎"
}
```

### 法令KBのデータ構造

```json
{
  "law_code": "JEAC8001",
  "title": "内線規程",
  "article": "第3章 低圧屋内配線",
  "clause_text": "配線は適切な保護装置を設置すること",
  "applicable_items": ["分電盤", "配線"],
  "source_document": "関係法令一覧_追加１.pdf"
}
```

---

### KB構築方法

**単価KB（PDF見積書から）**:
```python
from pipelines.kb_builder import PriceKBBuilder

kb = PriceKBBuilder()
items = kb.extract_estimate_from_pdf("見積書.pdf")
kb.save_kb_to_json(items, "kb/price_kb.json")
```

**法令KB（法令PDFから）**:
```python
# pages/3_LegalDB.py のUIからアップロード
# または
from pages.3_LegalDB import LegalKBBuilder

kb = LegalKBBuilder()
items = kb.extract_legal_from_pdf("法令.pdf")
kb.save_kb()
```

### UI操作

| ページ | 機能 |
|-------|------|
| `pages/2_PriceDB.py` | 単価DBのアップロード・管理 |
| `pages/3_LegalDB.py` | 法令DBのアップロード・管理 |

---

## 6. 関連ファイル一覧

| ファイル | 役割 |
|---------|------|
| `pipelines/estimate_generator_ai.py` | メイン見積生成エンジン |
| `pipelines/kb_builder.py` | 単価KB構築 |
| `pipelines/legal_requirement_extractor.py` | 法令要件抽出 |
| `pipelines/estimate_generator_with_legal.py` | 法令統合版見積生成 |
| `pipelines/export.py` | PDF/Excel出力 |
| `pages/1_Estimate.py` | 見積作成UI |
| `pages/2_PriceDB.py` | 単価DB管理UI |
| `pages/3_LegalDB.py` | 法令DB管理UI |
| `kb/price_kb.json` | 単価ナレッジベース |
| `kb/legal_kb.json` | 法令ナレッジベース |
