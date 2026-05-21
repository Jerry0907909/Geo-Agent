#!/usr/bin/env python
"""数据库初始化脚本

初始化MySQL数据库，创建所有必要的表。

用法:
    python scripts/init_database.py [--drop-all]
    
参数:
    --drop-all: 删除所有现有表后重建（危险操作，会丢失所有数据）
"""

import os
import sys

# 添加项目根目录到路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="初始化MySQL数据库")
    parser.add_argument(
        "--drop-all",
        action="store_true",
        help="删除所有现有表后重建（危险操作）"
    )
    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="创建管理员账户"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("地质文献智能体 - 数据库初始化")
    print("=" * 60)
    
    # 检查配置
    from src.utils.config import get_config
    config = get_config()
    db_cfg = config.get_database_config()
    
    print(f"\n数据库配置:")
    print(f"  主机: {db_cfg.get('mysql_host', 'localhost')}")
    print(f"  端口: {db_cfg.get('mysql_port', 3306)}")
    print(f"  数据库: {db_cfg.get('mysql_database', 'geology_agent')}")
    print(f"  用户: {db_cfg.get('mysql_user', 'root')}")
    
    if args.drop_all:
        print("\n⚠️  警告: 即将删除所有数据库表，所有数据将丢失！")
        confirm = input("确认继续? (输入 'YES' 确认): ")
        if confirm != "YES":
            print("操作已取消")
            return
    
    # 初始化数据库
    print("\n正在初始化数据库...")
    
    try:
        from src.database.mysql_manager import init_database, check_database_connection
        
        # 检查连接
        if not check_database_connection():
            print("\n✗ 无法连接到数据库")
            print("\n请检查:")
            print("  1. MySQL服务是否已启动")
            print("  2. .env文件中的数据库配置是否正确")
            print("  3. 数据库用户是否有足够权限")
            print("\n您可能需要先在MySQL中创建数据库:")
            print(f"  CREATE DATABASE {db_cfg.get('mysql_database', 'geology_agent')} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            return
        
        # 初始化表
        init_database(drop_all=args.drop_all)
        print("\n✓ 数据库表创建成功")
        
        # 创建管理员账户
        if args.create_admin:
            create_admin_user()
        
        print("\n" + "=" * 60)
        print("数据库初始化完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()


def create_admin_user():
    """创建管理员账户"""
    print("\n创建管理员账户...")
    
    from src.database.mysql_manager import get_db_session
    from src.database.models import User, UserPreference
    from src.auth.security import get_password_hash
    
    username = input("管理员用户名 (默认: admin): ").strip() or "admin"
    email = input("管理员邮箱: ").strip()
    if not email:
        email = f"{username}@localhost"
    password = input("管理员密码 (至少6位): ").strip()
    
    if len(password) < 6:
        print("✗ 密码长度至少6位")
        return
    
    try:
        with get_db_session() as session:
            # 检查用户是否存在
            existing = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing:
                print(f"✗ 用户 {username} 或邮箱 {email} 已存在")
                return
            
            # 创建用户
            admin = User(
                username=username,
                email=email,
                hashed_password=get_password_hash(password),
                full_name="系统管理员",
                is_active=True,
                is_superuser=True
            )
            session.add(admin)
            session.flush()
            
            # 创建偏好设置
            preference = UserPreference(user_id=admin.id)
            session.add(preference)
            
            session.commit()
            
            print(f"\n✓ 管理员账户创建成功")
            print(f"  用户名: {username}")
            print(f"  邮箱: {email}")
    
    except Exception as e:
        print(f"✗ 创建管理员失败: {e}")


if __name__ == "__main__":
    main()
