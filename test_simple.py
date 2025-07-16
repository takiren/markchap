#!/usr/bin/env python3
"""
簡単なテストケース
"""

import os
import tempfile
import shutil
from markchap import MarkchapCore

def test_simple_case():
    """簡単なテストケース"""
    
    # テストディレクトリを作成
    test_dir = tempfile.mkdtemp()
    print(f"テストディレクトリ: {test_dir}")
    
    try:
        # テスト用markdownファイルを作成
        test_content = """# 第1章

## 節1

### 小節1

![テスト画像](test.png)

<!-- 表: テスト表 -->
| 項目 | 値 |
|------|---|
| a    | 1 |

## 節2

### 小節1

![テスト画像2](test2.png)
"""
        
        test_file = os.path.join(test_dir, "test.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)
        
        # 現在のディレクトリを保存
        current_dir = os.getcwd()
        
        try:
            # テストディレクトリに移動
            os.chdir(test_dir)
            
            # markchapを実行
            core = MarkchapCore()
            core.process_directory(".")
            
            # 出力ファイルを確認
            output_file = os.path.join("mdbuild", "test.md")
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    result = f.read()
                
                print("=== 出力結果 ===")
                print(result)
                
                # 期待される結果をチェック
                expected_results = [
                    "# 1. 第1章",
                    "## 1.1. 節1",
                    "### 1.1.1. 小節1",
                    "![図1.1.1: テスト画像](test.png)",
                    "<!-- 表1.1.1: テスト表 -->",
                    "## 1.2. 節2",
                    "### 1.2.1. 小節1",
                    "![図1.2.1: テスト画像2](test2.png)"
                ]
                
                success = True
                for expected in expected_results:
                    if expected in result:
                        print(f"✓ 正しく処理されました: {expected}")
                    else:
                        print(f"✗ 処理が失敗しました: {expected}")
                        success = False
                
                if success:
                    print("\n✓ すべてのテストが成功しました！")
                else:
                    print("\n✗ 一部のテストが失敗しました。")
                
            else:
                print(f"✗ 出力ファイルが見つかりません: {output_file}")
                
        finally:
            # 元のディレクトリに戻る
            os.chdir(current_dir)
            
    finally:
        # テストディレクトリを削除
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_simple_case()