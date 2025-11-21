"""FMT Normalizer - 抽出データを社内統一フォーマットに変換"""

from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from pipelines.schemas import (
    FMTDocument,
    ProjectInfo,
    BuildingSpec,
    RoomSpec,
    FacilityType,
    DisciplineType
)


class FMTNormalizer:
    """抽出されたデータをFMT(社内統一フォーマット)に変換"""

    def __init__(self):
        pass

    def normalize(self, ingested_data: Dict[str, Any], project_info: Dict[str, Any],
                  building_specs: List[Dict[str, Any]]) -> FMTDocument:
        """
        取り込んだデータをFMTドキュメントに変換

        Args:
            ingested_data: ingest.pyから取得したデータ
            project_info: 案件情報
            building_specs: 建物仕様

        Returns:
            FMTDocument
        """
        logger.info("Normalizing data to FMT format")

        # ProjectInfo作成
        fmt_project_info = ProjectInfo(
            project_name=project_info.get('project_name', '不明'),
            client_name=project_info.get('client_name'),
            location=project_info.get('location'),
            contract_period=project_info.get('contract_period')
        )

        # BuildingSpec作成
        fmt_building_specs = []
        for spec in building_specs:
            rooms = []
            if 'rooms' in spec:
                for room in spec['rooms']:
                    rooms.append(RoomSpec(
                        room_name=room.get('room_name', ''),
                        area=room.get('area'),
                        equipment=room.get('equipment', []),
                        specifications=room.get('specifications', {})
                    ))

            fmt_building_specs.append(BuildingSpec(
                building_name=spec.get('building_name', '建物'),
                building_type=spec.get('building_type', '不明'),
                structure=spec.get('structure'),
                total_area=spec.get('total_area'),
                floors=spec.get('floors'),
                height=spec.get('height'),
                rooms=rooms
            ))

        # FMTDocument作成
        fmt_doc = FMTDocument(
            fmt_version="1.0",
            created_at=datetime.now().isoformat(),
            project_info=fmt_project_info,
            facility_type=self._infer_facility_type(ingested_data.get('text', '')),
            building_specs=fmt_building_specs,
            disciplines=[],  # classifierで設定
            requirements={},
            estimate_items=[],
            legal_references=[],
            qa_items=[],
            raw_text=ingested_data.get('text', ''),
            extracted_tables=ingested_data.get('tables', []),
            metadata={
                'page_count': ingested_data.get('metadata', {}).get('page_count', 0),
                'has_images': len(ingested_data.get('images', [])) > 0
            }
        )

        logger.info(f"Created FMT document with {len(fmt_building_specs)} buildings")

        return fmt_doc

    def _infer_facility_type(self, text: str) -> FacilityType:
        """テキストから施設区分を推論"""

        # キーワードマッピング
        keywords = {
            FacilityType.SCHOOL: ['学校', '校舎', '教室', '高等学校', '中学校', '小学校', '大学'],
            FacilityType.OFFICE: ['オフィス', '事務所', '本社', '支社'],
            FacilityType.HOSPITAL: ['病院', '医療', 'クリニック', '診療所'],
            FacilityType.FACTORY: ['工場', '製造', 'プラント'],
            FacilityType.COMMERCIAL: ['商業', '店舗', 'ショッピング', 'モール'],
        }

        for facility_type, kws in keywords.items():
            if any(kw in text for kw in kws):
                return facility_type

        return FacilityType.OTHER

    def extract_requirements(self, fmt_doc: FMTDocument) -> Dict[str, Any]:
        """
        FMTドキュメントから要求事項を抽出

        Returns:
            要求事項の辞書
        """
        requirements = {
            'electrical': [],
            'mechanical': [],
            'hvac': [],
            'plumbing': [],
            'gas': [],
            'fire_protection': [],
            'construction': []
        }

        text = fmt_doc.raw_text or ''

        # 設備キーワードから要求事項を抽出
        equipment_keywords = {
            'electrical': ['照明', '電灯', 'コンセント', '分電盤', '配線', '電源'],
            'mechanical': ['エレベーター', '昇降機', '機械'],
            'hvac': ['空調', 'エアコン', '換気', '空気調和', '冷暖房'],
            'plumbing': ['給水', '排水', '衛生', '水道', '配管', '給湯'],
            'gas': ['ガス', '都市ガス', 'ガス配管'],
            'fire_protection': ['消防', '消火', 'スプリンクラー', '火災報知', '防火'],
        }

        for category, keywords in equipment_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    requirements[category].append(f'{keyword}設備')

        # 建物仕様から部屋ごとの設備を抽出
        for building in fmt_doc.building_specs:
            for room in building.rooms:
                for equip in room.equipment:
                    # 設備を適切なカテゴリに分類
                    for category, keywords in equipment_keywords.items():
                        if any(kw in equip for kw in keywords):
                            requirements[category].append(f'{room.room_name}: {equip}')
                            break

        # 重複を削除
        for category in requirements:
            requirements[category] = list(set(requirements[category]))

        return requirements

    def update_fmt_with_requirements(self, fmt_doc: FMTDocument) -> FMTDocument:
        """FMTドキュメントに要求事項を追加"""
        requirements = self.extract_requirements(fmt_doc)
        fmt_doc.requirements = requirements
        return fmt_doc
