"""
見積生成システムv2のテスト（file_logic.md分析ベース）
"""

import sys
sys.path.insert(0, '.')

from pathlib import Path
from pipelines.estimate_generator import EstimateGenerator
from pipelines.schemas import DisciplineType


def main():
    """メイン関数"""
    print("\n" + "="*80)
    print("📋 見積生成システムv2テスト（file_logic.md分析ベース）")
    print("="*80)

    # 見積生成システムを初期化
    generator = EstimateGenerator(kb_path="kb/price_kb.json")

    # 仕様書パス
    spec_path = "test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf"

    if not Path(spec_path).exists():
        print(f"❌ 仕様書が見つかりません: {spec_path}")
        return

    # 見積書を生成
    print(f"\n📄 仕様書: {Path(spec_path).name}")
    print(f"🔧 工事区分: ガス設備工事")
    print(f"⏳ 見積書を生成中...\n")

    fmt_doc = generator.generate_estimate(
        spec_path,
        disciplines=[DisciplineType.GAS],
        add_welfare_costs=True
    )

    # 結果を表示
    print("\n" + "="*80)
    print("✅ 見積書生成完了")
    print("="*80)

    # プロジェクト情報
    print(f"\n【プロジェクト情報】")
    print(f"  工事名: {fmt_doc.project_info.project_name}")
    print(f"  場所: {fmt_doc.project_info.location}")
    print(f"  リース期間: {fmt_doc.project_info.contract_period}")

    # 見積項目数
    print(f"\n【見積項目数】")
    print(f"  総項目数: {len(fmt_doc.estimate_items)}")

    # 費用区分別の項目数を集計
    cost_type_count = {}
    for item in fmt_doc.estimate_items:
        ct = item.cost_type.value if item.cost_type else "未分類"
        cost_type_count[ct] = cost_type_count.get(ct, 0) + 1

    print(f"\n【費用区分別項目数】")
    for ct, count in sorted(cost_type_count.items()):
        print(f"  {ct}: {count}項目")

    # 単価・金額付与状況
    items_with_unit_price = [item for item in fmt_doc.estimate_items if item.unit_price]
    items_with_amount = [item for item in fmt_doc.estimate_items if item.amount]

    print(f"\n【単価・金額付与状況】")
    print(f"  単価付与: {len(items_with_unit_price)}/{len(fmt_doc.estimate_items)} 項目 ({len(items_with_unit_price)/len(fmt_doc.estimate_items)*100:.1f}%)")
    print(f"  金額計算: {len(items_with_amount)}/{len(fmt_doc.estimate_items)} 項目 ({len(items_with_amount)/len(fmt_doc.estimate_items)*100:.1f}%)")

    # 合計金額
    total_amount = generator.calculate_total_amount(fmt_doc)
    print(f"\n【合計金額】")
    print(f"  総額: ¥{total_amount:,.0f}")

    # 諸経費
    if fmt_doc.overhead_calculations:
        print(f"\n【諸経費計算】")
        for overhead in fmt_doc.overhead_calculations:
            print(f"  {overhead.name}: ¥{overhead.amount:,.0f}")
            print(f"  計算式: {overhead.formula}")
            print(f"  備考: {overhead.remarks}")

    # 見積項目を表示
    print(f"\n【見積項目一覧】")
    print(f"{'階層':<4} {'項目名':<40} {'仕様':<15} {'数量':<10} {'単価':<12} {'金額':<15} {'費用区分':<15}")
    print("-" * 140)

    for i, item in enumerate(fmt_doc.estimate_items):
        indent = "  " * item.level
        name_str = f"{indent}{item.name}"[:40]
        spec_str = (item.specification or "")[:15]
        qty_str = f"{item.quantity or ''} {item.unit or ''}".strip()[:10]
        price_str = f"¥{item.unit_price:,.0f}" if item.unit_price else "-"
        amount_str = f"¥{item.amount:,.0f}" if item.amount else "-"
        ct = item.cost_type.value if item.cost_type else "未分類"

        print(f"{item.level:<4} {name_str:<40} {spec_str:<15} {qty_str:<10} {price_str:<12} {amount_str:<15} {ct:<15}")

    # 精度評価
    print(f"\n{'='*80}")
    print("📊 精度評価")
    print("="*80)

    # 参照見積書との比較（file_logic.mdより）
    reference_items = 34  # 参照見積書の項目数
    reference_amount = 13401093  # 参照見積書の総額（¥13,401,093）

    print(f"\n【参照見積書との比較】")
    print(f"  参照見積書（file_logic.md分析）:")
    print(f"    - 項目数: {reference_items}項目")
    print(f"    - 総額: ¥{reference_amount:,.0f}")
    print(f"\n  今回の生成結果:")
    print(f"    - 項目数: {len(fmt_doc.estimate_items)}項目 ({len(fmt_doc.estimate_items)/reference_items*100:.1f}%)")
    print(f"    - 総額: ¥{total_amount:,.0f} ({total_amount/reference_amount*100:.1f}%)")

    # 改善点の提示
    print(f"\n【改善点】")
    if total_amount == 0:
        print("  ⚠️  単価マッチングが機能していません。")
        print("      - KBの内容を確認してください")
        print("      - マッチングアルゴリズムを改善してください（ベクトル検索の実装）")

    if len(fmt_doc.estimate_items) < reference_items:
        print(f"  ⚠️  項目数が参照見積書の {len(fmt_doc.estimate_items)/reference_items*100:.1f}% です。")
        print("      - LLMプロンプトを改善して詳細項目を抽出してください")
        print("      - 仕様書に記載されていない項目は推定ルールで補完してください")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
