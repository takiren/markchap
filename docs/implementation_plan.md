# markchapツール実装計画

## 1. プロジェクト構造
```
markchap/
├── markchap.py          # メインスクリプト
├── config.json          # 設定ファイル
├── requirements.txt     # 依存関係
├── docs/                # ドキュメント
│   └── implementation_plan.md
└── README.md           # 使用方法
```

## 2. 実装するファイル

### markchap.py
- コマンドライン引数の処理
- ディレクトリ内のmdファイル取得（辞書順）
- 各ファイルの章番号・図表番号処理
- mdbuildディレクトリへの出力

### config.json
- 除外見出しリスト
- 図表認識パターン
- 番号付与形式の設定

## 3. 主要機能

### 章番号処理
- `# 見出し` → `# 1. 見出し`
- `## 見出し` → `## 1.1. 見出し`
- 複数ファイル間で連番継続

### 図表番号処理
- 図: `![説明](image.png)` → `![図1.1.1: 説明](image.png)`
- 表: `<!-- 表: 説明 -->` → `<!-- 表1.1.1: 説明 -->`
- 章が変わると図表番号リセット

### 除外機能
- config.jsonで設定可能な除外見出し
- デフォルト: はじめに、参考文献、謝辞、付録、索引、目次、あとがき、概要、まとめ

### 出力機能
- mdbuildディレクトリに元の構造を再現
- 元ファイルは上書きしない

## 4. 実装手順
1. 基本的なファイル構造作成
2. 設定ファイル実装
3. 章番号処理機能実装
4. 図表番号処理機能実装
5. ディレクトリ処理・出力機能実装
6. テスト用サンプルファイル作成
7. 動作確認・デバッグ

## 5. 要件詳細

### 入力仕様
- 対象ディレクトリ内の全.mdファイルをファイル名順（辞書順）で処理
- 複数ファイル間で章番号は連番継続

### 図表認識仕様
- 図: `![図1: 説明](image.png)` 形式
- 表: `<!-- 表: 説明 -->` 形式（HTMLコメント）

### 番号付与仕様
- 章番号: `1.2.3` 形式
- 図表番号: `図1.2.1` `表1.2.1` 形式（章番号 + 連番）
- 章が変わると図表番号はリセット

### 除外仕様
- 既存の章番号は削除しない
- 設定ファイルで指定した見出しには番号を付けない

### 出力仕様
- 元ファイルは上書きしない
- mdbuildディレクトリに元の構造を再現して出力
- mdbuild内のファイルは上書き可能