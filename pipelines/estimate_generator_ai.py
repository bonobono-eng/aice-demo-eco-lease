"""
AI自動見積生成エンジン

仕様書から直接、建築設備の専門知識を使って詳細な見積項目を自動生成します。
参照見積書不要で、AIが設計レベルの詳細項目を推定します。
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from loguru import logger
import PyPDF2

from pipelines.schemas import (
    EstimateItem, DisciplineType, FMTDocument, ProjectInfo, FacilityType,
    CostType
)


class AIEstimateGenerator:
    """
    AI自動見積生成器

    仕様書から建物情報を抽出し、建築設備の専門知識を使って
    詳細な見積項目（配管サイズ、数量、材料等）を自動生成します。
    """

    def __init__(self, kb_path: str = "kb/price_kb.json"):
        load_dotenv()
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model_name = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.kb_path = kb_path
        self.price_kb = self._load_price_kb()

    def _load_price_kb(self) -> List[Dict]:
        """価格KBを読み込み"""
        if os.path.exists(self.kb_path):
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        logger.warning(f"Price KB not found: {self.kb_path}")
        return []

    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = 50) -> str:
        """PDFからテキストを抽出"""
        logger.info(f"Extracting text from PDF: {pdf_path}")

        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num in range(min(len(pdf_reader.pages), max_pages)):
                    text += pdf_reader.pages[page_num].extract_text() + "\n"

            logger.info(f"Extracted {len(text)} characters from {min(len(pdf_reader.pages), max_pages)} pages")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def extract_building_info(self, spec_text: str) -> Dict[str, Any]:
        """
        仕様書から建物情報を詳細抽出

        建築設備設計に必要な情報を抽出します：
        - 建物面積、階数、部屋数
        - 用途、設備仕様
        - 工事条件
        """
        logger.info("Extracting detailed building information")

        prompt = f"""あなたは建築設備の専門家です。以下の仕様書から、設備設計に必要な建物情報を詳細に抽出してください。

仕様書:
{spec_text[:20000]}

【抽出する情報】
以下の情報をJSON形式で抽出してください：

```json
{{
  "project_name": "工事名",
  "client_name": "顧客名",
  "location": "工事場所",
  "contract_period": "工期・リース期間",

  "building_info": {{
    "total_floor_area": 2145,  // 延床面積（㎡）
    "floors": 2,  // 階数
    "building_type": "仮設校舎",  // 建物種別
    "num_rooms": 20,  // 部屋数（推定）
    "num_floors_above": 2,  // 地上階数
    "num_floors_below": 0,  // 地下階数
    "structure": "鉄骨造",  // 構造
    "is_temporary": true  // 仮設かどうか
  }},

  "facility_requirements": {{
    "gas": {{
      "required": true,
      "type": "都市ガス",
      "usage": "給湯、厨房機器",
      "num_connection_points": 38  // ガス栓数（推定）
    }},
    "electrical": {{
      "required": true,
      "voltage": "低圧",
      "estimated_capacity_kva": 150  // 推定容量（kVA）
    }},
    "mechanical": {{
      "required": true,
      "hvac_type": "空調設備",
      "plumbing": true
    }}
  }},

  "construction_conditions": {{
    "existing_building": true,  // 既存建物の有無
    "requires_demolition": true,  // 解体工事の要否
    "site_access": "良好",  // 現場アクセス
    "work_restrictions": "授業時間外"  // 作業制限
  }}
}}
```

