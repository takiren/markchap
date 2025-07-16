#!/usr/bin/env python3
"""
markchap ユニットテスト
"""

import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch, mock_open
from typing import List

# テスト対象のインポート
from markchap_refactored import (
    Heading, Figure, NumberState,
    TokenRenderer, FigureProcessor, ValidationManager,
    ConfigManager, NumberingManager, MarkdownParser,
    MarkchapError, ConfigError, ParsingError, ValidationError
)


class TestHeading(unittest.TestCase):
    """Headingデータクラスのテスト"""
    
    def test_valid_heading(self):
        """正常な見出しの作成"""
        heading = Heading(
            level=1,
            text="テスト見出し",
            raw_text="テスト見出し",
            token_index=0,
            line_number=1
        )
        
        self.assertEqual(heading.level, 1)
        self.assertEqual(heading.text, "テスト見出し")
        self.assertFalse(heading.is_excluded)
        self.assertEqual(heading.number, "")
    
    def test_invalid_heading_level(self):
        """無効な見出しレベルのテスト"""
        with self.assertRaises(ValidationError):
            Heading(
                level=7,  # 無効なレベル
                text="テスト",
                raw_text="テスト",
                token_index=0,
                line_number=1
            )


class TestFigure(unittest.TestCase):
    """Figureデータクラスのテスト"""
    
    def test_valid_figure(self):
        """正常な図表の作成"""
        figure = Figure(
            type="figure",
            original_text="![test](image.png)",
            caption="テスト画像",
            token_index=5,
            line_number=10
        )
        
        self.assertEqual(figure.type, "figure")
        self.assertEqual(figure.caption, "テスト画像")
        self.assertEqual(figure.figure_number, 0)
    
    def test_invalid_figure_type(self):
        """無効な図表タイプのテスト"""
        with self.assertRaises(ValidationError):
            Figure(
                type="invalid",  # 無効なタイプ
                original_text="test",
                caption="test",
                token_index=0,
                line_number=1
            )


class TestValidationManager(unittest.TestCase):
    """ValidationManagerのテスト"""
    
    def setUp(self):
        self.validator = ValidationManager()
    
    def test_validate_input_directory_success(self):
        """正常なディレクトリの検証"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 正常ケースでは例外が発生しない
            self.validator.validate_input_directory(tmpdir)
    
    def test_validate_input_directory_not_exists(self):
        """存在しないディレクトリの検証"""
        with self.assertRaises(ValidationError):
            self.validator.validate_input_directory("/nonexistent")
    
    def test_validate_config_file_valid_json(self):
        """正常なJSONファイルの検証"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "value"}, f)
            f.flush()
            
            try:
                self.validator.validate_config_file(f.name)
            finally:
                os.unlink(f.name)
    
    def test_validate_markdown_files_empty(self):
        """空のMarkdownファイルリストの検証"""
        with self.assertRaises(ValidationError):
            self.validator.validate_markdown_files([])


class TestTokenRenderer(unittest.TestCase):
    """TokenRendererのテスト"""
    
    def setUp(self):
        self.renderer = TokenRenderer()
    
    def test_render_empty_tokens(self):
        """空のトークンリストのレンダリング"""
        result = self.renderer.render([])
        self.assertEqual(result, "")
    
    def test_render_heading(self):
        """見出しのレンダリング"""
        # モックトークンを作成
        heading_open = Mock()
        heading_open.type = 'heading_open'
        heading_open.tag = 'h1'
        
        inline = Mock()
        inline.type = 'inline'
        inline.content = "テスト見出し"
        inline.children = None
        
        heading_close = Mock()
        heading_close.type = 'heading_close'
        
        tokens = [heading_open, inline, heading_close]
        result = self.renderer.render(tokens)
        
        self.assertEqual(result, "# テスト見出し")
    
    def test_render_image(self):
        """画像のレンダリング"""
        image_token = Mock()
        image_token.type = 'image'
        image_token.attrGet = Mock(side_effect=lambda key: {
            'alt': 'テスト画像',
            'src': 'test.png'
        }.get(key, ''))
        
        tokens = [image_token]
        result = self.renderer.render(tokens)
        
        self.assertEqual(result, "![テスト画像](test.png)")


