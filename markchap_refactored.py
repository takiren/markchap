#!/usr/bin/env python3
"""
markchap - Markdownファイルに章番号と図表番号を付与するツール (リファクタリング版)
"""

import os
import json
import argparse
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Protocol, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from markdown_it import MarkdownIt


# カスタム例外クラス
class MarkchapError(Exception):
    """markchap基底例外クラス"""
    pass


class ConfigError(MarkchapError):
    """設定関連エラー"""
    pass


class ParsingError(MarkchapError):
    """解析関連エラー"""
    pass


class ValidationError(MarkchapError):
    """検証関連エラー"""
    pass


# ログ設定
class MarkchapLogger:
    """markchap専用ログ管理"""
    
    @staticmethod
    def setup_logger(name: str = "markchap", level: int = logging.INFO) -> logging.Logger:
        """ログの設定"""
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(level)
        return logger


# データクラス（改善版）
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

    def __post_init__(self):
        if self.level < 1 or self.level > 6:
            raise ValidationError(f"見出しレベルは1-6である必要があります: {self.level}")


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

    def __post_init__(self):
        if self.type not in ['figure', 'table']:
            raise ValidationError(f"図表タイプは'figure'または'table'である必要があります: {self.type}")


@dataclass
class NumberState:
    """番号管理状態"""
    current_numbers: List[int]
    figure_count: int = 0
    table_count: int = 0
    global_file_count: int = 0


# TokenRenderer クラス
class TokenRenderer:
    """Markdownトークンからテキストへの変換を担当"""
    
    def __init__(self):
        self.logger = MarkchapLogger.setup_logger(f"{__name__}.TokenRenderer")
    
    def render(self, tokens: List[Any]) -> str:
        """トークンリストをMarkdownテキストに変換"""
        try:
            result = []
            i = 0
            while i < len(tokens):
                token = tokens[i]
                rendered, next_index = self._render_token(token, tokens, i)
                if rendered is not None:
                    result.append(rendered)
                i = next_index
            
            return '\n'.join(result)
        except Exception as e:
            raise ParsingError(f"トークンレンダリングに失敗: {e}")
    
    def _render_token(self, token: Any, tokens: List[Any], index: int) -> tuple[Optional[str], int]:
        """単一トークンのレンダリング"""
        if token.type == 'heading_open':
            return self._render_heading(token, tokens, index)
        elif token.type == 'paragraph_open':
            return None, index + 1
        elif token.type == 'paragraph_close':
            return "", index + 1
        elif token.type == 'inline':
            return self._render_inline(token), index + 1
        elif token.type == 'image':
            return self._render_image(token), index + 1
        elif token.type in ['code_block', 'fence']:
            return self._render_code_block(token), index + 1
        elif token.type == 'html_inline':
            return token.content, index + 1
        elif token.type == 'html_block':
            return token.content.rstrip(), index + 1
        elif token.type in self._get_table_token_types():
            return None, index + 1  # テーブル要素はスキップ
        else:
            return None, index + 1
    
    def _render_heading(self, token: Any, tokens: List[Any], index: int) -> tuple[str, int]:
        """見出しのレンダリング"""
        level = int(token.tag[1])
        prefix = '#' * level
        
        # 次のトークンが見出しテキスト
        if index + 1 < len(tokens) and tokens[index + 1].type == 'inline':
            text = tokens[index + 1].content
            result = f"{prefix} {text}"
            
            # heading_open, inline, heading_close をスキップ
            next_index = index + 2
            if next_index < len(tokens) and tokens[next_index].type == 'heading_close':
                next_index += 1
            return result, next_index
        else:
            return f"{prefix} ", index + 1
    
    def _render_inline(self, token: Any) -> str:
        """インライン要素のレンダリング"""
        if not token.children:
            return token.content if token.content else ""
        
        line_parts = []
        for child in token.children:
            if child.type == 'text':
                line_parts.append(child.content)
            elif child.type == 'image':
                alt = child.attrGet('alt') or ''
                src = child.attrGet('src') or ''
                line_parts.append(f"![{alt}]({src})")
            elif child.type == 'code_inline':
                line_parts.append(f"`{child.content}`")
            elif child.type == 'strong_open':
                line_parts.append("**")
            elif child.type == 'strong_close':
                line_parts.append("**")
            elif child.type == 'em_open':
                line_parts.append("*")
            elif child.type == 'em_close':
                line_parts.append("*")
            elif child.type == 'link_open':
                href = child.attrGet('href') or ''
                line_parts.append(f"[")
            elif child.type == 'link_close':
                # リンクのhrefは後で処理
                line_parts.append(f"]")
        
        return ''.join(line_parts)
    
    def _render_image(self, token: Any) -> str:
        """画像のレンダリング"""
        alt = token.attrGet('alt') or ''
        src = token.attrGet('src') or ''
        return f"![{alt}]({src})"
    
    def _render_code_block(self, token: Any) -> str:
        """コードブロックのレンダリング"""
        lang = token.info or ''
        content = token.content.rstrip()
        return f"```{lang}\n{content}\n```\n"
    
    def _get_table_token_types(self) -> List[str]:
        """テーブル関連のトークンタイプ一覧"""
        return [
            'table_open', 'table_close', 'thead_open', 'thead_close',
            'tbody_open', 'tbody_close', 'tr_open', 'tr_close',
            'th_open', 'th_close', 'td_open', 'td_close'
        ]


