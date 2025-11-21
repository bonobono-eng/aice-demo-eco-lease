"""PDFレイアウトエディタ - Streamlitを使ったインタラクティブなレイアウト調整ツール"""

import streamlit as st
from pipelines.schemas import FMTDocument, ProjectInfo, EstimateItem, FacilityType, DisciplineType
from pipelines.pdf_generator import EcoleasePDFGenerator
from datetime import datetime
import tempfile
import base64

st.set_page_config(page_title="PDFレイアウトエディタ", layout="wide")

st.title("📄 御見積書 レイアウトエディタ")

# サンプルデータ
@st.cache_data
def get_sample_data():
    return FMTDocument(
        created_at=datetime.now().isoformat(),
        project_info=ProjectInfo(
            project_name="都立山崎高校仮設校舎　都市ガス設備工事",
            client_name="株式会社システムハウスR&C東京支店",
            location="東京都町田市山崎町1453番地1",
            contract_period="25ヶ月（2026.8.1～2028.8.31）見積有効期間6ヶ月"
        ),
        facility_type=FacilityType.SCHOOL,
        disciplines=[DisciplineType.GAS],
        estimate_items=[
            EstimateItem(item_no="1", level=0, name="都市ガス設備工事", amount=11275000),
            EstimateItem(item_no="2", level=0, name="解体費", amount=1500000),
            EstimateItem(item_no="3", level=0, name="法定福利費", amount=657263),
        ],
        metadata={"quote_no": "0976589-00"}
    )

# サイドバーでレイアウト設定
st.sidebar.header("⚙️ レイアウト設定")

st.sidebar.subheader("📐 外枠とマージン")
outer_margin = st.sidebar.slider("外側マージン (mm)", 5.0, 30.0, 12.0, 0.5)
inner_margin = st.sidebar.slider("内側マージン (mm)", 0.0, 10.0, 3.0, 0.5)
outer_line_width = st.sidebar.slider("外枠線の太さ", 0.1, 8.0, 2.5, 0.1)
inner_line_width = st.sidebar.slider("内枠線の太さ", 0.1, 5.0, 0.8, 0.1)
content_padding_left = st.sidebar.slider("コンテンツ左padding (mm)", 0.0, 20.0, 8.0, 0.5)
content_padding_right = st.sidebar.slider("コンテンツ右padding (mm)", 0.0, 20.0, 8.0, 0.5)
content_padding_top = st.sidebar.slider("コンテンツ上padding (mm)", 0.0, 20.0, 8.0, 0.5)

