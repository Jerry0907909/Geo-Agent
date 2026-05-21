#!/usr/bin/env python
"""
终端交互式聊天脚本
通过调用 SiliconFlow API 与 LLM 进行对话
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.llm_provider import create_llm_provider
from src.utils.config import get_config


def main():
    """主交互循环"""
    print("=" * 60)
    print("地质文献智能体 - 终端聊天")
    print("=" * 60)
    print("输入 'exit' 或 'quit' 退出\n")

    try:
        # 从配置创建 LLM 提供者
        provider = create_llm_provider()
        print(f"✓ 已连接到 LLM 服务\n")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        print("\n请检查 config.yaml 中的 LLM 配置和环境变量")
        return

    conversation_history = []

    while True:
        try:
            # 获取用户输入
            user_input = input("你: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                print("\n再见！")
                break

            # 调用 LLM API（流式输出）
            print("\nLLM: ", end="", flush=True)
            response_text = ""
            for chunk in provider.stream_generate(user_input):
                print(chunk, end="", flush=True)
                response_text += chunk
            print("\n")

            # 记录对话历史
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response_text})

        except KeyboardInterrupt:
            print("\n\n已中断")
            break
        except Exception as e:
            print(f"\n✗ 错误: {e}\n")


if __name__ == "__main__":
    main()
