"""test_template.pyの正確なデータから過去見積KBを構築"""

import json
import os
from datetime import date
from pipelines.schemas import PriceReference, DisciplineType

# test_template.pyのデータを基に過去見積KBを構築
price_kb_data = []

# ガス設備工事の価格データ（test_template.pyから）
gas_items = [
    {"name": "基本工事費", "spec": "増設・他", "qty": 1, "unit": "件", "price": 13600},
    {"name": "白ガス管（ネジ接合）", "spec": "15A", "qty": 93, "unit": "m", "price": 8990},
    {"name": "白ガス管（ネジ接合）", "spec": "20A", "qty": 18, "unit": "m", "price": 8990},
    {"name": "白ガス管（ネジ接合）", "spec": "25A", "qty": 16, "unit": "m", "price": 8990},
    {"name": "白ガス管（ネジ接合）", "spec": "32A", "qty": 34, "unit": "m", "price": 8990},
    {"name": "白ガス管（ネジ接合）", "spec": "50A", "qty": 10, "unit": "m", "price": 15210},
    {"name": "白ガス管（ネジ接合）", "spec": "80A", "qty": 2, "unit": "m", "price": 22360},
    {"name": "カラー鋼管（ネジ接合）", "spec": "25A", "qty": 4, "unit": "m", "price": 10680},
    {"name": "カラー鋼管（ネジ接合）", "spec": "32A", "qty": 54, "unit": "m", "price": 10680},
    {"name": "カラー鋼管（ネジ接合）", "spec": "50A", "qty": 19, "unit": "m", "price": 18200},
    {"name": "PE管", "spec": "25A", "qty": 8, "unit": "m", "price": 9420},
    {"name": "PE管", "spec": "30A", "qty": 4, "unit": "m", "price": 9420},
    {"name": "PE管", "spec": "50A", "qty": 4, "unit": "m", "price": 12200},
    {"name": "PE管", "spec": "75A", "qty": 104, "unit": "m", "price": 16120},
    {"name": "露出結び（鋼管）", "spec": "40A", "qty": 1, "unit": "ヶ所", "price": 11120},
    {"name": "露出結び（鋼管）", "spec": "80A", "qty": 1, "unit": "ヶ所", "price": 19240},
    {"name": "ガスコンセント（S露出）", "spec": "", "qty": 16, "unit": "個", "price": 9220},
    {"name": "ガスコンセント（W露出）", "spec": "", "qty": 13, "unit": "個", "price": 13910},
    {"name": "ネジコック（WPII型）", "spec": "20A", "qty": 3, "unit": "個", "price": 7300},
    {"name": "分岐コック", "spec": "80A", "qty": 2, "unit": "個", "price": 36010},
    {"name": "ボールスライドジョイント200mm", "spec": "80A", "qty": 2, "unit": "個", "price": 347230},
    {"name": "配管撤去費", "spec": "", "qty": 1, "unit": "式", "price": 10400},
    {"name": "配管支持金具費（SUS）", "spec": "", "qty": 1, "unit": "式", "price": 956800},
    {"name": "穴補修費", "spec": "", "qty": 1, "unit": "式", "price": 19500},
    {"name": "埋戻し費", "spec": "", "qty": 1, "unit": "式", "price": 172850},
    {"name": "カッター切", "spec": "151～200mm", "qty": 1, "unit": "式", "price": 793730},
    {"name": "コンクリート壊し", "spec": "～200mm", "qty": 1, "unit": "式", "price": 441170},
    {"name": "コンクリート復旧", "spec": "～200mm", "qty": 1, "unit": "式", "price": 703250},
    {"name": "完全固定金具", "spec": "80Ax4", "qty": 1, "unit": "式", "price": 232860},
    {"name": "高所作業車使用料", "spec": "", "qty": 1, "unit": "式", "price": 195000},
    {"name": "資機材運搬費", "spec": "", "qty": 1, "unit": "式", "price": 909000},
    {"name": "諸経費", "spec": "", "qty": 1, "unit": "式", "price": 1200810},
    {"name": "解体費", "spec": "解体後整地別途等", "qty": 1, "unit": "式", "price": 1500000},
    {"name": "法定福利費", "spec": "A=¥4,090,000 Ax16.07%", "qty": 1, "unit": "式", "price": 657263},
]

# PriceReferenceオブジェクトに変換
for i, item in enumerate(gas_items):
    price_ref = PriceReference(
        item_id=f"GAS_{i+1:03d}",
        description=item["name"],
        discipline=DisciplineType.GAS,
        unit=item["unit"],
        unit_price=float(item["price"]),
        vendor="株式会社エコリース",
        valid_from=date(2025, 9, 18),
        valid_to=None,
        source_project="都立山崎高校仮設校舎_都市ガス設備工事",
        context_tags=["学校", "高校", "仮設", "都市ガス"],
        features={
            "specification": item["spec"],
            "quantity": item["qty"],
            "location": "東京都町田市"
        },
        similarity_score=0.0
    )
    price_kb_data.append(price_ref.model_dump(mode='json'))

# KB保存
os.makedirs("kb", exist_ok=True)
kb_path = "kb/price_kb.json"

with open(kb_path, 'w', encoding='utf-8') as f:
    json.dump(price_kb_data, f, ensure_ascii=False, indent=2, default=str)

print(f"✅ 過去見積KB構築完了:")
print(f"   項目数: {len(price_kb_data)}")
print(f"   保存先: {kb_path}")

print(f"\n【価格KB サンプル（最初の10項目）】")
for ref_dict in price_kb_data[:10]:
    print(f"  - {ref_dict['description']} {ref_dict['features']['specification']} : ¥{ref_dict['unit_price']:,}/{ref_dict['unit']}")

# 統計情報
total_value = sum(ref['unit_price'] * ref['features']['quantity']
                  for ref in price_kb_data if ref['features'].get('quantity'))
avg_price = sum(ref['unit_price'] for ref in price_kb_data) / len(price_kb_data)

print(f"\n【統計情報】")
print(f"  総額: ¥{total_value:,}")
print(f"  平均単価: ¥{avg_price:,.0f}")
print(f"  工事区分: {price_kb_data[0]['discipline']}")
print(f"  出典: {price_kb_data[0]['source_project']}")
