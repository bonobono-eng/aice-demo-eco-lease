"""RAG機能と信頼度スコアのデモ

仕様書から項目抽出 → KB検索で単価付与 → 根拠付き見積書生成
"""

import json
import PyPDF2
from pathlib import Path
from pipelines.schemas import PriceReference, DisciplineType
from pipelines.kb_builder import EnhancedEstimateExtractor
from pipelines.export import EstimateExporter

print("=" * 80)
print("RAG機能デモ: 仕様書 → KB単価検索 → 根拠付き見積書")
print("=" * 80)

# 1. 過去見積KBを読み込み
print("\n【ステップ1】過去見積KBの読み込み")
kb_path = "kb/price_kb.json"

with open(kb_path, 'r', encoding='utf-8') as f:
    kb_data = json.load(f)

price_kb = [PriceReference(**item) for item in kb_data]
print(f"✅ KB読み込み完了: {len(price_kb)}項目")

# 2. 仕様書PDFからテキスト抽出
print("\n【ステップ2】仕様書からのテキスト抽出")
spec_path = "test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf"

with open(spec_path, 'rb') as file:
    pdf_reader = PyPDF2.PdfReader(file)
    spec_text = ""
    for page_num in range(min(len(pdf_reader.pages), 50)):
        spec_text += pdf_reader.pages[page_num].extract_text() + "\n"

print(f"✅ テキスト抽出完了: {len(spec_text)}文字")

# 3. 信頼度スコア付きで項目を抽出
print("\n【ステップ3】信頼度スコア付き項目抽出（LLM）")
extractor = EnhancedEstimateExtractor(price_kb)
items = extractor.extract_with_confidence(spec_text, DisciplineType.GAS)

print(f"✅ 抽出完了: {len(items)}項目")
print("\n【抽出された項目（信頼度スコア付き）】")
for i, item in enumerate(items[:10], 1):
    indent = "  " * item.level
    conf_indicator = "●" * int(item.confidence * 5) if item.confidence else "○"
    print(f"{i:2d}. {indent}{item.name} [{item.specification}] (信頼度: {item.confidence:.1f} {conf_indicator})")

# 4. KBから単価を検索して付与（RAG）
print("\n【ステップ4】KB単価検索（RAG）")
enriched_items = extractor.enrich_with_price_rag(items)

# マッチング結果の表示
print("\n【単価マッチング結果】")
matched_items = [item for item in enriched_items if item.unit_price is not None]
unmatched_items = [item for item in enriched_items if item.unit_price is None]

print(f"✅ マッチング成功: {len(matched_items)}/{len(enriched_items)}項目")
print(f"\n【マッチした項目（最初の10項目）】")
for i, item in enumerate(matched_items[:10], 1):
    indent = "  " * item.level
    print(f"{i:2d}. {indent}{item.name} {item.specification}")
    print(f"     単価: ¥{item.unit_price:,}/{item.unit}")
    print(f"     根拠: {item.source_reference}")
    if item.quantity and item.amount:
        print(f"     金額: ¥{item.amount:,} (= {item.quantity}{item.unit} × ¥{item.unit_price:,})")

if unmatched_items:
    print(f"\n【未マッチ項目】({len(unmatched_items)}項目)")
    for item in unmatched_items[:5]:
        print(f"  - {item.name} {item.specification} (要確認)")

# 5. 精度評価
print("\n【精度評価】")
if matched_items:
    # 信頼度の統計
    avg_confidence = sum(item.confidence for item in enriched_items if item.confidence) / len(enriched_items)
    high_conf_count = sum(1 for item in enriched_items if item.confidence and item.confidence >= 0.8)

    print(f"  マッチング率: {len(matched_items)/len(enriched_items)*100:.1f}%")
    print(f"  平均信頼度: {avg_confidence:.2f}")
    print(f"  高信頼度項目（≥0.8）: {high_conf_count}/{len(enriched_items)}")

    # 総額を計算
    total_amount = sum(item.amount for item in matched_items if item.amount)
    print(f"  推定総額: ¥{total_amount:,}")

print(f"\n【参照見積書との比較】")
print(f"  参照見積書総額: ¥13,432,263")
print(f"  RAG推定総額: ¥{total_amount:,}")
if total_amount > 0:
    accuracy = (1 - abs(13432263 - total_amount) / 13432263) * 100
    print(f"  精度: {accuracy:.1f}%")

print("\n" + "=" * 80)
print("デモ完了！")
print("=" * 80)
