# 設計判断とライブラリ選択 (v2)

## 使用予定ライブラリ

### コア機能
- **markdown-it-py**: Markdownパーサー（ASTベース）
- **標準ライブラリ**: `os`, `json`, `argparse`, `pathlib`

### markdown-it-py選択理由
1. **正確な構造解析**: ASTベースでMarkdownを正確に解析
2. **コードブロック対応**: コードブロック内の見出し記号を誤検出しない
3. **プラグインシステム**: 将来的な拡張が容易
4. **アクティブなメンテナンス**: executablebooksによる活発な開発
5. **Python標準**: PythonのMarkdownエコシステムで広く使用

### 依存関係
```
markdown-it-py>=3.0.0
```

## アーキテクチャ設計（更新版）

### クラス設計

#### 1. ConfigManager
- 設定ファイルの読み込み・管理
- デフォルト設定の提供
- 設定値の検証

#### 2. MarkdownParser（更新）
- markdown-it-pyを使用したMarkdown解析
- ASTからの見出し抽出
- 図表の検出（ASTベース）
- 除外見出しの判定
- トークン操作による番号付与

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

#### 見出し情報（更新）
```python
class Heading:
    level: int          # 見出しレベル (1-6)
    text: str          # 見出しテキスト（プレーン）
    raw_text: str      # 元のテキスト（マークアップ含む）
    token_index: int   # ASTトークンのインデックス
    line_number: int   # 行番号
    is_excluded: bool  # 除外対象か
    number: str        # 付与する番号 (例: "1.2.3")
```

#### 図表情報（更新）
```python
class Figure:
    type: str          # "figure" or "table"
    original_text: str # 元のテキスト
    caption: str       # キャプション
    token_index: int   # ASTトークンのインデックス
    line_number: int   # 行番号
    chapter_number: str # 章番号
    figure_number: int  # 図表内番号
```

## markdown-it-pyベースの処理フロー

### 解析フロー
1. **Markdownファイル読み込み**
2. **markdown-it-pyでASTに変換**
3. **ASTトークンの走査**
   - 見出しトークンの抽出
   - 画像トークンの抽出
   - HTMLコメントトークンの抽出（表用）
4. **番号付与の計算**
5. **ASTトークンの更新**
6. **更新されたASTからMarkdownを再生成**

### 見出し検出（ASTベース）
```python
def extract_headings(tokens):
    headings = []
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            level = int(token.tag[1])  # h1 -> 1, h2 -> 2
            # 次のトークンが見出しテキスト
            text_token = tokens[i + 1]
            heading = Heading(
                level=level,
                text=text_token.content,
                raw_text=text_token.content,
                token_index=i,
                line_number=token.map[0] if token.map else 0
            )
            headings.append(heading)
    return headings
```

### 図表検出（ASTベース）
```python
def extract_figures(tokens):
    figures = []
    for i, token in enumerate(tokens):
        # 画像の検出
        if token.type == 'image':
            figure = Figure(
                type='figure',
                original_text=token.content,
                caption=token.attrGet('alt') or '',
                token_index=i,
                line_number=token.map[0] if token.map else 0
            )
            figures.append(figure)
        
        # 表の検出（HTMLコメント）
        elif token.type == 'html_inline' and '<!-- 表' in token.content:
            # 表のキャプション抽出
            import re
            match = re.search(r'<!--\s*表\s*:\s*([^>]+)\s*-->', token.content)
            if match:
                figure = Figure(
                    type='table',
                    original_text=token.content,
                    caption=match.group(1),
                    token_index=i,
                    line_number=token.map[0] if token.map else 0
                )
                figures.append(figure)
    return figures
```

### 番号付与（ASTベース）
```python
def apply_numbering(tokens, headings, figures):
    # 見出しの番号付与
    for heading in headings:
        if not heading.is_excluded:
            token = tokens[heading.token_index + 1]  # テキストトークン
            token.content = f"{heading.number}. {heading.text}"
    
    # 図表の番号付与
    for figure in figures:
        token = tokens[figure.token_index]
        if figure.type == 'figure':
            # 画像のalt属性を更新
            token.attrSet('alt', f"図{figure.chapter_number}.{figure.figure_number}: {figure.caption}")
        elif figure.type == 'table':
            # HTMLコメントを更新
            token.content = f"<!-- 表{figure.chapter_number}.{figure.figure_number}: {figure.caption} -->"
```

## 設定ファイル構造（更新）

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
  "number_formats": {
    "chapter": "{}",
    "figure": "図{}",
    "table": "表{}"
  },
  "output_directory": "mdbuild",
  "preserve_existing_numbers": true,
  "markdown_it_options": {
    "html": true,
    "breaks": false,
    "linkify": true
  }
}
```

## 利点

### markdown-it-py使用の利点
1. **正確性**: ASTベースで構造を正確に把握
2. **安全性**: コードブロック内の誤検出を防止
3. **拡張性**: プラグインシステムで機能拡張が容易
4. **保守性**: 正規表現より理解しやすいコード
5. **標準準拠**: CommonMarkに準拠した解析

### 従来の正規表現との比較
| 項目 | 正規表現 | markdown-it-py |
|------|----------|----------------|
| 実装の簡単さ | ○ | △ |
| 解析精度 | △ | ○ |
| 拡張性 | △ | ○ |
| メンテナンス性 | △ | ○ |
| 依存関係 | ○ | △ |

## テスト戦略（更新）

### 単体テスト
- ASTパーサーの機能テスト
- 見出し抽出の正確性テスト
- 図表検出の精度テスト
- 番号付与ロジックのテスト

### 統合テスト
- 複雑なMarkdown構造のテスト
- コードブロック内の見出し記号テスト
- HTMLタグ混在テスト
- 複数ファイル処理テスト

### テストケース例
```markdown
# 通常の見出し

```python
# コードブロック内（検出されない）
def hello():
    pass
```

## 実際の見出し

> # 引用内の見出し（特別な扱い）

<!-- 表: サンプル表 -->
| 項目 | 値 |
|------|-----|
| A | 1 |

![図: サンプル図](image.png)
```

## 実装上の注意点

1. **ASTトークンの順序**: トークンのインデックス管理が重要
2. **行番号の取得**: `token.map`を使用して元の行番号を取得
3. **トークンの更新**: 番号付与後のトークン内容更新
4. **Markdown再生成**: 更新されたASTからMarkdownテキストを再生成