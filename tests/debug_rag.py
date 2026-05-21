"""诊断 RAG 检索问题"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.database.chroma_manager import create_chroma_manager
from src.utils.config import get_config

def main():
    print("=" * 60)
    print("RAG 检索诊断工具")
    print("=" * 60)
    
    # 0. 检查配置
    print("\n0. 检查配置...")
    config = get_config()
    rag_cfg = config.get_rag_config()
    chroma_cfg = config.get_chroma_config()
    print(f"  similarity_threshold: {rag_cfg.get('similarity_threshold')}")
    print(f"  top_k: {rag_cfg.get('top_k')}")
    print(f"  persist_directory: {chroma_cfg.get('persist_directory')}")
    print(f"  collection_name: {chroma_cfg.get('collection_name')}")
    
    # 1. 检查向量库
    print("\n1. 检查向量库...")
    try:
        cm = create_chroma_manager()
        count = cm.collection.count()
        print(f"✓ 向量库连接成功")
        print(f"✓ 集合名称: {cm.collection.name}")
        print(f"✓ 文档总数: {count}")
        
        if count == 0:
            print("⚠️  向量库为空，需要先导入文档！")
            return
        
        # 查看前5个文档
        print("\n1.1 查看前5个文档...")
        sample = cm.collection.get(limit=5)
        for i, doc in enumerate(sample.get('documents', [])[:5]):
            print(f"  [{i}] {doc[:100]}...")
        
    except Exception as e:
        print(f"✗ 向量库连接失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. 测试检索（不使用阈值过滤）
    print("\n2. 测试原始检索（直接调用 collection.query）...")
    test_query = "莺歌海盆地地质情况"
    
    try:
        # 直接调用 chroma 检索
        results = cm.collection.query(
            query_texts=[test_query],
            n_results=5
        )
        
        print(f"查询: '{test_query}'")
        print(f"原始结果数: {len(results.get('documents', [[]])[0])}")
        
        docs = results.get('documents', [[]])[0]
        distances = results.get('distances', [[]])[0]
        
        for i, (doc, dist) in enumerate(zip(docs, distances)):
            similarity = 1.0 - dist
            print(f"  [{i}] 距离: {dist:.4f} | 相似度: {similarity:.4f}")
            print(f"      内容: {doc[:100]}...")
            
    except Exception as e:
        print(f"✗ 检索失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. 测试 ChromaManager 的 similarity_search
    print("\n3. 测试 ChromaManager.similarity_search...")
    try:
        docs = cm.similarity_search(test_query, top_k=5)
        print(f"  过滤后结果数: {len(docs)}")
        
        for i, doc in enumerate(docs):
            score = doc.metadata.get('relevance_score', 'N/A')
            print(f"  [{i}] 相似度: {score}")
            print(f"      内容: {doc.page_content[:100]}...")
            
    except Exception as e:
        print(f"✗ 检索失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