# FigureProcessor クラス
class FigureProcessor:
    """図表処理専用クラス"""
    
    def __init__(self, config: 'ConfigManager'):
        self.config = config
        self.logger = MarkchapLogger.setup_logger(f"{__name__}.FigureProcessor")
    
    def extract_figures(self, tokens: List[Any]) -> List[Figure]:
        """トークンから図表を抽出"""
        figures = []
        
        for i, token in enumerate(tokens):
            try:
                # 画像の検出
                if token.type == 'image':
                    figure = self._extract_image_figure(token, i)
                    figures.append(figure)
                
                # 表の検出（HTMLコメント）
                elif token.type == 'html_inline' and '<!-- 表' in token.content:
                    figure = self._extract_table_figure(token, i)
                    if figure:
                        figures.append(figure)
                        
            except Exception as e:
                self.logger.warning(f"図表抽出でエラー（トークン{i}）: {e}")
        
        return figures
    
    def _extract_image_figure(self, token: Any, index: int) -> Figure:
        """画像図表の抽出"""
        caption = token.attrGet('alt') or ''
        return Figure(
            type='figure',
            original_text=token.content,
            caption=caption,
            token_index=index,
            line_number=token.map[0] if token.map else 0
        )
    
    def _extract_table_figure(self, token: Any, index: int) -> Optional[Figure]:
        """表図表の抽出"""
        match = re.search(r'<!--\s*表\s*:\s*([^>]+)\s*-->', token.content)
        if match:
            caption = match.group(1).strip()
            return Figure(
                type='table',
                original_text=token.content,
                caption=caption,
                token_index=index,
                line_number=token.map[0] if token.map else 0
            )
        return None
    
    def assign_numbers(self, figures: List[Figure], headings: List[Heading], state: NumberState) -> None:
        """図表に番号を付与"""
        current_heading_index = 0
        
        for figure in figures:
            try:
                # 図表の位置から対応する見出しを見つける
                while (current_heading_index < len(headings) - 1 and 
                       headings[current_heading_index + 1].line_number <= figure.line_number):
                    current_heading_index += 1
                
                # 対応する見出しの章番号を使用
                current_chapter = "1"
                if current_heading_index < len(headings):
                    current_chapter = headings[current_heading_index].number or "1"
                
                # 図表番号の付与
                if figure.type == 'figure':
                    state.figure_count += 1
                    figure.figure_number = state.figure_count
                elif figure.type == 'table':
                    state.table_count += 1
                    figure.figure_number = state.table_count
                
                figure.chapter_number = current_chapter
                
            except Exception as e:
                self.logger.warning(f"図表番号付与でエラー: {e}")
    
    def update_tokens(self, tokens: List[Any], figures: List[Figure]) -> None:
        """トークンに図表番号を反映"""
        for figure in figures:
            try:
                if figure.figure_number > 0 and figure.token_index < len(tokens):
                    token = tokens[figure.token_index]
                    
                    if figure.type == 'figure':
                        self._update_image_token(token, figure)
                    elif figure.type == 'table':
                        self._update_table_token(token, figure)
                        
            except Exception as e:
                self.logger.warning(f"図表トークン更新でエラー: {e}")
    
    def _update_image_token(self, token: Any, figure: Figure) -> None:
        """画像トークンの更新"""
        new_alt = f"図{figure.chapter_number}.{figure.figure_number}: {figure.caption}"
        
        # 画像トークンの場合、childrenを確認
        if hasattr(token, 'children') and token.children:
            for child in token.children:
                if child.type == 'image':
                    child.attrSet('alt', new_alt)
        elif token.type == 'image':
            token.attrSet('alt', new_alt)
    
    def _update_table_token(self, token: Any, figure: Figure) -> None:
        """表トークンの更新"""
        token.content = f"<!-- 表{figure.chapter_number}.{figure.figure_number}: {figure.caption} -->"


