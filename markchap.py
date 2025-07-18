#!/usr/bin/env python3
"""
markchap - Markdownファイルに章番号と図表番号を付与するツール
"""

import os
import json
import argparse
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from markdown_it import MarkdownIt


@dataclass
class Heading:
    """見出し情報"""

    level: int
    text: str
    raw_text: str
    token_index: int
    line_number: int
    is_excluded: bool = False
    number: str = ""


@dataclass
class Figure:
    """図表情報"""

    type: str  # "figure" or "table"
    original_text: str
    caption: str
    token_index: int
    line_number: int
    chapter_number: str = ""
    figure_number: int = 0


@dataclass
class NumberState:
    """番号管理状態"""

    current_numbers: List[int]
    # 以下のフィールドは使用されていないが、互換性のために残す
    figure_count: int = 0
    table_count: int = 0
    global_file_count: int = 0


class ConfigManager:
    """設定ファイルの管理"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(
                f"設定ファイル {self.config_path} が見つかりません。デフォルト設定を使用します。"
            )
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"設定ファイルの読み込みエラー: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を返す"""
        return {
            "excluded_headings": [
                "はじめに",
                "参考文献",
                "謝辞",
                "付録",
                "索引",
                "目次",
                "あとがき",
                "概要",
                "まとめ",
            ],
            "number_formats": {"chapter": "{}", "figure": "図{}", "table": "表{}"},
            "output_directory": "mdbuild",
            "preserve_existing_numbers": True,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.config.get(key, default)


class MarkdownParser:
    """Markdownパーサー（markdown-it-pyベース）"""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.md = MarkdownIt()

    def parse_file(
        self, file_path: str
    ) -> Tuple[List[Heading], List[Figure], List[Any]]:
        """ファイルを解析して見出し・図表・トークンを抽出"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tokens = self.md.parse(content)
        headings = self._extract_headings(tokens)
        figures = self._extract_figures_from_content(content)

        return headings, figures, tokens

    def _extract_headings(self, tokens: List[Any]) -> List[Heading]:
        """ASTトークンから見出しを抽出"""
        headings = []
        excluded_headings = self.config.get("excluded_headings", [])

        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                level = int(token.tag[1])  # h1 -> 1, h2 -> 2

                # 次のトークンが見出しテキスト
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    text_token = tokens[i + 1]
                    text = text_token.content.strip()

                    # 除外見出しの判定
                    is_excluded = any(
                        excluded in text for excluded in excluded_headings
                    )

                    heading = Heading(
                        level=level,
                        text=text,
                        raw_text=text,  # 元のテキストを保存
                        token_index=i,
                        line_number=token.map[0] if token.map else 0,
                        is_excluded=is_excluded,
                    )
                    headings.append(heading)

        return headings


    def _extract_figures_from_content(self, content: str) -> List[Figure]:
        """ファイルの内容から直接図表を抽出"""
        figures = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 画像の検出
            image_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if image_match:
                caption = image_match.group(1)
                src = image_match.group(2)
                figure = Figure(
                    type="figure",
                    original_text=line,
                    caption=caption,
                    token_index=0,  # 仮の値
                    line_number=i + 1,
                )
                figures.append(figure)
            
            # 表の検出
            table_match = re.match(r'<!--\s*表\s*:\s*([^>]+)\s*-->', line)
            if table_match:
                caption = table_match.group(1).strip()
                figure = Figure(
                    type="table",
                    original_text=line,
                    caption=caption,
                    token_index=0,  # 仮の値
                    line_number=i + 1,
                )
                figures.append(figure)
        
        return figures



class NumberingManager:
    """番号付与の管理"""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.state = NumberState(current_numbers=[])

    def process_headings(self, headings: List[Heading]) -> None:
        """見出しに章番号を付与"""
        for heading in headings:
            if heading.is_excluded:
                continue

            # 章番号の計算
            level = heading.level

            # 現在の番号リストを調整
            if len(self.state.current_numbers) < level:
                # レベルが深くなった場合、新しいレベルを追加
                self.state.current_numbers.extend(
                    [0] * (level - len(self.state.current_numbers))
                )
            elif len(self.state.current_numbers) > level:
                # レベルが浅くなった場合、余分なレベルを削除
                self.state.current_numbers = self.state.current_numbers[:level]

            # 現在のレベルの番号を増加
            self.state.current_numbers[level - 1] += 1

            # それより深いレベルをリセット
            for i in range(level, len(self.state.current_numbers)):
                self.state.current_numbers[i] = 0

            # 番号文字列を生成
            number_parts = [
                str(num) for num in self.state.current_numbers[:level] if num > 0
            ]
            heading.number = ".".join(number_parts)

            # 図表番号のリセット（章が変わった場合）
            # 注意: 実際の図表番号管理は_assign_figure_numbersで行われる
            if level == 1:
                self.state.figure_count = 0
                self.state.table_count = 0



class FileProcessor:
    """ファイル操作の管理"""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.output_dir = config.get("output_directory", "mdbuild")

    def get_markdown_files(self, input_dir: str) -> List[str]:
        """指定ディレクトリからMarkdownファイルを取得（辞書順）"""
        md_files = []
        for root, dirs, files in os.walk(input_dir):
            for file in sorted(files):
                if file.endswith(".md"):
                    md_files.append(os.path.join(root, file))
        return sorted(md_files)

    def prepare_output_directory(self, input_dir: str) -> None:
        """出力ディレクトリの準備"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 入力ディレクトリの構造を再現（出力ディレクトリは除外）
        for root, dirs, files in os.walk(input_dir):
            # 出力ディレクトリを除外
            if self.output_dir in dirs:
                dirs.remove(self.output_dir)
            
            for dir_name in dirs:
                input_path = os.path.join(root, dir_name)
                relative_path = os.path.relpath(input_path, input_dir)
                output_path = os.path.join(self.output_dir, relative_path)
                if not os.path.exists(output_path):
                    os.makedirs(output_path)

    def write_output_file(self, input_file: str, input_dir: str, content: str) -> None:
        """出力ファイルの書き込み"""
        relative_path = os.path.relpath(input_file, input_dir)
        output_file = os.path.join(self.output_dir, relative_path)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)


