# 604ファイルKB化に関するインフラ調査レポート

**作成日**: 2025-12-15
**対象システム**: aice-demo-eco-lease（見積書生成システム）

---

## 1. 調査概要

### 1.1 調査目的
604ファイルの見積データをKB（ナレッジベース）化する際に、追加のインフラ契約が必要かどうかを調査。

### 1.2 調査対象
- ベクトル化データの保存・検索
- トランザクション処理
- AIとの対話（LLM API）
- Streamlit UIのスケーラビリティ

---

## 2. 現在のシステム構成

### 2.1 技術スタック

| コンポーネント | 現在の実装 | バージョン |
|--------------|----------|-----------|
| **ベクトルDB** | FAISS (faiss-cpu) | >= 1.7.4 |
| **Embedding** | sentence-transformers | >= 2.2.0 |
| **AI/LLM** | Anthropic Claude API | claude-sonnet-4 |
| **データ保存** | JSON ファイル | - |
| **Web UI** | Streamlit | >= 1.28.0 |
| **PDF処理** | PyPDF2, PyMuPDF | >= 3.0.0 |

### 2.2 現在のKB構成

```
kb/
├── price_kb.json      # 価格KB（現在約60項目）
└── legal_kb.json      # 法令KB（スキーマのみ）
```

### 2.3 KB構築フロー（現在）

```
[見積書PDF/Excel]
       ↓ PyPDF2 / openpyxl
[テキスト抽出]
       ↓ Claude API (構造化)
[PriceReference オブジェクト]
       ↓
[JSON保存] → [FAISS インデックス化]
```

---

## 3. 604ファイルKB化の要件分析

### 3.1 データ規模の見積もり

| 項目 | 数値 | 備考 |
|-----|------|------|
| ファイル数 | 604件 | PDF/Excel混在想定 |
| 1ファイルあたり項目数 | 30〜100項目 | 見積書の詳細度による |
| **総KB項目数** | 18,000〜60,000項目 | |
| 1項目あたりデータサイズ | 約500バイト | JSON形式 |
| **総データサイズ** | 約10〜30MB | JSON |
| FAISSインデックスサイズ | 約100〜200MB | ベクトル次元による |

### 3.2 FAISSの処理能力

| 指標 | 値 | 604ファイル対応 |
|-----|---|---------------|
| 最大ベクトル数 | 数百万〜数千万 | ✅ 余裕 |
| 検索速度 | < 100ms / クエリ | ✅ 問題なし |
| メモリ使用量 | 約1〜2GB | ✅ 一般PCで対応可能 |

**結論**: FAISSは604ファイル（約60,000項目）を問題なく処理可能

---

## 4. インフラ契約の必要性

### 4.1 結論

**追加のインフラ契約は基本的に不要**

現在のシステム構成で604ファイルのKB化は十分対応可能。

### 4.2 コンポーネント別評価

| コンポーネント | 契約必要性 | 理由 |
|--------------|----------|------|
| **ベクトルDB (FAISS)** | ❌ 不要 | ローカルで数百万ベクトル対応 |
| **AI/LLM (Claude API)** | ✅ 既存契約で対応 | 従量課金、追加契約不要 |
| **データ保存** | ❌ 不要 | JSON/SQLiteでローカル対応 |
| **Web UI (Streamlit)** | ❌ 不要 | ローカル実行で対応 |

### 4.3 インフラ契約が必要になる条件

以下の条件に該当する場合は、クラウドサービスの契約を検討：

| 条件 | 推奨サービス | 月額目安 |
|------|------------|---------|
| 複数ユーザーが同時利用 | Streamlit Cloud / AWS | ¥3,000〜 |
| データの永続化・チーム共有 | Supabase / PostgreSQL | 無料〜¥2,000 |
| 高速なセマンティック検索 | Pinecone / Weaviate | ¥0〜¥8,000 |
| 本番環境での24/7運用 | AWS / GCP / Azure | ¥10,000〜 |

---

## 5. コスト見積もり

### 5.1 初回KB構築コスト

| 項目 | 単価 | 数量 | 合計 |
|-----|------|------|------|
| Claude API（PDF構造化） | $0.03〜0.10/ファイル | 604件 | **$18〜$60** |
| ローカル処理 | ¥0 | - | ¥0 |
| **合計** | | | **約¥3,000〜¥10,000** |

※ 1回限りの費用

### 5.2 運用コスト（月額）

| 項目 | 費用 | 備考 |
|-----|------|------|
| Claude API（検索時） | 約¥500〜2,000 | 使用頻度による |
| インフラ | ¥0 | ローカル運用の場合 |
| **合計** | **¥500〜2,000/月** | |

### 5.3 処理時間の見積もり

```
604ファイル × 約30秒/ファイル = 約5時間

推奨: バッチ処理で一晩実行
```

---

## 6. 推奨構成

### 6.1 パターンA: 最小コスト構成（推奨）

**対象**: 個人利用、小規模チーム（1〜3名）

```
ローカルPC / 社内サーバー
├── FAISS (ベクトル検索)
├── SQLite (データ管理) ※JSONからの移行推奨
├── Streamlit (UI)
└── Claude API (AI) ← 唯一の外部サービス
```

| 項目 | 値 |
|-----|---|
| 初期費用 | 約¥5,000（API費用） |
| 月額費用 | 約¥1,000（API費用） |
| 追加契約 | 不要 |

### 6.2 パターンB: チーム利用構成

**対象**: 中規模チーム（5〜10名）、外部共有あり

