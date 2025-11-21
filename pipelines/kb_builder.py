"""過去見積KBとLLM抽出機能の統合モジュール"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dotenv import load_dotenv
from anthropic import Anthropic
from loguru import logger
import PyPDF2

from pipelines.schemas import (
    PriceReference, DisciplineType, EstimateItem,
    Requirement, LegalReference
)


class PriceKBBuilder:
    """見積書PDFから過去見積KBを構築"""

    def __init__(self):
        load_dotenv()
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model_name = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    def extract_estimate_from_pdf(self, pdf_path: str) -> List[PriceReference]:
        """見積書PDFから価格情報を抽出してKB化"""
        logger.info(f"Building price KB from: {pdf_path}")

        # PDFからテキストを抽出
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(min(len(pdf_reader.pages), 10)):  # 最大10ページ
                text += pdf_reader.pages[page_num].extract_text() + "\n"

        logger.info(f"Extracted {len(text)} characters from PDF")

        # LLMで構造化データに変換
        prompt = f"""以下の見積書PDFから、単価情報を抽出してください。

見積書テキスト:
{text[:12000]}

【抽出する情報】
各見積項目について：
1. 項目名（name）
2. 仕様（specification）
3. 数量（quantity）
4. 単位（unit）
5. 単価（unit_price）
6. 金額（amount）
7. 工事区分（discipline: 電気|機械|空調|衛生|ガス|消防）

【出力形式】
JSON配列で出力してください：
```json
[
  {{
    "name": "白ガス管（ネジ接合）",
    "specification": "15A",
    "quantity": 93,
    "unit": "m",
    "unit_price": 8990,
    "amount": 836070,
    "discipline": "ガス"
  }}
]
```

単価が記載されている具体的な項目のみを抽出してください。親項目（小計のみ）は除外してください。"""

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=8000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # JSONを抽出
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1

            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in response")
                return []

            json_str = response_text[json_start:json_end]
            items_data = json.loads(json_str)

            logger.info(f"Extracted {len(items_data)} price items")

            # PriceReferenceオブジェクトに変換
            price_refs = []
            project_name = Path(pdf_path).stem

            for i, item in enumerate(items_data):
                if item.get("unit_price") and item.get("unit_price") > 0:
                    # 工事区分のマッピング
                    discipline_map = {
                        "電気": DisciplineType.ELECTRICAL,
                        "機械": DisciplineType.MECHANICAL,
                        "空調": DisciplineType.HVAC,
                        "衛生": DisciplineType.PLUMBING,
                        "ガス": DisciplineType.GAS,
                        "消防": DisciplineType.FIRE_PROTECTION
                    }

                    discipline = discipline_map.get(
                        item.get("discipline", ""),
                        DisciplineType.GAS
                    )

                    # コンテキストタグの生成
                    context_tags = []
                    if "学校" in project_name or "高校" in project_name:
                        context_tags.append("学校")
                    if "改修" in project_name:
                        context_tags.append("改修")
                    if "仮設" in project_name:
                        context_tags.append("仮設")

                    price_ref = PriceReference(
                        item_id=f"{project_name}_{i+1:03d}",
                        description=item.get("name", ""),
                        discipline=discipline,
                        unit=item.get("unit", "式"),
                        unit_price=float(item.get("unit_price", 0)),
                        vendor=None,
                        valid_from=date.today(),
                        valid_to=None,
                        source_project=project_name,
                        context_tags=context_tags,
                        features={
                            "specification": item.get("specification", ""),
                            "quantity": item.get("quantity"),
                        },
                        similarity_score=0.0
                    )
                    price_refs.append(price_ref)

            return price_refs

        except Exception as e:
            logger.error(f"Error extracting prices: {e}")
            return []

    def save_kb_to_json(self, price_refs: List[PriceReference], output_path: str):
        """KBをJSONファイルに保存"""
        kb_data = [ref.model_dump(mode='json') for ref in price_refs]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(kb_data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Saved {len(price_refs)} price references to {output_path}")

    def load_kb_from_json(self, kb_path: str) -> List[PriceReference]:
        """JSONファイルからKBを読み込み"""
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)

        price_refs = [PriceReference(**item) for item in kb_data]
        logger.info(f"Loaded {len(price_refs)} price references from {kb_path}")
        return price_refs


class EnhancedEstimateExtractor:
    """EstimateExtractorに信頼度スコアと根拠情報を追加"""

    def __init__(self, price_kb: List[PriceReference]):
        load_dotenv()
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model_name = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.price_kb = price_kb
        logger.info(f"Initialized with {len(price_kb)} price references")

    def extract_with_confidence(self, spec_text: str, discipline: DisciplineType) -> List[EstimateItem]:
        """
        信頼度スコア付きで見積項目を抽出

        Returns:
            信頼度スコアと根拠情報を含むEstimateItemのリスト
        """
        logger.info(f"Extracting items with confidence for {discipline}")

        discipline_map = {
            DisciplineType.ELECTRICAL: "電気設備工事",
            DisciplineType.MECHANICAL: "機械設備工事",
            DisciplineType.HVAC: "空調設備工事",
            DisciplineType.PLUMBING: "衛生設備工事",
            DisciplineType.GAS: "都市ガス設備工事",
            DisciplineType.FIRE_PROTECTION: "消防設備工事"
        }

        discipline_name = discipline_map.get(discipline, "設備工事")

        prompt = f"""以下の入札仕様書から、{discipline_name}に関連する見積項目を抽出してください。

仕様書テキスト:
{spec_text[:15000]}

