#!/usr/bin/env python3
"""
改进版：智能清理 HertzBeat YAML 定义文件中的日文（ja-JP）行
避免过度删除，只移除 ja-JP 相关的行
"""

import os
import re
import glob

def remove_japanese_lines_smart(file_path):
    """智能移除日文行，避免过度删除"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        cleaned_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检查是否包含 ja-JP:
            if 'ja-JP:' in line:
                # 只移除这一行，不删除缩进内容
                i += 1
                # 检查下一行是否也是 ja-JP 相关（处理多行 ja-JP 内容）
                while i < len(lines) and lines[i].strip().startswith('ja-JP:'):
                    i += 1
            else:
                cleaned_lines.append(line)
                i += 1
        
        # 再次处理，移除空的 ja-JP 块
        final_lines = []
        i = 0
        
        while i < len(cleaned_lines):
            line = cleaned_lines[i]
            
            # 检查是否是 i18n 块中的 ja-JP 行
            if 'i18n:' in line and i + 1 < len(cleaned_lines):
                # 检查接下来的几行
                j = i + 1
                ja_jp_found = False
                other_langs_found = False
                
                while j < len(cleaned_lines) and cleaned_lines[j].startswith('  '):
                    if 'ja-JP:' in cleaned_lines[j]:
                        ja_jp_found = True
                    elif 'zh-CN:' in cleaned_lines[j] or 'en-US:' in cleaned_lines[j] or 'zh-TW:' in cleaned_lines[j]:
                        other_langs_found = True
                    j += 1
                
                # 如果只有 ja-JP 没有其他语言，保留结构
                if ja_jp_found and other_langs_found:
                    # 正常处理，保留 i18n 块
                    final_lines.append(line)
                    i += 1
                else:
                    # 跳过这个块
                    i = j
            else:
                final_lines.append(line)
                i += 1
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(final_lines)
        
        print(f"✓ 已清理: {file_path}")
        return True
            
    except Exception as e:
        print(f"✗ 处理失败: {file_path} - {e}")
        return False

def remove_japanese_lines_yaml_aware(file_path):
    """YAML 结构感知的日文行移除"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式智能移除 ja-JP 行
        # 模式1：移除单独的 ja-JP 行
        pattern1 = r'\s+ja-JP:.*\n'
        cleaned_content = re.sub(pattern1, '', content)
        
        # 模式2：移除 i18n 块中的 ja-JP 行
        pattern2 = r'(\s+i18n:\s*\n)(\s+zh-CN:.*\n)?(\s+en-US:.*\n)?(\s+zh-TW:.*\n)?(\s+ja-JP:.*\n)?'
        
        def replace_i18n_block(match):
            # 重建 i18n 块，排除 ja-JP
            lines = []
            if match.group(2):  # zh-CN
                lines.append(match.group(2))
            if match.group(3):  # en-US
                lines.append(match.group(3))
            if match.group(4):  # zh-TW
                lines.append(match.group(4))
            # 跳过 ja-JP (match.group(5))
            
            if lines:
                return match.group(1) + ''.join(lines)
            else:
                return match.group(1)
        
        cleaned_content = re.sub(pattern2, replace_i18n_block, cleaned_content)
        
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
    print("开始智能清理日文（ja-JP）行...")
    print("-" * 50)
    
    cleaned_count = 0
    
    for file_path in yaml_files:
        if remove_japanese_lines_yaml_aware(file_path):
            cleaned_count += 1
    
    print("-" * 50)
    print(f"清理完成! 共处理了 {len(yaml_files)} 个文件，其中 {cleaned_count} 个文件被清理")

if __name__ == "__main__":
    main()