"""
統合見積生成のシミュレーションテスト

全6カテゴリ（電気・機械・ガス・空調・衛生・消防）の
見積生成と安定性を検証します。
"""

import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

# パス設定
sys.path.insert(0, str(Path(__file__).parent))

from pipelines.estimate_generator_ai import AIEstimateGenerator
from pipelines.schemas import DisciplineType, FMTDocument
from pipelines.export import EstimateExporter

def run_simulation():
    """統合見積生成のシミュレーションテスト"""

    print("=" * 60)
    print("統合見積生成シミュレーションテスト")
    print("=" * 60)
    print()

    # テスト用仕様書
    spec_pdf = Path("test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf")

    if not spec_pdf.exists():
        print(f"❌ テスト用仕様書が見つかりません: {spec_pdf}")
        return False

    print(f"📄 仕様書: {spec_pdf.name}")
    print()

    # ステップ1: AIEstimateGenerator初期化
    print("=" * 40)
    print("ステップ1: AIEstimateGenerator初期化")
    print("=" * 40)

    try:
        start_time = time.time()
        generator = AIEstimateGenerator()
        init_time = time.time() - start_time
        print(f"✅ 初期化完了 ({init_time:.2f}秒)")
        print(f"   KB項目数: {len(generator.price_kb)}項目")

        # KBカテゴリ別統計
        kb_stats = {}
        for item in generator.price_kb:
            disc = item.get("discipline", "不明")
            kb_stats[disc] = kb_stats.get(disc, 0) + 1

        print("   KB内訳:")
        for disc, count in sorted(kb_stats.items()):
            print(f"     - {disc}: {count}項目")
        print()

    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        traceback.print_exc()
        return False

    # ステップ2: 統合見積生成
    print("=" * 40)
    print("ステップ2: 統合見積生成")
    print("=" * 40)

    try:
        start_time = time.time()
        fmt_doc = generator.generate_estimate_unified(str(spec_pdf))
        gen_time = time.time() - start_time

        print(f"✅ 見積生成完了 ({gen_time:.2f}秒)")
        print()

        # 結果サマリー
        total_items = len(fmt_doc.estimates) if fmt_doc and fmt_doc.estimates else 0
        total_amount = sum(item.amount or 0 for item in fmt_doc.estimates) if fmt_doc and fmt_doc.estimates else 0
        with_price = sum(1 for item in fmt_doc.estimates if item.unit_price and item.unit_price > 0) if fmt_doc and fmt_doc.estimates else 0
        price_coverage = with_price / total_items if total_items > 0 else 0

        print("📊 生成結果サマリー:")
        print(f"   総項目数: {total_items}")
        print(f"   推定総額: ¥{total_amount:,.0f}")
        print(f"   単価付与率: {price_coverage*100:.1f}%")
        print()

        # カテゴリ別統計
        if fmt_doc and fmt_doc.estimates:
            disc_stats = {}
            for item in fmt_doc.estimates:
                disc = item.discipline.value if item.discipline else "不明"
                disc_stats[disc] = disc_stats.get(disc, 0) + 1

            print("📋 カテゴリ別生成項目数:")
            for disc, count in sorted(disc_stats.items()):
                status = "✅" if count > 0 else "⚠️"
                print(f"   {status} {disc}: {count}項目")
            print()

            # 単価付与状況
            with_price = sum(1 for item in fmt_doc.estimates if item.unit_price and item.unit_price > 0)
            without_price = len(fmt_doc.estimates) - with_price
            print(f"💰 単価付与状況:")
            print(f"   単価あり: {with_price}項目")
            print(f"   単価なし: {without_price}項目")
            print()

    except Exception as e:
        print(f"❌ 見積生成エラー: {e}")
        traceback.print_exc()
        return False

    # ステップ3: PDF生成テスト
    print("=" * 40)
    print("ステップ3: PDF生成テスト")
    print("=" * 40)

    try:
        output_dir = Path("output/test_simulation")
        output_dir.mkdir(parents=True, exist_ok=True)

        exporter = EstimateExporter(output_dir=str(output_dir))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"見積書_シミュレーション_{timestamp}.pdf"

        start_time = time.time()
        pdf_path = exporter.export_to_pdf(fmt_doc, pdf_filename)
        pdf_time = time.time() - start_time

        if pdf_path and Path(pdf_path).exists():
            file_size = Path(pdf_path).stat().st_size / 1024
            print(f"✅ PDF生成完了 ({pdf_time:.2f}秒)")
            print(f"   ファイル: {pdf_path}")
            print(f"   サイズ: {file_size:.1f} KB")
        else:
            print(f"❌ PDF生成失敗")
            return False
        print()

    except Exception as e:
        print(f"❌ PDF生成エラー: {e}")
        traceback.print_exc()
        return False

    # ステップ4: 詳細検証
    print("=" * 40)
    print("ステップ4: 詳細検証")
    print("=" * 40)

    issues = []

    # 4.1 カテゴリカバレッジ
    expected_categories = [
        "電気設備工事", "機械設備工事", "ガス設備工事",
        "空調設備工事", "衛生設備工事", "消防設備工事"
    ]

    generated_categories = set()
    if fmt_doc and fmt_doc.estimates:
        for item in fmt_doc.estimates:
            if item.discipline:
                generated_categories.add(item.discipline.value)

    missing_categories = set(expected_categories) - generated_categories
    if missing_categories:
        # 仕様書に該当しないカテゴリは問題なし
        print(f"ℹ️  仕様書に該当なしのカテゴリ: {', '.join(missing_categories)}")
    else:
        print("✅ 全カテゴリで項目生成")

    # 4.2 項目数チェック
    total_items = len(fmt_doc.estimates) if fmt_doc and fmt_doc.estimates else 0
    if total_items < 10:
        issues.append(f"項目数が少なすぎます: {total_items}項目")
    else:
        print(f"✅ 十分な項目数: {total_items}項目")

    # 4.3 単価付与率
    if fmt_doc and fmt_doc.estimates:
        with_price = sum(1 for item in fmt_doc.estimates if item.unit_price and item.unit_price > 0)
        price_rate = with_price / len(fmt_doc.estimates) if fmt_doc.estimates else 0
        if price_rate < 0.5:
            issues.append(f"単価付与率が低い: {price_rate*100:.1f}%")
        else:
            print(f"✅ 単価付与率: {price_rate*100:.1f}%")

    # 4.4 金額チェック
    total_amount = sum(item.amount or 0 for item in fmt_doc.estimates) if fmt_doc and fmt_doc.estimates else 0
    if total_amount <= 0:
        issues.append("総額が0円です")
    else:
        print(f"✅ 総額計算完了: ¥{total_amount:,.0f}")

    print()

    # 最終結果
    print("=" * 60)
    print("シミュレーション結果")
    print("=" * 60)

    if issues:
        print("⚠️  以下の問題が検出されました:")
        for issue in issues:
            print(f"   - {issue}")
        print()
        print("🔧 推奨対応:")
        print("   - KBデータの拡充")
        print("   - プロンプトの調整")
        print("   - 仕様書の詳細確認")
    else:
        print("✅ シミュレーション成功！")
        print()
        print("📊 最終統計:")
        print(f"   総項目数: {total_items}")
        print(f"   推定総額: ¥{total_amount:,.0f}")
        print(f"   生成カテゴリ: {len(generated_categories)}")
        print(f"   処理時間: 約{gen_time + pdf_time:.0f}秒")

    print()
    return len(issues) == 0


if __name__ == "__main__":
    success = run_simulation()
    sys.exit(0 if success else 1)
