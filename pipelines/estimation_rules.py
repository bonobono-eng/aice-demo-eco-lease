"""
見積精度向上モジュール

工事区分別チェックリスト、数量推定ルール、妥当性検証を提供します。
人間の見積プロセスを模倣し、精度向上を図ります。
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger

from pipelines.schemas import EstimateItem, DisciplineType


# =============================================================================
# 工事区分別チェックリスト
# =============================================================================

DISCIPLINE_CHECKLISTS = {
    DisciplineType.ELECTRICAL: {
        "name": "電気設備工事",
        "categories": {
            "受変電設備": [
                "キュービクル",
                "高圧気中開閉器（PAS）",
                "変圧器",
                "進相コンデンサ",
                "高圧ケーブル",
                "接地工事",
            ],
            "幹線設備": [
                "幹線ケーブル（CV/CVT）",
                "ケーブルラック",
                "配管・配線",
                "ジョイントボックス",
                "プルボックス",
            ],
            "分電盤・制御盤": [
                "主幹分電盤",
                "電灯分電盤",
                "動力分電盤",
                "制御盤",
            ],
            "照明設備": [
                "照明器具",
                "非常照明",
                "誘導灯",
                "外灯",
                "スイッチ",
            ],
            "コンセント設備": [
                "コンセント",
                "OAコンセント",
                "防水コンセント",
            ],
            "弱電設備": [
                "電話配管・配線",
                "LAN配管・配線",
                "インターホン",
                "放送設備",
                "テレビ共聴設備",
                "監視カメラ設備",
            ],
            "防災設備": [
                "自動火災報知設備",
                "非常放送設備",
                "避雷設備",
            ],
            "その他": [
                "仮設電気工事",
                "既存設備撤去",
                "試験調整費",
                "諸経費",
            ],
        },
    },
    DisciplineType.MECHANICAL: {
        "name": "機械設備工事",
        "categories": {
            "空調設備": [
                "エアコン（室内機）",
                "エアコン（室外機）",
                "冷媒配管",
                "ドレン配管",
                "換気扇",
                "ダクト",
            ],
            "換気設備": [
                "換気扇",
                "全熱交換器",
                "送風機",
                "排煙設備",
            ],
            "給水設備": [
                "給水ポンプ",
                "受水槽",
                "給水配管",
                "給水栓",
            ],
            "給湯設備": [
                "給湯器",
                "給湯配管",
            ],
            "排水設備": [
                "排水配管",
                "排水ポンプ",
                "グリストラップ",
                "汚水槽",
            ],
            "衛生器具": [
                "便器",
                "洗面器",
                "流し台",
            ],
            "消火設備": [
                "屋内消火栓",
                "スプリンクラー",
                "消火器",
            ],
            "その他": [
                "保温工事",
                "塗装工事",
                "試験調整費",
                "諸経費",
            ],
        },
    },
    DisciplineType.GAS: {
        "name": "ガス設備工事",
        "categories": {
            "配管工事": [
                "都市ガス引込み",
                "白ガス管",
                "カラー鋼管",
                "PE管（ポリエチレン管）",
                "フレキ管",
                "配管支持金具",
            ],
            "ガス栓・機器": [
                "ガスコンセント",
                "ガス栓",
                "ネジコック",
                "分岐コック",
                "ボールバルブ",
            ],
            "安全装置": [
                "ガス漏れ警報器",
                "緊急遮断弁",
                "ヒューズコック",
            ],
            "付帯工事": [
                "掘削・埋戻し",
                "舗装復旧",
                "穴補修",
                "配管撤去",
            ],
            "その他": [
                "気密試験",
                "資機材運搬",
                "諸経費",
            ],
        },
    },
}


# =============================================================================
# 数量推定ルール（面積・部屋数ベース）
# =============================================================================

@dataclass
class QuantityRule:
    """数量推定ルール"""
    item_keywords: List[str]  # 対象項目のキーワード
    per_sqm: Optional[float] = None  # ㎡あたりの数量
    per_room: Optional[float] = None  # 部屋あたりの数量
    per_floor: Optional[float] = None  # 階あたりの数量
    fixed_quantity: Optional[float] = None  # 固定数量
    min_quantity: Optional[float] = None  # 最小数量
    max_quantity: Optional[float] = None  # 最大数量
    unit: str = "個"  # 単位
    description: str = ""  # 説明


QUANTITY_RULES = {
    DisciplineType.ELECTRICAL: [
        # 照明
        QuantityRule(
            item_keywords=["照明器具", "照明", "ライト"],
            per_sqm=0.08,  # 8台/100㎡
            min_quantity=10,
            unit="台",
            description="床面積から推定（8台/100㎡）"
        ),
        QuantityRule(
            item_keywords=["非常照明", "非常灯"],
            per_sqm=0.02,  # 2台/100㎡
            min_quantity=5,
            unit="台",
            description="床面積から推定（2台/100㎡）"
        ),
        QuantityRule(
            item_keywords=["誘導灯"],
            per_room=0.5,  # 2部屋に1台
            min_quantity=5,
            unit="台",
            description="部屋数から推定（2部屋に1台）"
        ),
        # コンセント
        QuantityRule(
            item_keywords=["コンセント"],
            per_sqm=0.15,  # 15個/100㎡
            per_room=4,  # または4個/室
            min_quantity=20,
            unit="箇所",
            description="床面積または部屋数から推定"
        ),
        # スイッチ
        QuantityRule(
            item_keywords=["スイッチ"],
            per_room=2,  # 2個/室
            min_quantity=10,
            unit="箇所",
            description="部屋数から推定（2個/室）"
        ),
        # 分電盤
        QuantityRule(
            item_keywords=["分電盤"],
            per_floor=2,  # 2面/階
            min_quantity=2,
            unit="面",
            description="階数から推定（2面/階）"
        ),
        # ケーブル
        QuantityRule(
            item_keywords=["ケーブル", "幹線", "CV", "CVT"],
            per_sqm=0.5,  # 50m/100㎡
            min_quantity=100,
            unit="m",
            description="床面積から推定（50m/100㎡）"
        ),
        # 電話・LAN
        QuantityRule(
            item_keywords=["電話", "LAN", "情報"],
            per_room=2,  # 2口/室
            min_quantity=10,
            unit="箇所",
            description="部屋数から推定（2口/室）"
        ),
    ],
    DisciplineType.MECHANICAL: [
        # エアコン
        QuantityRule(
            item_keywords=["エアコン", "空調機", "室内機"],
            per_sqm=0.05,  # 5台/100㎡
            min_quantity=5,
            unit="台",
            description="床面積から推定（5台/100㎡）"
        ),
        # 換気扇
        QuantityRule(
            item_keywords=["換気扇"],
            per_room=0.5,  # 2部屋に1台
            min_quantity=5,
            unit="台",
            description="部屋数から推定"
        ),
        # 給水栓
        QuantityRule(
            item_keywords=["給水栓", "蛇口", "水栓"],
            per_room=0.3,  # 3部屋に1個
            min_quantity=5,
            unit="個",
            description="部屋数から推定"
        ),
        # 便器
        QuantityRule(
            item_keywords=["便器", "トイレ"],
            per_sqm=0.01,  # 1台/100㎡
            min_quantity=2,
            unit="台",
            description="床面積から推定"
        ),
        # 配管
        QuantityRule(
            item_keywords=["給水配管", "排水配管", "配管"],
            per_sqm=0.3,  # 30m/100㎡
            min_quantity=50,
            unit="m",
            description="床面積から推定"
        ),
    ],
    DisciplineType.GAS: [
        # ガス栓
        QuantityRule(
            item_keywords=["ガス栓", "ガスコンセント", "ガス口"],
            per_room=0.2,  # 5部屋に1個（調理室等）
            min_quantity=2,
            unit="個",
            description="部屋数から推定（調理室等）"
        ),
        # ガス配管
        QuantityRule(
            item_keywords=["ガス管", "白ガス管", "配管"],
            per_sqm=0.15,  # 15m/100㎡
            min_quantity=30,
            unit="m",
            description="床面積から推定"
        ),
        # 警報器
        QuantityRule(
            item_keywords=["警報器", "ガス漏れ"],
            per_room=0.1,  # 10部屋に1個
            min_quantity=1,
            unit="個",
            description="ガス使用箇所に設置"
        ),
    ],
}


# =============================================================================
# 建物タイプ別 ㎡単価目安（妥当性チェック用）
# =============================================================================

BUILDING_TYPE_UNIT_PRICES = {
    "学校": {
        DisciplineType.ELECTRICAL: {"min": 15000, "max": 40000, "typical": 25000},
        DisciplineType.MECHANICAL: {"min": 20000, "max": 50000, "typical": 35000},
        DisciplineType.GAS: {"min": 1000, "max": 8000, "typical": 3000},
    },
    "オフィス": {
        DisciplineType.ELECTRICAL: {"min": 20000, "max": 50000, "typical": 30000},
        DisciplineType.MECHANICAL: {"min": 25000, "max": 60000, "typical": 40000},
        DisciplineType.GAS: {"min": 500, "max": 3000, "typical": 1000},
    },
    "病院": {
        DisciplineType.ELECTRICAL: {"min": 30000, "max": 70000, "typical": 45000},
        DisciplineType.MECHANICAL: {"min": 40000, "max": 80000, "typical": 55000},
        DisciplineType.GAS: {"min": 2000, "max": 10000, "typical": 5000},
    },
    "default": {
        DisciplineType.ELECTRICAL: {"min": 15000, "max": 50000, "typical": 30000},
        DisciplineType.MECHANICAL: {"min": 20000, "max": 60000, "typical": 35000},
        DisciplineType.GAS: {"min": 1000, "max": 10000, "typical": 4000},
    },
}


# =============================================================================
# チェックリスト検証
# =============================================================================

class EstimationChecker:
    """見積精度チェッカー"""

    def __init__(self):
        pass

    def check_item_coverage(
        self,
        items: List[EstimateItem],
        discipline: DisciplineType
    ) -> Dict[str, Any]:
        """
        チェックリストに対する項目カバー率を検証

        Returns:
            {
                "coverage_rate": 0.85,
                "covered_items": ["照明器具", "コンセント", ...],
                "missing_items": ["誘導灯", ...],
                "extra_items": [...],
                "suggestions": [...]
            }
        """
        checklist = DISCIPLINE_CHECKLISTS.get(discipline)
        if not checklist:
            return {"coverage_rate": 0, "message": f"No checklist for {discipline.value}"}

        # 全チェック項目をフラット化
        all_check_items = []
        for category, items_list in checklist["categories"].items():
            all_check_items.extend(items_list)

        # 生成された項目名をリスト化
        generated_names = [item.name for item in items]
        generated_names_lower = [n.lower() for n in generated_names]

        # カバー率計算
        covered = []
        missing = []

        for check_item in all_check_items:
            # 部分一致でチェック
            found = False
            for gen_name in generated_names:
                if self._is_similar(check_item, gen_name):
                    found = True
                    covered.append(check_item)
                    break
            if not found:
                missing.append(check_item)

        coverage_rate = len(covered) / len(all_check_items) if all_check_items else 0

        # 提案生成
        suggestions = []
        for item in missing[:10]:  # 最大10件
            suggestions.append(f"「{item}」が見積に含まれていません。必要に応じて追加してください。")

        return {
            "discipline": discipline.value,
            "total_check_items": len(all_check_items),
            "coverage_rate": coverage_rate,
            "covered_count": len(covered),
            "covered_items": covered,
            "missing_count": len(missing),
            "missing_items": missing,
            "suggestions": suggestions,
        }

    def _is_similar(self, check_item: str, generated_name: str) -> bool:
        """2つの項目名が類似しているかチェック"""
        check_lower = check_item.lower()
        gen_lower = generated_name.lower()

        # 完全一致
        if check_lower in gen_lower or gen_lower in check_lower:
            return True

        # キーワード一致（3文字以上の共通部分）
        for i in range(len(check_lower) - 2):
            substr = check_lower[i:i+3]
            if substr in gen_lower:
                return True

        return False

    def estimate_quantities(
        self,
        items: List[EstimateItem],
        discipline: DisciplineType,
        floor_area: float,
        num_rooms: int = 0,
        num_floors: int = 1
    ) -> List[EstimateItem]:
        """
        数量が未設定の項目に推定数量を設定

        Args:
            items: 見積項目リスト
            discipline: 工事区分
            floor_area: 延床面積（㎡）
            num_rooms: 部屋数
            num_floors: 階数

        Returns:
            数量が補完された項目リスト
        """
        rules = QUANTITY_RULES.get(discipline, [])

        for item in items:
            # 数量が既に設定されている場合はスキップ
            if item.quantity is not None and item.quantity > 0:
                continue

            # ルールに基づいて数量を推定
            for rule in rules:
                if self._matches_rule(item.name, rule.item_keywords):
                    estimated_qty = self._calculate_quantity(
                        rule, floor_area, num_rooms, num_floors
                    )
                    if estimated_qty > 0:
                        item.quantity = estimated_qty
                        item.unit = rule.unit
                        item.estimation_basis = f"自動推定: {rule.description}"
                        item.confidence = 0.6  # 推定値は信頼度を下げる
                        logger.debug(f"Estimated quantity for '{item.name}': {estimated_qty} {rule.unit}")
                        break

        return items

    def _matches_rule(self, item_name: str, keywords: List[str]) -> bool:
        """項目名がルールのキーワードにマッチするか"""
        item_lower = item_name.lower()
        for kw in keywords:
            if kw.lower() in item_lower:
                return True
        return False

    def _calculate_quantity(
        self,
        rule: QuantityRule,
        floor_area: float,
        num_rooms: int,
        num_floors: int
    ) -> float:
        """ルールに基づいて数量を計算"""
        quantity = 0

        if rule.per_sqm and floor_area > 0:
            quantity = floor_area * rule.per_sqm

        if rule.per_room and num_rooms > 0:
            room_qty = num_rooms * rule.per_room
            quantity = max(quantity, room_qty) if quantity > 0 else room_qty

        if rule.per_floor and num_floors > 0:
            floor_qty = num_floors * rule.per_floor
            quantity = max(quantity, floor_qty) if quantity > 0 else floor_qty

        if rule.fixed_quantity:
            quantity = rule.fixed_quantity

        # 最小・最大制限
        if rule.min_quantity:
            quantity = max(quantity, rule.min_quantity)
        if rule.max_quantity:
            quantity = min(quantity, rule.max_quantity)

        return round(quantity, 1)

    def validate_unit_price(
        self,
        items: List[EstimateItem],
        discipline: DisciplineType,
        building_type: str,
        floor_area: float
    ) -> Dict[str, Any]:
        """
        ㎡単価の妥当性を検証

        Returns:
            {
                "is_valid": True/False,
                "actual_unit_price": 25000,
                "expected_range": {"min": 15000, "max": 40000},
                "deviation": 0.1,
                "message": "..."
            }
        """
        # 工事区分の合計金額を計算（Level 0のみ）
        total_amount = sum(item.amount or 0 for item in items if item.level == 0)

        if floor_area <= 0:
            return {"is_valid": False, "message": "床面積が不明です"}

        actual_unit_price = total_amount / floor_area

        # 期待範囲を取得
        building_prices = BUILDING_TYPE_UNIT_PRICES.get(
            building_type,
            BUILDING_TYPE_UNIT_PRICES["default"]
        )
        expected = building_prices.get(discipline, {"min": 0, "max": 999999, "typical": 0})

        # 妥当性判定
        is_valid = expected["min"] <= actual_unit_price <= expected["max"]
        deviation = (actual_unit_price - expected["typical"]) / expected["typical"] if expected["typical"] > 0 else 0

        message = ""
        if actual_unit_price < expected["min"]:
            message = f"㎡単価が低すぎます（¥{actual_unit_price:,.0f}/㎡ < 下限¥{expected['min']:,}/㎡）"
        elif actual_unit_price > expected["max"]:
            message = f"㎡単価が高すぎます（¥{actual_unit_price:,.0f}/㎡ > 上限¥{expected['max']:,}/㎡）"
        else:
            message = f"㎡単価は妥当な範囲内です（¥{actual_unit_price:,.0f}/㎡）"

        return {
            "discipline": discipline.value,
            "is_valid": is_valid,
            "total_amount": total_amount,
            "floor_area": floor_area,
            "actual_unit_price": actual_unit_price,
            "expected_range": {"min": expected["min"], "max": expected["max"]},
            "typical_unit_price": expected["typical"],
            "deviation": deviation,
            "deviation_pct": f"{deviation * 100:+.1f}%",
            "message": message,
        }

    def generate_missing_items(
        self,
        existing_items: List[EstimateItem],
        discipline: DisciplineType,
        floor_area: float = 0,
        num_rooms: int = 0
    ) -> List[EstimateItem]:
        """
        チェックリストに基づいて不足項目を生成

        Returns:
            追加すべき項目のリスト
        """
        coverage = self.check_item_coverage(existing_items, discipline)
        missing = coverage.get("missing_items", [])

        new_items = []
        for item_name in missing[:20]:  # 最大20項目
            # 数量推定ルールを適用
            quantity = None
            unit = "式"
            estimation_basis = "チェックリストから追加"

            for rule in QUANTITY_RULES.get(discipline, []):
                if self._matches_rule(item_name, rule.item_keywords):
                    quantity = self._calculate_quantity(rule, floor_area, num_rooms, 1)
                    unit = rule.unit
                    estimation_basis = f"チェックリスト追加: {rule.description}"
                    break

            new_item = EstimateItem(
                item_no="",
                name=item_name,
                quantity=quantity,
                unit=unit,
                level=2,  # 詳細項目として追加
                discipline=discipline,
                confidence=0.5,  # 自動追加は信頼度を下げる
                estimation_basis=estimation_basis,
            )
            new_items.append(new_item)

        logger.info(f"Generated {len(new_items)} missing items for {discipline.value}")
        return new_items

    def correct_underpriced_estimate(
        self,
        items: List[EstimateItem],
        discipline: DisciplineType,
        building_type: str,
        floor_area: float,
        correction_method: str = "adjustment_item"
    ) -> Dict[str, Any]:
        """
        ㎡単価が下限を下回る場合に補正を行う

        Args:
            items: 見積項目リスト
            discipline: 工事区分
            building_type: 建物タイプ
            floor_area: 延床面積（㎡）
            correction_method: 補正方法
                - "adjustment_item": 調整項目を追加
                - "overhead_increase": 諸経費率を上げる
                - "none": 補正しない（検証のみ）

        Returns:
            {
                "corrected": True/False,
                "correction_item": EstimateItem or None,
                "shortage_amount": 金額,
                "validation": validate_unit_price結果
            }
        """
        # 現在の㎡単価を検証
        validation = self.validate_unit_price(items, discipline, building_type, floor_area)

        if validation.get("is_valid", True):
            return {
                "corrected": False,
                "correction_item": None,
                "shortage_amount": 0,
                "validation": validation,
                "message": "㎡単価は適正範囲内です。補正不要。"
            }

        # 下限を下回っている場合のみ補正
        actual_price = validation.get("actual_unit_price", 0)
        min_price = validation.get("expected_range", {}).get("min", 0)

        if actual_price >= min_price:
            return {
                "corrected": False,
                "correction_item": None,
                "shortage_amount": 0,
                "validation": validation,
                "message": "㎡単価が上限を超えていますが、自動補正は行いません。"
            }

        # 不足金額を計算
        shortage_per_sqm = min_price - actual_price
        shortage_amount = shortage_per_sqm * floor_area

        logger.info(
            f"㎡単価補正: {discipline.value} - "
            f"現在¥{actual_price:,.0f}/㎡ → 目標¥{min_price:,}/㎡, "
            f"不足額¥{shortage_amount:,.0f}"
        )

        if correction_method == "none":
            return {
                "corrected": False,
                "correction_item": None,
                "shortage_amount": shortage_amount,
                "validation": validation,
                "message": f"補正が必要です（不足額: ¥{shortage_amount:,.0f}）"
            }

        # 調整項目を作成
        correction_item = EstimateItem(
            item_no="ADJ",
            name="見積調整費",
            specification=f"㎡単価調整（¥{shortage_per_sqm:,.0f}/㎡ × {floor_area:,.0f}㎡）",
            quantity=1,
            unit="式",
            unit_price=shortage_amount,
            amount=shortage_amount,
            level=1,
            discipline=discipline,
            cost_type="諸経費",
            confidence=0.7,
            source_type="adjustment",
            source_reference=f"㎡単価下限補正: {min_price:,}円/㎡",
            estimation_basis=f"建物タイプ「{building_type}」の{discipline.value}㎡単価下限に基づく調整"
        )

        return {
            "corrected": True,
            "correction_item": correction_item,
            "shortage_amount": shortage_amount,
            "shortage_per_sqm": shortage_per_sqm,
            "validation": validation,
            "message": f"㎡単価補正項目を追加しました（¥{shortage_amount:,.0f}）"
        }

    def apply_all_corrections(
        self,
        items: List[EstimateItem],
        discipline: DisciplineType,
        building_type: str,
        floor_area: float,
        auto_correct: bool = True
    ) -> Dict[str, Any]:
        """
        全ての補正を適用し、結果をまとめる

        Args:
            items: 見積項目リスト
            discipline: 工事区分
            building_type: 建物タイプ
            floor_area: 延床面積
            auto_correct: 自動補正を行うかどうか

        Returns:
            {
                "original_amount": 元の合計,
                "corrected_amount": 補正後の合計,
                "corrections": [補正内容リスト],
                "items_added": [追加された項目],
                "validation_before": 補正前の検証結果,
                "validation_after": 補正後の検証結果
            }
        """
        # 元の合計を計算
        original_amount = sum(item.amount or 0 for item in items if item.level == 0)

        # 検証
        validation_before = self.validate_unit_price(items, discipline, building_type, floor_area)

        corrections = []
        items_added = []

        if auto_correct and not validation_before.get("is_valid", True):
            # ㎡単価補正
            correction_result = self.correct_underpriced_estimate(
                items, discipline, building_type, floor_area,
                correction_method="adjustment_item"
            )

            if correction_result.get("corrected"):
                corrections.append({
                    "type": "unit_price_adjustment",
                    "amount": correction_result["shortage_amount"],
                    "message": correction_result["message"]
                })
                items_added.append(correction_result["correction_item"])

        # 補正後の合計
        added_amount = sum(item.amount or 0 for item in items_added)
        corrected_amount = original_amount + added_amount

        # 補正後の検証（仮想的に）
        validation_after = {
            **validation_before,
            "actual_unit_price": corrected_amount / floor_area if floor_area > 0 else 0,
            "total_amount": corrected_amount,
        }
        if floor_area > 0:
            new_price = corrected_amount / floor_area
            expected = validation_before.get("expected_range", {})
            validation_after["is_valid"] = expected.get("min", 0) <= new_price <= expected.get("max", 999999)
            validation_after["message"] = f"補正後㎡単価: ¥{new_price:,.0f}/㎡"

        return {
            "discipline": discipline.value,
            "original_amount": original_amount,
            "corrected_amount": corrected_amount,
            "correction_total": added_amount,
            "corrections": corrections,
            "items_added": items_added,
            "validation_before": validation_before,
            "validation_after": validation_after,
        }


# =============================================================================
# ユーティリティ関数
# =============================================================================

def get_checklist_summary(discipline: DisciplineType) -> str:
    """チェックリストのサマリーを取得"""
    checklist = DISCIPLINE_CHECKLISTS.get(discipline)
    if not checklist:
        return f"No checklist for {discipline.value}"

    lines = [f"【{checklist['name']}チェックリスト】"]
    for category, items in checklist["categories"].items():
        lines.append(f"\n■ {category}")
        for item in items:
            lines.append(f"  - {item}")

    return "\n".join(lines)


if __name__ == "__main__":
    # テスト
    checker = EstimationChecker()

    # チェックリストサマリー表示
    print(get_checklist_summary(DisciplineType.ELECTRICAL))

    # 数量推定テスト
    test_items = [
        EstimateItem(item_no="1", name="照明器具", level=2, discipline=DisciplineType.ELECTRICAL),
        EstimateItem(item_no="2", name="コンセント", level=2, discipline=DisciplineType.ELECTRICAL),
    ]

    result = checker.estimate_quantities(
        test_items,
        DisciplineType.ELECTRICAL,
        floor_area=2000,
        num_rooms=30
    )

    for item in result:
        print(f"{item.name}: {item.quantity} {item.unit} - {item.estimation_basis}")
