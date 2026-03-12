"""
LLM配置文件
"""

import os
from pathlib import Path


def get_config_path() -> Path:
    """获取配置文件路径"""
    return Path.home() / ".learnmate" / "config.yaml"


def load_config() -> dict:
    """加载配置"""
    config_path = get_config_path()
    if not config_path.exists():
        return get_default_config()

    import yaml
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_default_config() -> dict:
    """获取默认配置"""
    return {
        "llm": {
            "provider": os.getenv("LLM_PROVIDER", "mock"),
            "model": os.getenv("LLM_MODEL", "gpt-4"),
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        }
    }


def ensure_config_dir():
    """确保配置目录存在"""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)


def save_config(config: dict):
    """保存配置"""
    ensure_config_dir()
    import yaml
    config_path = get_config_path()
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
