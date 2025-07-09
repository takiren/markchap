# 設計判断とライブラリ選択

## 使用予定ライブラリ

### コア機能
- **標準ライブラリのみ使用**: `os`, `json`, `re`, `argparse`, `pathlib`
- **理由**: 外部依存を最小限に抑え、インストールを簡単にする

### 検討したライブラリ（不採用）
- **markdown**: Markdownパーサーライブラリ
  - 不採用理由: 見出しと図表の検出には正規表現で十分
- **click**: コマンドライン引数処理
  - 不採用理由: 標準の`argparse`で十分な機能
- **pyyaml**: YAML設定ファイル
  - 不採用理由: JSON設定で十分、追加依存を避ける

## アーキテクチャ設計

### 全体構成
```
markchap/
├── markchap.py          # メインエントリーポイント
├── config.json          # 設定ファイル
├── requirements.txt     # 依存関係（標準ライブラリのみ）
└── docs/               # ドキュメント
```

### クラス設計

#### 1. ConfigManager
- 設定ファイルの読み込み・管理
- デフォルト設定の提供
- 設定値の検証

#### 2. MarkdownParser
- Markdownファイルの解析
- 見出しレベルの抽出
- 図表の検出
- 除外見出しの判定

#### 3. NumberingManager
- 章番号の管理
- 図表番号の管理
- 複数ファイル間での連番継続

#### 4. FileProcessor
- ファイル操作の管理
- ディレクトリの作成
- ファイルの読み書き

#### 5. MarkchapCore
- 全体の処理フローの制御
- 各コンポーネントの連携

### データ構造設計

#### 見出し情報
```python
class Heading:
    level: int          # 見出しレベル (1-6)
    text: str          # 見出しテキスト
    line_number: int   # 行番号
    is_excluded: bool  # 除外対象か
    number: str        # 付与する番号 (例: "1.2.3")
```

#### 図表情報
```python
class Figure:
    type: str          # "figure" or "table"
    original_text: str # 元のテキスト
    caption: str       # キャプション
    line_number: int   # 行番号
    chapter_number: str # 章番号
    figure_number: int  # 図表内番号
```

#### 番号管理
```python
class NumberState:
    current_numbers: List[int]  # 現在の章番号レベル
    figure_count: int           # 現在の章での図番号
    table_count: int            # 現在の章での表番号
    global_file_count: int      # ファイル通し番号
```

## 正規表現パターン

### 見出し検出
```python
HEADING_PATTERN = r'^(#{1,6})\s+(.+)$'
```

### 図の検出
```python
FIGURE_PATTERN = r'!\[([^\]]*)\]\(([^)]+)\)'
```

### 表の検出
```python
TABLE_PATTERN = r'<!--\s*表\s*:\s*([^>]+)\s*-->'
```

## 設定ファイル構造

### config.json
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
  "figure_patterns": {
    "figure": "!\\[([^\\]]*)\\]\\(([^)]+)\\)",
    "table": "<!--\\s*表\\s*:\\s*([^>]+)\\s*-->"
  },
  "number_formats": {
    "chapter": "{}.{}",
    "figure": "図{}.{}",
    "table": "表{}.{}"
  },
  "output_directory": "mdbuild",
  "preserve_existing_numbers": true
}
```

## 処理フロー

### メイン処理フロー
1. 設定ファイル読み込み
2. 入力ディレクトリの検証
3. mdファイルの取得・ソート
4. 出力ディレクトリの準備
5. 各ファイルの処理
6. 結果の出力

### ファイル処理フロー
1. ファイル読み込み
2. 見出し・図表の検出
3. 番号付与の計算
4. テキストの変換
5. 出力ファイルの書き込み

## エラーハンドリング

### 想定エラー
- 設定ファイルの読み込みエラー
- 入力ディレクトリの存在確認エラー
- ファイル読み書きエラー
- 不正なMarkdown構造エラー

### 対処方針
- エラーメッセージは日本語で表示
- 処理継続可能なエラーは警告として表示
- 致命的エラーは適切な終了コードで終了

## テスト戦略

### 単体テスト
- 各クラスの機能テスト
- 正規表現パターンのテスト
- 設定ファイル読み込みテスト

### 統合テスト
- 実際のMarkdownファイルを使用
- 複数ファイル処理のテスト
- エラーケースのテスト

### テストデータ
- 各種見出しレベルを含むサンプル
- 図表を含むサンプル
- 除外見出しを含むサンプル
- 既存番号を含むサンプル