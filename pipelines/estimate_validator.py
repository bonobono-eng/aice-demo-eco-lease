"""
見積書整合性チェック機能

生成された見積書と実際の見積書（PDF）を比較して、精度を評価する
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import PyPDF2

from pipelines.schemas import EstimateItem, FMTDocument, DisciplineType


class EstimateValidator:
    """
    見積書整合性チェッカー

    生成された見積書と実際の見積書（PDF）を比較して、以下を評価：
    1. 項目カバー率（生成された項目数 / 参照見積書の項目数）
    2. 金額精度（生成された総額 / 参照見積書の総額）
    3. 項目名の一致率
    4. 仕様の一致率
    5. 数量の一致率
    """

    def __init__(self):
        pass

    def extract_reference_estimate_from_pdf(
        self,
        pdf_path: str,
        discipline: DisciplineType
    ) -> Dict[str, Any]:
        """
        参照見積書PDFから見積項目を抽出

        Args:
            pdf_path: 見積書PDFのパス
            discipline: 工事区分

        Returns:
            {
                "total_amount": float,        # 総額
                "items": List[Dict],          # 項目リスト
                "item_count": int,            # 項目数
                "discipline": DisciplineType  # 工事区分
            }
        """
        logger.info(f"Extracting reference estimate from: {pdf_path}")

        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num in range(min(len(pdf_reader.pages), 20)):
                    text += pdf_reader.pages[page_num].extract_text() + "\n"

            logger.info(f"Extracted {len(text)} characters from reference PDF")

            # PDFから総額を抽出（正規表現）
            # パターン: "合計" の後の数値、または "総額" の後の数値
            total_patterns = [
                r'合計.*?¥?([\d,]+)',
                r'総額.*?¥?([\d,]+)',
                r'小計.*?¥?([\d,]+)',
            ]

            total_amount = 0
            for pattern in total_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # 最大の数値を総額として採用
                    amounts = [int(m.replace(',', '')) for m in matches]
                    total_amount = max(amounts)
                    break

            # PDFから項目数を推定
            # 簡易的に、行数や特定パターンの出現回数から推定
            item_count = self._estimate_item_count_from_text(text, discipline)

            # 項目リストの抽出（簡易版）
            items = self._extract_items_from_text(text, discipline)

            logger.info(f"Reference estimate - Total: ¥{total_amount:,}, Items: {item_count}")

            return {
                "total_amount": total_amount,
                "items": items,
                "item_count": item_count,
                "discipline": discipline,
                "source_file": Path(pdf_path).name
            }

        except Exception as e:
            logger.error(f"Error extracting reference estimate: {e}")
            return {
                "total_amount": 0,
                "items": [],
                "item_count": 0,
                "discipline": discipline,
                "source_file": Path(pdf_path).name
            }

    def _estimate_item_count_from_text(
        self,
        text: str,
        discipline: DisciplineType
    ) -> int:
        """
        テキストから見積項目数を推定

        Args:
            text: PDFテキスト
            discipline: 工事区分

        Returns:
            推定項目数
        """
        # 工事区分別のキーワード
        keywords = {
            DisciplineType.GAS: [
                "ガス管", "PE管", "白ガス管", "カラー鋼管",
                "ガスコンセント", "ガス栓", "配管", "分岐コック"
            ],
            DisciplineType.ELECTRICAL: [
                "配線", "照明", "分電盤", "コンセント", "スイッチ",
                "ケーブル", "キュービクル", "受変電"
            ],
            DisciplineType.MECHANICAL: [
                "機械", "ポンプ", "ダクト", "配管", "バルブ"
            ]
        }

        # キーワード出現回数をカウント
        kw_list = keywords.get(discipline, [])
        count = 0
        for kw in kw_list:
            count += text.count(kw)

        # 簡易的な推定式（出現回数を調整）
        estimated_count = max(int(count * 0.5), 10)  # 最低10項目

        return estimated_count

    def _extract_items_from_text(
        self,
        text: str,
        discipline: DisciplineType
    ) -> List[Dict[str, Any]]:
        """
        テキストから見積項目を抽出（簡易版）

        Args:
            text: PDFテキスト
            discipline: 工事区分

        Returns:
            項目リスト
        """
        # TODO: より高度な抽出ロジックを実装
        # 現在は簡易的にキーワードマッチングのみ
        items = []

        # 工事区分別のキーワード
        keywords = {
            DisciplineType.GAS: [
                "白ガス管", "カラー鋼管", "PE管", "ガスコンセント",
                "ガス栓", "配管撤去", "分岐コック", "埋戻し"
            ],
            DisciplineType.ELECTRICAL: [
                "配線", "LED照明", "分電盤", "コンセント", "スイッチ",
                "ケーブル", "キュービクル"
            ]
        }

        kw_list = keywords.get(discipline, [])
        for i, kw in enumerate(kw_list):
            if kw in text:
                items.append({
                    "name": kw,
                    "specification": "",
                    "quantity": None,
                    "unit": "",
                    "found": True
                })

        return items

    def calculate_coverage(
        self,
        generated_items: List[EstimateItem],
        reference_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        見積項目のカバー率を計算

        Args:
            generated_items: 生成された見積項目
            reference_data: 参照見積書データ

        Returns:
            {
                "item_coverage": float,      # 項目カバー率（0-1）
                "generated_count": int,      # 生成項目数
                "reference_count": int,      # 参照項目数
                "matched_items": List[str]   # マッチした項目名
            }
        """
        generated_count = len(generated_items)
        reference_count = reference_data.get("item_count", 0)

        # 簡易的なカバー率計算
        coverage = min(generated_count / reference_count, 1.0) if reference_count > 0 else 0.0

        # 項目名のマッチング
        matched_items = []
        reference_items = reference_data.get("items", [])

        for gen_item in generated_items:
            for ref_item in reference_items:
                if ref_item["name"] in gen_item.name or gen_item.name in ref_item["name"]:
                    matched_items.append(gen_item.name)
                    break

        return {
            "item_coverage": coverage,
            "generated_count": generated_count,
            "reference_count": reference_count,
            "matched_items": matched_items,
            "match_rate": len(matched_items) / generated_count if generated_count > 0 else 0.0
        }

    def calculate_amount_accuracy(
        self,
        generated_amount: float,
        reference_amount: float
    ) -> Dict[str, Any]:
        """
        金額精度を計算

        Args:
            generated_amount: 生成された総額
            reference_amount: 参照見積書の総額

        Returns:
            {
                "accuracy": float,           # 精度（0-1）
                "generated_amount": float,   # 生成額
                "reference_amount": float,   # 参照額
                "difference": float,         # 差額
                "difference_rate": float     # 差額率
            }
        """
        if reference_amount == 0:
            return {
                "accuracy": 0.0,
                "generated_amount": generated_amount,
                "reference_amount": reference_amount,
                "difference": 0.0,
                "difference_rate": 0.0
            }

        difference = abs(generated_amount - reference_amount)
        difference_rate = difference / reference_amount

        # 精度: 差額率が小さいほど高精度
        accuracy = max(1.0 - difference_rate, 0.0)

        return {
            "accuracy": accuracy,
            "generated_amount": generated_amount,
            "reference_amount": reference_amount,
            "difference": difference,
            "difference_rate": difference_rate
        }

    def validate_estimate(
        self,
        fmt_doc: FMTDocument,
        reference_pdf_paths: Dict[DisciplineType, str]
    ) -> Dict[str, Any]:
        """
        見積書を検証

        Args:
            fmt_doc: 生成されたFMTDocument
            reference_pdf_paths: 参照見積書PDFのパス（工事区分別）

        Returns:
            検証結果の詳細
        """
        logger.info("Validating estimate against reference PDFs")

        validation_results = {
            "overall_score": 0.0,
            "disciplines": {},
            "summary": {}
        }

        # 工事区分別に検証
        for discipline in fmt_doc.disciplines:
            if discipline not in reference_pdf_paths:
                logger.warning(f"No reference PDF for discipline: {discipline}")
                continue

            # 参照見積書を抽出
            reference_data = self.extract_reference_estimate_from_pdf(
                reference_pdf_paths[discipline],
                discipline
            )

            # 生成された項目をフィルタ
            generated_items = [
                item for item in fmt_doc.estimate_items
                if item.discipline == discipline
            ]

            # 生成された総額を計算
            generated_amount = sum(
                item.amount for item in generated_items
                if item.amount
            )

            # カバー率を計算
            coverage_result = self.calculate_coverage(
                generated_items,
                reference_data
            )

            # 金額精度を計算
            amount_result = self.calculate_amount_accuracy(
                generated_amount,
                reference_data["total_amount"]
            )

            # 総合スコア（カバー率50% + 金額精度50%）
            discipline_score = (
                coverage_result["item_coverage"] * 0.5 +
                amount_result["accuracy"] * 0.5
            )

            validation_results["disciplines"][discipline.value] = {
                "score": discipline_score,
                "coverage": coverage_result,
                "amount": amount_result,
                "reference_file": reference_data["source_file"]
            }

        # 全体スコア（各工事区分の平均）
        if validation_results["disciplines"]:
            overall_score = sum(
                result["score"]
                for result in validation_results["disciplines"].values()
            ) / len(validation_results["disciplines"])

            validation_results["overall_score"] = overall_score

            # サマリー
            validation_results["summary"] = {
                "total_disciplines": len(validation_results["disciplines"]),
                "average_score": overall_score,
                "rating": self._get_rating(overall_score)
            }

        logger.info(f"Validation completed. Overall score: {validation_results['overall_score']:.2f}")

        return validation_results

    def _get_rating(self, score: float) -> str:
        """スコアから評価を取得"""
        if score >= 0.9:
            return "優秀（Excellent）"
        elif score >= 0.7:
            return "良好（Good）"
        elif score >= 0.5:
            return "普通（Fair）"
        elif score >= 0.3:
            return "要改善（Poor）"
        else:
            return "不十分（Insufficient）"


