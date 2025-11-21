"""Streamlit UI for Ecolease PoC - 入札見積自動化システム"""

import streamlit as st
from pathlib import Path
import tempfile
from datetime import datetime
from loguru import logger

from pipelines.ingest import DocumentIngestor
from pipelines.normalize import FMTNormalizer
from pipelines.classify import Classifier
from pipelines.rag_price import PriceRAG
from pipelines.estimate import EstimateGenerator
from pipelines.export import EstimateExporter


# ページ設定
st.set_page_config(
    page_title="Ecolease 入札見積自動化システム",
    page_icon="📄",
    layout="wide"
)


def init_session_state():
    """セッション状態を初期化"""
    if 'fmt_doc' not in st.session_state:
        st.session_state.fmt_doc = None
    if 'processing_time' not in st.session_state:
        st.session_state.processing_time = None


def main():
    init_session_state()

    st.title("📄 Ecolease 入札見積自動化システム PoC")
    st.caption("Powered by Claude Sonnet 4.5")
    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")

        use_llm = st.checkbox("LLMを使用", value=True,
                             help="Azure OpenAI GPT-4oを使用して見積項目を生成")

        use_rag = st.checkbox("過去見積RAGを使用", value=True,
                             help="過去見積から類似価格を検索")

        st.markdown("---")

        st.header("📊 システム情報")
        st.info("""
        **使用AI**
        - Claude Sonnet 4.5 (最新)

        **目標**
        - 処理時間: 5分以内
        - 完成度: 70%以上

        **対応工事区分**
        - 電気・機械・空調
        - 衛生・ガス・消防
        """)

    # メインコンテンツ
    tab1, tab2, tab3 = st.tabs(["📤 ファイルアップロード", "📋 見積生成", "📥 出力"])

    with tab1:
        st.header("入札書類のアップロード")

        uploaded_file = st.file_uploader(
            "入札仕様書PDFをアップロード",
            type=['pdf', 'docx', 'xlsx'],
            help="入札仕様書のPDFファイルを選択してください"
        )

        if uploaded_file:
            st.success(f"✅ ファイル: {uploaded_file.name} ({uploaded_file.size:,} bytes)")

            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🚀 処理開始", type="primary"):
                    process_document(uploaded_file, use_llm, use_rag)

    with tab2:
        st.header("見積内容の確認・編集")

        if st.session_state.fmt_doc:
            fmt_doc = st.session_state.fmt_doc

            # 案件情報
            st.subheader("📌 案件情報")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("案件名", fmt_doc.project_info.project_name)
            with col2:
                st.metric("施設区分", fmt_doc.facility_type.value)
            with col3:
                st.metric("工事区分", f"{len(fmt_doc.disciplines)}種類")

            st.markdown(f"**対象工事**: {', '.join([d.value for d in fmt_doc.disciplines])}")

            # 建物仕様
            if fmt_doc.building_specs:
                st.subheader("🏢 建物仕様")
                for building in fmt_doc.building_specs:
                    with st.expander(f"📐 {building.building_name}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**延床面積**: {building.total_area}㎡" if building.total_area else "")
                        with col2:
                            st.write(f"**構造**: {building.structure}" if building.structure else "")
                        with col3:
                            st.write(f"**部屋数**: {len(building.rooms)}")

                        if building.rooms:
                            st.write("**部屋一覧**:")
                            room_data = []
                            for room in building.rooms[:10]:  # 最大10件表示
                                room_data.append({
                                    "部屋名": room.room_name,
                                    "面積": f"{room.area}㎡" if room.area else "",
                                    "設備数": len(room.equipment)
                                })
                            st.dataframe(room_data, use_container_width=True)

            # 見積明細
            st.subheader("💰 見積明細")

            if fmt_doc.estimate_items:
                # 合計金額
                total = sum(item.amount or 0 for item in fmt_doc.estimate_items if item.level == 0)
                st.metric("**合計金額（税別）**", f"¥{total:,.0f}")

                # テーブル表示
                estimate_data = []
                for item in fmt_doc.estimate_items:
                    indent = "　" * item.level
                    estimate_data.append({
                        "No": item.item_no,
                        "名称": f"{indent}{item.name}",
                        "仕様": item.specification or "",
                        "数量": item.quantity if item.quantity else "",
                        "単位": item.unit or "",
                        "単価": f"¥{item.unit_price:,.0f}" if item.unit_price else "",
                        "金額": f"¥{item.amount:,.0f}" if item.amount else "",
                        "摘要": item.remarks or ""
                    })

                st.dataframe(estimate_data, use_container_width=True, height=400)

                # 処理時間表示
                if st.session_state.processing_time:
                    st.info(f"⏱️ 処理時間: {st.session_state.processing_time:.2f}秒")

            else:
                st.warning("見積明細が生成されていません")
        else:
            st.info("👈 左のタブから入札書類をアップロードして処理を開始してください")

    with tab3:
        st.header("見積書の出力")

        if st.session_state.fmt_doc:
            st.write("生成された見積書を以下の形式でダウンロードできます")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("📊 Excelファイルを出力", type="primary"):
                    export_excel()

            with col2:
                if st.button("📄 PDFファイルを出力"):
                    export_pdf()

            # FMTドキュメントをJSON出力
            with st.expander("🔧 FMTドキュメント（JSON）"):
                st.json(st.session_state.fmt_doc.model_dump(mode='json'))

        else:
            st.info("見積を生成してから出力してください")


