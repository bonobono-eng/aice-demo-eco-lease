#!/bin/bash

# IPA明朝フォントをインストールするスクリプト

echo "IPA明朝フォントをダウンロード中..."

# 一時ディレクトリを作成
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# IPAex明朝フォントをダウンロード
curl -L -o ipaexfont.zip "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexfont00401.zip"

# 解凍
unzip -q ipaexfont.zip

# フォントファイルをコピー
sudo cp ipaexfont00401/ipaexm.ttf /Library/Fonts/
sudo cp ipaexfont00401/ipaexg.ttf /Library/Fonts/

echo "✅ IPA明朝フォントのインストールが完了しました"
echo "   - /Library/Fonts/ipaexm.ttf (IPA明朝)"
echo "   - /Library/Fonts/ipaexg.ttf (IPAゴシック)"

# クリーンアップ
cd -
rm -rf "$TEMP_DIR"

echo ""
echo "フォントを確認するには:"
echo "  python3 check_fonts.py"