```
クラウド
├── FAISS (ベクトル検索)
├── Supabase PostgreSQL (データ管理)
├── Streamlit Cloud (UI)
└── Claude API (AI)
```

| 項目 | 値 |
|-----|---|
| 初期費用 | 約¥5,000 |
| 月額費用 | 約¥3,000〜5,000 |
| 追加契約 | Supabase（無料枠〜）、Streamlit Cloud（無料） |

### 6.3 パターンC: 本番運用構成

**対象**: 大規模運用、高可用性要件

```
AWS / GCP / Azure
├── Pinecone (マネージドベクトルDB)
├── PostgreSQL (RDS / Cloud SQL)
├── ECS / Cloud Run (アプリケーション)
└── Claude API (AI)
```

| 項目 | 値 |
|-----|---|
| 初期費用 | 約¥10,000〜30,000 |
| 月額費用 | 約¥10,000〜50,000 |
| 追加契約 | AWS/GCP/Azure、Pinecone等 |

---

## 7. 実装方法

### 7.1 既存システムでのKB構築

現在の`kb_builder.py`を使用して604ファイルを処理可能：

```python
from pipelines.kb_builder import PriceKBBuilder
from pathlib import Path

# KB Builderの初期化
kb_builder = PriceKBBuilder()

# 604ファイルのパスを取得
data_dir = Path("path/to/estimate_files")
file_paths = list(data_dir.glob("*.pdf")) + list(data_dir.glob("*.xlsx"))
print(f"処理対象: {len(file_paths)}ファイル")

# 複数見積を統合（中央値で価格を統合）
aggregated_refs = kb_builder.aggregate_multiple_estimates(
    [str(p) for p in file_paths],
    method="median"  # 同一項目は中央値で統合
)

# 保存
kb_builder.save_kb_to_json(aggregated_refs, "kb/price_kb_full.json")
print(f"KB構築完了: {len(aggregated_refs)}項目")
```

### 7.2 推奨: 段階的KB構築

```
Phase 1: パイロット（1週間）
├── 50件でテスト実行
├── 抽出精度の確認
└── 問題点の洗い出し

Phase 2: 本格構築（2〜3日）
├── 残り554件を処理
├── バッチ処理で一括実行
└── 品質チェック

Phase 3: 運用開始
├── 定期更新の仕組み化
├── 新規見積の自動KB追加
└── 古いデータのアーカイブ
```

### 7.3 バッチ処理スクリプト例

```python
import time
from pathlib import Path
from pipelines.kb_builder import PriceKBBuilder

def batch_build_kb(file_paths: list, batch_size: int = 50):
    """604ファイルをバッチ処理でKB化"""
    kb_builder = PriceKBBuilder()
    all_refs = []

    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}: {len(batch)} files")

        refs = kb_builder.aggregate_multiple_estimates(batch, method="median")
        all_refs.extend(refs)

        # API制限対策: バッチ間で待機
        time.sleep(5)

    # 最終統合
    final_refs = kb_builder.aggregate_multiple_estimates(
        [],  # 既存データを使用
        method="median"
    )

    kb_builder.save_kb_to_json(all_refs, "kb/price_kb_full.json")
    return all_refs
```

---

## 8. リスクと対策

### 8.1 想定されるリスク

| リスク | 影響度 | 対策 |
|-------|-------|------|
| API制限（レートリミット） | 中 | バッチ処理 + 待機時間 |
| 抽出精度のばらつき | 中 | 品質チェック + 手動補正 |
| ファイル形式の非対応 | 低 | 事前にフォーマット確認 |
| 処理中断 | 低 | チェックポイント保存 |

### 8.2 品質管理

```python
# 抽出結果の品質チェック
def validate_kb_quality(refs):
    issues = []

    for ref in refs:
        # 単価が異常に高い/低い
        if ref.unit_price > 100_000_000 or ref.unit_price < 1:
            issues.append(f"異常単価: {ref.description} = ¥{ref.unit_price}")

        # 項目名が空または不明
        if not ref.description or ref.description in ["同上", "〃"]:
            issues.append(f"不明な項目名: {ref.item_id}")

    return issues
```

---

## 9. 結論と推奨事項

### 9.1 結論

1. **追加のインフラ契約は不要**
   - 604ファイル（約60,000項目）は現在のシステムで十分対応可能
   - FAISSは数百万ベクトルまで処理可能

2. **必要なのはClaude APIの従量課金のみ**
   - 初回構築: 約¥5,000〜10,000
   - 月額運用: 約¥1,000〜2,000

3. **将来的なスケールアップも容易**
   - チーム利用時はStreamlit Cloud + Supabaseを検討
   - 本番運用時はAWS/GCP + Pineconeを検討

### 9.2 推奨アクション

| 優先度 | アクション | 期間 |
|-------|----------|------|
| **P0** | 50件でパイロットテスト | 1週間 |
| **P1** | 全604件のKB構築 | 2〜3日 |
| **P2** | SQLiteへの移行検討 | 1週間 |
| **P3** | 定期更新の自動化 | 2週間 |

---

## 付録

### A. 参考リンク

- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [Anthropic API Pricing](https://www.anthropic.com/pricing)
- [Streamlit Cloud](https://streamlit.io/cloud)
- [Supabase](https://supabase.com/)

### B. 関連ファイル

- `pipelines/kb_builder.py` - KB構築モジュール
- `kb/price_kb.json` - 現在の価格KB
- `requirements.txt` - 依存パッケージ

---

*本レポートは2025-12-15時点の調査に基づいています。*
