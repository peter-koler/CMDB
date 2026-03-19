#!/usr/bin/env python3
"""
最终版：精确清理 HertzBeat YAML 定义文件中的日文（ja-JP）行
使用精确的 YAML 结构处理，避免格式问题
"""

import os
import re
import glob

def remove_japanese_lines_precise(file_path):
    """精确移除日文行，保持 YAML 结构完整"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        cleaned_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检查是否包含 ja-JP:
            if 'ja-JP:' in line:
                # 只移除这一行，保留其他内容
                i += 1
                continue
            
            # 检查是否是 i18n 块中的 ja-JP 行
            if 'i18n:' in line and i + 1 < len(lines):
                # 处理 i18n 块
                i18n_lines = [line]  # 保留 i18n: 行
                j = i + 1
                
                # 收集 i18n 块中的所有行
                while j < len(lines) and lines[j].startswith('  '):
                    if 'ja-JP:' not in lines[j]:  # 跳过 ja-JP 行
                        i18n_lines.append(lines[j])
                    j += 1
                
                # 如果 i18n 块中还有其他语言，保留整个块
                if len(i18n_lines) > 1:
                    cleaned_lines.extend(i18n_lines)
                else:
                    # 如果只有 i18n: 没有其他语言，跳过这个块
                    pass
                
                i = j
            else:
                cleaned_lines.append(line)
                i += 1
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
        
        print(f"✓ 已清理: {file_path}")
        return True
            
    except Exception as e:
        print(f"✗ 处理失败: {file_path} - {e}")
        return False

def remove_japanese_lines_simple(file_path):
    """简单但精确的日文行移除"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用精确的正则表达式模式
        # 模式1：移除单独的 ja-JP 行（保持缩进结构）
        pattern1 = r'^\s*ja-JP:.*$\n'
        cleaned_content = re.sub(pattern1, '', content, flags=re.MULTILINE)
        
        # 模式2：处理 i18n 块中的 ja-JP 行
        # 匹配 i18n 块，然后移除其中的 ja-JP 行
        pattern2 = r'(^\s+i18n:\s*$)((?:\n\s+[^\s].*)*)'
        
        def process_i18n_block(match):
            i18n_header = match.group(1)
            i18n_content = match.group(2)
            
            # 移除 i18n 内容中的 ja-JP 行
            cleaned_i18n_content = re.sub(r'\n\s+ja-JP:.*', '', i18n_content)
            
            return i18n_header + cleaned_i18n_content
        
        cleaned_content = re.sub(pattern2, process_i18n_block, cleaned_content, flags=re.MULTILINE)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"✓ 已清理: {file_path}")
        return True
            
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
    print("开始精确清理日文（ja-JP）行...")
    print("-" * 50)
    
    cleaned_count = 0
    
    for file_path in yaml_files:
        if remove_japanese_lines_simple(file_path):
            cleaned_count += 1
    
    print("-" * 50)
    print(f"清理完成! 共处理了 {len(yaml_files)} 个文件，其中 {cleaned_count} 个文件被清理")

if __name__ == "__main__":
    main()