#!/usr/bin/env python3
"""
批量清理 HertzBeat YAML 定义文件中的日文（ja-JP）行
"""

import os
import re
import glob

def remove_japanese_lines(file_path):
    """从单个文件中移除所有包含 ja-JP 的行"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除所有包含 ja-JP 的行
        lines = content.split('\n')
        cleaned_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 检查是否包含 ja-JP
            if 'ja-JP:' in line:
                # 跳过这一行
                i += 1
                # 如果下一行是缩进的，也跳过（处理多行内容）
                while i < len(lines) and lines[i].startswith('  '):
                    i += 1
            else:
                cleaned_lines.append(line)
                i += 1
        
        cleaned_content = '\n'.join(cleaned_lines)
        
        # 如果内容有变化，则写入文件
        if cleaned_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"✓ 已清理: {file_path}")
            return True
        else:
            print(f"○ 无需清理: {file_path}")
            return False
            
    except Exception as e:
        print(f"✗ 处理失败: {file_path} - {e}")
        return False

def main():
    """主函数"""
    define_dir = "/Users/peter/Documents/arco/hertzbeat-master/hertzbeat-manager/src/main/resources/define"
    
    if not os.path.exists(define_dir):
        print(f"错误: 目录不存在 - {define_dir}")
        return
    
    # 获取所有 YAML 文件
    yaml_files = glob.glob(os.path.join(define_dir, "*.yml"))
    
    print(f"找到 {len(yaml_files)} 个 YAML 文件")
    print("开始清理日文（ja-JP）行...")
    print("-" * 50)
    
    cleaned_count = 0
    
    for file_path in yaml_files:
        if remove_japanese_lines(file_path):
            cleaned_count += 1
    
    print("-" * 50)
    print(f"清理完成! 共处理了 {len(yaml_files)} 个文件，其中 {cleaned_count} 个文件被清理")

if __name__ == "__main__":
    main()