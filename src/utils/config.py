import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

# 尝试导入 dotenv，如果不存在则跳过
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path=None):
        """如果dotenv不可用，提供一个空实现"""
        pass


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = "config.yaml", env_path: str = ".env"):
        """
        初始化配置
        
        Args:
            config_path: YAML配置文件路径
            env_path: 环境变量文件路径
        """
        # 加载环境变量
        load_dotenv(env_path)
        
        # 加载YAML配置
        self.config_path = Path(config_path)
        self.config = self._load_yaml_config()
        
        # 替换环境变量
        self._substitute_env_vars()
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """加载YAML配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _substitute_env_vars(self):
        """递归替换配置中的环境变量"""
        def substitute(obj):
            if isinstance(obj, dict):
                return {k: substitute(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute(item) for item in obj]
            elif isinstance(obj, str):
                # 替换 ${VAR_NAME} 格式的环境变量
                if obj.startswith("${") and obj.endswith("}"):
                    var_name = obj[2:-1]
                    return os.getenv(var_name, obj)
                return obj
            return obj
        
        self.config = substitute(self.config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键
        
        Args:
            key: 配置键，如 "embedding.api_endpoint"
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """获取词向量模型配置"""
        return self.config.get('embedding', {})
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取大语言模型配置"""
        return self.config.get('llm', {})
    
    def get_chroma_config(self) -> Dict[str, Any]:
        """获取Chroma向量库配置"""
        return self.config.get('chroma', {})
    
    def get_rag_config(self) -> Dict[str, Any]:
        """获取RAG配置"""
        return self.config.get('rag', {})
    
    def get_agent_config(self) -> Dict[str, Any]:
        """获取Agent配置"""
        return self.config.get('agent', {})
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return self.config.get('server', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.config.get('logging', {})
    
    def get_text_processing_config(self) -> Dict[str, Any]:
        """获取文本处理配置"""
        return self.config.get('text_processing', {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self.config.get('database', {})
    
    def get_auth_config(self) -> Dict[str, Any]:
        """获取认证配置"""
        return self.config.get('auth', {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return self.config.get('cache', {})
    
    @property
    def raw_config(self) -> Dict[str, Any]:
        """获取原始配置字典"""
        return self.config
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __repr__(self) -> str:
        return f"<Config from {self.config_path}>"


# 全局配置实例
_config_instance: Optional[Config] = None


def get_config(config_path: str = "config.yaml", env_path: str = ".env") -> Config:
    """
    获取全局配置实例（单例模式）
    
    Args:
        config_path: YAML配置文件路径
        env_path: 环境变量文件路径
    
    Returns:
        Config实例
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config(config_path, env_path)
    
    return _config_instance


def reset_config():
    """重置全局配置实例"""
    global _config_instance
    _config_instance = None


if __name__ == "__main__":
    # 测试配置加载
    config = get_config()
    
    print("=== Embedding 配置 ===")
    print(f"Provider: {config.get('embedding.provider')}")
    print(f"API Endpoint: {config.get('embedding.api_endpoint')}")
    print(f"Model Name: {config.get('embedding.model_name')}")
    
    print("\n=== LLM 配置 ===")
    print(f"Provider: {config.get('llm.provider')}")
    print(f"API Endpoint: {config.get('llm.api_endpoint')}")
    print(f"Model Name: {config.get('llm.model_name')}")
    
    print("\n=== Chroma 配置 ===")
    print(f"Persist Directory: {config.get('chroma.persist_directory')}")
    print(f"Collection Name: {config.get('chroma.collection_name')}")
    
    print("\n=== RAG 配置 ===")
    print(f"Top K: {config.get('rag.top_k')}")
    print(f"Chunk Size: {config.get('rag.chunk_size')}")
