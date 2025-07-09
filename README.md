# markchap

Markdownファイルに章番号と図表番号を自動的に付与するPythonツールです。

## 概要

markchapは、複数のMarkdownファイルに対して階層的な章番号（1.1.1形式）と図表番号を自動的に付与するツールです。技術文書や学術論文などの長い文書を複数のファイルに分割して管理する際に便利です。

## 主な機能

- **章番号の自動付与**: 見出しレベルに応じた階層的な番号付与
- **複数ファイル対応**: ディレクトリ内の複数Markdownファイルを連番で処理
- **図表番号付与**: 画像と表に章番号連動の番号を付与
- **ASTベース解析**: markdown-it-pyによる正確なMarkdown解析
- **除外見出し**: 「はじめに」「参考文献」など特定の見出しを除外
- **設定ファイル**: 柔軟な設定による動作カスタマイズ

## 変換例

### 入力
```markdown
# ピアノの練習方法
## 初心者向け
### 毎日やること
![ピアノの鍵盤](keyboard.png)
```

### 出力
```markdown
# 1. ピアノの練習方法
## 1.1. 初心者向け
### 1.1.1. 毎日やること
![図1.1.1: ピアノの鍵盤](keyboard.png)
```

## インストール

### 必要な環境
- Python 3.7以上

### 依存関係のインストール
```bash
pip install -r requirements.txt
```

## 使用方法

### 基本的な使い方

```bash
python3 markchap.py <入力ディレクトリ>
```

### 例
```bash
# test_samplesディレクトリのMarkdownファイルを処理
python3 markchap.py test_samples

# 設定ファイルを指定して処理
python3 markchap.py -c my_config.json docs/
```

### 出力

処理されたファイルは `mdbuild/` ディレクトリに保存されます。元のディレクトリ構造が保持されます。

## 設定ファイル

`config.json`で動作をカスタマイズできます：

```json
{
  "excluded_headings": [
    "はじめに",
    "参考文献",
    "謝辞",
    "付録",
    "索引",
    "目次",
    "あとがき",
    "概要",
    "まとめ"
  ],
  "number_formats": {
    "chapter": "{}",
    "figure": "図{}",
    "table": "表{}"
  },
  "output_directory": "mdbuild",
  "preserve_existing_numbers": true
}
```

### 設定項目

- `excluded_headings`: 章番号を付与しない見出しのリスト
- `number_formats`: 章番号・図表番号の形式
- `output_directory`: 出力ディレクトリ名
- `preserve_existing_numbers`: 既存の番号を保持するか

## 図表の記法

### 図（画像）
```markdown
![説明文](image.png)
```
↓
```markdown
![図1.1.1: 説明文](image.png)
```

### 表
```markdown
<!-- 表: 練習スケジュール -->
| 項目 | 内容 |
|------|------|
| 月   | ハノン |
```
↓
```markdown
<!-- 表1.1.1: 練習スケジュール -->
| 項目 | 内容 |
|------|------|
| 月   | ハノン |
```

## 技術的特徴

- **ASTベース解析**: markdown-it-pyを使用した正確なMarkdown解析
- **コードブロック対応**: コードブロック内の見出し記号を誤検出しない
- **階層的番号管理**: 複雑な見出し構造に対応
- **ファイル間連番**: 複数ファイル間での一貫した番号付与

## 開発情報

### プロジェクト構造
```
markchap/
├── markchap.py          # メインスクリプト
├── config.json          # 設定ファイル
├── requirements.txt     # 依存関係
├── docs/               # ドキュメント
│   ├── implementation_plan.md
│   ├── design_decisions_v2.md
│   └── development_tasks.md
├── test_samples/       # テストファイル
└── README.md          # このファイル
```

### 主要クラス
- `ConfigManager`: 設定ファイル管理
- `MarkdownParser`: Markdown解析（markdown-it-pyベース）
- `NumberingManager`: 章番号・図表番号管理
- `FileProcessor`: ファイル操作
- `MarkchapCore`: 全体制御

## ライセンス

MIT License

## 作者

takiren
