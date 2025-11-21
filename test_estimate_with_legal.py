"""
見積生成システム v3（法令要件統合版）の総合テスト
"""

import sys
sys.path.insert(0, '.')

from pathlib import Path
from pipelines.estimate_generator_with_legal import EstimateGeneratorWithLegal
from pipelines.schemas import DisciplineType


def print_header(title: str):
    """ヘッダーを表示"""
    print("\n" + "="*100)
    print(f"{title}")
    print("="*100)


def main():
    """メイン関数"""
    print_header("📋 見積生成システム v3（法令要件統合版）総合テスト")

    # 見積生成システムを初期化
    generator = EstimateGeneratorWithLegal(kb_path="kb/price_kb.json")

    # 仕様書パス
    spec_path = "test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf"

    if not Path(spec_path).exists():
        print(f"❌ 仕様書が見つかりません: {spec_path}")
        return

    print(f"\n📄 仕様書: {Path(spec_path).name}")
    print(f"🔧 工事区分: 電気設備工事")
    print(f"⏳ 見積書を生成中（法令要件抽出含む）...\n")

    # 見積書を生成（法令要件統合版）
    result = generator.generate_estimate_with_legal(
        spec_path,
        disciplines=[DisciplineType.ELECTRICAL],
        add_welfare_costs=True,
        validate_legal=True
    )

    fmt_doc = result["fmt_doc"]
    legal_refs = result["legal_refs"]
    violations = result["violations"]
    summary = result["summary"]

    # ============================================================
    # 1. プロジェクト情報
    # ============================================================
    print_header("✅ 見積書生成完了")

    print(f"\n【プロジェクト情報】")
    print(f"  工事名: {fmt_doc.project_info.project_name}")
    print(f"  場所: {fmt_doc.project_info.location}")
    print(f"  リース期間: {fmt_doc.project_info.contract_period}")

    # ============================================================
    # 2. 見積サマリー
    # ============================================================
    print(f"\n【見積サマリー】")
    print(f"  総項目数: {summary['total_items']}")
    print(f"  法令対応項目: {summary['legal_items_added']}")
    print(f"  合計金額: ¥{summary['total_amount']:,.0f}")

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
    print(f"  単価付与: {len(items_with_unit_price)}/{len(fmt_doc.estimate_items)} 項目 "
          f"({len(items_with_unit_price)/len(fmt_doc.estimate_items)*100:.1f}%)")
    print(f"  金額計算: {len(items_with_amount)}/{len(fmt_doc.estimate_items)} 項目 "
          f"({len(items_with_amount)/len(fmt_doc.estimate_items)*100:.1f}%)")

    # ============================================================
    # 3. 法令遵守状況
    # ============================================================
    print_header("⚖️  法令遵守状況")

    print(f"\n【適用法令数】: {summary['legal_requirements']}件")
    print(f"【法令違反リスク】: {summary['legal_violations']}件")

    # 法令参照リストを表示
    if legal_refs:
        print(f"\n【抽出された法令要件（上位10件）】")
        print(f"{'No':<4} {'法令コード':<20} {'要件':<40} {'信頼度':<10}")
        print("-" * 100)

        for i, legal_ref in enumerate(legal_refs[:10]):
            print(f"{i+1:<4} {legal_ref.law_code:<20} {legal_ref.article[:40]:<40} {legal_ref.relevance_score:.2f}")

    # 法令違反リスクを表示
    if violations:
        print(f"\n【法令違反リスク詳細】")
        for i, violation in enumerate(violations[:10]):
            print(f"\n  {i+1}. {violation['law_name']}")
            print(f"     重要度: {violation['severity'].upper()}")
            print(f"     内容: {violation['message']}")
            print(f"     推奨対応: {violation['recommendation']}")

    # ============================================================
    # 4. 見積項目一覧
    # ============================================================
    print_header("📑 見積項目一覧（最初の30項目）")

    print(f"{'階層':<4} {'項目名':<50} {'仕様':<20} {'数量':<12} {'単価':<15} {'金額':<18} {'費用区分':<15} {'出典':<10}")
    print("-" * 170)

    for i, item in enumerate(fmt_doc.estimate_items[:30]):
        indent = "  " * item.level
        name_str = f"{indent}{item.name}"[:50]
        spec_str = (item.specification or "")[:20]
        qty_str = f"{item.quantity or ''} {item.unit or ''}".strip()[:12]
        price_str = f"¥{item.unit_price:,.0f}" if item.unit_price else "-"
        amount_str = f"¥{item.amount:,.0f}" if item.amount else "-"
        ct = item.cost_type.value if item.cost_type else "未分類"
        source = item.source_type or "-"

        print(f"{item.level:<4} {name_str:<50} {spec_str:<20} {qty_str:<12} {price_str:<15} {amount_str:<18} {ct:<15} {source:<10}")

    # ============================================================
    # 5. 諸経費計算
    # ============================================================
    if fmt_doc.overhead_calculations:
        print_header("💰 諸経費計算")
        for overhead in fmt_doc.overhead_calculations:
            print(f"\n  {overhead.name}: ¥{overhead.amount:,.0f}")
            print(f"  計算式: {overhead.formula}")
            print(f"  備考: {overhead.remarks}")

    # ============================================================
    # 6. 精度評価
    # ============================================================
    print_header("📊 精度評価")

    # 参照見積書との比較（file_logic.mdより）
    reference_items = 34  # 参照見積書の項目数
    reference_amount = 13401093  # 参照見積書の総額

    # 電気設備の場合
    if DisciplineType.ELECTRICAL in fmt_doc.disciplines:
        reference_amount = 209992533  # 電気・機械設備の総額

    print(f"\n【参照見積書との比較】")
    print(f"  参照見積書:")
    print(f"    - 項目数: {reference_items}項目")
    print(f"    - 総額: ¥{reference_amount:,.0f}")

    print(f"\n  今回の生成結果:")
    print(f"    - 項目数: {summary['total_items']}項目 ({summary['total_items']/reference_items*100:.1f}%)")
    print(f"    - 総額: ¥{summary['total_amount']:,.0f} ({summary['total_amount']/reference_amount*100:.1f}%)")

    print(f"\n【法令対応状況】")
    print(f"  法令要件抽出数: {summary['legal_requirements']}件")
    print(f"  法令対応項目追加: {summary['legal_items_added']}項目")
    print(f"  法令違反リスク: {summary['legal_violations']}件")

    # ============================================================
    # 7. 改善提案
    # ============================================================
    print_header("💡 改善提案")

    if summary['total_amount'] == 0:
        print("\n  ⚠️  単価マッチングが機能していません。")
        print("      - KBの内容を確認してください")
        print("      - マッチングアルゴリズムを改善してください（ベクトル検索の実装）")

    if summary['total_items'] < reference_items:
        print(f"\n  ⚠️  項目数が参照見積書の {summary['total_items']/reference_items*100:.1f}% です。")
        print("      - LLMプロンプトを改善して詳細項目を抽出してください")
        print("      - 仕様書に記載されていない項目は推定ルールで補完してください")

    if summary['legal_violations'] > 0:
        print(f"\n  ⚠️  {summary['legal_violations']}件の法令違反リスクが検出されました。")
        print("      - 法令要件に対応する見積項目を追加してください")
        print("      - 設計変更や仕様追加を検討してください")

    if summary['legal_items_added'] > 0:
        print(f"\n  ✅ {summary['legal_items_added']}件の法令対応項目が自動追加されました。")
        print("      - これらの項目は法令遵守のために必要な項目です")
        print("      - 具体的な仕様・数量は発注者と協議して確定してください")

    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    main()
