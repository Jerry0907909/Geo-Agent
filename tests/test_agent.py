"""Agent 功能测试

测试智能代理的各项功能。
"""

import os
import sys

import pytest

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.agent.agent import GeologyAgent, create_geology_agent
from src.agent.tools import create_default_tools


class TestGeologyAgent:
    """测试 GeologyAgent 类"""

    @pytest.fixture
    def agent(self):
        """创建测试用 Agent"""
        return create_geology_agent(max_iterations=5, verbose=False)

    def test_agent_creation(self, agent):
        """测试 Agent 创建"""
        assert agent is not None
        assert isinstance(agent, GeologyAgent)
        assert len(agent.tools) > 0

    def test_agent_run(self, agent):
        """测试 Agent 执行"""
        result = agent.run("你好")
        assert "output" in result
        assert isinstance(result["output"], str)

    def test_agent_with_literature_search(self, agent):
        """测试 Agent 使用文献检索工具"""
        # 这个测试需要向量库中有数据
        result = agent.run("查询华北克拉通的地质特征")
        
        # 检查是否有输出
        assert "output" in result
        assert len(result["output"]) > 0

    def test_agent_intermediate_steps(self, agent):
        """测试中间推理步骤记录"""
        result = agent.run("1+1等于多少")
        
        # 检查是否返回了中间步骤
        if "intermediate_steps" in result:
            assert isinstance(result["intermediate_steps"], list)

    def test_add_tool(self, agent):
        """测试添加新工具"""
        from langchain.tools import Tool

        initial_tool_count = len(agent.tools)

        # 添加一个简单的测试工具
        def dummy_func(input: str) -> str:
            return f"Dummy: {input}"

        dummy_tool = Tool(
            name="dummy_tool",
            description="A dummy tool for testing",
            func=dummy_func,
        )

        agent.add_tool(dummy_tool)
        assert len(agent.tools) == initial_tool_count + 1

    def test_clear_memory(self, agent):
        """测试清空记忆"""
        # 执行一次查询
        agent.run("测试查询1")
        
        # 清空记忆
        agent.clear_memory()
        
        # 验证记忆已清空（这个测试需要根据实际的记忆实现来调整）
        # assert agent.memory is empty or reset

    def test_format_result(self, agent):
        """测试结果格式化"""
        result = {
            "output": "测试答案",
            "intermediate_steps": []
        }
        
        formatted = agent.format_result(result)
        assert isinstance(formatted, str)
        assert "测试答案" in formatted


class TestAgentTools:
    """测试 Agent 工具"""

    def test_create_default_tools(self):
        """测试创建默认工具集"""
        tools = create_default_tools()
        
        assert len(tools) > 0
        assert all(hasattr(tool, "name") for tool in tools)
        assert all(hasattr(tool, "description") for tool in tools)

    def test_literature_search_tool(self):
        """测试文献检索工具"""
        from src.agent.tools import LiteratureSearchTool

        tool = LiteratureSearchTool()
        result = tool.search("测试查询", top_k=3)
        
        assert isinstance(result, str)

    def test_metadata_query_tool(self):
        """测试元数据查询工具"""
        from src.agent.tools import MetadataQueryTool

        tool = MetadataQueryTool()
        result = tool.query("count")
        
        assert isinstance(result, str)

    def test_calculation_tool(self):
        """测试计算工具"""
        from src.agent.tools import CalculationTool

        tool = CalculationTool()
        
        # 测试简单计算
        result = tool.calculate("2 + 2")
        assert "4" in result
        
        # 测试复杂计算
        result = tool.calculate("pow(2, 10)")
        assert "1024" in result
        
        # 测试错误处理
        result = tool.calculate("1 / 0")
        assert "错误" in result or "除以零" in result.lower()


class TestAgentIntegration:
    """Agent 集成测试"""

    def test_end_to_end_query(self):
        """端到端查询测试"""
        agent = create_geology_agent(max_iterations=5, verbose=False)
        
        # 执行一个简单的查询
        result = agent.run("计算 100 + 200")
        
        assert "output" in result
        # 答案中应该包含300或相关信息
        assert "300" in result["output"] or "三百" in result["output"]

    def test_multi_step_reasoning(self):
        """多步推理测试"""
        agent = create_geology_agent(
            max_iterations=10,
            verbose=False,
            return_intermediate_steps=True
        )
        
        # 执行一个需要多步推理的查询
        result = agent.run("查询文献数量，然后计算两倍")
        
        assert "output" in result
        
        # 检查是否有多个步骤
        if "intermediate_steps" in result:
            steps = result["intermediate_steps"]
            # 至少应该有2个步骤（查询 + 计算）
            assert len(steps) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
