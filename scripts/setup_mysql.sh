#!/bin/bash
# MySQL数据库一键设置脚本（macOS）

echo "=============================="
echo "MySQL数据库设置向导"
echo "=============================="

# 检查MySQL是否安装
if ! command -v mysql &> /dev/null; then
    echo "✗ MySQL未安装"
    echo ""
    echo "请先安装MySQL:"
    echo "  brew install mysql"
    exit 1
fi

echo "✓ MySQL已安装"

# 检查MySQL服务状态
if ! pgrep -x mysqld > /dev/null; then
    echo ""
    echo "MySQL服务未运行，正在启动..."
    brew services start mysql
    sleep 3
fi

echo "✓ MySQL服务正在运行"
echo ""

# 读取.env配置
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "数据库配置:"
    echo "  主机: ${MYSQL_HOST:-localhost}"
    echo "  端口: ${MYSQL_PORT:-3306}"
    echo "  用户: ${MYSQL_USER:-root}"
    echo "  数据库: ${MYSQL_DATABASE:-geology_agent}"
else
    echo "✗ 未找到.env文件"
    exit 1
fi

echo ""
echo "=============================="
echo "步骤1: 创建数据库"
echo "=============================="

# 创建数据库SQL
mysql -h${MYSQL_HOST:-localhost} -P${MYSQL_PORT:-3306} -u${MYSQL_USER:-root} -p${MYSQL_PASSWORD} <<EOF
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE:-geology_agent}\` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

SHOW DATABASES LIKE '${MYSQL_DATABASE:-geology_agent}';
EOF

if [ $? -eq 0 ]; then
    echo "✓ 数据库创建成功"
else
    echo "✗ 数据库创建失败"
    exit 1
fi

echo ""
echo "=============================="
echo "步骤2: 初始化数据库表"
echo "=============================="

python scripts/init_database.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=============================="
    echo "设置完成！"
    echo "=============================="
    echo ""
    echo "可选: 创建管理员账户"
    echo "  python scripts/init_database.py --create-admin"
else
    echo "✗ 初始化失败"
    exit 1
fi
