#!/usr/bin/env python
"""终端 RAG 演示脚本

功能：
1. 构建 / 重建向量索引（从 ./data/documents 加载文献）
2. 在终端交互式提问，调用 RAGChain 完成“检索 + 生成回答”
"""

import os
import sys

# 确保项目根目录在 sys.path 中，以便导入 src.* 包
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.rag.chain import create_rag_chain


def main() -> None:
    print("=" * 60)
    print("地质文献智能体 - RAG 终端 Demo")
    print("=" * 60)
    print("此脚本将：")
    print("1) 从 ./data/documents 加载文献并构建/重建 Chroma 向量索引")
    print("2) 进入交互式问答模式，基于文献进行 RAG 检索与回答")
    print("输入 'exit' 或 'quit' 退出\n")

    # 创建完整的 RAGChain
    try:
        rag_chain = create_rag_chain()
    except Exception as e:
        print(f"✗ 创建 RAGChain 失败: {e}")
        print("请检查 config.yaml / .env 配置以及依赖是否安装完整。")
        return

    # 构建 / 重建索引
    print("[1/2] 正在构建/重建向量索引 (rebuild=True)...")
    try:
        stats = rag_chain.build_index(rebuild=True)
    except Exception as e:
        print(f"✗ 构建索引失败: {e}")
        return

    print(
        f"✓ 索引构建完成: {stats.num_source_documents} 篇源文献, "
        f"{stats.num_chunks} 个分割片段\n"
    )

    # 交互式查询
    print("[2/2] 进入 RAG 问答模式。\n")

    while True:
        try:
            question = input("问题: ").strip()
        except KeyboardInterrupt:
            print("\n\n已中断，退出。")
            break

        if not question:
            continue

        if question.lower() in {"exit", "quit"}:
            print("再见！")
            break

        try:
            result = rag_chain.query(question)
        except Exception as e:
            print(f"✗ 查询失败: {e}\n")
            continue

        print("\n答案:\n")
        print(result.answer)

        # 简单显示参考文献来源
        if result.context_documents:
            print("\n参考文献片段来源:")
            seen_sources = set()
            for doc in result.context_documents:
                src = doc.metadata.get("source") or doc.metadata.get("file_name")
                if src and src not in seen_sources:
                    seen_sources.add(src)
                    print(f"- {src}")
        else:
            print("\n(本次回答未检索到任何文献片段，可能仅基于模型常识。)")

        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    main()
