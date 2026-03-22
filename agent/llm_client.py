"""
LLM客户端模块

支持多种LLM provider: OpenAI, Anthropic, Ollama
"""

import os
import json
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """LLM客户端基类"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送聊天请求"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI客户端"""

    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class AnthropicClient(BaseLLMClient):
    """Anthropic (Claude) 客户端"""

    def __init__(self, api_key: str = None, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import requests

        # 将消息转换为Anthropic格式
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append(msg)

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "system": system,
            "messages": anthropic_messages
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]


class OllamaClient(BaseLLMClient):
    """Ollama本地客户端"""

    def __init__(self, base_url: str = None, model: str = "llama2"):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import requests

        # 转换消息格式
        ollama_messages = []
        system = ""
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                ollama_messages.append(msg)

        data = {
            "model": kwargs.get("model", self.model),
            "messages": ollama_messages,
            "stream": False
        }

        if system:
            data["system"] = system

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=data,
            timeout=60
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


class MiniMaxClient(BaseLLMClient):
    """MiniMax客户端 (使用官方 Anthropic SDK)"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = "MiniMax-M2.7"):
        self.api_key = api_key or os.getenv("ANTHROPIC_AUTH_TOKEN")
        self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        self.model = model
        self._client = None

    def _get_client(self):
        """获取或创建 Anthropic 客户端"""
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # 将消息转换为 Anthropic 格式
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": [{
                        "type": "text",
                        "text": msg["content"]
                    }]
                })

        client = self._get_client()
        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", 1000)

        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system if system else None,
            messages=anthropic_messages
        )

        # 解析响应
        for block in message.content:
            if block.type == "text":
                return block.text

        # 如果没有 text 类型，返回第一个可用的内容
        return str(message.content[0])


class MockLLMClient(BaseLLMClient):
    """模拟LLM客户端（用于测试）"""

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # 返回模拟回复
        last_message = messages[-1]["content"] if messages else ""

        if "理解" in last_message or "了解" in last_message:
            return "很好！你已经对这个问题有了初步的理解。让我们继续深入探讨..."
        elif "总结" in last_message:
            return "非常好！看来你已经掌握了这个概念的核心要点。"
        else:
            return "这是一个很有趣的观点。能告诉我更多关于你是怎么想的吗？"


def create_llm_client(provider: str = None, **kwargs) -> BaseLLMClient:
    """
    创建LLM客户端

    Args:
        provider: provider名称 (openai/anthropic/ollama/minimax/mock)
        **kwargs: 其他参数

    Returns:
        BaseLLMClient: LLM客户端实例
    """
    provider = provider or os.getenv("LLM_PROVIDER", "mock")

    if provider == "openai":
        return OpenAIClient(
            api_key=kwargs.get("api_key"),
            model=kwargs.get("model", "gpt-4")
        )
    elif provider == "anthropic":
        return AnthropicClient(
            api_key=kwargs.get("api_key"),
            model=kwargs.get("model", "claude-3-opus-20240229")
        )
    elif provider == "ollama":
        return OllamaClient(
            base_url=kwargs.get("base_url"),
            model=kwargs.get("model", "llama2")
        )
    elif provider == "minimax":
        return MiniMaxClient(
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            model=kwargs.get("model", "MiniMax-M2.5")
        )
    else:
        return MockLLMClient()


# 全局客户端实例
_llm_client: Optional[BaseLLMClient] = None


def get_llm_client() -> BaseLLMClient:
    """获取全局LLM客户端"""
    global _llm_client
    if _llm_client is None:
        # 优先从配置加载
        try:
            from agent.config import get_llm_config
            llm_config = get_llm_config()
            _llm_client = create_llm_client(
                provider=llm_config.get("provider"),
                api_key=llm_config.get("api_key"),
                base_url=llm_config.get("base_url"),
                model=llm_config.get("model")
            )
        except ImportError:
            # 如果配置模块不可用，回退到环境变量
            _llm_client = create_llm_client()
    return _llm_client


def set_llm_client(client: BaseLLMClient):
    """设置全局LLM客户端"""
    global _llm_client
    _llm_client = client


def reset_llm_client():
    """重置全局LLM客户端（用于测试或配置更改后重新加载）"""
    global _llm_client
    _llm_client = None