class MarkchapCore:
    """メイン処理の制御"""

    def __init__(self, config_path: str = "config.json"):
        self.config = ConfigManager(config_path)
        self.parser = MarkdownParser(self.config)
        self.numbering = NumberingManager(self.config)
        self.file_processor = FileProcessor(self.config)

    def process_directory(self, input_dir: str) -> None:
        """ディレクトリ全体を処理"""
        if not os.path.exists(input_dir):
            print(f"エラー: 入力ディレクトリ '{input_dir}' が存在しません。")
            return

        # Markdownファイルの取得
        md_files = self.file_processor.get_markdown_files(input_dir)
        if not md_files:
            print(f"エラー: '{input_dir}' にMarkdownファイルが見つかりません。")
            return

        print(f"処理対象ファイル数: {len(md_files)}")

        # 出力ディレクトリの準備
        self.file_processor.prepare_output_directory(input_dir)

        # 各ファイルの処理
        for file_path in md_files:
            print(f"処理中: {file_path}")
            self.process_file(file_path, input_dir)

        print(
            f"処理完了。結果は '{self.file_processor.output_dir}' ディレクトリに保存されました。"
        )

    def process_file(self, file_path: str, input_dir: str) -> None:
        """単一ファイルの処理"""
        try:
            # ファイルの解析
            headings, figures, tokens = self.parser.parse_file(file_path)

            # 章番号の付与
            self.numbering.process_headings(headings)

            # 図表番号の付与
            self._assign_figure_numbers(figures, headings)

            # 元のファイルを読み込み、直接置換
            content = self._process_content_directly(file_path, headings, figures)

            # 出力ファイルの書き込み
            self.file_processor.write_output_file(file_path, input_dir, content)

        except Exception as e:
            print(f"エラー: {file_path} の処理に失敗しました: {e}")

    def _assign_figure_numbers(self, figures: List[Figure], headings: List[Heading]) -> None:
        """図表番号を適切に付与"""
        # 各レベル2の見出し（小節）ごとに図表番号を管理
        section_figure_count = {}
        section_table_count = {}
        
        for figure in figures:
            # 図表の位置から対応する小節を見つける
            current_section = self._find_section_for_figure(figure, headings)
            
            # 小節番号ごとに図表番号を管理
            figure.figure_number = self._get_next_figure_number(
                figure.type, current_section, section_figure_count, section_table_count
            )
            figure.chapter_number = current_section
    
    def _get_next_figure_number(
        self, 
        figure_type: str, 
        section: str, 
        figure_count: Dict[str, int], 
        table_count: Dict[str, int]
    ) -> int:
        """次の図表番号を取得"""
        if figure_type == "figure":
            if section not in figure_count:
                figure_count[section] = 0
            figure_count[section] += 1
            return figure_count[section]
        elif figure_type == "table":
            if section not in table_count:
                table_count[section] = 0
            table_count[section] += 1
            return table_count[section]
        else:
            print(f"警告: 不明な図表タイプ: {figure_type}")
            return 1

    def _find_section_for_figure(self, figure: Figure, headings: List[Heading]) -> str:
        """図表に対応する小節を見つける"""
        try:
            for heading in headings:
                if (not heading.is_excluded and 
                    heading.number and 
                    heading.level == 2 and  # レベル2の見出し（小節）
                    heading.line_number <= figure.line_number):
                    return heading.number
        except (AttributeError, TypeError) as e:
            print(f"警告: 図表の小節検索中にエラー: {e}")
        
        # デフォルト値を動的に取得
        return self._get_default_section(headings)
    
    def _get_default_section(self, headings: List[Heading]) -> str:
        """デフォルトの小節番号を取得"""
        for heading in headings:
            if not heading.is_excluded and heading.number and heading.level == 2:
                return heading.number
        return "1.1"  # フォールバック値

    def _process_content_directly(
        self, file_path: str, headings: List[Heading], figures: List[Figure]
    ) -> str:
        """元のファイルを直接処理して図表番号を付与"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 見出しの処理（逆順で実行）
        for heading in reversed(headings):
            if not heading.is_excluded and heading.number:
                # 見出しの行を置換（元のテキストを使用）
                old_pattern = f"{'#' * heading.level} {heading.raw_text}"
                new_pattern = f"{'#' * heading.level} {heading.number}. {heading.raw_text}"
                content = content.replace(old_pattern, new_pattern, 1)  # 1回だけ置換

        # 図表の処理
        for figure in figures:
            if figure.figure_number > 0:
                if figure.type == "figure":
                    # 画像の処理 - altテキストを更新
                    old_pattern = f"![{figure.caption}]"
                    new_pattern = f"![図{figure.chapter_number}.{figure.figure_number}: {figure.caption}]"
                    content = content.replace(old_pattern, new_pattern)
                    
                    # 画像の後にキャプションラベルを追加（空行を挟む）
                    image_pattern = re.escape(f"![図{figure.chapter_number}.{figure.figure_number}: {figure.caption}]") + r"\([^)]+\)"
                    caption_label = f"**図 {figure.chapter_number}.{figure.figure_number}: {figure.caption}**"
                    replacement = r"\g<0>" + "\n\n" + caption_label
                    content = re.sub(image_pattern, replacement, content)
                elif figure.type == "table":
                    # 表の処理 - コメントをキャプション形式に変換
                    old_pattern = f"<!-- 表: {figure.caption} -->"
                    new_pattern = f"**表{figure.chapter_number}.{figure.figure_number}: {figure.caption}**"
                    content = content.replace(old_pattern, new_pattern)

        return content

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Markdownファイルに章番号と図表番号を付与する"
    )
    parser.add_argument("input_dir", help="入力ディレクトリ")
    parser.add_argument(
        "--config",
        "-c",
        default="config.json",
        help="設定ファイル (デフォルト: config.json)",
    )

    args = parser.parse_args()

    # メイン処理の実行
    core = MarkchapCore(args.config)
    core.process_directory(args.input_dir)


if __name__ == "__main__":
    main()
