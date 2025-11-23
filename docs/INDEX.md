# ドキュメント一覧

## 概要

本ディレクトリには、見積書自動生成システムのドキュメントが含まれています。

---

## ドキュメント一覧

### 技術ドキュメント

| ファイル | 内容 | 対象者 |
|---------|------|--------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | システムアーキテクチャ、モジュール構成、データフロー | 開発者、アーキテクト |
| [TECH_SELECTION.md](./TECH_SELECTION.md) | 技術選定と選定理由、不採用技術の理由 | 開発者、技術リーダー |
| [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) | 実装ガイド、環境構築、新機能追加方法 | 開発者 |
| [ESTIMATE_FLOW.md](./ESTIMATE_FLOW.md) | 見積書作成フロー、単価KB/法令KBの詳細 | 開発者 |

### 運用ドキュメント

| ファイル | 内容 | 対象者 |
|---------|------|--------|
| [USER_MANUAL.md](./USER_MANUAL.md) | ユーザーマニュアル、操作手順、FAQ | エンドユーザー |
| [API_COST_ESTIMATE.md](./API_COST_ESTIMATE.md) | LLM API料金見積もり、コスト最適化 | 運用担当者、管理者 |

---

## 読む順序

### 初めての方

1. **USER_MANUAL.md** - 基本的な使い方を理解
2. **API_COST_ESTIMATE.md** - 料金体系を確認

### 開発者

1. **ARCHITECTURE.md** - システム全体像を把握
2. **TECH_SELECTION.md** - 技術選定の背景を理解
3. **IMPLEMENTATION_GUIDE.md** - 開発環境構築と実装方法
4. **ESTIMATE_FLOW.md** - 処理フローの詳細

### 技術リーダー・アーキテクト

1. **ARCHITECTURE.md** - アーキテクチャ設計の確認
2. **TECH_SELECTION.md** - 技術選定の妥当性確認

---

## ドキュメント更新履歴

| 日付 | ファイル | 変更内容 |
|-----|---------|---------|
| 2025-11-23 | USER_MANUAL.md | 見積作成ページのUI変更に合わせて手順更新 |
| 2025-11-23 | ARCHITECTURE.md | モジュール一覧を最新化、データモデル詳細追加 |
| 2025-11-23 | TECH_SELECTION.md | ハイブリッドマッチング方式に更新 |
| 2025-11-23 | IMPLEMENTATION_GUIDE.md | ベクトル検索オプション追加 |
| 2025-11-23 | ESTIMATE_FLOW.md | ハイブリッドマッチング方式に更新 |
| 2025-11-23 | INDEX.md | 新規作成 |
| 2025-11-22 | ESTIMATE_FLOW.md | 単価KB/法令KB詳細追加 |
| 2025-11-21 | API_COST_ESTIMATE.md | 初版作成 |

---

## 今後追加予定のドキュメント

| ファイル | 内容 | 優先度 |
|---------|------|--------|
| DEPLOYMENT.md | デプロイ手順（本番環境） | 中 |
| API_REFERENCE.md | 内部API仕様 | 低 |
| TESTING.md | テスト戦略・テストケース | 低 |
| CHANGELOG.md | 変更履歴 | 中 |

---

## 関連ファイル

| ファイル | 場所 | 内容 |
|---------|------|------|
| CLAUDE.md | プロジェクトルート | 開発履歴、改善記録 |
| requirements.txt | プロジェクトルート | 依存パッケージ |
| .env.example | プロジェクトルート | 環境変数テンプレート |

---

*最終更新: 2025年11月23日*
