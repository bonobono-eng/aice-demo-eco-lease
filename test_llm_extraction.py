"""LLM抽出機能の精度テスト"""

from pipelines.estimate_extractor import EstimateExtractor
from pipelines.schemas import DisciplineType
from pipelines.export import EstimateExporter

# 仕様書から見積項目を抽出
extractor = EstimateExtractor()

print("=" * 80)
print("仕様書から見積項目を自動抽出してPDF生成")
print("=" * 80)

spec_path = "test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf"

# ガス設備工事の項目を抽出
fmt_doc = extractor.create_fmt_document_from_spec(
    spec_path,
    disciplines=[DisciplineType.GAS]
)

print(f"\n【抽出されたプロジェクト情報】")
print(f"工事名: {fmt_doc.project_info.project_name}")
print(f"場所: {fmt_doc.project_info.location}")
print(f"期間: {fmt_doc.project_info.contract_period}")
print(f"顧客名: {fmt_doc.project_info.client_name}")

print(f"\n【抽出された見積項目】")
print(f"総項目数: {len(fmt_doc.estimate_items)}")

print(f"\n【項目詳細（全項目）】")
for i, item in enumerate(fmt_doc.estimate_items, 1):
    indent = "  " * item.level
    qty_str = f"{item.quantity}{item.unit}" if item.quantity else ""
    spec_str = f"[{item.specification}]" if item.specification else ""
    print(f"{i:2d}. {indent}{item.name} {spec_str} {qty_str}")

# PDFを生成
print(f"\n【PDF生成】")
exporter = EstimateExporter(output_dir="./output")
output_paths = exporter.export_to_pdfs_by_discipline(fmt_doc)

print(f"✅ PDF生成完了:")
for path in output_paths:
    print(f"   - {path}")

print(f"\n【比較分析】")
print(f"参照見積書: test-files/250918_送付状　見積書（都市ｶﾞｽ).pdf")
print(f"- 参照見積書の項目数: 34項目（詳細含む）")
print(f"- LLM抽出項目数: {len(fmt_doc.estimate_items)}項目")
print(f"- カバー率: {len(fmt_doc.estimate_items)/34*100:.1f}%")
print(f"\n注意: LLMは仕様書から抽出しているため、")
print(f"     詳細な数量・単価は見積書からの情報が必要です。")
