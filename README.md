<div align="center">
    <img src="./media/logo_small.webp"/>
    <h1>🌱 Spec Kit JP</h1>
    <h3><em>仕様駆動開発で高品質なソフトウェアをより速く構築</em></h3>
</div>

<p align="center">
    <strong>Spec-Driven Development（仕様駆動開発）により、組織が未分化なコードを書くのではなく、製品シナリオに集中できるようにする取り組みの日本語版です。</strong>
</p>

[![Release](https://github.com/github/spec-kit/actions/workflows/release.yml/badge.svg)](https://github.com/github/spec-kit/actions/workflows/release.yml)

---

## 📚 目次

- [🎌 Spec Kit JPとは](#-spec-kit-jpとは)
- [🤔 仕様駆動開発とは？](#-仕様駆動開発とは)
- [⚡ クイックスタート](#-クイックスタート)
- [🚀 使い方](#-使い方)
- [📖 コマンド詳細](#-コマンド詳細)
- [🌟 開発フェーズ](#-開発フェーズ)
- [🔧 前提条件](#-前提条件)
- [📝 テンプレート](#-テンプレート)
- [💻 実行例](#-実行例)
- [🤝 貢献](#-貢献)

## 🎌 Spec Kit JPとは

Spec Kit JPは、[Spec Kit](https://github.com/github/spec-kit)の日本語版フォークです。すべてのテンプレート、CLIメッセージ、ドキュメントが日本語に翻訳されており、日本のチームが仕様駆動開発を母国語で実践できるようになっています。

### 主な特徴

- ✅ **完全日本語対応** - CLIメッセージ、テンプレート、生成される文書がすべて日本語
- 🤖 **AI対応** - Claude Code、Gemini CLI、GitHub Copilotで動作
- 📝 **日本語テンプレート** - 仕様書、実装計画、タスクリストのテンプレートを日本語化
- 🔄 **オリジナルとの互換性** - Spec Kitの機能をそのまま維持

## 🤔 仕様駆動開発とは？

仕様駆動開発は従来のソフトウェア開発を**逆転**させます。数十年間、コードが王様でした - 仕様書は「本当の作業」であるコーディングが始まったら構築して破棄する足場に過ぎませんでした。仕様駆動開発はこれを変えます：**仕様書が実行可能になり**、単に実装を導くだけでなく、直接動作する実装を生成します。

## ⚡ クイックスタート

### 1. Specifyのインストール

```bash
# uvを使用してローカルから実行
uv run python src/specify_cli/__init__.py init プロジェクト名

# または、GitHubから直接インストール
uvx --from git+https://github.com/r1cA18/spec-kit-jp.git specify init プロジェクト名
```

### 2. プロジェクトの初期化

```bash
# 新しいプロジェクトディレクトリを作成
specify init my-project --ai claude

# または現在のディレクトリで初期化
specify init --here --ai claude
```

## 🚀 使い方

### 1. 仕様を作成

`/specify` コマンドを使用して、構築したいものを説明します。**何を**、**なぜ**に焦点を当て、技術スタックには触れません。

```bash
/specify 写真を別々のフォトアルバムに整理できるアプリケーションを構築する。アルバムは日付でグループ化され、メインページでドラッグ＆ドロップで再編成できる。アルバムは他のアルバムをネストしない。各アルバム内では、写真がタイル状のインターフェースでプレビューされる。
```

### 2. 技術的な実装計画を作成

`/plan` コマンドを使用して、技術スタックとアーキテクチャの選択を提供します。

```bash
/plan アプリケーションはViteを使用し、ライブラリの数は最小限にする。可能な限りバニラHTML、CSS、JavaScriptを使用する。画像はどこにもアップロードされず、メタデータはローカルのSQLiteデータベースに保存される。
```

### 3. タスクに分解して実装

`/tasks` を使用してアクション可能なタスクリストを作成し、エージェントに機能の実装を依頼します。

```bash
/tasks
```

## 📖 コマンド詳細

### `/specify` - 仕様書作成
新機能の仕様書と機能ブランチを作成します。

```bash
# 使用例
/specify ユーザー認証システムを構築する
```

生成されるもの：
- 機能ブランチ（例：`001-create-auth-system`）
- 仕様書（`specs/001-create-auth-system/spec.md`）

### `/plan` - 実装計画
技術的な実装計画を作成します。

```bash
# 使用例
/plan Next.js 14とTypeScriptを使用、認証にはSupabaseを使用
```

生成されるもの：
- 実装計画（`plan.md`）
- データモデル（`data-model.md`）
- API契約（`contracts/`）
- クイックスタートガイド（`quickstart.md`）

### `/tasks` - タスク生成
実装タスクリストを生成します。

```bash
# 使用例
/tasks
```

生成されるもの：
- タスクリスト（`tasks.md`）
- 番号付きタスク（T001、T002...）
- 依存関係グラフ

## 🌟 開発フェーズ

| フェーズ | フォーカス | 主な活動 |
|---------|-----------|----------|
| **0-to-1開発**（グリーンフィールド） | ゼロから生成 | • 高レベル要件から開始<br>• 仕様を生成<br>• 実装ステップを計画<br>• 本番環境対応アプリケーションを構築 |
| **創造的探索** | 並列実装 | • 多様なソリューションを探索<br>• 複数の技術スタックとアーキテクチャをサポート<br>• UXパターンを実験 |
| **反復的強化**（ブラウンフィールド） | 既存システムの改善 | • 機能を反復的に追加<br>• レガシーシステムを近代化<br>• プロセスを適応 |

## 🔧 前提条件

- **Linux/macOS**（WindowsではWSL2）
- **uv** - Pythonパッケージ管理
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Python 3.11+**
- **Git**
- **AIコーディングエージェント**（以下のいずれか）：
  - [Claude Code](https://www.anthropic.com/claude-code)
  - [GitHub Copilot](https://code.visualstudio.com/)
  - [Gemini CLI](https://github.com/google-gemini/gemini-cli)

## 📝 テンプレート

日本語化されたテンプレート：

### 仕様書テンプレート (`spec-template.md`)
- ユーザーシナリオとテスト
- 機能要件
- 受け入れ基準

### 実装計画テンプレート (`plan-template.md`)
- 技術コンテキスト
- プロジェクト構造
- フェーズ別実装計画

### タスクテンプレート (`tasks-template.md`)
- TDD準拠のタスク順序
- 並列実行可能タスクの識別
- 依存関係管理

## 💻 実行例

### ローカル開発

```bash
# プロジェクトのクローン
git clone https://github.com/r1cA18/spec-kit-jp.git
cd spec-kit-jp

# CLIツールのテスト
uv run python src/specify_cli/__init__.py --help

# システムチェック
uv run python src/specify_cli/__init__.py check

# 新規プロジェクトの初期化
uv run python src/specify_cli/__init__.py init test-project --ai claude
```

### グローバルインストール

```bash
# パッケージとしてインストール
uv tool install git+https://github.com/r1cA18/spec-kit-jp.git

# 任意の場所から使用
specify init my-project --ai claude
```

### Docker使用（オプション）

```dockerfile
FROM python:3.11-slim
RUN pip install uv
RUN uv tool install git+https://github.com/r1cA18/spec-kit-jp.git
```

## 🤝 貢献

貢献を歓迎します！以下の方法で参加できます：

1. **バグ報告** - [Issues](https://github.com/r1cA18/spec-kit-jp/issues)で報告
2. **機能リクエスト** - 新機能の提案
3. **プルリクエスト** - 改善の提出
4. **翻訳改善** - より自然な日本語表現への改善

## 📜 ライセンス

このプロジェクトはMITライセンスの条件の下でライセンスされています。詳細は[LICENSE](./LICENSE)ファイルを参照してください。

## 🙏 謝辞

このプロジェクトは[GitHub](https://github.com/github)の[Spec Kit](https://github.com/github/spec-kit)をベースにしています。特に[John Lam](https://github.com/jflam)氏の研究と作業に大きく影響を受けています。

## メンテナー

- オリジナル: Den Delimarsky ([@localden](https://github.com/localden)), John Lam ([@jflam](https://github.com/jflam))
- 日本語版: [@r1cA18](https://github.com/r1cA18)