【抽出する項目】
各見積項目について、以下の情報を抽出してください：
1. 項目名（name）
2. 仕様（specification）
3. 数量（quantity）: 明記されている場合のみ
4. 単位（unit）
5. 階層レベル（level）: 0=親項目, 1=子項目, 2=孫項目
6. 信頼度（confidence）: 0.0-1.0（仕様書に明記=0.9-1.0、推測=0.3-0.6、不明=0.0-0.2）
7. 根拠（source_page）: 該当ページ番号があれば

【重要】
- 数量が明記されていない場合は null を設定
- 単価は設定しない（後でKBから検索）
- 信頼度は以下の基準で設定:
  * 1.0: 仕様書に具体的な数値で明記
  * 0.8: 仕様書に記載あるが曖昧
  * 0.5: 図面や文脈から推測可能
  * 0.3: 一般的な標準値
  * 0.0: 不明・要確認

【出力形式】
JSON配列形式で出力してください：
```json
[
  {{
    "item_no": "1",
    "level": 0,
    "name": "{discipline_name}",
    "specification": "",
    "quantity": null,
    "unit": "式",
    "confidence": 0.9,
    "source_page": 1
  }},
  {{
    "item_no": "",
    "level": 2,
    "name": "白ガス管（ネジ接合）",
    "specification": "15A",
    "quantity": 93,
    "unit": "m",
    "confidence": 1.0,
    "source_page": 5
  }}
]
```"""

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=8000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # JSONを抽出
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1

            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in response")
                return []

            json_str = response_text[json_start:json_end]
            items_data = json.loads(json_str)

            # EstimateItemオブジェクトに変換
            estimate_items = []
            for item_data in items_data:
                estimate_item = EstimateItem(
                    item_no=item_data.get("item_no", ""),
                    level=item_data.get("level", 0),
                    name=item_data.get("name", ""),
                    specification=item_data.get("specification", ""),
                    quantity=item_data.get("quantity"),
                    unit=item_data.get("unit", ""),
                    unit_price=None,
                    amount=None,
                    discipline=discipline,
                    confidence=item_data.get("confidence", 0.5),
                    source_type="llm_extraction",
                    source_reference=f"spec_page_{item_data.get('source_page', 'unknown')}"
                )
                estimate_items.append(estimate_item)

            logger.info(f"Extracted {len(estimate_items)} items with confidence scores")
            return estimate_items

        except Exception as e:
            logger.error(f"Error extracting items with confidence: {e}")
            return []

    def enrich_with_price_rag(self, items: List[EstimateItem]) -> List[EstimateItem]:
        """
        KBから単価を検索して付与（簡易RAG）

        Args:
            items: 単価未設定の見積項目リスト

        Returns:
            単価と根拠情報が付与された見積項目リスト
        """
        logger.info(f"Enriching {len(items)} items with price RAG")

        enriched_items = []

        for item in items:
            # 同じ工事区分のKBエントリを検索
            matching_refs = [
                ref for ref in self.price_kb
                if ref.discipline == item.discipline
            ]

            # 項目名と仕様で簡易マッチング（実運用ではベクトル検索を使用）
            best_match = None
            best_score = 0.0

            for ref in matching_refs:
                # 簡易的な類似度計算（実運用ではembedding使用）
                score = 0.0
                if item.name and ref.description:
                    if item.name in ref.description or ref.description in item.name:
                        score += 0.5

                if item.specification and ref.features.get("specification"):
                    if item.specification == ref.features["specification"]:
                        score += 0.5

                if item.unit == ref.unit:
                    score += 0.3

                if score > best_score:
                    best_score = score
                    best_match = ref

            # 単価を設定
            if best_match and best_score >= 0.3:
                item.unit_price = best_match.unit_price
                item.price_references = [best_match.item_id]
                item.source_type = "rag"
                item.source_reference = f"KB:{best_match.item_id}(score={best_score:.2f})"

                # 金額を計算
                if item.quantity and item.unit_price:
                    item.amount = item.quantity * item.unit_price

                logger.debug(f"Matched '{item.name}' with '{best_match.description}' (score={best_score:.2f}, price=¥{best_match.unit_price:,})")
            else:
                logger.debug(f"No match found for '{item.name}' (best_score={best_score:.2f})")

            enriched_items.append(item)

        # 統計情報
        matched_count = sum(1 for item in enriched_items if item.unit_price is not None)
        logger.info(f"Matched {matched_count}/{len(enriched_items)} items with KB prices")

        return enriched_items


if __name__ == "__main__":
    # テスト実行
    kb_builder = PriceKBBuilder()

    # 見積書PDFから過去見積KBを構築
    estimate_pdf = "test-files/250918_送付状　見積書（都市ｶﾞｽ).pdf"

    if Path(estimate_pdf).exists():
        price_refs = kb_builder.extract_estimate_from_pdf(estimate_pdf)
        print(f"\n✅ 過去見積KB構築完了:")
        print(f"   抽出項目数: {len(price_refs)}")

        # KBを保存
        kb_output = "kb/price_kb.json"
        os.makedirs("kb", exist_ok=True)
        kb_builder.save_kb_to_json(price_refs, kb_output)
        print(f"   保存先: {kb_output}")

        # サンプル表示
        print(f"\n【価格KB サンプル（最初の5項目）】")
        for ref in price_refs[:5]:
            print(f"  - {ref.description} {ref.features.get('specification', '')} : ¥{ref.unit_price:,}/{ref.unit}")
    else:
        print(f"❌ 見積書が見つかりません: {estimate_pdf}")
