0) まず結論：フローはこの理解でOK
入札資料 → FMT（社内統一フォーマット）正規化 → 必須項目抽出 → 単価RAG（過去見積KB） → 法令KB参照（社内DB/外部） → 見積草案生成（根拠付き）
本仕様は、上記の全フローを“デモで一気通貫に見せる”ための最短構成です。実運用向けの堅牢化ポイントも脚注で併記。
1) デモのゴール / スコープ
ゴール：入札PDF一式を投入→約5分以内に「見積草案（70%）」「質疑ドラフト」「法令根拠リスト」を出力。
対象：まずは**学校（改修/建替え）**の電気・空調・給排水・防災のうち、定型項目を中心に。自衛隊/現場事務所はPoC評価後に横展開。
出力：
見積草案（御社Excelテンプレ互換、根拠列つき）
質疑書ドラフト（不確定要素を自動抽出）
法令・規格の根拠リスト（条番号/年版/出典URL or DBキー）
2) 全体アーキテクチャ（ハイレベル）
[Upload UI]
   │ PDF/Excel/Docx
   ▼
[Doc Ingest] ── OCR/版面解析 ──▶ [FMT Normalizer]
   │                                   │
   │                                   ├─▶ [要点シート(JSON)]
   │                                   └─▶ [添付メタ/図面メタ]
   ▼
[分類器(用途/工種)]
   │
   ├─▶ [過去見積KB(Index)] ── RAG ──┐
   └─▶ [法令KB(Index)] ──────── RAG ─┼─▶ [Estimator]
                                          └─▶ [質疑抽出]
                                              │
                                              ▼
                                        [Excel/PDF Export + 根拠ログ]
セキュリティ分離：
社内データ処理系（入札/見積/図面）と、外部参照系（法令/公知規格クローラ）は論理分離。
デモでは外部参照はキャッシュ優先（当日ネット障害のリスク回避）。
3) データ契約（FMT/要点シート）
3.1 入力ファイル
入札資料（PDF） / 質疑・回答（PDF/Docx） / 過去見積（Excel） / 図面（PDF）
3.2 FMT（社内統一フォーマット）スキーマ（v1）
{
  "tender_header": {
    "project_name": "string",
    "client": "string",
    "category": "school|military|site_office|other",
    "location_pref": "string",
    "floor_area_m2": "number",
    "num_rooms": "integer",
    "building_age": "integer|null",
    "deadline": "date|null"
  },
  "requirements": [
    {
      "discipline": "electric|hvac|plumbing|fire",
      "topic": "照度|コンセント|換気量|空調能力|配管径|非常放送|感知器等",
      "target_value": "string|number",
      "standard_ref": "{law_code}:{article}:{year}",
      "source_page": "int",
      "confidence": "0-1"
    }
  ],
  "attachments": [{"type":"drawing|price_sheet|qa","path":"string","page":1}],
  "metadata": {"doc_hash":"sha256","ingested_at":"datetime"}
}
3.3 過去見積KB（最小）
{
  "item_id": "string",
  "description": "string",
  "discipline": "electric|hvac|plumbing|fire",
  "unit": "台|本|m|m2|式|回",
  "unit_price": 12345,
  "vendor": "string|null",
  "valid_from": "date",
  "valid_to": "date|null",
  "source_project": "string",
  "context_tags": ["学校","普通教室","改修"],
  "features": {"room_area_m2": 50, "ceiling_height_m": 2.7}
}
3.4 法令KB（最小）
{
  "law_code": "JEAC8001|建築基準法|電気設備技術基準|SHASE|JIS...",
  "title": "string",
  "article": "string",
  "year": 2024,
  "clause_text": "string",
  "norm_value": {"topic":"照度","value":"300lx","condition":"普通教室"},
  "citation": {"url":"string","publisher":"string"}
}
4) パイプライン設計（実装手順）
4.1 Doc Ingest & 正規化
抽出：PyMuPDF/pdfplumber → テキスト/表/画像切り出し、表はpandas化。
OCR：埋め込み文字が粗い場合のみ Tesseract/PaddleOCR（日/英）を条件適用。
版面解析：layoutparser/Unstructured で章/表/図/凡例を区分。
マッピング：ルール + 小型LLM で FMT に項目割付（mapping_rules.yaml）。
信頼度：フィールドごとにconfidenceを採点（閾値<0.8 はレビュー待ち）。
4.2 分類（用途/工種）
事前ラベル（school/military/site_office）× discipline（electric/hvac/plumbing/fire）をBOW+埋め込みで粗分類→誤りを人手で1クリック補正。
4.3 KB 構築
過去見積KB：ExcelをETLし、(description, discipline, unit, unit_price, context_tags)を索引化。
向き不一致ケア：同義語辞書（例："非常警報設備"≒"非常放送"）と単位換算（m:左右矢印:本/式）。
法令KB：先方提示の採用法令リストを初期ロード。条番号と年版を主キー化。外部取得は夜間バッチでキャッシュ更新。
4.4 RAG（検索戦略）
単価候補検索：query = discipline + item_keyword + context(room_type, area) → FAISS/Qdrantでk近傍取得。
価格集約：時系列重み + コンテキスト一致度で最尤単価を選択（メディアン推奨）。
法令照合：topicに対応する規範値をLawKBから引当。改修/新築/用途で分岐。
4.5 Estimator（数量・型番・見積生成）
数量推定の仮ルール（デモ用）：
照明台数 ≈ ceil( floor_area_m2 / 8 )（教室想定、デモ用）
コンセント数 ≈ ceil( 6 + floor_area_m2 / 10 )
換気量 ≈ room_volume * ACH（ACHは用途別規範値）
型番候補：過去採用品から上位3件、在庫/調達性タグがあれば加点。
見積草案：
行構成：工種 > 項目 > 数量 > 単位 > 単価 > 金額 > 根拠(事例/条文/式)
Excel出力：御社テンプレに沿ってシート/列名を合わせる（export_mapping.json）。
4.6 質疑抽出器
充足不能/不確定フィールドを列挙し、定型文テンプレにはめ込む（例：換気仕様の明記、非常放送の系統分割 等）。
4.7 監査ログ/再現性
入力hash、モデル/辞書バージョン、RAGヒットIDs、法令条番号、確率/スコアをJSONで保存。
5) UI/デモシナリオ
入札PDFドラッグ&ドロップ → 自動抽出が走り、右パネルに要点シート(JSONプレビュー)。
不足項目が赤表示 → 1クリックで補足入力 or スキップ（質疑に回る）。
RAG計算 → 単価候補+根拠のプレビュー（事例サマリ & 法令条番号）。
見積草案を生成 → Excel/PDFをダウンロード、同時に質疑ドラフト/根拠リストも出力。
監査ビュー → どの根拠から値が来たかをトレース（RAGヒット/条番号/式）。
6) 技術スタック（推奨/代替）
Backend：Python 3.11 + FastAPI
Parsing：PyMuPDF, pdfplumber, unstructured, layoutparser
OCR：Tesseract(+jpn) or PaddleOCR(japan)
Embeddings：bge-m3 もしくは text-embedding-3-large（クラウド可否で選択）
Vector：FAISS（ローカル） or Qdrant（Docker）
LLM：社内許諾に応じて（Azure OpenAI / ローカルLLM）。
UI：Streamlit or Next.js(簡易) ※デモ優先ならStreamlitが早い
Export：openpyxl/xlwings でテンプレ書き込み
Infra：Docker Compose（api, vectordb, ui）
7) リポジトリ構成（例）
repo/
 ├─ api/ (FastAPI)
 ├─ ui/  (Streamlit)
 ├─ pipelines/
 │   ├─ ingest.py
 │   ├─ normalize.py
 │   ├─ classify.py
 │   ├─ build_kb.py
 │   ├─ rag_price.py
 │   ├─ rag_law.py
 │   └─ estimate.py
 ├─ configs/
 │   ├─ mapping_rules.yaml
 │   ├─ export_mapping.json
 │   └─ synonyms.yaml
 ├─ kb/
 │   ├─ estimates.parquet
 │   └─ lawkb.parquet
 └─ tests/
     ├─ demo_docs/
     └─ e2e_demo.py
