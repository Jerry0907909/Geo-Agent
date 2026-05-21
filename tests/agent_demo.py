#!/usr/bin/env python
"""Agent 智能代理演示脚本

功能：
1. 构建/重建向量索引
2. 在终端交互式使用 Agent 进行复杂查询
3. 展示多步推理过程
"""

import os
import sys

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.agent.agent import create_geology_agent
from src.rag.chain import create_rag_chain


def main() -> None:
    print("=" * 60)
    print("地质文献智能体 - Agent 终端 Demo")
    print("=" * 60)
    print("此脚本将：")
    print("1) 从 ./data/documents 加载文献并构建/重建 Chroma 向量索引")
    print("2) 进入交互式 Agent 模式，支持多步推理和工具调用")
    print("\n命令：")
    print("  - 输入问题进行查询")
    print("  - 'clear' - 清空对话记忆")
    print("  - 'memory' - 查看记忆摘要")
    print("  - 'exit' 或 'quit' - 退出\n")

    # 创建 RAG Chain 并构建索引
    print("[1/2] 正在构建/重建向量索引...")
    try:
        rag_chain = create_rag_chain()
        stats = rag_chain.build_index(rebuild=True)
        print(
            f"✓ 索引构建完成: {stats.num_source_documents} 篇源文献, "
            f"{stats.num_chunks} 个分割片段\n"
        )
    except Exception as e:
        print(f"✗ 构建索引失败: {e}")
        print("注意: Agent 将继续运行，但检索功能可能不可用。\n")

    # 创建 Agent
    print("[2/2] 初始化 Agent...")
    try:
        agent = create_geology_agent(verbose=True, return_intermediate_steps=True)
        print("✓ Agent 初始化成功\n")
    except Exception as e:
        print(f"✗ Agent 初始化失败: {e}")
        return

    print("=" * 60)
    print("进入 Agent 问答模式")
    print("=" * 60)

    # 交互式查询
    while True:
        try:
            question = input("\n问题: ").strip()
        except KeyboardInterrupt:
            print("\n\n已中断，退出。")
            break

        if not question:
            continue

        if question.lower() in {"exit", "quit"}:
            print("再见！")
            break

        if question.lower() == "clear":
            agent.clear_memory()
            print("✓ 对话记忆已清空")
            continue

        if question.lower() == "memory":
            summary = agent.get_memory_summary()
            print(f"\n记忆摘要:\n{summary}")
            continue

        # 执行查询
        print("\n正在推理中...\n")
        try:
            result = agent.run(question)
            
            # 格式化输出
            formatted = agent.format_result(result)
            print(formatted)
            
        except Exception as e:
            print(f"✗ 查询失败: {e}\n")
            continue


if __name__ == "__main__":
    main()
