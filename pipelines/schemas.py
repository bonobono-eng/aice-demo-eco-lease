"""Data schemas for FMT (社内統一フォーマット) standardized format."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date
from enum import Enum


class DisciplineType(str, Enum):
    """工事区分"""
    ELECTRICAL = "電気"
    MECHANICAL = "機械"
    HVAC = "空調"
    PLUMBING = "衛生"
    GAS = "ガス"
    FIRE_PROTECTION = "消防"
    CONSTRUCTION = "建築"


class FacilityType(str, Enum):
    """施設区分"""
    SCHOOL = "学校"
    OFFICE = "オフィス"
    HOSPITAL = "病院"
    FACTORY = "工場"
    COMMERCIAL = "商業施設"
    OTHER = "その他"


class RoomSpec(BaseModel):
    """部屋仕様"""
    room_name: str = Field(description="部屋名")
    room_number: Optional[str] = Field(default=None, description="部屋番号")
    area: Optional[float] = Field(default=None, description="面積(㎡)")
    floor: Optional[str] = Field(default=None, description="階数")
    equipment: List[str] = Field(default_factory=list, description="設備リスト")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="仕様詳細")


class BuildingSpec(BaseModel):
    """建物仕様"""
    building_name: str = Field(description="建物名称")
    building_type: str = Field(description="建物種別")
    structure: Optional[str] = Field(default=None, description="構造")
    total_area: Optional[float] = Field(default=None, description="延床面積(㎡)")
    floors: Optional[int] = Field(default=None, description="階数")
    height: Optional[float] = Field(default=None, description="高さ(m)")
    rooms: List[RoomSpec] = Field(default_factory=list, description="部屋リスト")


class ProjectInfo(BaseModel):
    """案件情報"""
    project_id: Optional[str] = Field(default=None, description="案件ID")
    project_name: str = Field(description="案件名")
    client_name: Optional[str] = Field(default=None, description="顧客名")
    location: Optional[str] = Field(default=None, description="所在地")
    bid_date: Optional[date] = Field(default=None, description="入札日")
    delivery_date: Optional[date] = Field(default=None, description="納期")
    contract_period: Optional[str] = Field(default=None, description="契約期間")


class EstimateItem(BaseModel):
    """見積明細項目"""
    item_no: str = Field(description="項番")
    name: str = Field(description="名称")
    specification: Optional[str] = Field(default=None, description="仕様")
    quantity: Optional[float] = Field(default=None, description="数量")
    unit: Optional[str] = Field(default=None, description="単位")
    unit_price: Optional[float] = Field(default=None, description="単価")
    amount: Optional[float] = Field(default=None, description="金額")
    remarks: Optional[str] = Field(default=None, description="摘要")
    parent_item_no: Optional[str] = Field(default=None, description="親項番")
    level: int = Field(default=0, description="階層レベル")
    discipline: Optional[DisciplineType] = Field(default=None, description="工事区分")


class LegalReference(BaseModel):
    """法令参照"""
    law_name: str = Field(description="法令名")
    article: Optional[str] = Field(default=None, description="条項")
    description: str = Field(description="内容")
    relevance_score: float = Field(default=0.0, description="関連度スコア")
    source_url: Optional[str] = Field(default=None, description="参照URL")


class QAItem(BaseModel):
    """質問事項"""
    question_no: str = Field(description="質問番号")
    category: str = Field(description="カテゴリ")
    question: str = Field(description="質問内容")
    background: Optional[str] = Field(default=None, description="背景・理由")
    priority: str = Field(default="中", description="優先度(高/中/低)")


class FMTDocument(BaseModel):
    """FMT統一フォーマット - メインドキュメント"""

    # メタデータ
    fmt_version: str = Field(default="1.0", description="FMTバージョン")
    created_at: str = Field(description="作成日時")

    # 入札情報
    project_info: ProjectInfo = Field(description="案件情報")

    # 施設情報
    facility_type: FacilityType = Field(description="施設区分")
    building_specs: List[BuildingSpec] = Field(default_factory=list, description="建物仕様")

    # 工事区分
    disciplines: List[DisciplineType] = Field(default_factory=list, description="対象工事区分")

    # 抽出された要求事項
    requirements: Dict[str, Any] = Field(default_factory=dict, description="要求事項")

    # 見積項目
    estimate_items: List[EstimateItem] = Field(default_factory=list, description="見積明細")

    # 法令参照
    legal_references: List[LegalReference] = Field(default_factory=list, description="法令参照")

    # 質問事項
    qa_items: List[QAItem] = Field(default_factory=list, description="質問事項")

    # その他
    raw_text: Optional[str] = Field(default=None, description="抽出された生テキスト")
    extracted_tables: List[Dict[str, Any]] = Field(default_factory=list, description="抽出されたテーブル")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="その他メタデータ")


class PriceReference(BaseModel):
    """過去価格参照"""
    item_name: str = Field(description="項目名")
    specification: Optional[str] = Field(default=None, description="仕様")
    unit_price: float = Field(description="単価")
    unit: str = Field(description="単位")
    project_name: str = Field(description="案件名")
    reference_date: date = Field(description="実施日")
    similarity_score: float = Field(default=0.0, description="類似度スコア")
    source: str = Field(description="出典")
