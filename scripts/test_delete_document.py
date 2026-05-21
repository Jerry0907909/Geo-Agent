"""
测试助手文档删除功能
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置环境变量
os.chdir(project_root)

from src.database.chroma_manager import ChromaManager
from src.database.database import SessionLocal
from src.database.models import CustomAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_delete_document():
    """测试删除文档功能"""
    db = SessionLocal()
    
    try:
        # 获取第一个助手
        agent = db.query(CustomAgent).filter(CustomAgent.is_active == True).first()
        
        if not agent:
            logger.error("没有找到活跃的助手")
            return
        
        if not agent.collection_name:
            logger.error(f"助手 {agent.name} 没有配置知识库")
            return
        
        logger.info(f"测试助手: {agent.name}, 集合: {agent.collection_name}")
        
        # 获取集合中的所有文档
        manager = ChromaManager(collection_name=agent.collection_name)
        all_docs = manager.collection.get()
        
        ids = all_docs.get("ids", [])
        metadatas = all_docs.get("metadatas", [])
        
        logger.info(f"集合中共有 {len(ids)} 个文档片段")
        
        if not metadatas:
            logger.warning("集合中没有文档")
            return
        
        # 打印前5个文档的 metadata
        logger.info("前5个文档的 metadata:")
        for i, meta in enumerate(metadatas[:5]):
            logger.info(f"  [{i}] {meta}")
        
        # 统计不同的 source
        sources = set()
        for meta in metadatas:
            if "source" in meta:
                sources.add(meta["source"])
            if "file_name" in meta:
                sources.add(meta["file_name"])
        
        logger.info(f"\n集合中的文档来源: {sources}")
        
        # 测试删除第一个文档
        if sources:
            test_source = list(sources)[0]
            logger.info(f"\n尝试删除文档: {test_source}")
            
            # 测试用 source 字段删除
            deleted = manager.delete_by_filter({"source": test_source})
            logger.info(f"使用 source 字段删除了 {deleted} 个片段")
            
            if deleted == 0:
                # 测试用 file_name 字段删除
                deleted = manager.delete_by_filter({"file_name": test_source})
                logger.info(f"使用 file_name 字段删除了 {deleted} 个片段")
            
            # 再次查询确认
            remaining = manager.collection.get()
            logger.info(f"删除后剩余 {len(remaining.get('ids', []))} 个片段")
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    test_delete_document()
