# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

このリポジトリは「markchap」という名前のツールで、Markdownの見出しに章番号を振るツールです。

## プロジェクト構造

このプロジェクトは以下の構造になっています：

- `README.md` - プロジェクトの説明（日本語）
- `LICENSE` - MITライセンス
- `.claude/settings.local.json` - Claude設定ファイル（findコマンドの権限設定）
- `docs/` - ドキュメントフォルダ
  - `implementation_plan.md` - 実装計画書
- `markchap.py` - メインスクリプト（実装予定）
- `config.json` - 設定ファイル（実装予定）
- `requirements.txt` - 依存関係（実装予定）

## ドキュメント

プロジェクトのドキュメントは `docs/` フォルダに格納されています：

- `docs/implementation_plan.md` - 詳細な実装計画と要件定義
- `docs/design_decisions_v2.md` - 設計判断とライブラリ選択（markdown-it-py採用版）
- `docs/development_tasks.md` - 開発タスクのTodo管理

## 開発環境

このプロジェクトはPythonで開発されるツールです。Markdownファイルに章番号と図表番号を自動的に付与する機能を提供します。

### 主要な依存関係
- **markdown-it-py**: Markdownの正確な解析のためのASTベースパーサー
- **Python標準ライブラリ**: `os`, `json`, `argparse`, `pathlib`

### 技術的な特徴
- ASTベースの解析により、コードブロック内の見出し記号誤検出を防止
- 複雑なMarkdown構造への対応
- 設定ファイルによる柔軟なカスタマイズ

## 注意事項

- このプロジェクトは日本語のドキュメントとコメントを使用しています
- 作者は takiren です
- プロジェクトはMITライセンスの下で公開されています