def process_document(uploaded_file, use_llm: bool, use_rag: bool):
    """ドキュメントを処理して見積を生成"""

    start_time = datetime.now()

    with st.spinner("処理中..."):
        try:
            # 一時ファイルに保存
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name

            # ステップ1: ドキュメント取り込み
            st.info("📥 ステップ1: ドキュメントを解析中...")
            ingestor = DocumentIngestor()
            ingested_data = ingestor.ingest(tmp_path)

            # 案件情報と建物仕様を抽出
            project_info = ingestor.extract_project_info(ingested_data)
            building_specs_raw = ingestor.extract_building_specs(ingested_data)

            # 建物仕様を整形
            if building_specs_raw:
                building_specs = building_specs_raw
            else:
                # デフォルトの建物仕様を作成
                building_specs = [{
                    'building_name': project_info.get('project_name', '建物'),
                    'building_type': '不明',
                    'rooms': building_specs_raw
                }]

            st.success(f"✅ {ingested_data.get('metadata', {}).get('page_count', 0)}ページ、"
                      f"{len(ingested_data.get('tables', []))}テーブルを抽出")

            # ステップ2: FMT正規化
            st.info("🔄 ステップ2: データを正規化中...")
            normalizer = FMTNormalizer()
            fmt_doc = normalizer.normalize(ingested_data, project_info, building_specs)
            fmt_doc = normalizer.update_fmt_with_requirements(fmt_doc)

            st.success(f"✅ FMTフォーマットに変換")

            # ステップ3: 分類
            st.info("🏷️ ステップ3: 工事区分を分類中...")
            classifier = Classifier()
            fmt_doc = classifier.classify(fmt_doc)

            st.success(f"✅ {len(fmt_doc.disciplines)}種類の工事区分を検出: "
                      f"{', '.join([d.value for d in fmt_doc.disciplines])}")

            # ステップ4: RAG初期化（オプション）
            price_rag = None
            if use_rag:
                st.info("🔍 ステップ4: 過去見積データベースを準備中...")
                price_rag = PriceRAG()
                price_rag.initialize()

                # サンプルデータを追加（実際にはExcelから読み込み）
                # price_rag.build_from_excel("path/to/past_estimates.xlsx")

                st.success("✅ RAGデータベース準備完了")

            # ステップ5: 見積生成
            st.info("💰 ステップ5: 見積を生成中...")
            generator = EstimateGenerator(use_llm=use_llm)
            if price_rag:
                generator.set_price_rag(price_rag)

            fmt_doc = generator.generate(fmt_doc)

            total = sum(item.amount or 0 for item in fmt_doc.estimate_items if item.level == 0)
            st.success(f"✅ {len(fmt_doc.estimate_items)}項目の見積を生成 (合計: ¥{total:,.0f})")

            # セッションに保存
            st.session_state.fmt_doc = fmt_doc

            # 処理時間を記録
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            st.session_state.processing_time = processing_time

            # 完了メッセージ
            st.success(f"🎉 処理完了！ (処理時間: {processing_time:.2f}秒)")

            # 目標達成チェック
            if processing_time <= 300:  # 5分
                st.balloons()
                st.success("✅ 目標処理時間（5分以内）を達成！")
            else:
                st.warning(f"⚠️ 処理時間が目標（5分）を超えました: {processing_time:.2f}秒")

        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")
            logger.exception("Processing error")


def export_excel():
    """Excelファイルを出力"""

    with st.spinner("Excelファイルを生成中..."):
        try:
            exporter = EstimateExporter()
            output_path = exporter.export_to_excel(st.session_state.fmt_doc)

            st.success(f"✅ Excelファイルを生成しました: {output_path}")

            # ダウンロードボタン
            with open(output_path, 'rb') as f:
                st.download_button(
                    label="📥 Excelファイルをダウンロード",
                    data=f,
                    file_name=Path(output_path).name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"❌ Excel出力エラー: {str(e)}")
            logger.exception("Export error")


def export_pdf():
    """PDFファイルを出力"""

    with st.spinner("PDFファイルを生成中..."):
        try:
            exporter = EstimateExporter()
            output_path = exporter.export_to_pdf(st.session_state.fmt_doc)

            st.success(f"✅ PDFファイルを生成しました: {output_path}")

            # ダウンロードボタン
            with open(output_path, 'rb') as f:
                st.download_button(
                    label="📥 PDFファイルをダウンロード",
                    data=f,
                    file_name=Path(output_path).name,
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"❌ PDF出力エラー: {str(e)}")
            logger.exception("PDF export error")


if __name__ == "__main__":
    main()
