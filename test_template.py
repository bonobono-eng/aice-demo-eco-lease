"""テンプレートPDF生成テスト"""

from pipelines.schemas import FMTDocument, ProjectInfo, EstimateItem, FacilityType, DisciplineType
from pipelines.pdf_generator import EcoleasePDFGenerator
from datetime import datetime

# ダミーデータを作成
fmt_doc = FMTDocument(
    created_at=datetime.now().isoformat(),
    project_info=ProjectInfo(
        project_name="都立山崎高校仮設校舎　都市ガス設備工事",
        client_name="株式会社システムハウスR&C東京支店",
        location="東京都町田市山崎町1453番地1",
        contract_period="25ヶ月（2026.8.1～2028.8.31）見積有効期間6ヶ月"
    ),
    facility_type=FacilityType.SCHOOL,
    disciplines=[DisciplineType.GAS],
    estimate_items=[
        EstimateItem(
            item_no="1",
            level=0,
            name="都市ガス設備工事",
            amount=11275000
        ),
        EstimateItem(
            item_no="",
            level=1,
            name="基本工事費",
            specification="増設・他",
            quantity=1,
            unit="件",
            unit_price=13600,
            amount=13600
        ),
        EstimateItem(
            item_no="",
            level=1,
            name="配管工事費",
            specification="",
            quantity=None,
            unit="",
            unit_price=None,
            amount=None
        ),
        EstimateItem(
            item_no="",
            level=2,
            name="白ガス管（ネジ接合）",
            specification="15A",
            quantity=93,
            unit="m",
            unit_price=8990,
            amount=836070
        ),
        EstimateItem(
            item_no="",
            level=2,
            name="〃",
            specification="20A",
            quantity=18,
            unit="m",
            unit_price=8990,
            amount=161820
        ),
        EstimateItem(
            item_no="",
            level=2,
            name="〃",
            specification="25A",
            quantity=16,
            unit="m",
            unit_price=8990,
            amount=143840
        ),
        EstimateItem(
            item_no="2",
            level=0,
            name="解体費",
            amount=1500000
        ),
        EstimateItem(
            item_no="",
            level=1,
            name="解体費",
            specification="解体後整地別途\nコンクリートツリ補修費別途\nアスファルトカッター切り補修費別途\n既存補修費別途\n産廃処分別途",
            quantity=1,
            unit="式",
            unit_price=1500000,
            amount=1500000
        ),
        EstimateItem(
            item_no="3",
            level=0,
            name="法定福利費",
            amount=657263
        ),
        EstimateItem(
            item_no="",
            level=1,
            name="法定福利費",
            specification="A=¥4,090,000\nAx16.07%",
            quantity=1,
            unit="式",
            unit_price=657263,
            amount=657263
        ),
    ],
    metadata={
        "quote_no": "0976589-00"
    }
)

# PDF生成
pdf_gen = EcoleasePDFGenerator()
output_path = "./output/template_test.pdf"

import os
os.makedirs("./output", exist_ok=True)

pdf_gen.generate(fmt_doc, output_path)
print(f"✅ テンプレートPDFを生成しました: {output_path}")
