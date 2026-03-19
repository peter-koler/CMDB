#!/bin/bash

# 精确清理日文（ja-JP）行的脚本
# 使用 sed 命令逐行处理，避免格式问题

DEFINE_DIR="/Users/peter/Documents/arco/hertzbeat-master/hertzbeat-manager/src/main/resources/define"

echo "开始精确清理日文（ja-JP）行..."
echo "========================================"

# 使用 sed 命令精确移除包含 ja-JP 的行
# 这个命令会：
# 1. 移除所有包含 ja-JP: 的行
# 2. 保持 YAML 结构完整
# 3. 避免过度删除

find "$DEFINE_DIR" -name "*.yml" -type f | while read file; do
    echo "处理文件: $(basename "$file")"
    
    # 使用 sed 精确移除 ja-JP 行
    # -i.bak 创建备份，然后删除备份文件
    sed -i.bak '/ja-JP:/d' "$file"
    
    # 删除备份文件
    rm -f "$file.bak"
    
    echo "✓ 已清理: $(basename "$file")"
done

echo "========================================"
echo "清理完成!"