"""Classifier - 施設区分・工事区分を分類"""

from typing import List, Dict, Any
from loguru import logger

from pipelines.schemas import FMTDocument, DisciplineType, FacilityType


class Classifier:
    """施設区分と工事区分を分類"""

    def __init__(self):
        # 工事区分のキーワード定義
        self.discipline_keywords = {
            DisciplineType.ELECTRICAL: [
                '電気', '照明', '電灯', 'コンセント', '分電盤', '配線', '電源', '動力',
                '幹線', '弱電', 'LAN', '電話', '情報', 'インターホン', '電気設備'
            ],
            DisciplineType.MECHANICAL: [
                '機械', 'エレベーター', '昇降機', 'エスカレーター', '搬送設備'
            ],
            DisciplineType.HVAC: [
                '空調', 'エアコン', '冷暖房', '換気', '空気調和', '全熱交換',
                'ファン', '空調機', 'パッケージエアコン', 'ダクト'
            ],
            DisciplineType.PLUMBING: [
                '衛生', '給水', '給湯', '排水', '汚水', '雑排水', '水道', '配管',
                '便器', '洗面', '流し', '手洗', '浄化槽', '貯水槽', '受水槽'
            ],
            DisciplineType.GAS: [
                'ガス', '都市ガス', 'LPガス', 'プロパン', 'ガス配管', 'ガス設備'
            ],
            DisciplineType.FIRE_PROTECTION: [
                '消防', '消火', 'スプリンクラー', '火災報知', '自動火災報知',
                '誘導灯', '非常照明', '防火', '排煙', '消火器', '屋内消火栓'
            ],
        }

    def classify(self, fmt_doc: FMTDocument) -> FMTDocument:
        """
        FMTドキュメントの施設区分と工事区分を分類

        Args:
            fmt_doc: FMTドキュメント

        Returns:
            分類結果を含むFMTドキュメント
        """
        logger.info("Classifying facility type and disciplines")

        # 工事区分を分類
        disciplines = self._classify_disciplines(fmt_doc)
        fmt_doc.disciplines = disciplines

        logger.info(f"Identified disciplines: {[d.value for d in disciplines]}")

        return fmt_doc

    def _classify_disciplines(self, fmt_doc: FMTDocument) -> List[DisciplineType]:
        """
        テキストと要求事項から工事区分を分類

        Returns:
            検出された工事区分のリスト
        """
        text = (fmt_doc.raw_text or '').lower()
        disciplines_found = set()

        # キーワードマッチング
        for discipline, keywords in self.discipline_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    disciplines_found.add(discipline)
                    break

        # 要求事項からも分類
        requirements = fmt_doc.requirements or {}
        discipline_mapping = {
            'electrical': DisciplineType.ELECTRICAL,
            'mechanical': DisciplineType.MECHANICAL,
            'hvac': DisciplineType.HVAC,
            'plumbing': DisciplineType.PLUMBING,
            'gas': DisciplineType.GAS,
            'fire_protection': DisciplineType.FIRE_PROTECTION,
        }

        for req_key, discipline in discipline_mapping.items():
            if req_key in requirements and requirements[req_key]:
                disciplines_found.add(discipline)

        # 建物仕様の設備からも分類
        for building in fmt_doc.building_specs:
            for room in building.rooms:
                for equipment in room.equipment:
                    equipment_lower = equipment.lower()
                    for discipline, keywords in self.discipline_keywords.items():
                        if any(kw in equipment_lower for kw in keywords):
                            disciplines_found.add(discipline)

        return sorted(list(disciplines_found), key=lambda x: x.value)

    def get_discipline_priority(self, fmt_doc: FMTDocument) -> Dict[DisciplineType, float]:
        """
        各工事区分の優先度・重要度を算出

        Returns:
            工事区分ごとのスコア (0.0-1.0)
        """
        text = fmt_doc.raw_text or ''
        scores = {}

        for discipline in fmt_doc.disciplines:
            keywords = self.discipline_keywords.get(discipline, [])
            # キーワード出現回数をカウント
            count = sum(text.lower().count(kw) for kw in keywords)
            scores[discipline] = min(count / 10.0, 1.0)  # 正規化

        return scores
