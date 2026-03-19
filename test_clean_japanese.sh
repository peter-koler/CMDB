#!/bin/bash

# 测试脚本：对比 app-s7.yml 清理前后的差异

DEFINE_DIR="/Users/peter/Documents/arco/hertzbeat-master/hertzbeat-manager/src/main/resources/define"
BACKUP_FILE="$DEFINE_DIR/app-s7 3.yml"
TARGET_FILE="$DEFINE_DIR/app-s7.yml"

echo "========================================"
echo "测试日文行清理脚本"
echo "========================================"

# 检查文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在 - $BACKUP_FILE"
    exit 1
fi

if [ ! -f "$TARGET_FILE" ]; then
    echo "错误: 目标文件不存在 - $TARGET_FILE"
    exit 1
fi

echo "1. 备份文件内容检查（包含日文）:"
echo "----------------------------------------"
grep -n "ja-JP:" "$BACKUP_FILE" | head -10
echo ""

echo "2. 当前文件内容检查:"
echo "----------------------------------------"
grep -n "ja-JP:" "$TARGET_FILE" | head -10
echo ""

echo "3. 文件差异对比:"
echo "----------------------------------------"

# 创建临时文件用于对比
TEMP_BACKUP="/tmp/app-s7-backup.txt"
TEMP_CURRENT="/tmp/app-s7-current.txt"

# 提取关键内容进行对比
grep -v "^#" "$BACKUP_FILE" | grep -v "^$" > "$TEMP_BACKUP"
grep -v "^#" "$TARGET_FILE" | grep -v "^$" > "$TEMP_CURRENT"

echo "备份文件行数: $(wc -l < "$TEMP_BACKUP")"
echo "当前文件行数: $(wc -l < "$TEMP_CURRENT")"
echo ""

echo "4. 关键差异:"
echo "----------------------------------------"

# 对比 name 块
echo "名称块对比:"
echo "备份文件:"
grep -A 5 "name:" "$BACKUP_FILE" | head -6
echo ""
echo "当前文件:"
grep -A 5 "name:" "$TARGET_FILE" | head -6
echo ""

# 对比 help 块
echo "帮助块对比:"
echo "备份文件:"
grep -A 5 "help:" "$BACKUP_FILE" | head -6
echo ""
echo "当前文件:"
grep -A 5 "help:" "$TARGET_FILE" | head -6
echo ""

# 对比参数块
echo "参数块对比:"
echo "备份文件参数数量:"
grep -c "- field:" "$BACKUP_FILE"
echo "当前文件参数数量:"
grep -c "- field:" "$TARGET_FILE"
echo ""

echo "5. 清理效果验证:"
echo "----------------------------------------"

# 检查日文行是否被正确清理
JA_JP_COUNT_BACKUP=$(grep -c "ja-JP:" "$BACKUP_FILE")
JA_JP_COUNT_CURRENT=$(grep -c "ja-JP:" "$TARGET_FILE")

echo "备份文件日文行数量: $JA_JP_COUNT_BACKUP"
echo "当前文件日文行数量: $JA_JP_COUNT_CURRENT"

if [ "$JA_JP_COUNT_CURRENT" -eq 0 ]; then
    echo "✅ 日文行清理成功!"
else
    echo "❌ 日文行清理失败!"
fi

echo ""
echo "6. 文件完整性检查:"
echo "----------------------------------------"

# 检查重要配置是否完整
IMPORTANT_SECTIONS=("category:" "app:" "name:" "help:" "params:" "metrics:")

for section in "${IMPORTANT_SECTIONS[@]}"; do
    backup_has=$(grep -q "$section" "$BACKUP_FILE" && echo "✅" || echo "❌")
    current_has=$(grep -q "$section" "$TARGET_FILE" && echo "✅" || echo "❌")
    echo "$section: 备份文件 $backup_has | 当前文件 $current_has"
done

echo ""
echo "========================================"
echo "测试完成!"
echo "========================================"

# 清理临时文件
rm -f "$TEMP_BACKUP" "$TEMP_CURRENT"