必ずJSON形式で回答してください。コメント（//）は含めず、純粋なJSON形式で出力してください。"""

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=8000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text

        # JSONを抽出
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            logger.error("No JSON found in response")
            return {}

        json_str = response_text[json_start:json_end]

        # コメントを削除（//から行末まで）
        json_str = re.sub(r'//.*', '', json_str)

        building_info = json.loads(json_str)

        logger.info(f"Extracted building info: {building_info.get('project_name', 'N/A')}")
        return building_info

    def generate_detailed_items_for_gas(
        self,
        building_info: Dict[str, Any]
    ) -> List[EstimateItem]:
        """
        ガス設備の詳細見積項目をAI生成

        建物情報から、配管サイズ・数量・材料を設計レベルで推定します。
        """
        logger.info("Generating detailed gas equipment items")

        # 建物情報を文字列化
        building_summary = json.dumps(building_info, ensure_ascii=False, indent=2)

        prompt = f"""あなたは建築設備（ガス設備）の設計専門家です。以下の建物情報から、都市ガス設備工事の詳細な見積項目を設計してください。

建物情報:
{building_summary}

【設計タスク】
実際の設備設計と同様に、以下の項目を含む詳細な見積を作成してください：

1. **基本工事費**: 図面作成、申請業務、現場管理等
2. **配管工事費**:
   - 各サイズの配管（15A, 20A, 25A, 32A, 50A, 80A）
   - 延長メートル数を建物規模から推定
   - 材質（白ガス管、カラー鋼管、PE管等）を適切に選定
   - 露出結び（配管接続）
3. **ガス栓等材料費**:
   - ガスコンセント（S型露出、W型露出）
   - ネジコック
   - 各サイズ・個数を用途から推定
4. **特別材料費**:
   - 分岐コック
   - ボールスライドジョイント
5. **付帯工事費**:
   - 配管撤去（既存設備がある場合）
   - 配管支持金具
   - 穴補修、埋戻し
   - コンクリート切断・復旧
   - 高所作業車
6. **機器搬続費**:
   - 資機材運搬費
   - 諸経費

【設計の考え方】
- 建物面積から配管総延長を推定（例: 2,145㎡ → 約400-500m）
- 用途（学校）から各部屋のガス栓数を推定
- 配管サイズの割合: 15A(20%), 20A(30%), 25A(20%), 32A(15%), 50A(10%), 80A(5%)
- 仮設建物なので解体費・撤去費を考慮

【出力形式】
JSON配列で、階層構造を持った見積項目を出力してください：

```json
[
  {{
    "item_no": "1",
    "level": 0,
    "name": "都市ガス設備工事",
    "specification": "",
    "quantity": null,
    "unit": "式",
    "unit_price": null,
    "amount": null,
    "cost_type": "一式",
    "remarks": "",
    "confidence": 1.0
  }},
  {{
    "item_no": "",
    "level": 1,
    "name": "基本工事費",
    "specification": "",
    "quantity": 1,
    "unit": "式",
    "unit_price": null,
    "amount": null,
    "cost_type": "施工費",
    "remarks": "図面作成、申請業務、現場管理",
    "confidence": 0.9,
    "estimation_basis": "建物規模から標準的な基本工事費を算定"
  }},
  {{
    "item_no": "",
    "level": 1,
    "name": "配管工事費",
    "specification": "",
    "quantity": null,
    "unit": "",
    "unit_price": null,
    "amount": null,
    "cost_type": "材料費",
    "remarks": "",
    "confidence": 0.85
  }},
  {{
    "item_no": "",
    "level": 2,
    "name": "白ガス管（ネジ接合）",
    "specification": "15A",
    "quantity": 93,
    "unit": "m",
    "unit_price": null,
    "amount": null,
    "cost_type": "材料費",
    "remarks": "",
    "confidence": 0.8,
    "estimation_basis": "建物面積2,145㎡×4%≒86m、教室配置を考慮して93m"
  }},
  ... (34項目程度)
]
```

必ず30項目以上の詳細な見積を生成してください。単価はnullのままで構いません（後でKBから取得します）。"""

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=16000,
            temperature=0.3,  # 少し創造性を持たせる
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text
        logger.debug(f"LLM Response: {response_text[:500]}...")

        # JSONを抽出
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1

        if json_start == -1 or json_end == 0:
            logger.error("No JSON found in response")
            return []

        json_str = response_text[json_start:json_end]
        items_data = json.loads(json_str)

        logger.info(f"Generated {len(items_data)} detailed items for gas equipment")

        # EstimateItemに変換
        estimate_items = []
        for item_data in items_data:
            # cost_typeの変換
            cost_type_str = item_data.get("cost_type", "")
            cost_type = None
            if cost_type_str:
                for ct in CostType:
                    if ct.value == cost_type_str:
                        cost_type = ct
                        break

            estimate_item = EstimateItem(
                item_no=item_data.get("item_no", ""),
                level=item_data.get("level", 0),
                name=item_data.get("name", ""),
                specification=item_data.get("specification", ""),
                quantity=item_data.get("quantity"),
                unit=item_data.get("unit", ""),
                unit_price=item_data.get("unit_price"),
                amount=item_data.get("amount"),
                discipline=DisciplineType.GAS,
                cost_type=cost_type,
                remarks=item_data.get("remarks", ""),
                source_type="ai_generated",
                source_reference=item_data.get("estimation_basis", "AI設計"),
                confidence=item_data.get("confidence", 0.7)
            )

            estimate_items.append(estimate_item)

        return estimate_items

    def _normalize_text(self, text: str) -> str:
        """テキストを正規化（空白・記号を統一）"""
        if not text:
            return ""
        import re
        # 全角→半角
        text = text.replace('（', '(').replace('）', ')').replace('　', ' ')
        # 記号の統一
        text = text.replace('・', '').replace('/', '').replace('-', '')
        # 複数空白を1つに
        text = re.sub(r'\s+', ' ', text)
        return text.strip().lower()

    def _extract_size(self, text: str) -> str:
        """テキストからサイズ情報を抽出（例: 15A, 20mm）"""
        if not text:
            return ""
        import re
        # サイズパターン: 数値 + 単位（A, mm, cm等）
        match = re.search(r'(\d+)\s*([Aａmcm]{1,2})', text, re.IGNORECASE)
        if match:
            return f"{match.group(1)}{match.group(2).upper()}"
        return ""

    def _get_category(self, item_name: str) -> str:
        """項目名からカテゴリを抽出（例: 白ガス管、PE管）"""
        # カテゴリキーワード
        categories = [
            "白ガス管", "カラー鋼管", "PE管", "露出結び",
            "ガスコンセント", "ネジコック", "分岐コック",
            "ボールスライドジョイント", "ガスメーター",
            "配管支持金具", "穴あけ", "埋戻し", "コンクリート",
            "高所作業車", "運搬", "諸経費", "試験", "検査", "撤去"
        ]

        for category in categories:
            if category in item_name:
                return category
        return ""

    def enrich_with_prices(self, estimate_items: List[EstimateItem]) -> List[EstimateItem]:
        """
        KBから単価を取得して項目に付与（改善版）

        Args:
            estimate_items: 単価未設定の見積項目リスト

        Returns:
            単価・金額が設定された見積項目リスト
        """
        logger.info(f"Enriching {len(estimate_items)} items with prices from KB ({len(self.price_kb)} KB items loaded)")

        enriched_items = []

        for item in estimate_items:
            # 親項目（level 0や単価不要項目）はスキップ
            if item.level == 0 or not item.quantity:
                enriched_items.append(item)
                continue

            # テキストを正規化
            item_name_norm = self._normalize_text(item.name)
            item_spec_norm = self._normalize_text(item.specification or "")
            item_size = self._extract_size(item.specification or "")
            item_category = self._get_category(item.name)

            logger.debug(f"Matching: '{item.name}' {item.specification} | discipline={item.discipline.value}")
            logger.debug(f"  Normalized: name='{item_name_norm}', spec='{item_spec_norm}', size={item_size}, category={item_category}")

            # KBから類似項目を検索
            best_match = None
            best_score = 0.0
            category_fallback = None
            category_fallback_score = 0.0
            kb_candidates = 0

            for kb_item in self.price_kb:
                # 工事区分でフィルタ
                if kb_item.get("discipline") != item.discipline.value:
                    continue
                kb_candidates += 1

                kb_desc = kb_item.get("description", "")
                kb_spec = kb_item.get("features", {}).get("specification", "")
                kb_full_text = f"{kb_desc} {kb_spec}"

                # 正規化
                kb_desc_norm = self._normalize_text(kb_desc)
                kb_spec_norm = self._normalize_text(kb_spec)
                kb_full_norm = self._normalize_text(kb_full_text)
                kb_size = self._extract_size(kb_spec)
                kb_category = self._get_category(kb_desc)

                # 詳細な類似度計算
                score = 0.0

                # 1. 項目名の一致（正規化後）
                if item_name_norm == kb_desc_norm:
                    score += 2.0  # 完全一致は高スコア
                elif item_name_norm in kb_desc_norm or kb_desc_norm in item_name_norm:
                    score += 1.5
                elif any(word in kb_desc_norm for word in item_name_norm.split() if len(word) > 1):
                    score += 1.0

                # 2. カテゴリの一致
                if item_category and kb_category and item_category == kb_category:
                    score += 1.0
                    # カテゴリが一致する場合はフォールバック候補
                    if score > category_fallback_score:
                        category_fallback = kb_item
                        category_fallback_score = score

                # 3. 仕様・サイズの一致
                if item_spec_norm and kb_spec_norm:
                    # 完全一致
                    if item_spec_norm == kb_spec_norm:
                        score += 1.5
                    # サイズ一致（例: 15A）
                    elif item_size and kb_size and item_size == kb_size:
                        score += 1.2
                    # 仕様が含まれる
                    elif item_spec_norm in kb_full_norm or kb_spec_norm in item_spec_norm:
                        score += 0.8

                # 4. 単位の一致
                if item.unit == kb_item.get("unit"):
                    score += 0.5
                elif item.unit and kb_item.get("unit"):
                    # m と メートル、式 と 式 等
                    unit_norm_item = self._normalize_text(item.unit)
                    unit_norm_kb = self._normalize_text(kb_item.get("unit", ""))
                    if unit_norm_item == unit_norm_kb:
                        score += 0.5
                    elif unit_norm_item in unit_norm_kb or unit_norm_kb in unit_norm_item:
                        score += 0.3

                if score > best_score:
                    best_score = score
                    best_match = kb_item

            # マッチング成功（閾値を調整）
            logger.debug(f"  KB candidates: {kb_candidates}, best_score={best_score:.2f}")

            matched_item = None
            match_type = ""

            if best_match and best_score >= 1.0:
                # 高品質マッチ（項目名+仕様が一致）
                matched_item = best_match
                match_type = "exact"
                logger.debug(f"✓ Exact match '{item.name}' → '{best_match.get('item_id')}' (score={best_score:.2f})")
            elif best_match and best_score >= 0.5:
                # 中品質マッチ（項目名 or カテゴリが一致）
                matched_item = best_match
                match_type = "partial"
                logger.debug(f"≈ Partial match '{item.name}' → '{best_match.get('item_id')}' (score={best_score:.2f})")
            elif category_fallback and category_fallback_score >= 0.8:
                # カテゴリフォールバック（カテゴリは一致するが仕様が異なる）
                matched_item = category_fallback
                match_type = "category"
                logger.debug(f"↳ Category fallback '{item.name}' → '{category_fallback.get('item_id')}' (score={category_fallback_score:.2f})")
            else:
                logger.warning(f"✗ No match for '{item.name}' {item.specification} (best={best_score:.2f})")

            if matched_item:
                item.unit_price = matched_item.get("unit_price")
                if item.quantity and item.unit_price:
                    item.amount = item.quantity * item.unit_price
                item.price_references = [matched_item.get("item_id")]
                item.source_reference = f"KB:{matched_item.get('item_id')}[{match_type}](score={best_score:.2f}), {item.source_reference}"

            enriched_items.append(item)

        # 親項目の金額を子項目の合計で計算
        enriched_items = self._calculate_parent_amounts(enriched_items)

        matched_count = sum(1 for item in enriched_items if item.unit_price is not None)
        if len(estimate_items) > 0:
            logger.info(f"Price matching: {matched_count}/{len(estimate_items)} items ({matched_count/len(estimate_items)*100:.1f}%)")
        else:
            logger.warning("No items to match prices for")

        return enriched_items

    def _calculate_parent_amounts(self, items: List[EstimateItem]) -> List[EstimateItem]:
        """親項目の金額を子項目の合計で計算"""
        for i, item in enumerate(items):
            if item.level == 0:
                # level 0の金額 = 全level 1の合計
                total = 0
                for j in range(i+1, len(items)):
                    if items[j].level == 0:
                        break
                    if items[j].level == 1:
                        total += items[j].amount or 0
                item.amount = total if total > 0 else None
            elif item.amount is None:
                # 親項目の金額 = 直下の子項目の合計
                total = 0
                for j in range(i+1, len(items)):
                    if items[j].level <= item.level:
                        break
                    if items[j].level == item.level + 1:
                        total += items[j].amount or 0
                item.amount = total if total > 0 else None

        return items

    def generate_estimate(
        self,
        spec_pdf_path: str,
        discipline: DisciplineType
    ) -> FMTDocument:
        """
        仕様書からAIで詳細見積を自動生成

        Args:
            spec_pdf_path: 仕様書PDFのパス
            discipline: 工事区分

        Returns:
            生成されたFMTDocument
        """
        logger.info(f"Starting AI-based estimate generation for {discipline.value}")

        # 1. 仕様書からテキスト抽出
        spec_text = self.extract_text_from_pdf(spec_pdf_path)

        # 2. 建物情報を詳細抽出
        building_info = self.extract_building_info(spec_text)

        # 3. 工事区分別に詳細項目を生成
        if discipline == DisciplineType.GAS:
            estimate_items = self.generate_detailed_items_for_gas(building_info)
        elif discipline == DisciplineType.ELECTRICAL:
            logger.warning(f"電気設備のAI自動生成は開発中です。参照見積書ベースを使用してください。")
            estimate_items = []
        elif discipline == DisciplineType.MECHANICAL:
            logger.warning(f"機械設備のAI自動生成は開発中です。参照見積書ベースを使用してください。")
            estimate_items = []
        else:
            logger.warning(f"{discipline.value} is not yet implemented")
            estimate_items = []

        # 4. KBから単価を取得
        estimate_items = self.enrich_with_prices(estimate_items)

        # 5. FMTDocumentを作成
        # contract_periodが辞書の場合は文字列に変換
        contract_period = building_info.get("contract_period", "")
        if isinstance(contract_period, dict):
            # 辞書の場合、値を結合して文字列化
            if "construction_period" in contract_period:
                contract_period = contract_period["construction_period"]
            elif "rental_period" in contract_period:
                contract_period = contract_period["rental_period"]
            else:
                contract_period = str(contract_period)

        project_info = ProjectInfo(
            project_name=building_info.get("project_name", ""),
            client_name=building_info.get("client_name", ""),
            location=building_info.get("location", ""),
            contract_period=contract_period,
            floor_area_m2=building_info.get("building_info", {}).get("total_floor_area"),
            num_rooms=building_info.get("building_info", {}).get("num_rooms")
        )

        fmt_doc = FMTDocument(
            created_at=datetime.now().isoformat(),
            project_info=project_info,
            facility_type=FacilityType.SCHOOL,
            disciplines=[discipline],
            estimate_items=estimate_items,
            metadata={
                "payment_terms": "本紙記載内容のみ有効とする。",
                "remarks": "法定福利費を含む。",
                "source": "AI自動生成",
                "building_info": building_info.get("building_info", {})
            }
        )

        logger.info(f"Generated FMTDocument with {len(estimate_items)} items")
        return fmt_doc


