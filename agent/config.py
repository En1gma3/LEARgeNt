"""
LearnMate 配置文件模块

支持从 config.yaml 加载配置，并通过环境变量覆盖
配置文件路径优先级:
1. LEARNMATE_CONFIG 环境变量指定的位置
2. 项目根目录下的 config/config.yaml
3. ~/.learnmate/config.yaml
"""

import os
from pathlib import Path
from typing import Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def get_config_path() -> Optional[Path]:
    """获取配置文件路径"""
    # 1. 首先检查环境变量 LEARNMATE_CONFIG
    if os.getenv("LEARNMATE_CONFIG"):
        config_path = Path(os.getenv("LEARNMATE_CONFIG"))
        if config_path.exists():
            return config_path

    # 2. 检查项目根目录下的 config/config.yaml
    project_config = PROJECT_ROOT / "config" / "config.yaml"
    if project_config.exists():
        return project_config

    # 3. 检查用户主目录 ~/.learnmate/config.yaml
    home_config = Path.home() / ".learnmate" / "config.yaml"
    if home_config.exists():
        return home_config

    return None


def load_config() -> dict:
    """加载配置"""
    config_path = get_config_path()
    if config_path is None:
        return get_default_config()

    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # 合并环境变量覆盖
    return apply_env_overrides(config)


def apply_env_overrides(config: dict) -> dict:
    """应用环境变量覆盖"""
    if "llm" not in config:
        config["llm"] = {}

    llm_config = config["llm"]

    # LLM provider
    if os.getenv("LLM_PROVIDER"):
        llm_config["provider"] = os.getenv("LLM_PROVIDER")

    # API key - 支持多种环境变量
    if os.getenv("OPENAI_API_KEY"):
        llm_config["api_key"] = os.getenv("OPENAI_API_KEY")
    if os.getenv("ANTHROPIC_API_KEY"):
        llm_config["api_key"] = os.getenv("ANTHROPIC_API_KEY")
    if os.getenv("ANTHROPIC_AUTH_TOKEN"):
        llm_config["api_key"] = os.getenv("ANTHROPIC_AUTH_TOKEN")

    # Base URL
    if os.getenv("OLLAMA_BASE_URL"):
        llm_config["base_url"] = os.getenv("OLLAMA_BASE_URL")
    if os.getenv("ANTHROPIC_BASE_URL"):
        llm_config["base_url"] = os.getenv("ANTHROPIC_BASE_URL")

    # Model
    if os.getenv("LLM_MODEL"):
        llm_config["model"] = os.getenv("LLM_MODEL")

    # Temperature
    if os.getenv("LLM_TEMPERATURE"):
        llm_config["temperature"] = float(os.getenv("LLM_TEMPERATURE"))

    # Max tokens
    if os.getenv("LLM_MAX_TOKENS"):
        llm_config["max_tokens"] = int(os.getenv("LLM_MAX_TOKENS"))

    return config


def get_default_config() -> dict:
    """获取默认配置"""
    return {
        "llm": {
            "provider": os.getenv("LLM_PROVIDER", "mock"),
            "model": os.getenv("LLM_MODEL", "gpt-4"),
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "temperature": 0.7,
            "max_tokens": 1000,
        }
    }


def ensure_config_dir():
    """确保配置目录存在"""
    config_path = get_config_path()
    if config_path:
        config_path.parent.mkdir(parents=True, exist_ok=True)


def save_config(config: dict):
    """保存配置"""
    ensure_config_dir()
    import yaml

    config_path = get_config_path()
    if config_path is None:
        # 默认保存到用户主目录
        config_path = Path.home() / ".learnmate" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def get_config() -> dict:
    """
    统一获取配置的接口

    Returns:
        dict: 配置字典，包含 llm 配置项
    """
    return load_config()


def get_llm_config() -> dict:
    """
    获取LLM配置项

    Returns:
        dict: LLM配置字典
    """
    config = load_config()
    return config.get("llm", {})


def get_obsidian_config() -> dict:
    """
    获取Obsidian配置项

    Returns:
        dict: Obsidian配置字典
    """
    config = load_config()
    return config.get("obsidian", {})


def get_vault_dir() -> str:
    """
    获取Obsidian知识库目录

    Returns:
        str: 知识库目录路径，默认为 "vault"
    """
    obsidian_config = get_obsidian_config()
    return obsidian_config.get("vault_dir", "vault")
