# 明朝体フォントのインストール方法

## 現在の状態
✅ Arial Unicode（ゴシック体）で日本語を表示できます

## MS明朝フォントのインストール

### 方法1: Microsoft Officeから（推奨）
Microsoft Officeがインストールされている場合、MS明朝は自動的に含まれています。

### 方法2: フォントファイルを手動でコピー
1. MS明朝フォントファイル（`msmincho.ttf` または `MS Mincho.ttf`）を入手
2. 以下のコマンドでコピー：
```bash
# フォントファイルがあるディレクトリに移動してから
sudo cp "MS Mincho.ttf" /Library/Fonts/
```

### 方法3: IPA明朝フォント（無料・オープンソース）
IPA明朝は無料で使える明朝体フォントです：

1. IPAフォントをダウンロード：
   https://moji.or.jp/ipafont/

2. ダウンロードしたzipファイルを解凍

3. フォントファイルをコピー：
```bash
sudo cp ipaexm.ttf /Library/Fonts/
```

## インストール後
フォントをインストールした後、以下のコマンドで確認：
```bash
python3 check_fonts.py
```

PDFを再生成：
```bash
python3 test_template.py
```

## Streamlitエディタの起動
```bash
streamlit run pdf_layout_editor.py
```

## 現在使用可能なフォント
- ✅ Arial Unicode（ゴシック体、日本語対応）
- ⏳ MS明朝（インストール後に利用可能）
- ⏳ IPA明朝（インストール後に利用可能）

## 注意事項
reportlabではTTCファイル（macOSのヒラギノ明朝など）が正しく動作しないため、TTF/OTFファイルが必要です。