if __name__ == "__main__":
    # テスト実行
    import sys
    sys.path.insert(0, '.')

    generator = AIEstimateGenerator()

    spec_path = "test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】ord202403101060100130187c1e4d0.pdf"

    if Path(spec_path).exists():
        print("\n" + "="*80)
        print("AI自動見積生成テスト")
        print("="*80)

        # 見積書を生成
        fmt_doc = generator.generate_estimate(
            spec_path,
            DisciplineType.GAS
        )

        print(f"\n【生成結果】")
        print(f"  工事名: {fmt_doc.project_info.project_name}")
        print(f"  項目数: {len(fmt_doc.estimate_items)}")

        # 合計金額を計算
        total = sum(item.amount or 0 for item in fmt_doc.estimate_items if item.level == 0)
        print(f"  合計金額: ¥{total:,.0f}")

        # 単価マッチング率
        with_price = sum(1 for item in fmt_doc.estimate_items if item.unit_price is not None)
        print(f"  単価マッチング率: {with_price}/{len(fmt_doc.estimate_items)} ({with_price/len(fmt_doc.estimate_items)*100:.1f}%)")

        # 階層別統計
        level_counts = {}
        for item in fmt_doc.estimate_items:
            level_counts[item.level] = level_counts.get(item.level, 0) + 1

        print(f"\n【階層別項目数】")
        for level in sorted(level_counts.keys()):
            print(f"  Level {level}: {level_counts[level]}項目")

        # 最初の30項目を表示
        print(f"\n【見積項目（最初の30項目）】")
        for i, item in enumerate(fmt_doc.estimate_items[:30]):
            indent = "  " * item.level
            spec_str = f" {item.specification}" if item.specification else ""
            qty_str = f" {item.quantity}{item.unit}" if item.quantity else ""
            price_str = f" @¥{item.unit_price:,.0f}" if item.unit_price else ""
            amount_str = f" = ¥{item.amount:,.0f}" if item.amount else ""
            conf = f" [信頼度:{item.confidence:.2f}]" if item.confidence else ""
            print(f"{indent}{item.name}{spec_str}{qty_str}{price_str}{amount_str}{conf}")

    else:
        print(f"❌ ファイルが見つかりません: {spec_path}")