st.sidebar.subheader("📋 見積No・日付")
header_font_size = st.sidebar.slider("見積No・日付の文字サイズ (pt)", 6.0, 16.0, 9.0, 0.5)
header_font_weight = st.sidebar.slider("見積No・日付の文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
header_offset_y = st.sidebar.slider("見積No・日付の垂直位置 (mm)", 0.0, 20.0, 0.0, 0.5)

st.sidebar.subheader("📝 タイトル")
title_font_size = st.sidebar.slider("タイトル文字サイズ (pt)", 16.0, 60.0, 36.0, 1.0)
title_font_weight = st.sidebar.slider("タイトルの文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
title_offset_y = st.sidebar.slider("タイトル位置（上からのオフセット） (mm)", 10.0, 50.0, 24.0, 0.5)
title_letter_spacing = st.sidebar.slider("タイトル文字間隔 (mm)", 0.0, 10.0, 0.0, 0.5)

st.sidebar.subheader("👤 宛先")
client_font_size = st.sidebar.slider("宛先の文字サイズ (pt)", 8.0, 20.0, 13.0, 0.5)
client_font_weight = st.sidebar.slider("宛先の文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
client_offset_y = st.sidebar.slider("宛先位置（上からのオフセット） (mm)", 25.0, 65.0, 42.0, 0.5)
client_underline_offset = st.sidebar.slider("宛先下線のオフセット (mm)", 0.0, 5.0, 2.5, 0.1)

st.sidebar.subheader("💰 金額")
amount_label_font_size = st.sidebar.slider("「御見積金額」ラベルのサイズ (pt)", 8.0, 20.0, 12.0, 0.5)
amount_label_font_weight = st.sidebar.slider("「御見積金額」ラベルの文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
amount_font_size = st.sidebar.slider("金額の文字サイズ (pt)", 14.0, 48.0, 28.0, 1.0)
amount_font_weight = st.sidebar.slider("金額の文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
amount_offset_x = st.sidebar.slider("金額の横オフセット (mm)", 15.0, 50.0, 32.0, 0.5)
amount_offset_y = st.sidebar.slider("金額セクション位置 (mm)", 10.0, 30.0, 18.0, 0.5)
note_font_size = st.sidebar.slider("注釈の文字サイズ (pt)", 6.0, 12.0, 8.0, 0.5)
note_font_weight = st.sidebar.slider("注釈の文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
note_offset_y = st.sidebar.slider("注釈のオフセット (mm)", 4.0, 12.0, 7.0, 0.5)

st.sidebar.subheader("📄 上記の通り〜")
above_text_font_size = st.sidebar.slider("「上記の通り〜」の文字サイズ (pt)", 7.0, 14.0, 9.0, 0.5)
above_text_font_weight = st.sidebar.slider("「上記の通り〜」の文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
above_text_offset_y = st.sidebar.slider("「上記の通り〜」の位置 (mm)", 15.0, 30.0, 20.0, 0.5)

st.sidebar.subheader("🔨 工事情報")
work_info_font_size = st.sidebar.slider("工事情報の文字サイズ (pt)", 6.0, 16.0, 9.0, 0.5)
work_info_font_weight = st.sidebar.slider("工事情報の文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
work_info_label_width = st.sidebar.slider("ラベル幅 (mm)", 15.0, 45.0, 25.0, 0.5)
work_info_line_spacing = st.sidebar.slider("行間隔 (mm)", 3.0, 15.0, 7.0, 0.5)
work_info_offset_y = st.sidebar.slider("工事情報セクション位置 (mm)", 8.0, 20.0, 12.0, 0.5)

st.sidebar.subheader("✅ 検印欄")
stamp_width = st.sidebar.slider("検印欄の幅 (mm)", 30.0, 80.0, 50.0, 1.0)
stamp_height = st.sidebar.slider("検印欄の高さ (mm)", 12.0, 35.0, 18.0, 1.0)
stamp_offset_y = st.sidebar.slider("検印欄位置（上からのオフセット） (mm)", 35.0, 75.0, 52.0, 0.5)
stamp_label_font_size = st.sidebar.slider("検印欄ラベルのサイズ (pt)", 5.0, 12.0, 7.0, 0.5)
stamp_label_font_weight = st.sidebar.slider("検印欄ラベルの文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
stamp_label_offset_y = st.sidebar.slider("検印欄ラベル位置 (mm)", 2.0, 8.0, 4.0, 0.5)

st.sidebar.subheader("🏢 会社情報")
company_name_font_size = st.sidebar.slider("会社名の文字サイズ (pt)", 8.0, 18.0, 11.0, 0.5)
company_name_font_weight = st.sidebar.slider("会社名の文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
company_president_font_size = st.sidebar.slider("代表取締役の文字サイズ (pt)", 6.0, 14.0, 8.0, 0.5)
company_president_font_weight = st.sidebar.slider("代表取締役の文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
company_address_font_size = st.sidebar.slider("住所の文字サイズ (pt)", 5.0, 12.0, 7.0, 0.5)
company_address_font_weight = st.sidebar.slider("住所の文字の太さ (-2: extra light, 0: 通常, 2: 太字)", -2.0, 2.0, -1.5, 0.1)
company_offset_y = st.sidebar.slider("会社情報位置（下からのオフセット） (mm)", 20.0, 55.0, 35.0, 0.5)
company_line_spacing = st.sidebar.slider("会社情報行間隔 (mm)", 2.0, 8.0, 4.0, 0.5)

# レイアウト設定をPDF生成に反映するカスタムクラス
class CustomEcoleasePDFGenerator(EcoleasePDFGenerator):
    def __init__(self, layout_params):
        super().__init__()
        self.layout = layout_params

    def _draw_text_with_weight(self, c, x, y, text, weight, align='left', width=None):
        """文字の太さを考慮してテキストを描画

        Args:
            c: Canvas オブジェクト
            x, y: 描画位置
            text: 描画するテキスト
            weight: 文字の太さ (-2.0: extra light, 0.0: 通常, 2.0: 太字)
            align: 'left', 'center', 'right'
            width: centerやrightの場合に必要な幅
        """
        if weight < 0:
            # 細字効果（透明度を下げて細く見せる）
            opacity = max(0.4, 1.0 + (weight * 0.2))  # -2.0なら0.6, -1.5なら0.7
            c.setFillAlpha(opacity)
            if align == 'center':
                c.drawCentredString(x, y, text)
            elif align == 'right':
                c.drawRightString(x, y, text)
            else:
                c.drawString(x, y, text)
            c.setFillAlpha(1.0)  # 透明度を戻す
        elif weight == 0:
            # 太さ0の場合は通常描画
            if align == 'center':
                c.drawCentredString(x, y, text)
            elif align == 'right':
                c.drawRightString(x, y, text)
            else:
                c.drawString(x, y, text)
        else:
            # 太字効果のため、微妙にずらして複数回描画
            offsets = [
                (0, 0),
                (weight * 0.3, 0),
                (0, weight * 0.3),
                (weight * 0.3, weight * 0.3),
            ]
            for dx, dy in offsets:
                if align == 'center':
                    c.drawCentredString(x + dx, y + dy, text)
                elif align == 'right':
                    c.drawRightString(x + dx, y + dy, text)
                else:
                    c.drawString(x + dx, y + dy, text)

    def _create_quotation_page(self, c, fmt_doc):
        """カスタマイズ可能な御見積書ページ"""
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm

        width, height = landscape(A4)

        # 二重線の大外枠（カスタマイズ可能）
        outer_margin = self.layout['outer_margin']*mm
        inner_margin = self.layout['inner_margin']*mm
        c.setLineWidth(self.layout['outer_line_width'])
        c.rect(outer_margin, outer_margin, width - 2*outer_margin, height - 2*outer_margin, stroke=1, fill=0)
        c.setLineWidth(self.layout['inner_line_width'])
        c.rect(outer_margin + inner_margin, outer_margin + inner_margin,
               width - 2*outer_margin - 2*inner_margin, height - 2*outer_margin - 2*inner_margin, stroke=1, fill=0)

        # コンテンツエリア（カスタマイズ可能なpadding）
        content_left = outer_margin + inner_margin + self.layout['content_padding_left']*mm
        content_right = width - outer_margin - inner_margin - self.layout['content_padding_right']*mm
        content_top = height - outer_margin - inner_margin - self.layout['content_padding_top']*mm

        # 見積No（左上）
        c.setFont(self.font_name, self.layout['header_font_size'])
        quote_no = fmt_doc.metadata.get('quote_no', 'XXXXXXX-00')
        header_y = content_top - self.layout['header_offset_y']*mm
        self._draw_text_with_weight(c, content_left, header_y, f"見積No　{quote_no}",
                                     self.layout['header_font_weight'], align='left')

        # 日付（右上）
        c.setFont(self.font_name, self.layout['header_font_size'])
        self._draw_text_with_weight(c, content_right, header_y,
                                     datetime.now().strftime("%Y年　%m月　%d日"),
                                     self.layout['header_font_weight'], align='right')

        # タイトル
        c.setFont(self.font_name, self.layout['title_font_size'])
        title_y = content_top - self.layout['title_offset_y']*mm
        self._draw_text_with_weight(c, width / 2, title_y, "御　見　積　書",
                                     self.layout['title_font_weight'], align='center')

        # 宛先
        y = content_top - self.layout['client_offset_y']*mm
        c.setFont(self.font_name, self.layout['client_font_size'])
        client_name = fmt_doc.project_info.client_name or ""
        client_text = f"{client_name}　御中"
        self._draw_text_with_weight(c, content_left, y, client_text,
                                     self.layout['client_font_weight'], align='left')

        # 宛先の下線
        text_width = c.stringWidth(client_text, self.font_name, self.layout['client_font_size'])
        underline_y = y - self.layout['client_underline_offset']*mm
        c.line(content_left, underline_y, content_left + text_width, underline_y)

        # 御見積金額
        y -= self.layout['amount_offset_y']*mm
        total_amount = sum(item.amount or 0 for item in fmt_doc.estimate_items if item.level == 0)
        c.setFont(self.font_name, self.layout['amount_label_font_size'])
        self._draw_text_with_weight(c, content_left, y, "御見積金額",
                                     self.layout['amount_label_font_weight'], align='left')

        # 金額を大きく表示
        c.setFont(self.font_name, self.layout['amount_font_size'])
        amount_text = f"￥{int(total_amount):,}*"
        amount_x = content_left + self.layout['amount_offset_x']*mm
        self._draw_text_with_weight(c, amount_x, y, amount_text,
                                     self.layout['amount_font_weight'], align='left')

        # 金額の下線
        amount_width = c.stringWidth(amount_text, self.font_name, self.layout['amount_font_size'])
        underline_y = y - 2.5*mm
        c.line(amount_x, underline_y, amount_x + amount_width, underline_y)

        # NET金額注釈（金額の下線の下に配置）
        c.setFont(self.font_name, self.layout['note_font_size'])
        note_y = underline_y - self.layout['note_offset_y']*mm
        self._draw_text_with_weight(c, amount_x, note_y,
                                     "上記NET金額の為値引き不可となります",
                                     self.layout['note_font_weight'], align='left')

        # 「上記の通り御見積申し上げます。」
        y -= self.layout['above_text_offset_y']*mm
        c.setFont(self.font_name, self.layout['above_text_font_size'])
        self._draw_text_with_weight(c, content_left, y, "上記の通り御見積申し上げます。",
                                     self.layout['above_text_font_weight'], align='left')

        # 工事情報
        y -= self.layout['work_info_offset_y']*mm
        c.setFont(self.font_name, self.layout['work_info_font_size'])
        label_width = self.layout['work_info_label_width']*mm
        line_spacing = self.layout['work_info_line_spacing']*mm

        self._draw_text_with_weight(c, content_left, y, "工　事　名",
                                     self.layout['work_info_font_weight'], align='left')
        self._draw_text_with_weight(c, content_left + label_width, y, fmt_doc.project_info.project_name,
                                     self.layout['work_info_font_weight'], align='left')

        y -= line_spacing
        self._draw_text_with_weight(c, content_left, y, "工事場所",
                                     self.layout['work_info_font_weight'], align='left')
        self._draw_text_with_weight(c, content_left + label_width, y, fmt_doc.project_info.location or "",
                                     self.layout['work_info_font_weight'], align='left')

        y -= line_spacing
        self._draw_text_with_weight(c, content_left, y, "リース期間",
                                     self.layout['work_info_font_weight'], align='left')
        self._draw_text_with_weight(c, content_left + label_width, y, fmt_doc.project_info.contract_period or "",
                                     self.layout['work_info_font_weight'], align='left')

        y -= line_spacing
        self._draw_text_with_weight(c, content_left, y, "決済条件",
                                     self.layout['work_info_font_weight'], align='left')
        self._draw_text_with_weight(c, content_left + label_width, y, "本紙記載内容のみ有効とする。",
                                     self.layout['work_info_font_weight'], align='left')

        y -= line_spacing
        self._draw_text_with_weight(c, content_left, y, "備　　　考",
                                     self.layout['work_info_font_weight'], align='left')
        self._draw_text_with_weight(c, content_left + label_width, y, "法定福利費を含む。",
                                     self.layout['work_info_font_weight'], align='left')

        # 会社情報（左寄せ）
        company_y = outer_margin + inner_margin + self.layout['company_offset_y']*mm
        company_spacing = self.layout['company_line_spacing']*mm
        company_x = content_right - self.layout['stamp_width']*mm  # 検印欄の左端に合わせる

        c.setFont(self.font_name, self.layout['company_name_font_size'])
        self._draw_text_with_weight(c, company_x, company_y, "株式会社　エコリース",
                                     self.layout['company_name_font_weight'], align='left')
        company_y -= company_spacing

        c.setFont(self.font_name, self.layout['company_president_font_size'])
        self._draw_text_with_weight(c, company_x, company_y, "代表取締役　　赤澤　健一",
                                     self.layout['company_president_font_weight'], align='left')
        company_y -= company_spacing

        c.setFont(self.font_name, self.layout['company_address_font_size'])
        self._draw_text_with_weight(c, company_x, company_y, "徳島県板野郡板野町川端字鶴ヶ須47-10",
                                     self.layout['company_address_font_weight'], align='left')
        company_y -= company_spacing * 0.9
        self._draw_text_with_weight(c, company_x, company_y, "TEL　(088)　672-0441(代)",
                                     self.layout['company_address_font_weight'], align='left')
        company_y -= company_spacing * 0.9
        self._draw_text_with_weight(c, company_x, company_y, "FAX　(088)　672-3623",
                                     self.layout['company_address_font_weight'], align='left')

        # 検印欄（会社情報の上に配置）
        stamp_width_val = self.layout['stamp_width']*mm
        stamp_height_val = self.layout['stamp_height']*mm

        # 会社名の上部から十分なスペースを確保して配置
        stamp_bottom = outer_margin + inner_margin + self.layout['company_offset_y']*mm + 10*mm
        stamp_y = stamp_bottom
        stamp_x = content_right - stamp_width_val

        c.rect(stamp_x, stamp_y, stamp_width_val, stamp_height_val)

        # 縦線で3分割
        col_width = stamp_width_val / 3
        c.line(stamp_x + col_width, stamp_y, stamp_x + col_width, stamp_y + stamp_height_val)
        c.line(stamp_x + col_width * 2, stamp_y, stamp_x + col_width * 2, stamp_y + stamp_height_val)

        # ラベル（上部）
        c.setFont(self.font_name, self.layout['stamp_label_font_size'])
        label_y = stamp_y + stamp_height_val - self.layout['stamp_label_offset_y']*mm
        self._draw_text_with_weight(c, stamp_x + col_width / 2, label_y, "検印",
                                     self.layout['stamp_label_font_weight'], align='center')
        self._draw_text_with_weight(c, stamp_x + col_width * 1.5, label_y, "検印",
                                     self.layout['stamp_label_font_weight'], align='center')
        self._draw_text_with_weight(c, stamp_x + col_width * 2.5, label_y, "作成者",
                                     self.layout['stamp_label_font_weight'], align='center')

        # ラベルの下にボーダー（横線）を追加
        border_y = stamp_y + stamp_height_val - self.layout['stamp_label_offset_y']*mm - 3*mm
        c.line(stamp_x, border_y, stamp_x + stamp_width_val, border_y)

# メインエリア
col1, col2 = st.columns([1, 1])

# レイアウトパラメータ（自動的にPDFを生成）
layout_params = {
    # 外枠とマージン
    'outer_margin': outer_margin,
    'inner_margin': inner_margin,
    'outer_line_width': outer_line_width,
    'inner_line_width': inner_line_width,
    'content_padding_left': content_padding_left,
    'content_padding_right': content_padding_right,
    'content_padding_top': content_padding_top,

    # 見積No・日付
    'header_font_size': header_font_size,
    'header_font_weight': header_font_weight,
    'header_offset_y': header_offset_y,

    # タイトル
    'title_font_size': title_font_size,
    'title_font_weight': title_font_weight,
    'title_offset_y': title_offset_y,
    'title_letter_spacing': title_letter_spacing,

    # 宛先
    'client_font_size': client_font_size,
    'client_font_weight': client_font_weight,
    'client_offset_y': client_offset_y,
    'client_underline_offset': client_underline_offset,

    # 金額
    'amount_label_font_size': amount_label_font_size,
    'amount_label_font_weight': amount_label_font_weight,
    'amount_font_size': amount_font_size,
    'amount_font_weight': amount_font_weight,
    'amount_offset_x': amount_offset_x,
    'amount_offset_y': amount_offset_y,
    'note_font_size': note_font_size,
    'note_font_weight': note_font_weight,
    'note_offset_y': note_offset_y,

    # 上記の通り〜
    'above_text_font_size': above_text_font_size,
    'above_text_font_weight': above_text_font_weight,
    'above_text_offset_y': above_text_offset_y,

    # 工事情報
    'work_info_font_size': work_info_font_size,
    'work_info_font_weight': work_info_font_weight,
    'work_info_label_width': work_info_label_width,
    'work_info_line_spacing': work_info_line_spacing,
    'work_info_offset_y': work_info_offset_y,

    # 検印欄
    'stamp_width': stamp_width,
    'stamp_height': stamp_height,
    'stamp_offset_y': stamp_offset_y,
    'stamp_label_font_size': stamp_label_font_size,
    'stamp_label_font_weight': stamp_label_font_weight,
    'stamp_label_offset_y': stamp_label_offset_y,

    # 会社情報
    'company_name_font_size': company_name_font_size,
    'company_name_font_weight': company_name_font_weight,
    'company_president_font_size': company_president_font_size,
    'company_president_font_weight': company_president_font_weight,
    'company_address_font_size': company_address_font_size,
    'company_address_font_weight': company_address_font_weight,
    'company_offset_y': company_offset_y,
    'company_line_spacing': company_line_spacing,
}

with col1:
    st.subheader("📝 プレビュー")

    with st.spinner("PDFを生成中..."):
        # PDF生成
        fmt_doc = get_sample_data()
        pdf_gen = CustomEcoleasePDFGenerator(layout_params)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_gen.generate(fmt_doc, tmp_file.name)
            tmp_file.seek(0)
            pdf_bytes = open(tmp_file.name, 'rb').read()

        # PDFを表示
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)

        # ダウンロードボタン
        st.download_button(
            label="📥 PDFをダウンロード",
            data=pdf_bytes,
            file_name=f"quotation_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf"
        )

with col2:
    st.subheader("📋 使い方")
    st.markdown("""
    1. 左のサイドバーでレイアウトパラメータを調整
    2. リアルタイムでプレビューが更新されます
    3. 気に入ったら設定をコピーしてコードに反映
    """)

    st.subheader("⚙️ 現在の設定値")

    # 設定値をPythonコードとして生成
    config_code = f"""# 外枠とマージン
outer_margin = {outer_margin}*mm
inner_margin = {inner_margin}*mm
c.setLineWidth({outer_line_width})  # 外枠線
c.setLineWidth({inner_line_width})  # 内枠線
content_left = outer_margin + inner_margin + {content_padding_left}*mm
content_right = width - outer_margin - inner_margin - {content_padding_right}*mm
content_top = height - outer_margin - inner_margin - {content_padding_top}*mm

# 見積No・日付
header_font_size = {header_font_size}
header_font_weight = {header_font_weight}
header_y = content_top - {header_offset_y}*mm

# タイトル
title_font_size = {title_font_size}
title_font_weight = {title_font_weight}
title_y = content_top - {title_offset_y}*mm

# 宛先
client_font_size = {client_font_size}
client_font_weight = {client_font_weight}
client_y = content_top - {client_offset_y}*mm
client_underline_offset = {client_underline_offset}*mm

# 金額
amount_label_font_size = {amount_label_font_size}
amount_label_font_weight = {amount_label_font_weight}
amount_font_size = {amount_font_size}
amount_font_weight = {amount_font_weight}
amount_offset_x = {amount_offset_x}*mm
amount_offset_y = {amount_offset_y}*mm
note_font_size = {note_font_size}
note_font_weight = {note_font_weight}
note_offset_y = {note_offset_y}*mm

# 上記の通り〜
above_text_font_size = {above_text_font_size}
above_text_font_weight = {above_text_font_weight}
above_text_offset_y = {above_text_offset_y}*mm

# 工事情報
work_info_font_size = {work_info_font_size}
work_info_font_weight = {work_info_font_weight}
work_info_label_width = {work_info_label_width}*mm
work_info_line_spacing = {work_info_line_spacing}*mm
work_info_offset_y = {work_info_offset_y}*mm

# 検印欄
stamp_width = {stamp_width}*mm
stamp_height = {stamp_height}*mm
stamp_offset_y = {stamp_offset_y}*mm
stamp_label_font_size = {stamp_label_font_size}
stamp_label_font_weight = {stamp_label_font_weight}
stamp_label_offset_y = {stamp_label_offset_y}*mm

# 会社情報
company_name_font_size = {company_name_font_size}
company_name_font_weight = {company_name_font_weight}
company_president_font_size = {company_president_font_size}
company_president_font_weight = {company_president_font_weight}
company_address_font_size = {company_address_font_size}
company_address_font_weight = {company_address_font_weight}
company_offset_y = {company_offset_y}*mm
company_line_spacing = {company_line_spacing}*mm
"""

    st.code(config_code, language="python")

    st.markdown("### 📝 コードへの反映方法")
    st.info("""
    **手順：**
    1. 上記のコードをコピー
    2. `pipelines/pdf_generator.py` を開く
    3. `_create_quotation_page` メソッド内の該当する値を置き換える

    **置き換える場所：**
    - 行番号: 160-290 付近
    - メソッド名: `def _create_quotation_page(self, c, fmt_doc)`

    **例：**
    ```python
    # 変更前
    c.setFont(self.font_name, 9)  # 見積No

    # 変更後（上記の設定値を使用）
    c.setFont(self.font_name, {header_font_size})  # 見積No
    ```
    """)

    st.warning("⚠️ 注意: `*mm` の計算は既にコード内に含まれているため、数値をそのまま置き換えてください。")

    st.success("🎉 設定を調整したら、上記のコードをコピーして `pdf_generator.py` に反映してください！")
