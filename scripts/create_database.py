#!/usr/bin/env python
"""创建MySQL数据库

在运行init_database.py之前，先创建数据库。
"""

import os
import sys
import pymysql

# 添加项目根目录到路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)


def create_database():
    """创建数据库"""
    from src.utils.config import get_config
    
    config = get_config()
    db_cfg = config.get_database_config()
    
    host = db_cfg.get("mysql_host", "localhost")
    port = db_cfg.get("mysql_port", 3306)
    user = db_cfg.get("mysql_user", "root")
    password = db_cfg.get("mysql_password", "")
    database = db_cfg.get("mysql_database", "geology_agent")
    
    print("=" * 60)
    print("创建MySQL数据库")
    print("=" * 60)
    print(f"\n连接信息:")
    print(f"  主机: {host}")
    print(f"  端口: {port}")
    print(f"  用户: {user}")
    print(f"  数据库: {database}")
    
    try:
        # 连接到MySQL服务器（不指定数据库）
        print(f"\n正在连接到MySQL服务器...")
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        
        print("✓ 连接成功")
        
        with connection.cursor() as cursor:
            # 检查数据库是否存在
            cursor.execute(f"SHOW DATABASES LIKE '{database}'")
            result = cursor.fetchone()
            
            if result:
                print(f"\n数据库 '{database}' 已存在")
                overwrite = input("是否删除并重建? (输入 'yes' 确认): ").strip().lower()
                if overwrite == 'yes':
                    cursor.execute(f"DROP DATABASE `{database}`")
                    print(f"✓ 已删除数据库 '{database}'")
                else:
                    print("操作已取消")
                    return
            
            # 创建数据库
            print(f"\n正在创建数据库 '{database}'...")
            cursor.execute(
                f"CREATE DATABASE `{database}` "
                f"CHARACTER SET utf8mb4 "
                f"COLLATE utf8mb4_unicode_ci"
            )
            print(f"✓ 数据库 '{database}' 创建成功")
            
            # 验证数据库
            cursor.execute(f"USE `{database}`")
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()[0]
            print(f"✓ 当前数据库: {current_db}")
        
        connection.close()
        
        print("\n" + "=" * 60)
        print("数据库创建完成！")
        print("=" * 60)
        print("\n下一步: 运行以下命令初始化数据库表:")
        print("  python scripts/init_database.py")
        print("\n或创建管理员账户:")
        print("  python scripts/init_database.py --create-admin")
        
    except pymysql.err.OperationalError as e:
        print(f"\n✗ 连接失败: {e}")
        print("\n请检查:")
        print("  1. MySQL服务是否已启动")
        print("     macOS: brew services start mysql")
        print("     或: mysql.server start")
        print("  2. .env文件中的用户名和密码是否正确")
        print("  3. MySQL用户是否有CREATE DATABASE权限")
        
    except Exception as e:
        print(f"\n✗ 创建失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_database()
