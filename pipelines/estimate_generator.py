"""
見積生成システム（file_logic.md分析に基づく実装）
仕様書から見積書を生成（RAG + 諸経費計算 統合版）
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from pipelines.schemas import (
    EstimateItem, DisciplineType, FMTDocument,
    CostType, OverheadCalculation, PriceReference
)
from pipelines.estimate_extractor_v2 import EstimateExtractorV2


class EstimateGenerator:
    """
    見積生成システム（file_logic.md分析に基づく実装）

    機能:
    1. 仕様書から見積項目を抽出（EstimateExtractorV2）
    2. 過去見積KBから単価をRAG検索
    3. 金額を自動計算（材料費×数量、労務費、諸経費）
    4. 法定福利費（16.07%）を自動追加
    """

    def __init__(self, kb_path: Optional[str] = None):
        """
        Args:
            kb_path: 過去見積KBのパス（デフォルト: kb/price_kb.json）
        """
        self.extractor = EstimateExtractorV2()

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
        """
        過去見積KBから単価をマッチング

        Args:
            item: 見積項目
            similarity_threshold: 類似度閾値

        Returns:
            マッチした単価（見つからない場合はNone）
        """
        if not self.price_kb:
            return None

        # 工事区分でフィルタリング
        discipline_items = [
            kb_item for kb_item in self.price_kb
            if kb_item.get("discipline") == item.discipline.value
        ]

        if not discipline_items:
            return None

        # 簡易マッチング（項目名+仕様で文字列マッチング）
        # TODO: ベクトル検索（FAISS + embedding）に置き換え
        best_match = None
        best_score = 0.0

        target_str = f"{item.name} {item.specification or ''}".lower()

        for kb_item in discipline_items:
            kb_str = f"{kb_item.get('description', '')} {kb_item.get('features', {}).get('specification', '')}".lower()

            # 簡易類似度（共通単語数 / 全単語数）
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
        """
        見積項目の金額を計算（file_logic.md分析のロジックに基づく）

        Args:
            item: 見積項目

        Returns:
            計算された金額
        """
        if item.amount:
            # 既に金額が設定されている場合はそのまま返す
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
                # 労務費が単価×数量で計上されている場合
                amount = item.unit_price * item.quantity
                item.calculation_formula = f"¥{item.unit_price:,.0f} × {item.quantity}{item.unit}"
                return amount

        # 諸経費: 基礎額 × 率
        elif item.cost_type == CostType.OVERHEAD:
            if item.overhead_base_amount and item.overhead_rate:
                amount = item.overhead_base_amount * item.overhead_rate
                item.calculation_formula = f"¥{item.overhead_base_amount:,.0f} × {item.overhead_rate*100:.2f}%"
                return amount

        # その他の費用区分: 単価が設定されていれば計算
        elif item.unit_price and item.quantity:
            amount = item.unit_price * item.quantity
            item.calculation_formula = f"¥{item.unit_price:,.0f} × {item.quantity}{item.unit}"
            return amount

        # 計算できない場合は0
        return 0.0

    def enrich_with_rag(
        self,
        fmt_doc: FMTDocument,
        similarity_threshold: float = 0.3
    ) -> FMTDocument:
        """
        RAGで単価を付与し、金額を計算

        Args:
            fmt_doc: FMTDocument
            similarity_threshold: 類似度閾値

        Returns:
            単価・金額が付与されたFMTDocument
        """
        logger.info("Enriching estimate items with RAG")

        for item in fmt_doc.estimate_items:
            # 材料費のみRAGでマッチング
            if item.cost_type == CostType.MATERIAL and not item.unit_price:
                matched_price = self.match_price_from_kb(item, similarity_threshold)
                if matched_price:
                    item.unit_price = matched_price
                    item.source_type = "rag"
                    item.source_reference = f"KB (similarity >= {similarity_threshold})"

            # 金額を計算
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
        """
        法定福利費を追加（file_logic.md分析より: 16.07%）

        Args:
            fmt_doc: FMTDocument
            rate: 法定福利費率（デフォルト: 16.07%）

        Returns:
            法定福利費が追加されたFMTDocument
        """
        logger.info(f"Adding statutory welfare costs (rate={rate*100:.2f}%)")

        # 工事費の合計を計算（諸経費を除く）
        base_amount = 0.0
        for item in fmt_doc.estimate_items:
            if item.cost_type != CostType.OVERHEAD and item.amount:
                base_amount += item.amount

        # 法定福利費を計算
        welfare_amount = base_amount * rate

        # 法定福利費項目を追加
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

        # OverheadCalculationも追加
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

    def generate_estimate(
        self,
        spec_pdf_path: str,
        disciplines: List[DisciplineType],
        add_welfare_costs: bool = True
    ) -> FMTDocument:
        """
        仕様書から見積書を生成（file_logic.md分析に基づく完全版）

        Args:
            spec_pdf_path: 仕様書PDFのパス
            disciplines: 工事区分のリスト
            add_welfare_costs: 法定福利費を自動追加するか（デフォルト: True）

        Returns:
            生成された見積書（FMTDocument）
        """
        logger.info(f"Generating estimate from spec: {spec_pdf_path}")

        # 1. 仕様書から見積項目を抽出
        fmt_doc = self.extractor.create_fmt_document_from_spec(
            spec_pdf_path,
            disciplines
        )

        # 2. RAGで単価を付与し、金額を計算
        fmt_doc = self.enrich_with_rag(fmt_doc)

        # 3. 法定福利費を追加
        if add_welfare_costs:
            fmt_doc = self.add_statutory_welfare_costs(fmt_doc)

        # 4. メタデータを更新
        fmt_doc.metadata["generation_method"] = "EstimateGenerator v1.0"
        fmt_doc.metadata["rag_enabled"] = True
        fmt_doc.metadata["welfare_costs_added"] = add_welfare_costs

        logger.info("Estimate generation completed")
        return fmt_doc

    def calculate_total_amount(self, fmt_doc: FMTDocument) -> float:
        """
        見積書の合計金額を計算

        Args:
            fmt_doc: FMTDocument

        Returns:
            合計金額
        """
        total = 0.0
        for item in fmt_doc.estimate_items:
            if item.amount:
                total += item.amount
        return total


if __name__ == "__main__":
    # テスト実行
    generator = EstimateGenerator(kb_path="kb/price_kb.json")

    spec_path = "test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf"

    if Path(spec_path).exists():
        # 見積書を生成
        fmt_doc = generator.generate_estimate(
            spec_path,
            disciplines=[DisciplineType.GAS],
            add_welfare_costs=True
        )

        print(f"\n{'='*60}")
        print(f"✅ 見積書生成完了")
        print(f"{'='*60}")
        print(f"工事名: {fmt_doc.project_info.project_name}")
        print(f"場所: {fmt_doc.project_info.location}")
        print(f"見積項目数: {len(fmt_doc.estimate_items)}")

        # 費用区分別の項目数を集計
        cost_type_count = {}
        for item in fmt_doc.estimate_items:
            ct = item.cost_type.value if item.cost_type else "未分類"
            cost_type_count[ct] = cost_type_count.get(ct, 0) + 1

        print(f"\n【費用区分別項目数】")
        for ct, count in cost_type_count.items():
            print(f"  {ct}: {count}項目")

        # 金額が付与された項目数を集計
        items_with_price = [item for item in fmt_doc.estimate_items if item.amount]
        print(f"\n【単価・金額付与状況】")
        print(f"  単価付与: {len([i for i in fmt_doc.estimate_items if i.unit_price])}/{len(fmt_doc.estimate_items)} 項目")
        print(f"  金額計算: {len(items_with_price)}/{len(fmt_doc.estimate_items)} 項目")

        # 合計金額を計算
        total_amount = generator.calculate_total_amount(fmt_doc)
        print(f"\n【合計金額】")
        print(f"  総額: ¥{total_amount:,.0f}")

        # 諸経費を表示
        if fmt_doc.overhead_calculations:
            print(f"\n【諸経費計算】")
            for overhead in fmt_doc.overhead_calculations:
                print(f"  {overhead.name}: ¥{overhead.amount:,.0f}")
                print(f"  計算式: {overhead.formula}")

        # 見積項目を表示（最初の20項目）
        print(f"\n【見積項目（最初の20項目）】")
        for i, item in enumerate(fmt_doc.estimate_items[:20]):
            indent = "  " * item.level
            ct = item.cost_type.value if item.cost_type else "未分類"
            spec_str = f" {item.specification}" if item.specification else ""
            qty_str = f" {item.quantity}{item.unit}" if item.quantity else ""
            price_str = f" @¥{item.unit_price:,.0f}" if item.unit_price else ""
            amount_str = f" = ¥{item.amount:,.0f}" if item.amount else ""
            print(f"{indent}{item.name}{spec_str}{qty_str}{price_str}{amount_str} [{ct}]")

    else:
        print(f"❌ 仕様書が見つかりません: {spec_path}")
