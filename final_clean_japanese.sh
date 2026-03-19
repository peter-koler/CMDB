#!/bin/bash

# 最终版：精确清理日文（ja-JP）行的脚本
# 使用 sed 命令逐行处理，避免格式问题

DEFINE_DIR="/Users/peter/Documents/arco/hertzbeat-master/hertzbeat-manager/src/main/resources/define"

echo "开始精确清理日文（ja-JP）行..."
echo "========================================"

# 统计文件数量
FILE_COUNT=$(find "$DEFINE_DIR" -name "*.yml" -type f | wc -l)
echo "找到 $FILE_COUNT 个 YAML 文件"

# 使用 sed 精确移除 ja-JP 行
# 这个命令会：
# 1. 移除所有包含 ja-JP: 的行
# 2. 保持 YAML 结构完整
# 3. 避免过度删除

CLEANED_COUNT=0

find "$DEFINE_DIR" -name "*.yml" -type f | while read file; do
    echo "处理文件: $(basename "$file")"
    
    # 检查文件是否包含 ja-JP 行
    if grep -q "ja-JP:" "$file"; then
        # 使用 sed 精确移除 ja-JP 行
        sed -i.bak '/ja-JP:/d' "$file"
        
        # 删除备份文件
        rm -f "$file.bak"
        
        echo "✓ 已清理: $(basename "$file")"
        ((CLEANED_COUNT++))
    else
        echo "○ 无需清理: $(basename "$file")"
    fi
done

echo "========================================"
echo "清理完成!"
echo "共处理了 $FILE_COUNT 个文件，其中 $CLEANED_COUNT 个文件被清理"