class TestNumberingManager(unittest.TestCase):
    """NumberingManagerのテスト"""
    
    def setUp(self):
        self.config = Mock()
        self.numbering = NumberingManager(self.config)
    
    def test_process_single_heading(self):
        """単一見出しの処理"""
        heading = Heading(
            level=1,
            text="テスト",
            raw_text="テスト",
            token_index=0,
            line_number=1
        )
        
        self.numbering.process_headings([heading])
        
        self.assertEqual(heading.number, "1")
        self.assertEqual(self.numbering.state.current_numbers, [1])
    
    def test_process_nested_headings(self):
        """階層的見出しの処理"""
        headings = [
            Heading(1, "章1", "章1", 0, 1),
            Heading(2, "節1.1", "節1.1", 2, 2),
            Heading(2, "節1.2", "節1.2", 4, 3),
            Heading(1, "章2", "章2", 6, 4)
        ]
        
        self.numbering.process_headings(headings)
        
        self.assertEqual(headings[0].number, "1")
        self.assertEqual(headings[1].number, "1.1")
        self.assertEqual(headings[2].number, "1.2")
        self.assertEqual(headings[3].number, "2")
    
    def test_process_excluded_heading(self):
        """除外見出しの処理"""
        heading = Heading(
            level=1,
            text="はじめに",
            raw_text="はじめに",
            token_index=0,
            line_number=1,
            is_excluded=True
        )
        
        self.numbering.process_headings([heading])
        
        self.assertEqual(heading.number, "")  # 番号が付かない
        self.assertEqual(self.numbering.state.current_numbers, [])


class TestFigureProcessor(unittest.TestCase):
    """FigureProcessorのテスト"""
    
    def setUp(self):
        self.config = Mock()
        self.processor = FigureProcessor(self.config)
    
    def test_extract_image_figure(self):
        """画像図表の抽出"""
        token = Mock()
        token.type = 'image'
        token.attrGet = Mock(return_value='テスト画像')
        token.content = 'test content'
        token.map = [5]
        
        tokens = [token]
        figures = self.processor.extract_figures(tokens)
        
        self.assertEqual(len(figures), 1)
        self.assertEqual(figures[0].type, 'figure')
        self.assertEqual(figures[0].caption, 'テスト画像')
    
    def test_extract_table_figure(self):
        """表図表の抽出"""
        token = Mock()
        token.type = 'html_inline'
        token.content = '<!-- 表: テスト表 -->'
        token.map = [10]
        
        tokens = [token]
        figures = self.processor.extract_figures(tokens)
        
        self.assertEqual(len(figures), 1)
        self.assertEqual(figures[0].type, 'table')
        self.assertEqual(figures[0].caption, 'テスト表')
    
    def test_assign_numbers(self):
        """図表番号の付与"""
        # 図表を作成
        figure = Figure("figure", "test", "テスト", 0, 5)
        table = Figure("table", "test", "テスト", 1, 10)
        
        # 見出しを作成
        heading = Heading(1, "章1", "章1", 0, 1)
        heading.number = "1"
        
        # 番号状態を作成
        state = NumberState([1])
        
        self.processor.assign_numbers([figure, table], [heading], state)
        
        self.assertEqual(figure.figure_number, 1)
        self.assertEqual(figure.chapter_number, "1")
        self.assertEqual(table.figure_number, 1)
        self.assertEqual(table.chapter_number, "1")


class TestConfigManager(unittest.TestCase):
    """ConfigManagerのテスト"""
    
    def test_load_default_config(self):
        """デフォルト設定の読み込み"""
        config = ConfigManager("nonexistent_config.json")
        
        # デフォルト設定が読み込まれることを確認
        excluded = config.get("excluded_headings", [])
        self.assertIn("はじめに", excluded)
        self.assertIn("参考文献", excluded)
    
    @patch("builtins.open", mock_open(read_data='{"test_key": "test_value"}'))
    @patch("os.path.exists", return_value=True)
    def test_load_custom_config(self):
        """カスタム設定の読み込み"""
        config = ConfigManager("test_config.json")
        
        self.assertEqual(config.get("test_key"), "test_value")
    
    @patch("builtins.open", mock_open(read_data='invalid json'))
    @patch("os.path.exists", return_value=True)
    def test_load_invalid_json(self):
        """無効なJSONファイルの処理"""
        with self.assertRaises(ValidationError):
            ConfigManager("invalid_config.json")


class TestIntegration(unittest.TestCase):
    """統合テスト"""
    
    def test_end_to_end_simple(self):
        """シンプルなエンドツーエンドテスト"""
        # テスト用の設定
        config = ConfigManager()
        
        # 見出しを作成
        headings = [
            Heading(1, "はじめに", "はじめに", 0, 1, is_excluded=True),
            Heading(1, "章1", "章1", 2, 2),
            Heading(2, "節1.1", "節1.1", 4, 3)
        ]
        
        # 番号付与
        numbering = NumberingManager(config)
        numbering.process_headings(headings)
        
        # 結果の確認
        self.assertEqual(headings[0].number, "")  # 除外
        self.assertEqual(headings[1].number, "1")
        self.assertEqual(headings[2].number, "1.1")


if __name__ == '__main__':
    # ログを無効化（テスト実行時）
    import logging
    logging.disable(logging.CRITICAL)
    
    unittest.main()