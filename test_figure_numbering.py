#!/usr/bin/env python3
"""
図表番号付与のテストケース
"""

import unittest
import tempfile
import os
import shutil
from markchap import MarkchapCore


class TestFigureNumbering(unittest.TestCase):
    """図表番号付与のテスト"""

    def setUp(self):
        """各テストの前に実行"""
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.test_dir, "mdbuild")
        self.config_path = os.path.join(self.test_dir, "config.json")
        
        # テスト用設定ファイルを作成
        config_content = """{
  "excluded_headings": ["はじめに", "参考文献", "まとめ"],
  "number_formats": {
    "chapter": "{}",
    "figure": "図{}",
    "table": "表{}"
  },
  "output_directory": "mdbuild",
  "preserve_existing_numbers": true
}"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(config_content)

    def tearDown(self):
        """各テストの後に実行"""
        shutil.rmtree(self.test_dir)

    def test_basic_figure_numbering(self):
        """基本的な図表番号付与のテスト"""
        # テスト用markdownファイルを作成
        test_content = """# テスト章

## 1.1. 第一節

### 1.1.1. 小節1

![テスト画像1](image1.png)

<!-- 表: テスト表1 -->
| 項目 | 値 |
|------|---|
| a    | 1 |

### 1.1.2. 小節2

![テスト画像2](image2.png)

## 1.2. 第二節

### 1.2.1. 小節1

![テスト画像3](image3.png)

<!-- 表: テスト表2 -->
| 項目 | 値 |
|------|---|
| b    | 2 |
"""
        test_file = os.path.join(self.test_dir, "test.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        # markchapを実行
        current_dir = os.getcwd()
        os.chdir(self.test_dir)  # テストディレクトリに移動
        try:
            core = MarkchapCore(self.config_path)
            core.process_directory(".")
        finally:
            os.chdir(current_dir)  # 元のディレクトリに戻る

        # 出力ファイルを確認
        output_file = os.path.join(self.test_dir, "mdbuild", "test.md")
        self.assertTrue(os.path.exists(output_file), f"出力ファイルが存在しません: {output_file}")

        with open(output_file, "r", encoding="utf-8") as f:
            result = f.read()

        # 図表番号が正しく付与されていることを確認
        self.assertIn("![図1.1.1: テスト画像1](image1.png)", result)
        self.assertIn("<!-- 表1.1.1: テスト表1 -->", result)
        self.assertIn("![図1.1.2: テスト画像2](image2.png)", result)
        self.assertIn("![図1.2.1: テスト画像3](image3.png)", result)
        self.assertIn("<!-- 表1.2.1: テスト表2 -->", result)

    def test_multiple_chapters(self):
        """複数章の図表番号付与のテスト"""
        test_content = """# 第1章

## 1.1. 節1

![画像1](img1.png)

# 第2章

## 2.1. 節1

![画像2](img2.png)

<!-- 表: 表1 -->
| a | b |
|---|---|
| 1 | 2 |

## 2.2. 節2

![画像3](img3.png)
"""
        test_file = os.path.join(self.test_dir, "multi_chapter.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        # markchapを実行
        current_dir = os.getcwd()
        os.chdir(self.test_dir)  # テストディレクトリに移動
        try:
            core = MarkchapCore(self.config_path)
            core.process_directory(".")
        finally:
            os.chdir(current_dir)  # 元のディレクトリに戻る

        # 出力ファイルを確認
        output_file = os.path.join(self.test_dir, "mdbuild", "multi_chapter.md")
        with open(output_file, "r", encoding="utf-8") as f:
            result = f.read()

        # 図表番号が正しく付与されていることを確認
        self.assertIn("![図1.1.1: 画像1](img1.png)", result)
        self.assertIn("![図2.1.1: 画像2](img2.png)", result)
        self.assertIn("<!-- 表2.1.1: 表1 -->", result)
        self.assertIn("![図2.2.1: 画像3](img3.png)", result)

    def test_excluded_headings(self):
        """除外見出しのテスト"""
        test_content = """# はじめに

この章は除外されます。

![除外画像](excluded.png)

# 第1章

## 1.1. 節1

![画像1](img1.png)

# まとめ

この章も除外されます。

![除外画像2](excluded2.png)
"""
        test_file = os.path.join(self.test_dir, "excluded.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        # markchapを実行
        current_dir = os.getcwd()
        os.chdir(self.test_dir)  # テストディレクトリに移動
        try:
            core = MarkchapCore(self.config_path)
            core.process_directory(".")
        finally:
            os.chdir(current_dir)  # 元のディレクトリに戻る

        # 出力ファイルを確認
        output_file = os.path.join(self.test_dir, "mdbuild", "excluded.md")
        with open(output_file, "r", encoding="utf-8") as f:
            result = f.read()

        # 除外見出しには番号が付かないことを確認
        self.assertIn("# はじめに", result)
        self.assertNotIn("# 1. はじめに", result)
        self.assertIn("# まとめ", result)
        self.assertNotIn("# 2. まとめ", result)
        
        # 通常の見出しには番号が付くことを確認
        self.assertIn("# 1. 第1章", result)
        self.assertIn("![図1.1.1: 画像1](img1.png)", result)

    def test_complex_numbering(self):
        """複雑な図表番号付与のテスト"""
        test_content = """# 第1章

## 1.1. 節1

### 1.1.1. 小節1

![画像1](img1.png)
![画像2](img2.png)

<!-- 表: 表1 -->
| a | b |
|---|---|
| 1 | 2 |

### 1.1.2. 小節2

![画像3](img3.png)

<!-- 表: 表2 -->
| c | d |
|---|---|
| 3 | 4 |

<!-- 表: 表3 -->
| e | f |
|---|---|
| 5 | 6 |

## 1.2. 節2

### 1.2.1. 小節1

![画像4](img4.png)
"""
        test_file = os.path.join(self.test_dir, "complex.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        # markchapを実行
        current_dir = os.getcwd()
        os.chdir(self.test_dir)  # テストディレクトリに移動
        try:
            core = MarkchapCore(self.config_path)
            core.process_directory(".")
        finally:
            os.chdir(current_dir)  # 元のディレクトリに戻る

        # 出力ファイルを確認
        output_file = os.path.join(self.test_dir, "mdbuild", "complex.md")
        with open(output_file, "r", encoding="utf-8") as f:
            result = f.read()

        # 図表番号が正しく付与されていることを確認
        self.assertIn("![図1.1.1: 画像1](img1.png)", result)
        self.assertIn("![図1.1.2: 画像2](img2.png)", result)
        self.assertIn("<!-- 表1.1.1: 表1 -->", result)
        self.assertIn("![図1.1.3: 画像3](img3.png)", result)
        self.assertIn("<!-- 表1.1.2: 表2 -->", result)
        self.assertIn("<!-- 表1.1.3: 表3 -->", result)
        self.assertIn("![図1.2.1: 画像4](img4.png)", result)


if __name__ == "__main__":
    unittest.main()