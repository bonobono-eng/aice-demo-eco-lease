"""
見積生成システム v3（法令要件統合版）

機能:
1. 仕様書から見積項目を抽出（file_logic.md分析ベース）
2. 関係法令から法令要件を抽出
3. 過去見積KBから単価をRAG検索
4. 法令要件に基づく見積項目の追加・検証
5. 法定福利費（16.07%）を自動追加
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from pipelines.schemas import (
    EstimateItem, DisciplineType, FMTDocument,
    CostType, OverheadCalculation, LegalReference
)
from pipelines.estimate_extractor_v2 import EstimateExtractorV2
from pipelines.legal_requirement_extractor import LegalRequirementExtractor


class EstimateGeneratorWithLegal:
    """
    見積生成システム v3（法令要件統合版）
    """

    def __init__(self, kb_path: Optional[str] = None):
        """
        Args:
            kb_path: 過去見積KBのパス（デフォルト: kb/price_kb.json）
        """
        self.extractor = EstimateExtractorV2()
        self.legal_extractor = LegalRequirementExtractor()

        if kb_path is None:
            kb_path = "kb/price_kb.json"

        self.kb_path = kb_path
        self.price_kb: List[Dict[str, Any]] = []

        # KBを読み込み
        if Path(kb_path).exists():
            with open(kb_path, 'r', encoding='utf-8') as f:
                self.price_kb = json.load(f)
            logger.info(f"Loaded {len(self.price_kb)} items from KB: {kb_path}")
        else:
            logger.warning(f"KB file not found: {kb_path}")

    def match_price_from_kb(
        self,
        item: EstimateItem,
        similarity_threshold: float = 0.3
    ) -> Optional[float]:
        """過去見積KBから単価をマッチング"""
        if not self.price_kb:
            return None

        # 工事区分でフィルタリング
        discipline_items = [
            kb_item for kb_item in self.price_kb
            if kb_item.get("discipline") == item.discipline.value
        ]

        if not discipline_items:
            return None

        # 簡易マッチング
        best_match = None
        best_score = 0.0

        target_str = f"{item.name} {item.specification or ''}".lower()

        for kb_item in discipline_items:
            kb_str = f"{kb_item.get('description', '')} {kb_item.get('features', {}).get('specification', '')}".lower()

            target_words = set(target_str.split())
            kb_words = set(kb_str.split())

            if not target_words or not kb_words:
                continue

            common_words = target_words & kb_words
            score = len(common_words) / max(len(target_words), len(kb_words))

            if score > best_score:
                best_score = score
                best_match = kb_item

        if best_match and best_score >= similarity_threshold:
            logger.info(f"Matched: {item.name} -> KB:{best_match['item_id']} (score={best_score:.2f})")
            return best_match.get("unit_price")

        return None

    def calculate_item_amount(self, item: EstimateItem) -> float:
        """見積項目の金額を計算"""
        if item.amount:
            return item.amount

        # 材料費: 単価 × 数量
        if item.cost_type == CostType.MATERIAL:
            if item.unit_price and item.quantity:
                amount = item.unit_price * item.quantity
                item.calculation_formula = f"¥{item.unit_price:,.0f} × {item.quantity}{item.unit}"
                return amount

        # 労務費: 労務単価 × 人工数
        elif item.cost_type == CostType.LABOR:
            if item.labor_unit_price and item.labor_days:
                amount = item.labor_unit_price * item.labor_days
                item.calculation_formula = f"¥{item.labor_unit_price:,.0f}/人日 × {item.labor_days}人日"
                return amount
            elif item.unit_price and item.quantity:
                amount = item.unit_price * item.quantity
                item.calculation_formula = f"¥{item.unit_price:,.0f} × {item.quantity}{item.unit}"
                return amount

        # 諸経費: 基礎額 × 率
        elif item.cost_type == CostType.OVERHEAD:
            if item.overhead_base_amount and item.overhead_rate:
                amount = item.overhead_base_amount * item.overhead_rate
                item.calculation_formula = f"¥{item.overhead_base_amount:,.0f} × {item.overhead_rate*100:.2f}%"
                return amount

        # その他
        elif item.unit_price and item.quantity:
            amount = item.unit_price * item.quantity
            item.calculation_formula = f"¥{item.unit_price:,.0f} × {item.quantity}{item.unit}"
            return amount

        return 0.0

    def enrich_with_rag(
        self,
        fmt_doc: FMTDocument,
        similarity_threshold: float = 0.3
    ) -> FMTDocument:
        """RAGで単価を付与し、金額を計算"""
        logger.info("Enriching estimate items with RAG")

        for item in fmt_doc.estimate_items:
            if item.cost_type == CostType.MATERIAL and not item.unit_price:
                matched_price = self.match_price_from_kb(item, similarity_threshold)
                if matched_price:
                    item.unit_price = matched_price
                    item.source_type = "rag"
                    item.source_reference = f"KB (similarity >= {similarity_threshold})"

            amount = self.calculate_item_amount(item)
            if amount > 0:
                item.amount = amount

        logger.info("RAG enrichment completed")
        return fmt_doc

    def add_statutory_welfare_costs(
        self,
        fmt_doc: FMTDocument,
        rate: float = 0.1607
    ) -> FMTDocument:
        """法定福利費を追加"""
        logger.info(f"Adding statutory welfare costs (rate={rate*100:.2f}%)")

        base_amount = 0.0
        for item in fmt_doc.estimate_items:
            if item.cost_type != CostType.OVERHEAD and item.amount:
                base_amount += item.amount

        welfare_amount = base_amount * rate

        welfare_item = EstimateItem(
            item_no="",
            level=0,
            name="法定福利費",
            specification="",
            quantity=None,
            unit="",
            unit_price=None,
            amount=welfare_amount,
            discipline=fmt_doc.disciplines[0] if fmt_doc.disciplines else None,
            cost_type=CostType.OVERHEAD,
            calculation_formula=f"工事費 ¥{base_amount:,.0f} × {rate*100:.2f}%",
            overhead_rate=rate,
            overhead_base_amount=base_amount,
            source_type="rule",
            source_reference="file_logic.md分析: 都市ガス見積書に記載の標準率",
            remarks="工事費の16.07%"
        )

        fmt_doc.estimate_items.append(welfare_item)

        overhead_calc = OverheadCalculation(
            name="法定福利費",
            rate=rate,
            base_amount=base_amount,
            amount=welfare_amount,
            formula=f"工事費 ¥{base_amount:,.0f} × {rate*100:.2f}%",
            remarks="file_logic.md分析: 都市ガス見積書に記載の標準率"
        )

        fmt_doc.overhead_calculations.append(overhead_calc)

        logger.info(f"Added statutory welfare costs: ¥{welfare_amount:,.0f}")
        return fmt_doc

    def add_legal_based_items(
        self,
        fmt_doc: FMTDocument,
        legal_refs: List[LegalReference]
    ) -> FMTDocument:
        """
        法令要件に基づく見積項目を追加

        Args:
            fmt_doc: FMTDocument
            legal_refs: 法令参照リスト

        Returns:
            法令項目が追加されたFMTDocument
        """
        logger.info("Adding legal requirement based items")

        added_items = []

        for legal_ref in legal_refs:
            # 高信頼度（0.9以上）の法令要件のみ
            if legal_ref.relevance_score < 0.9:
                continue

            # 既に該当項目が存在するかチェック
            existing_item = None
            for item in fmt_doc.estimate_items:
                if legal_ref.article and legal_ref.article in item.name:
                    existing_item = item
                    break

            if existing_item:
                logger.info(f"Legal requirement already covered: {legal_ref.article}")
                continue

            # 新しい見積項目を作成
            # TODO: 法令要件から具体的な仕様・数量を推定
            legal_item = EstimateItem(
                item_no="",
                level=1,
                name=f"{legal_ref.article}（法令対応）",
                specification=legal_ref.norm_value.get("target", "") if legal_ref.norm_value else "",
                quantity=None,
                unit="式",
                unit_price=None,
                amount=None,
                discipline=fmt_doc.disciplines[0] if fmt_doc.disciplines else None,
                cost_type=CostType.LUMP_SUM,
                source_type="legal",
                source_reference=f"{legal_ref.law_code}:{legal_ref.article}",
                confidence=legal_ref.relevance_score,
                remarks=f"法令遵守項目: {legal_ref.title}"
            )

            added_items.append(legal_item)
            logger.info(f"Added legal item: {legal_item.name}")

        fmt_doc.estimate_items.extend(added_items)
        logger.info(f"Added {len(added_items)} legal requirement based items")

        return fmt_doc

    def generate_estimate_with_legal(
        self,
        spec_pdf_path: str,
        disciplines: List[DisciplineType],
        add_welfare_costs: bool = True,
        validate_legal: bool = True
    ) -> Dict[str, Any]:
        """
        仕様書から見積書を生成（法令要件統合版）

        Args:
            spec_pdf_path: 仕様書PDFのパス
            disciplines: 工事区分のリスト
            add_welfare_costs: 法定福利費を自動追加するか
            validate_legal: 法令遵守を検証するか

        Returns:
            {
                "fmt_doc": FMTDocument,
                "legal_refs": List[LegalReference],
                "violations": List[Dict],
                "summary": Dict
            }
        """
        logger.info(f"Generating estimate with legal requirements from: {spec_pdf_path}")

        # 1. 仕様書からテキストを抽出
        spec_text = self.extractor.extract_text_from_pdf(spec_pdf_path)

        # 2. 仕様書から見積項目を抽出
        fmt_doc = self.extractor.create_fmt_document_from_spec(
            spec_pdf_path,
            disciplines
        )

        # 3. 法令要件を抽出
        legal_requirements_data = []
        for discipline in disciplines:
            reqs = self.legal_extractor.extract_legal_requirements(
                spec_text,
                discipline
            )
            legal_requirements_data.extend(reqs)

        # LegalReferenceに変換
        legal_refs = self.legal_extractor.convert_to_legal_references(
            legal_requirements_data
        )

        fmt_doc.legal_references = legal_refs

        # 4. 法令に基づく見積項目を追加
        fmt_doc = self.add_legal_based_items(fmt_doc, legal_refs)

        # 5. RAGで単価を付与し、金額を計算
        fmt_doc = self.enrich_with_rag(fmt_doc)

        # 6. 法定福利費を追加
        if add_welfare_costs:
            fmt_doc = self.add_statutory_welfare_costs(fmt_doc)

        # 7. 法令遵守を検証
        violations = []
        if validate_legal:
            violations = self.legal_extractor.validate_estimate_against_laws(
                fmt_doc.estimate_items,
                legal_refs
            )

        # 8. メタデータを更新
        fmt_doc.metadata["generation_method"] = "EstimateGeneratorWithLegal v3.0"
        fmt_doc.metadata["rag_enabled"] = True
        fmt_doc.metadata["welfare_costs_added"] = add_welfare_costs
        fmt_doc.metadata["legal_validation_enabled"] = validate_legal
        fmt_doc.metadata["legal_requirements_count"] = len(legal_refs)
        fmt_doc.metadata["legal_violations_count"] = len(violations)

        # サマリーを作成
        total_amount = sum(item.amount for item in fmt_doc.estimate_items if item.amount)

        summary = {
            "total_items": len(fmt_doc.estimate_items),
            "legal_items_added": len([i for i in fmt_doc.estimate_items if i.source_type == "legal"]),
            "total_amount": total_amount,
            "legal_requirements": len(legal_refs),
            "legal_violations": len(violations)
        }

        logger.info("Estimate generation with legal requirements completed")

        return {
            "fmt_doc": fmt_doc,
            "legal_refs": legal_refs,
            "violations": violations,
            "summary": summary
        }


if __name__ == "__main__":
    # テスト実行
    import sys
    sys.path.insert(0, '.')

    generator = EstimateGeneratorWithLegal(kb_path="kb/price_kb.json")

    spec_path = "test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf"

    if Path(spec_path).exists():
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

        print(f"\n{'='*80}")
        print(f"✅ 見積書生成完了（法令要件統合版）")
        print(f"{'='*80}")

        print(f"\n【プロジェクト情報】")
        print(f"  工事名: {fmt_doc.project_info.project_name}")
        print(f"  場所: {fmt_doc.project_info.location}")

        print(f"\n【見積サマリー】")
        print(f"  総項目数: {summary['total_items']}")
        print(f"  法令対応項目: {summary['legal_items_added']}")
        print(f"  合計金額: ¥{summary['total_amount']:,.0f}")

        print(f"\n【法令遵守状況】")
        print(f"  適用法令数: {summary['legal_requirements']}")
        print(f"  法令違反リスク: {summary['legal_violations']}件")

        if violations:
            print(f"\n【法令違反リスク詳細】")
            for i, violation in enumerate(violations[:5]):
                print(f"\n  {i+1}. {violation['law_name']}")
                print(f"     重要度: {violation['severity']}")
                print(f"     内容: {violation['message']}")
                print(f"     推奨対応: {violation['recommendation']}")

    else:
        print(f"❌ 仕様書が見つかりません: {spec_path}")
