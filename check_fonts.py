"""利用可能な日本語フォントを確認するスクリプト"""

import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def check_font(font_path, subfont_index=None):
    """フォントが使えるかチェック"""
    if not os.path.exists(font_path):
        return False, "ファイルが存在しません"

    try:
        if subfont_index is not None:
            pdfmetrics.registerFont(TTFont('TestFont', font_path, subfontIndex=subfont_index))
        else:
            pdfmetrics.registerFont(TTFont('TestFont', font_path))
        return True, "✅ 使用可能"
    except Exception as e:
        return False, f"❌ エラー: {str(e)[:50]}"

print("=" * 80)
print("日本語フォント確認")
print("=" * 80)

# 明朝体フォント
print("\n【明朝体フォント】")
mincho_fonts = [
    ("ヒラギノ明朝 ProN (Light)", '/System/Library/Fonts/ヒラギノ明朝 ProN.ttc', 0),
    ("ヒラギノ明朝 ProN (W3)", '/System/Library/Fonts/ヒラギノ明朝 ProN.ttc', 3),
    ("ヒラギノ明朝 ProN (W6)", '/System/Library/Fonts/ヒラギノ明朝 ProN.ttc', 6),
    ("游明朝体 (Light)", '/System/Library/Fonts/游明朝体.ttc', 1),
    ("游明朝体 (Regular)", '/System/Library/Fonts/游明朝体.ttc', 3),
    ("游明朝体 (Medium)", '/System/Library/Fonts/游明朝体.ttc', 4),
    ("游明朝体 (Demibold)", '/System/Library/Fonts/游明朝体.ttc', 5),
    ("游明朝体 (Bold)", '/System/Library/Fonts/游明朝体.ttc', 6),
    ("IPA明朝", '/usr/share/fonts/opentype/ipaexfont-mincho/ipaexm.ttf', None),
    ("Takao明朝", '/usr/share/fonts/truetype/takao-mincho/TakaoMincho.ttf', None),
]

for name, path, index in mincho_fonts:
    success, message = check_font(path, index)
    status = "✅" if success else "❌"
    print(f"{status} {name}")
    print(f"   パス: {path}")
    if index is not None:
        print(f"   インデックス: {index}")
    print(f"   状態: {message}")
    print()

# ゴシック体フォント
print("\n【ゴシック体フォント】")
gothic_fonts = [
    ("ヒラギノ角ゴシック W3", '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc', 0),
    ("Arial Unicode", '/Library/Fonts/Arial Unicode.ttf', None),
]

for name, path, index in gothic_fonts:
    success, message = check_font(path, index)
    status = "✅" if success else "❌"
    print(f"{status} {name}")
    print(f"   パス: {path}")
    if index is not None:
        print(f"   インデックス: {index}")
    print(f"   状態: {message}")
    print()

print("=" * 80)
print("\n💡 推奨事項:")
print("明朝体のライトウェイトフォントとして、以下を推奨します:")
print("1. ヒラギノ明朝 ProN (Light) - macOSにデフォルトで含まれています")
print("2. 游明朝体 (Light) - macOSにデフォルトで含まれています")
print("\nMS明朝をインストールするには:")
print("1. Microsoft Officeをインストールしている場合、自動的に含まれています")
print("2. または、フォントファイルを /Library/Fonts/ にコピーしてください")
print("=" * 80)