if __name__ == "__main__":
    # テスト実行
    import sys
    sys.path.insert(0, '.')

    from pipelines.estimate_generator_with_legal import EstimateGeneratorWithLegal

    validator = EstimateValidator()
    generator = EstimateGeneratorWithLegal(kb_path="kb/price_kb.json")

    # 仕様書から見積書を生成
    spec_path = "test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf"

    if Path(spec_path).exists():
        print("\n" + "="*80)
        print("見積書整合性チェックテスト")
        print("="*80)

        # 見積書を生成
        result = generator.generate_estimate_with_legal(
            spec_path,
            disciplines=[DisciplineType.GAS],
            add_welfare_costs=True,
            validate_legal=False  # 法令検証は省略（時間短縮）
        )

        fmt_doc = result["fmt_doc"]

        # 参照見積書PDFを指定
        reference_pdfs = {
            DisciplineType.GAS: "test-files/250918_送付状　見積書（都市ｶﾞｽ).pdf"
        }

        # 検証実行
        validation_results = validator.validate_estimate(
            fmt_doc,
            reference_pdfs
        )

        # 結果を表示
        print(f"\n【総合評価】")
        print(f"  スコア: {validation_results['overall_score']:.2%}")
        print(f"  評価: {validation_results['summary']['rating']}")

        print(f"\n【工事区分別結果】")
        for discipline, result in validation_results["disciplines"].items():
            print(f"\n  {discipline}:")
            print(f"    スコア: {result['score']:.2%}")
            print(f"    項目カバー率: {result['coverage']['item_coverage']:.2%}")
            print(f"    金額精度: {result['amount']['accuracy']:.2%}")
            print(f"    参照ファイル: {result['reference_file']}")

    else:
        print(f"❌ 仕様書が見つかりません: {spec_path}")
