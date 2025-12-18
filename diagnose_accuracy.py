#!/usr/bin/env python3
"""
見積精度診断スクリプト

問題の切り分け：
1. 仕様書の読み込み精度
2. LLMの項目生成精度
3. KBマッチング精度
4. 金額計算ロジック
"""

import json
import os
from pathlib import Path

# 環境変数設定
os.environ.setdefault("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))

def test_1_spec_extraction():
    """1. 仕様書の読み込み精度を検証"""
    print("\n" + "="*60)
    print("【診断1】仕様書の読み込み精度")
    print("="*60)

    from pipelines.estimate_generator_ai import AIEstimateGenerator

    # 仕様書ファイルを明示的に指定
    spec_file = Path("test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf")
    if not spec_file.exists():
        print(f"ERROR: {spec_file} が見つかりません")
        return None

    print(f"テストファイル: {spec_file.name}")

    generator = AIEstimateGenerator()

    # テキスト抽出
    try:
        spec_text = generator.extract_text_from_pdf(str(spec_file))
        print(f"\n[結果]")
        print(f"  抽出文字数: {len(spec_text):,} 文字")
        print(f"  最初の500文字:\n{spec_text[:500]}")

        # 重要キーワードの検出
        keywords = ["工事", "設備", "配管", "電気", "ガス", "面積", "階", "室", "仕様"]
        found = [kw for kw in keywords if kw in spec_text]
        print(f"\n  検出キーワード: {found}")

        if len(spec_text) < 1000:
            print("\n  ⚠️ 警告: 抽出文字数が少なすぎます。PDFの読み込みに問題がある可能性")
        else:
            print("\n  ✅ テキスト抽出は正常")

        return spec_text
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def test_2_building_info_extraction(spec_text):
    """2. 建物情報の抽出精度を検証"""
    print("\n" + "="*60)
    print("【診断2】建物情報の抽出精度（LLM）")
    print("="*60)

    from pipelines.estimate_generator_ai import AIEstimateGenerator

    generator = AIEstimateGenerator()

    try:
        building_info = generator._extract_building_info_detailed(spec_text)
        print(f"\n[抽出された建物情報]")
        print(json.dumps(building_info, indent=2, ensure_ascii=False))

        # 重要フィールドのチェック
        required = ["project_name", "building_info"]
        missing = [f for f in required if not building_info.get(f)]

        if missing:
            print(f"\n  ⚠️ 警告: 以下のフィールドが未抽出: {missing}")
        else:
            print(f"\n  ✅ 建物情報の抽出は正常")

        # 床面積のチェック
        bldg = building_info.get("building_info", {})
        floor_area = bldg.get("total_floor_area")
        if floor_area:
            print(f"  延床面積: {floor_area}㎡")
        else:
            print(f"  ⚠️ 延床面積が抽出できていません")

        return building_info
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_3_llm_item_generation(spec_text, building_info):
    """3. LLMの項目生成精度を検証"""
    print("\n" + "="*60)
    print("【診断3】LLMの見積項目生成精度")
    print("="*60)

    from pipelines.estimate_generator_ai import AIEstimateGenerator
    from pipelines.schemas import DisciplineType

    generator = AIEstimateGenerator()

    try:
        # 電気設備で試行
        print("電気設備工事の項目を生成中...")
        items = generator._generate_items_for_electrical(spec_text, building_info)

        print(f"\n[生成結果]")
        print(f"  生成項目数: {len(items)}")

        # 数量の分布を確認
        qty_issues = []
        for item in items[:20]:
            qty = item.quantity
            name = item.name
            unit = item.unit
            if qty and qty > 100:
                qty_issues.append(f"  - {name}: {qty} {unit} ← 過大？")

        print(f"\n[生成された項目（先頭10件）]")
        for i, item in enumerate(items[:10]):
            print(f"  {i+1}. {item.name} | {item.quantity} {item.unit} | conf={item.confidence}")

        if qty_issues:
            print(f"\n  ⚠️ 数量が過大な項目:")
            for issue in qty_issues[:5]:
                print(issue)
        else:
            print(f"\n  ✅ 数量は妥当な範囲")

        return items
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_4_kb_matching(items):
    """4. KBマッチング精度を検証"""
    print("\n" + "="*60)
    print("【診断4】KBマッチング精度")
    print("="*60)

    from pipelines.estimate_generator_ai import AIEstimateGenerator

    generator = AIEstimateGenerator()

    # KB統計
    print(f"\n[KB統計]")
    print(f"  KB項目数: {len(generator.price_kb)}")

    # 単価分布
    prices = [item.get("unit_price", 0) for item in generator.price_kb if item.get("unit_price")]
    if prices:
        print(f"  単価範囲: ¥{min(prices):,.0f} - ¥{max(prices):,.0f}")
        print(f"  単価中央値: ¥{sorted(prices)[len(prices)//2]:,.0f}")

    # マッチングテスト
    try:
        print(f"\n[マッチングテスト]")
        enriched = generator.enrich_with_prices(items[:10])

        matched = sum(1 for item in enriched if item.unit_price)
        print(f"  マッチング率: {matched}/{len(enriched)} ({matched/len(enriched)*100:.1f}%)")

        print(f"\n[マッチング結果（先頭10件）]")
        for item in enriched:
            price_str = f"¥{item.unit_price:,.0f}" if item.unit_price else "未マッチ"
            amt_str = f"¥{item.amount:,.0f}" if item.amount else "-"
            kb_ref = item.price_references[0] if item.price_references else "-"
            print(f"  - {item.name[:20]:20} | {price_str:>12} | 金額: {amt_str:>12} | KB: {kb_ref}")

        # 高額マッチングの確認
        high_price = [item for item in enriched if item.unit_price and item.unit_price > 100000]
        if high_price:
            print(f"\n  ⚠️ 高額単価のマッチング:")
            for item in high_price[:5]:
                print(f"    - {item.name}: ¥{item.unit_price:,.0f}")

        return enriched
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_5_amount_calculation(items):
    """5. 金額計算ロジックを検証"""
    print("\n" + "="*60)
    print("【診断5】金額計算ロジック")
    print("="*60)

    total = sum(item.amount or 0 for item in items)
    leaf_total = sum(item.amount or 0 for item in items if item.level >= 2)

    print(f"\n[金額集計]")
    print(f"  全項目合計: ¥{total:,.0f}")
    print(f"  末端項目合計: ¥{leaf_total:,.0f}")

    # 高額項目
    high_items = sorted(items, key=lambda x: -(x.amount or 0))[:10]
    print(f"\n[高額項目TOP10]")
    for item in high_items:
        qty = item.quantity or 0
        up = item.unit_price or 0
        amt = item.amount or 0
        print(f"  - {item.name[:25]:25} | {qty:>6} {item.unit:4} × ¥{up:>10,.0f} = ¥{amt:>12,.0f}")

    # 問題の特定
    print(f"\n[問題の特定]")
    issues = []

    for item in items:
        qty = item.quantity or 0
        up = item.unit_price or 0
        amt = item.amount or 0

        # 数量×単価と金額の不一致
        if qty > 0 and up > 0 and amt != qty * up:
            issues.append(f"計算不一致: {item.name} ({qty}×{up}={qty*up} ≠ {amt})")

        # 異常な金額
        if amt > 5000000:  # 500万円超
            issues.append(f"高額項目: {item.name} = ¥{amt:,.0f}")

    if issues:
        print(f"  ⚠️ 検出された問題:")
        for issue in issues[:10]:
            print(f"    - {issue}")
    else:
        print(f"  ✅ 金額計算に明らかな問題なし")


def test_6_kb_data_quality():
    """6. KBデータ品質を検証"""
    print("\n" + "="*60)
    print("【診断6】KBデータ品質")
    print("="*60)

    kb_path = Path("kb/price_kb.json")
    if not kb_path.exists():
        print("ERROR: kb/price_kb.json が見つかりません")
        return

    with open(kb_path, 'r', encoding='utf-8') as f:
        kb_data = json.load(f)

    print(f"\n[KB基本統計]")
    print(f"  総項目数: {len(kb_data)}")

    # 問題のある項目を検出
    issues = {
        "式_高額": [],      # 「式」単位で高額
        "曖昧名": [],       # 「同上」などの曖昧な名称
        "単価異常": [],     # 異常に高い/低い単価
        "discipline混在": set(),
    }

    for item in kb_data:
        desc = item.get("description", "")
        unit = item.get("unit", "")
        price = item.get("unit_price", 0)
        disc = item.get("discipline", "")

        issues["discipline混在"].add(disc)

        # 「式」単位で高額
        if "式" in unit and price > 500000:
            issues["式_高額"].append(f"{desc}: ¥{price:,.0f}/式")

        # 曖昧な名称
        if desc.startswith("同上") or desc in ["その他", "雑"]:
            issues["曖昧名"].append(desc)

        # 異常単価
        if price > 5000000:
            issues["単価異常"].append(f"{desc}: ¥{price:,.0f}")

    print(f"\n[discipline一覧]")
    for d in sorted(issues["discipline混在"]):
        count = sum(1 for i in kb_data if i.get("discipline") == d)
        print(f"  - {d}: {count}件")

    print(f"\n[問題のある項目]")
    print(f"  「式」単位で50万円超: {len(issues['式_高額'])}件")
    for i in issues["式_高額"][:5]:
        print(f"    - {i}")

    print(f"\n  曖昧な名称: {len(issues['曖昧名'])}件")
    for i in issues["曖昧名"][:5]:
        print(f"    - {i}")

    print(f"\n  500万円超の単価: {len(issues['単価異常'])}件")
    for i in issues["単価異常"][:5]:
        print(f"    - {i}")


def main():
    print("="*60)
    print("見積精度 診断レポート")
    print("="*60)

    # 1. 仕様書読み込み
    spec_text = test_1_spec_extraction()
    if not spec_text:
        print("\n❌ 仕様書の読み込みに失敗。診断を中断します。")
        return

    # 2. 建物情報抽出
    building_info = test_2_building_info_extraction(spec_text)

    # 3. LLM項目生成
    items = None
    if building_info:
        items = test_3_llm_item_generation(spec_text, building_info)

    # 4. KBマッチング
    if items:
        enriched = test_4_kb_matching(items)

        # 5. 金額計算
        if enriched:
            test_5_amount_calculation(enriched)

    # 6. KBデータ品質
    test_6_kb_data_quality()

    # 総合診断
    print("\n" + "="*60)
    print("【総合診断】")
    print("="*60)
    print("""
問題の切り分けポイント:

1. 仕様書読み込み
   - 文字数が少ない → PDF解析に問題
   - キーワードが検出されない → OCR精度の問題

2. LLM項目生成
   - 項目数が少なすぎる → プロンプトの問題
   - 数量が過大 → 推定ルールの問題

3. KBマッチング
   - マッチング率が低い → KB項目名と生成項目名の乖離
   - 高額単価がマッチ → KBデータ品質の問題

4. 金額計算
   - 計算不一致 → ロジックバグ
   - 異常に高額 → 上記1-3の複合問題

5. KBデータ
   - 「式」単位の高額項目 → 誤マッチングの原因
   - 曖昧な項目名 → マッチング精度低下の原因
""")


if __name__ == "__main__":
    main()
