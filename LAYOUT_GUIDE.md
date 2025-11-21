# レイアウト設定の反映ガイド

## 📝 手順

### 1. Streamlitエディタで調整
```bash
streamlit run pdf_layout_editor.py
```

### 2. 設定値をコピー
- 右側の「⚙️ 現在の設定値」セクションに表示されるPythonコードをコピー

### 3. `pdf_generator.py` に反映

#### ファイル位置
```
pipelines/pdf_generator.py
```

#### 反映する場所
`_create_quotation_page` メソッド内（行番号: 160-290付近）

## 🔧 具体的な置き換え例

### 例1: 見積No・日付のフォントサイズ

**元のコード（pdf_generator.py:180）:**
```python
c.setFont(self.font_name, 9)
quote_no = fmt_doc.metadata.get('quote_no', 'XXXXXXX-00')
c.drawString(content_left, content_top, f"見積No　{quote_no}")
```

**変更後（エディタで設定した値を使用）:**
```python
c.setFont(self.font_name, 11)  # ← 9 から 11 に変更
quote_no = fmt_doc.metadata.get('quote_no', 'XXXXXXX-00')
c.drawString(content_left, content_top, f"見積No　{quote_no}")
```

### 例2: タイトルの位置とサイズ

**元のコード（pdf_generator.py:188-190）:**
```python
c.setFont(self.font_name, 36)
c.drawCentredString(width / 2, content_top - 24*mm, "御　見　積　書")
```

**変更後:**
```python
c.setFont(self.font_name, 42)  # ← タイトルサイズを変更
c.drawCentredString(width / 2, content_top - 20*mm, "御　見　積　書")  # ← 位置を変更
```

### 例3: 金額のフォントサイズと位置

**元のコード（pdf_generator.py:210-213）:**
```python
c.setFont(self.font_name, 28)
amount_text = f"￥{int(total_amount):,}*"
amount_x = content_left + 32*mm
c.drawString(amount_x, y, amount_text)
```

**変更後:**
```python
c.setFont(self.font_name, 32)  # ← 金額サイズを変更
amount_text = f"￥{int(total_amount):,}*"
amount_x = content_left + 28*mm  # ← 横位置を変更
c.drawString(amount_x, y, amount_text)
```

## 📋 主要な変更ポイントと行番号

| 項目 | 行番号（目安） | 変更する変数 |
|------|--------------|-------------|
| 外枠マージン | 166-167 | `outer_margin`, `inner_margin` |
| 線の太さ | 168, 170 | `c.setLineWidth()` |
| 見積No・日付 | 180, 185 | `c.setFont()` の第2引数 |
| タイトル | 189-190 | フォントサイズと位置 |
| 宛先 | 193-201 | フォントサイズと位置 |
| 金額 | 206-217 | フォントサイズ、横位置 |
| 工事情報 | 230-250 | フォントサイズ、行間隔 |
| 検印欄 | 253-270 | 幅、高さ、位置 |
| 会社情報 | 273-285 | フォントサイズ、行間隔 |

## ⚠️ 注意事項

1. **`*mm` の扱い**
   - エディタの設定値には `*mm` が含まれていますが、これはreportlabの単位変換です
   - 既に `from reportlab.lib.units import mm` でインポートされているため、そのまま使用できます

2. **変数の置き換え**
   - 数値を直接置き換えるだけでOK
   - 例: `12*mm` → `15*mm`

3. **保存と確認**
   - 変更を保存したら `python3 test_template.py` でPDFを生成して確認

## 🚀 クイックスタート

```bash
# 1. エディタを起動
streamlit run pdf_layout_editor.py

# 2. レイアウトを調整

# 3. 設定をコピーして pdf_generator.py に反映

# 4. テスト生成
python3 test_template.py

# 5. 生成されたPDFを確認
open ./output/template_test_*.pdf
```

## 💡 Tips

- **細かい調整**: スライダーは0.1-0.5単位で調整可能
- **リアルタイムプレビュー**: スライダーを動かすと即座にPDFが更新されます
- **元に戻す**: デフォルト値は各スライダーの初期値を参照
- **バックアップ**: 変更前に `pdf_generator.py` をコピーしておくと安全です

## 🆘 トラブルシューティング

### PDFが生成されない
```bash
# フォントが正しくインストールされているか確認
python3 check_fonts.py
```

### レイアウトが崩れる
- 値が極端すぎないか確認
- マージンやpaddingの合計がページサイズを超えていないか確認

### 文字が表示されない
- フォントサイズが0以下になっていないか確認
- 位置が画面外になっていないか確認
