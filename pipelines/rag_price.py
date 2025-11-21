"""RAG Price Search - 過去見積から類似価格を検索"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
from loguru import logger

try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError:
    logger.warning("FAISS or sentence-transformers not installed")

from pipelines.schemas import PriceReference, DisciplineType


class PriceRAG:
    """過去見積価格のRAG検索"""

    def __init__(self, kb_path: str = "./kb/past_estimates", model_name: str = "BAAI/bge-m3"):
        self.kb_path = Path(kb_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)

        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[Any] = None
        self.price_data: List[Dict[str, Any]] = []

        self.index_file = self.kb_path / "price_index.faiss"
        self.metadata_file = self.kb_path / "price_metadata.npy"

    def initialize(self):
        """モデルとインデックスを初期化"""
        logger.info(f"Initializing PriceRAG with model: {self.model_name}")

        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

        # インデックスをロード（存在すれば）
        if self.index_file.exists() and self.metadata_file.exists():
            self.load_index()
        else:
            logger.info("No existing index found. Will create new index when data is added.")

    def add_price_data(self, price_items: List[Dict[str, Any]]):
        """
        過去見積価格データを追加

        Args:
            price_items: 価格データのリスト
                [
                    {
                        'item_name': '照明器具',
                        'specification': 'LED 40W',
                        'unit_price': 15000,
                        'unit': '台',
                        'project_name': '〇〇学校',
                        'date': '2024-01-15',
                        'discipline': '電気'
                    },
                    ...
                ]
        """
        logger.info(f"Adding {len(price_items)} price items to knowledge base")

        self.price_data.extend(price_items)

        # テキストを生成
        texts = []
        for item in price_items:
            # アイテム名と仕様を組み合わせてテキスト化
            text = f"{item.get('item_name', '')} {item.get('specification', '')}"
            texts.append(text)

        # エンベディングを生成
        if self.model is None:
            self.initialize()

        embeddings = self.model.encode(texts, convert_to_numpy=True)

        # FAISSインデックスを作成または更新
        if self.index is None:
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner Product (cosine similarity)

        # L2正規化（コサイン類似度のため）
        faiss.normalize_L2(embeddings)

        # インデックスに追加
        self.index.add(embeddings)

        logger.info(f"Total items in index: {self.index.ntotal}")

    def search(self, query: str, top_k: int = 5,
               discipline: Optional[DisciplineType] = None) -> List[PriceReference]:
        """
        類似価格を検索

        Args:
            query: 検索クエリ（例: "LED照明器具 40W"）
            top_k: 取得する件数
            discipline: 工事区分でフィルタ（オプション）

        Returns:
            PriceReferenceのリスト
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Index is empty. Returning empty results.")
            return []

        # クエリをエンベディング
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)

        # 検索
        scores, indices = self.index.search(query_embedding, min(top_k * 2, self.index.ntotal))

        # 結果を作成
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.price_data):
                continue

            price_item = self.price_data[idx]

            # 工事区分でフィルタ
            if discipline and price_item.get('discipline') != discipline.value:
                continue

            # スコアが低すぎるものは除外
            if score < 0.3:
                continue

            try:
                from datetime import datetime
                date_obj = datetime.fromisoformat(price_item.get('date', '2024-01-01')).date()
            except:
                from datetime import date as date_type
                date_obj = date_type(2024, 1, 1)

            ref = PriceReference(
                item_name=price_item.get('item_name', ''),
                specification=price_item.get('specification'),
                unit_price=price_item.get('unit_price', 0.0),
                unit=price_item.get('unit', ''),
                project_name=price_item.get('project_name', ''),
                reference_date=date_obj,
                similarity_score=float(score),
                source=price_item.get('source', 'KB')
            )

            results.append(ref)

            if len(results) >= top_k:
                break

        logger.info(f"Found {len(results)} price references for query: {query}")

        return results

    def save_index(self):
        """インデックスとメタデータを保存"""
        if self.index is not None and self.index.ntotal > 0:
            faiss.write_index(self.index, str(self.index_file))
            np.save(str(self.metadata_file), self.price_data)
            logger.info(f"Index saved to {self.index_file}")

    def load_index(self):
        """インデックスとメタデータをロード"""
        try:
            self.index = faiss.read_index(str(self.index_file))
            self.price_data = np.load(str(self.metadata_file), allow_pickle=True).tolist()
            logger.info(f"Loaded index with {self.index.ntotal} items")
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            self.index = None
            self.price_data = []

    def build_from_excel(self, excel_path: str):
        """
        Excelファイルから過去見積データを読み込み

        Args:
            excel_path: 過去見積のExcelファイルパス
        """
        import pandas as pd

        logger.info(f"Building knowledge base from Excel: {excel_path}")

        df = pd.read_excel(excel_path)

        # 必要なカラム: 項目名, 仕様, 単価, 単位, 案件名, 日付, 工事区分
        required_cols = ['項目名', '仕様', '単価', '単位', '案件名', '日付', '工事区分']

        # カラム名を正規化
        col_mapping = {}
        for col in df.columns:
            if '項目' in col or '名称' in col:
                col_mapping[col] = '項目名'
            elif '仕様' in col or 'spec' in col.lower():
                col_mapping[col] = '仕様'
            elif '単価' in col or 'price' in col.lower():
                col_mapping[col] = '単価'
            elif '単位' in col or 'unit' in col.lower():
                col_mapping[col] = '単位'
            elif '案件' in col or 'project' in col.lower():
                col_mapping[col] = '案件名'
            elif '日付' in col or 'date' in col.lower():
                col_mapping[col] = '日付'
            elif '工事' in col or 'discipline' in col.lower():
                col_mapping[col] = '工事区分'

        df = df.rename(columns=col_mapping)

        # データを変換
        price_items = []
        for _, row in df.iterrows():
            item = {
                'item_name': str(row.get('項目名', '')),
                'specification': str(row.get('仕様', '')),
                'unit_price': float(row.get('単価', 0)),
                'unit': str(row.get('単位', '')),
                'project_name': str(row.get('案件名', '')),
                'date': str(row.get('日付', '2024-01-01')),
                'discipline': str(row.get('工事区分', '')),
                'source': excel_path
            }
            price_items.append(item)

        # KBに追加
        self.add_price_data(price_items)
        self.save_index()

        logger.info(f"Added {len(price_items)} items from Excel")
