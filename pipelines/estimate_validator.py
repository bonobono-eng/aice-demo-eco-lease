"""
見積書整合性チェックモジュール

生成された見積書の妥当性を検証します。
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from loguru import logger

from .schemas import FMTDocument, EstimateItem


class EstimateValidator:
    """見積書の整合性を検証するクラス"""

    # 建物タイプ別の標準単価範囲（円/㎡）
    BUILDING_TYPE_RANGES = {
        "学校": {
            "電気設備工事": (15000, 40000),    # 1.5万～4万円/㎡
            "機械設備工事": (20000, 50000),    # 2万～5万円/㎡
            "ガス設備工事": (1000, 5000),      # 0.1万～0.5万円/㎡
            "空調設備工事": (10000, 30000),    # 1万～3万円/㎡
            "衛生設備工事": (5000, 15000),     # 0.5万～1.5万円/㎡
            "消防設備工事": (3000, 10000),     # 0.3万～1万円/㎡
        },
        "オフィス": {
            "電気設備工事": (20000, 50000),
            "機械設備工事": (25000, 60000),
            "ガス設備工事": (500, 3000),
            "空調設備工事": (15000, 40000),
            "衛生設備工事": (5000, 15000),
            "消防設備工事": (3000, 10000),
        },
        "default": {
            "電気設備工事": (15000, 50000),
            "機械設備工事": (15000, 50000),
            "ガス設備工事": (1000, 10000),
            "空調設備工事": (10000, 40000),
            "衛生設備工事": (5000, 20000),
            "消防設備工事": (3000, 15000),
        }
    }

    def __init__(self):
        pass

    def validate_estimate(
        self,
        fmt_doc: FMTDocument,
        reference_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        見積書の整合性を検証

        Args:
            fmt_doc: 検証対象のFMTDocument
            reference_path: 参照見積書のパス（オプション）

        Returns:
            検証結果の辞書
        """
        results = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "summary": {},
            "discipline_checks": {},
            "anomaly_items": [],
        }

        items = fmt_doc.estimate_items
        floor_area = fmt_doc.project_info.floor_area_m2 or 2000
        building_type = fmt_doc.facility_type or "default"

        # 工事区分別の検証
        disciplines = {}
        for item in items:
            disc = item.discipline.value if item.discipline else "その他"
            if disc not in disciplines:
                disciplines[disc] = []
            disciplines[disc].append(item)

        for disc_name, disc_items in disciplines.items():
            check_result = self._check_discipline(
                disc_name, disc_items, floor_area, building_type
            )
            results["discipline_checks"][disc_name] = check_result

            if check_result.get("status") == "error":
                results["errors"].append(check_result["message"])
                results["is_valid"] = False
            elif check_result.get("status") == "warning":
                results["warnings"].append(check_result["message"])

        # 異常項目の検出
        anomalies = self._detect_anomalies(items)
        results["anomaly_items"] = anomalies
        if anomalies:
            results["warnings"].append(f"{len(anomalies)}件の異常項目を検出")

        # サマリー
        total_amount = sum(item.amount or 0 for item in items if item.level == 0)
        results["summary"] = {
            "total_amount": total_amount,
            "total_items": len(items),
            "floor_area": floor_area,
            "amount_per_sqm": total_amount / floor_area if floor_area > 0 else 0,
            "disciplines": len(disciplines),
        }

        return results

    def _check_discipline(
        self,
        disc_name: str,
        items: List[EstimateItem],
        floor_area: float,
        building_type: str
    ) -> Dict[str, Any]:
        """工事区分ごとの妥当性チェック"""
        # Level 0の合計を取得
        total = sum(item.amount or 0 for item in items if item.level == 0)

        # 標準範囲を取得
        ranges = self.BUILDING_TYPE_RANGES.get(
            building_type,
            self.BUILDING_TYPE_RANGES["default"]
        )
        disc_range = ranges.get(disc_name, (1000, 100000))
        min_per_sqm, max_per_sqm = disc_range

        # 単価計算
        per_sqm = total / floor_area if floor_area > 0 else 0
        expected_min = min_per_sqm * floor_area
        expected_max = max_per_sqm * floor_area

        result = {
            "discipline": disc_name,
            "total_amount": total,
            "item_count": len(items),
            "amount_per_sqm": per_sqm,
            "expected_range": (expected_min, expected_max),
            "expected_per_sqm": (min_per_sqm, max_per_sqm),
        }

        if total > expected_max * 1.5:
            result["status"] = "error"
            result["message"] = (
                f"{disc_name}: 金額が高すぎます（¥{total:,.0f} > 期待上限¥{expected_max:,.0f}の1.5倍）"
            )
        elif total > expected_max:
            result["status"] = "warning"
            result["message"] = (
                f"{disc_name}: 金額がやや高い（¥{total:,.0f} > 期待上限¥{expected_max:,.0f}）"
            )
        elif total < expected_min * 0.5 and total > 0:
            result["status"] = "warning"
            result["message"] = (
                f"{disc_name}: 金額がやや低い（¥{total:,.0f} < 期待下限¥{expected_min:,.0f}の半分）"
            )
        else:
            result["status"] = "ok"
            result["message"] = f"{disc_name}: 妥当な範囲内（¥{total:,.0f}）"

        return result

    def _detect_anomalies(self, items: List[EstimateItem]) -> List[Dict[str, Any]]:
        """異常項目の検出"""
        anomalies = []

        for item in items:
            if item.level == 0:
                continue

            anomaly = None

            # 1. 金額が1000万円を超える単一項目
            if item.amount and item.amount > 10000000:
                anomaly = {
                    "item": item.name,
                    "type": "high_amount",
                    "value": item.amount,
                    "message": f"金額が1000万円超（¥{item.amount:,.0f}）"
                }

            # 2. 単価が異常に高い
            if item.unit_price and item.unit_price > 5000000:
                # キュービクル等の高額機器は除外
                if not any(kw in item.name for kw in ["キュービクル", "変圧器", "発電機", "エレベーター"]):
                    anomaly = {
                        "item": item.name,
                        "type": "high_unit_price",
                        "value": item.unit_price,
                        "message": f"単価が500万円超（¥{item.unit_price:,.0f}）"
                    }

            # 3. 数量が異常に多い
            if item.quantity and item.quantity > 10000:
                anomaly = {
                    "item": item.name,
                    "type": "high_quantity",
                    "value": item.quantity,
                    "message": f"数量が1万を超過（{item.quantity}）"
                }

            if anomaly:
                anomalies.append(anomaly)

        return anomalies

    def format_report(self, results: Dict[str, Any]) -> str:
        """検証結果をレポート形式で出力"""
        lines = []
        lines.append("=" * 60)
        lines.append("見積書整合性チェックレポート")
        lines.append("=" * 60)

        summary = results.get("summary", {})
        lines.append(f"\n【サマリー】")
        lines.append(f"  総額: ¥{summary.get('total_amount', 0):,.0f}")
        lines.append(f"  項目数: {summary.get('total_items', 0)}件")
        lines.append(f"  延床面積: {summary.get('floor_area', 0):,.1f}㎡")
        lines.append(f"  単価/㎡: ¥{summary.get('amount_per_sqm', 0):,.0f}")

        lines.append(f"\n【工事区分別チェック】")
        for disc_name, check in results.get("discipline_checks", {}).items():
            status_icon = "✓" if check["status"] == "ok" else "⚠" if check["status"] == "warning" else "✗"
            lines.append(f"  {status_icon} {check['message']}")
            lines.append(f"      期待範囲: ¥{check['expected_range'][0]:,.0f} ～ ¥{check['expected_range'][1]:,.0f}")

        if results.get("anomaly_items"):
            lines.append(f"\n【異常項目】")
            for anomaly in results["anomaly_items"]:
                lines.append(f"  ⚠ {anomaly['item']}: {anomaly['message']}")

        if results.get("errors"):
            lines.append(f"\n【エラー】")
            for error in results["errors"]:
                lines.append(f"  ✗ {error}")

        if results.get("warnings"):
            lines.append(f"\n【警告】")
            for warning in results["warnings"]:
                lines.append(f"  ⚠ {warning}")

        lines.append("\n" + "=" * 60)
        verdict = "✓ 妥当" if results["is_valid"] else "✗ 要確認"
        lines.append(f"総合判定: {verdict}")
        lines.append("=" * 60)

        return "\n".join(lines)


if __name__ == "__main__":
    # テスト
    from pathlib import Path
    import json

    output_dir = Path("output")
    latest_json = sorted(output_dir.glob("見積データ_*.json"), key=lambda x: x.stat().st_mtime)[-1]

    with open(latest_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fmt_doc = FMTDocument.model_validate(data)

    validator = EstimateValidator()
    results = validator.validate_estimate(fmt_doc)
    report = validator.format_report(results)
    print(report)