# ValidationManager クラス
class ValidationManager:
    """入力検証専用クラス"""
    
    def __init__(self):
        self.logger = MarkchapLogger.setup_logger(f"{__name__}.ValidationManager")
    
    def validate_input_directory(self, input_dir: str) -> None:
        """入力ディレクトリの検証"""
        if not input_dir:
            raise ValidationError("入力ディレクトリが指定されていません")
        
        if not os.path.exists(input_dir):
            raise ValidationError(f"入力ディレクトリが存在しません: {input_dir}")
        
        if not os.path.isdir(input_dir):
            raise ValidationError(f"指定されたパスはディレクトリではありません: {input_dir}")
    
    def validate_config_file(self, config_path: str) -> None:
        """設定ファイルの検証"""
        if not config_path:
            return  # デフォルト設定を使用
        
        if not os.path.exists(config_path):
            raise ValidationError(f"設定ファイルが存在しません: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            raise ValidationError(f"設定ファイルのJSON形式が不正です: {e}")
    
    def validate_markdown_files(self, md_files: List[str]) -> None:
        """Markdownファイルリストの検証"""
        if not md_files:
            raise ValidationError("処理対象のMarkdownファイルが見つかりません")
        
        for file_path in md_files:
            if not os.path.exists(file_path):
                raise ValidationError(f"Markdownファイルが存在しません: {file_path}")


# 改善されたConfigManager
class ConfigManager:
    """設定ファイルの管理（改善版）"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.logger = MarkchapLogger.setup_logger(f"{__name__}.ConfigManager")
        self.validator = ValidationManager()
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        try:
            # ファイルが存在しない場合はデフォルト設定を使用
            if not os.path.exists(self.config_path):
                self.logger.info(f"設定ファイル {self.config_path} が見つかりません。デフォルト設定を使用します。")
                return self._get_default_config()
            
            # ファイルが存在する場合は検証してから読み込み
            self.validator.validate_config_file(self.config_path)
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.logger.info(f"設定ファイルを読み込みました: {self.config_path}")
                return config
                
        except ValidationError:
            raise
        except Exception as e:
            raise ConfigError(f"設定ファイルの読み込みに失敗: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を返す"""
        return {
            "excluded_headings": [
                "はじめに", "参考文献", "謝辞", "付録", "索引", 
                "目次", "あとがき", "概要", "まとめ"
            ],
            "number_formats": {
                "chapter": "{}",
                "figure": "図{}",
                "table": "表{}"
            },
            "output_directory": "mdbuild",
            "preserve_existing_numbers": True
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.config.get(key, default)


# 改善されたMarkdownParser
class MarkdownParser:
    """Markdownパーサー（改善版）"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.md = MarkdownIt()
        self.figure_processor = FigureProcessor(config)
        self.logger = MarkchapLogger.setup_logger(f"{__name__}.MarkdownParser")
    
    def parse_file(self, file_path: str) -> tuple[List[Heading], List[Figure], List[Any]]:
        """ファイルを解析して見出し・図表・トークンを抽出"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tokens = self.md.parse(content)
            headings = self._extract_headings(tokens)
            figures = self.figure_processor.extract_figures(tokens)
            
            self.logger.debug(f"ファイル解析完了: {file_path} (見出し: {len(headings)}, 図表: {len(figures)})")
            return headings, figures, tokens
            
        except Exception as e:
            raise ParsingError(f"ファイル解析に失敗 {file_path}: {e}")
    
    def _extract_headings(self, tokens: List[Any]) -> List[Heading]:
        """ASTトークンから見出しを抽出（改善版）"""
        headings = []
        excluded_headings = self.config.get("excluded_headings", [])
        
        for i, token in enumerate(tokens):
            try:
                if token.type == 'heading_open':
                    heading = self._create_heading_from_token(token, tokens, i, excluded_headings)
                    if heading:
                        headings.append(heading)
            except Exception as e:
                self.logger.warning(f"見出し抽出でエラー（トークン{i}）: {e}")
        
        return headings
    
    def _create_heading_from_token(self, token: Any, tokens: List[Any], index: int, excluded_headings: List[str]) -> Optional[Heading]:
        """トークンから見出しオブジェクトを作成"""
        level = int(token.tag[1])  # h1 -> 1, h2 -> 2
        
        # 次のトークンが見出しテキスト
        if index + 1 < len(tokens) and tokens[index + 1].type == 'inline':
            text_token = tokens[index + 1]
            text = text_token.content.strip()
            
            # 除外見出しの判定
            is_excluded = any(excluded in text for excluded in excluded_headings)
            
            return Heading(
                level=level,
                text=text,
                raw_text=text,
                token_index=index,
                line_number=token.map[0] if token.map else 0,
                is_excluded=is_excluded
            )
        return None
    
    def render_tokens(self, tokens: List[Any]) -> str:
        """トークンからMarkdownテキストを生成（TokenRendererに委譲）"""
        renderer = TokenRenderer()
        return renderer.render(tokens)


# 改善されたNumberingManager
class NumberingManager:
    """番号付与の管理（改善版）"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.state = NumberState(current_numbers=[])
        self.logger = MarkchapLogger.setup_logger(f"{__name__}.NumberingManager")
    
    def process_headings(self, headings: List[Heading]) -> None:
        """見出しに章番号を付与"""
        for heading in headings:
            try:
                if heading.is_excluded:
                    self.logger.debug(f"見出しを除外: {heading.text}")
                    continue
                
                self._assign_chapter_number(heading)
                self._reset_figure_numbers_if_needed(heading.level)
                
            except Exception as e:
                self.logger.error(f"見出し番号付与でエラー: {heading.text}, {e}")
    
    def _assign_chapter_number(self, heading: Heading) -> None:
        """見出しに章番号を割り当て"""
        level = heading.level
        
        # 現在の番号リストを調整
        self._adjust_number_list(level)
        
        # 現在のレベルの番号を増加
        self.state.current_numbers[level - 1] += 1
        
        # それより深いレベルをリセット
        self._reset_deeper_levels(level)
        
        # 番号文字列を生成
        heading.number = self._generate_number_string(level)
        
        self.logger.debug(f"章番号付与: {heading.number} - {heading.text}")
    
    def _adjust_number_list(self, level: int) -> None:
        """番号リストをレベルに合わせて調整"""
        if len(self.state.current_numbers) < level:
            # レベルが深くなった場合、新しいレベルを追加
            self.state.current_numbers.extend([0] * (level - len(self.state.current_numbers)))
        elif len(self.state.current_numbers) > level:
            # レベルが浅くなった場合、余分なレベルを削除
            self.state.current_numbers = self.state.current_numbers[:level]
    
    def _reset_deeper_levels(self, level: int) -> None:
        """指定レベルより深いレベルをリセット"""
        for i in range(level, len(self.state.current_numbers)):
            self.state.current_numbers[i] = 0
    
    def _generate_number_string(self, level: int) -> str:
        """番号文字列を生成"""
        number_parts = [str(num) for num in self.state.current_numbers[:level] if num > 0]
        return '.'.join(number_parts)
    
    def _reset_figure_numbers_if_needed(self, level: int) -> None:
        """章が変わった場合に図表番号をリセット"""
        if level == 1:
            self.state.figure_count = 0
            self.state.table_count = 0
            self.logger.debug("図表番号をリセット")
    
    def get_current_chapter(self) -> str:
        """現在の章番号を取得"""
        if not self.state.current_numbers:
            return "1"
        
        number_parts = [str(num) for num in self.state.current_numbers if num > 0]
        return '.'.join(number_parts) if number_parts else "1"


# 改善されたFileProcessor
class FileProcessor:
    """ファイル操作の管理（改善版）"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.output_dir = config.get("output_directory", "mdbuild")
        self.validator = ValidationManager()
        self.logger = MarkchapLogger.setup_logger(f"{__name__}.FileProcessor")
    
    def get_markdown_files(self, input_dir: str) -> List[str]:
        """指定ディレクトリからMarkdownファイルを取得（辞書順）"""
        try:
            self.validator.validate_input_directory(input_dir)
            
            md_files = []
            for root, dirs, files in os.walk(input_dir):
                for file in sorted(files):
                    if self._is_markdown_file(file):
                        md_files.append(os.path.join(root, file))
            
            md_files = sorted(md_files)
            self.validator.validate_markdown_files(md_files)
            
            self.logger.info(f"Markdownファイル {len(md_files)} 件を検出")
            return md_files
            
        except Exception as e:
            raise ValidationError(f"Markdownファイルの取得に失敗: {e}")
    
    def _is_markdown_file(self, filename: str) -> bool:
        """Markdownファイルかどうかを判定"""
        return filename.lower().endswith(('.md', '.markdown'))
    
    def prepare_output_directory(self, input_dir: str) -> None:
        """出力ディレクトリの準備"""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                self.logger.info(f"出力ディレクトリを作成: {self.output_dir}")
            
            # 入力ディレクトリの構造を再現
            self._recreate_directory_structure(input_dir)
            
        except Exception as e:
            raise ValidationError(f"出力ディレクトリの準備に失敗: {e}")
    
    def _recreate_directory_structure(self, input_dir: str) -> None:
        """ディレクトリ構造を再現"""
        for root, dirs, files in os.walk(input_dir):
            for dir_name in dirs:
                input_path = os.path.join(root, dir_name)
                relative_path = os.path.relpath(input_path, input_dir)
                output_path = os.path.join(self.output_dir, relative_path)
                
                if not os.path.exists(output_path):
                    os.makedirs(output_path)
                    self.logger.debug(f"ディレクトリ作成: {output_path}")
    
    def write_output_file(self, input_file: str, input_dir: str, content: str) -> None:
        """出力ファイルの書き込み"""
        try:
            relative_path = os.path.relpath(input_file, input_dir)
            output_file = os.path.join(self.output_dir, relative_path)
            
            # ディレクトリが存在しない場合は作成
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.debug(f"ファイル出力完了: {output_file}")
            
        except Exception as e:
            raise ValidationError(f"ファイル書き込みに失敗 {input_file}: {e}")


# 改善されたMarkchapCore
class MarkchapCore:
    """メイン処理の制御（改善版）"""
    
    def __init__(self, config_path: str = "config.json"):
        try:
            self.config = ConfigManager(config_path)
            self.parser = MarkdownParser(self.config)
            self.numbering = NumberingManager(self.config)
            self.file_processor = FileProcessor(self.config)
            self.figure_processor = FigureProcessor(self.config)
            self.logger = MarkchapLogger.setup_logger(f"{__name__}.MarkchapCore")
            
        except Exception as e:
            raise ConfigError(f"markchapの初期化に失敗: {e}")
    
    def process_directory(self, input_dir: str) -> None:
        """ディレクトリ全体を処理"""
        try:
            self.logger.info(f"処理開始: {input_dir}")
            
            # Markdownファイルの取得
            md_files = self.file_processor.get_markdown_files(input_dir)
            self.logger.info(f"処理対象ファイル数: {len(md_files)}")
            
            # 出力ディレクトリの準備
            self.file_processor.prepare_output_directory(input_dir)
            
            # 各ファイルの処理
            success_count = 0
            error_count = 0
            
            for file_path in md_files:
                try:
                    self.logger.info(f"処理中: {file_path}")
                    self.process_file(file_path, input_dir)
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"ファイル処理エラー {file_path}: {e}")
                    error_count += 1
            
            self.logger.info(f"処理完了 - 成功: {success_count}, エラー: {error_count}")
            self.logger.info(f"結果は '{self.file_processor.output_dir}' ディレクトリに保存されました")
            
        except Exception as e:
            self.logger.error(f"ディレクトリ処理に失敗: {e}")
            raise
    
    def process_file(self, file_path: str, input_dir: str) -> None:
        """単一ファイルの処理"""
        try:
            # ファイルの解析
            headings, figures, tokens = self.parser.parse_file(file_path)
            
            # 章番号の付与
            self.numbering.process_headings(headings)
            
            # 図表番号の付与
            self.figure_processor.assign_numbers(figures, headings, self.numbering.state)
            
            # トークンの更新
            self._update_tokens(tokens, headings, figures)
            
            # Markdownの再生成
            content = self.parser.render_tokens(tokens)
            
            # 出力ファイルの書き込み
            self.file_processor.write_output_file(file_path, input_dir, content)
            
        except Exception as e:
            raise ParsingError(f"ファイル処理に失敗 {file_path}: {e}")
    
    def _update_tokens(self, tokens: List[Any], headings: List[Heading], figures: List[Figure]) -> None:
        """トークンを更新して番号を付与"""
        try:
            # 見出しの更新
            self._update_heading_tokens(tokens, headings)
            
            # 図表の更新
            self.figure_processor.update_tokens(tokens, figures)
            
        except Exception as e:
            raise ParsingError(f"トークン更新に失敗: {e}")
    
    def _update_heading_tokens(self, tokens: List[Any], headings: List[Heading]) -> None:
        """見出しトークンの更新"""
        for heading in headings:
            try:
                if not heading.is_excluded and heading.number:
                    # 見出しのテキストトークンを更新
                    text_token_index = heading.token_index + 1
                    if (text_token_index < len(tokens) and 
                        tokens[text_token_index].type == 'inline'):
                        tokens[text_token_index].content = f"{heading.number}. {heading.text}"
                        
            except Exception as e:
                self.logger.warning(f"見出しトークン更新でエラー: {heading.text}, {e}")


def main():
    """メイン関数（改善版）"""
    try:
        # ログ設定
        logger = MarkchapLogger.setup_logger()
        
        # コマンドライン引数の解析
        parser = argparse.ArgumentParser(
            description='Markdownファイルに章番号と図表番号を付与する（リファクタリング版）'
        )
        parser.add_argument('input_dir', help='入力ディレクトリ')
        parser.add_argument('--config', '-c', default='config.json', 
                          help='設定ファイル (デフォルト: config.json)')
        parser.add_argument('--verbose', '-v', action='store_true', 
                          help='詳細ログを表示')
        
        args = parser.parse_args()
        
        # ログレベルの設定
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # メイン処理の実行
        core = MarkchapCore(args.config)
        core.process_directory(args.input_dir)
        
    except MarkchapError as e:
        print(f"エラー: {e}")
        exit(1)
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        exit(1)
    except Exception as e:
        print(f"予期しないエラー: {e}")
        exit(1)


if __name__ == "__main__":
    main()