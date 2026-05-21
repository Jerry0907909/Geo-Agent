"""LLM URL 规范化 — 确保测试连接与真实对话使用相同路径"""


def normalize_openai_base_url(base_url: str) -> str:
    """将用户输入的 URL 规范化为 ChatOpenAI 可用的 base_url（以 /v1 结尾）

    Examples:
        https://api.openai.com          → https://api.openai.com/v1
        https://api.openai.com/v1       → https://api.openai.com/v1
        https://api.openai.com/v1/      → https://api.openai.com/v1
        https://llmapi.paratera.com     → https://llmapi.paratera.com/v1
    """
    url = base_url.strip().rstrip("/")
    if not url.endswith("/v1"):
        url = url + "/v1"
    return url


def normalize_chat_endpoint(base_url: str) -> str:
    """将 base_url 转换为 /chat/completions 完整端点

    测试连接与 LangChain ChatOpenAI 均使用此函数。
    """
    url = normalize_openai_base_url(base_url)
    if not url.endswith("/chat/completions"):
        url = url + "/chat/completions"
    return url