8) 精度指標（デモKPI）
抽出：必須項目再現率 ≥ 0.90
単価RAG：中央値誤差（MAPE） ≤ 15%
合計見積差：±15% 以内（学校サンプルで）
所要時間：投入→出力 ≤ 5分（10MB/50ページ想定）
9) スケジュール（目安：4〜5週）
W1：要点シート定義/テンプレ吸収、過去見積ETL、UI雛形
W2：正規化/分類/KB構築、RAG単価検索α
W3：Estimator/質疑抽出、Excel出力、監査ログ
W4：精度チューニング、デモ台本/シナリオ整理、当日用キャッシュ作成
(W5)：自衛隊/現場事務所の横展開スパイク
10) 既知のリスクと回避
入札様式のバラつき → FMT項目を“必要最小”に絞る、低信頼は質疑へ回す
単価の時期ズレ → 直近案件に重み、古い案件は減衰
法令更新 → 年版キーで固定、外部参照はキャッシュ/承認フロー
図面→数量の自動化 → 現段階は当たり提示に留め、数量は簡易ルール
11) 当日デモ用 台本（簡易）
PDF投入 → 要点シート生成（赤項目 = 不足）
1クリック補足 → 「再計算」
RAGヒット根拠/条番号を確認 → 「見積作成」
Excel/PDF/質疑ドラフト/根拠リストをDL
監査ビューで“どの根拠から出たか”を追跡
12) 前提 / 必要物（先方/AICE）
先方：
代表案件10〜20（入札/QA/見積/図面）
見積Excelテンプレ
採用法令リスト（年版/条番号）
AICE：
セキュリティ分離アーキ図
FMT定義v1 / mapping_rules.yaml
既定単価辞書（不足領域の初期値）
13) 体制（デモ版）
PM/要件：AICE（星田）
Tech Lead：AICE（山岡）
実装：Parsing/RAG/Estimator（各1名）
QA：積算経験者レビュー（先方1名/AICE1名）



21:39