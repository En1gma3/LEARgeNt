"""
飞书机器人启动入口

用法:
    python -m cli.feishu_main

启动飞书机器人，使用 WebSocket 长连接接收消息
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import yaml

from utils import get_logger

logger = get_logger(__name__)


def load_feishu_config() -> dict:
    """
    加载飞书配置

    优先级: 环境变量 > config.yaml
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")

    config = {
        "enabled": False,
        "apps": []
    }

    # 读取配置文件
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
            feishu_config = yaml_config.get("feishu", {})
            config["enabled"] = feishu_config.get("enabled", False)
            config["apps"] = feishu_config.get("apps", [])

    # 环境变量覆盖
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if app_id and app_secret:
        # 使用环境变量配置
        config["enabled"] = True
        config["apps"] = [{
            "app_id": app_id,
            "app_secret": app_secret,
            "use_websocket": True,
            "dedup_ttl": 300
        }]

    return config


def check_dependencies():
    """检查依赖是否满足"""
    try:
        import lark_oapi
        return True
    except ImportError:
        logger.error("lark_oapi not installed")
        logger.error("请运行: pip install lark-oapi")
        return False


def run_feishu_bot(app_id: str, app_secret: str):
    """
    运行飞书机器人

    Args:
        app_id: 飞书应用 ID
        app_secret: 飞书应用密钥
    """
    from agent.adapters import FeishuAdapter
    from agent.learn_agent import LearnMateAgent
    from lark_oapi.ws.client import loop as sdk_loop

    logger.info(f"Starting Feishu bot with app_id: {app_id[:8]}...")

    # 创建适配器
    adapter = FeishuAdapter(
        app_id=app_id,
        app_secret=app_secret,
        AgentClass=LearnMateAgent
    )

    async def _run():
        await adapter.start()
        while adapter._running:
            await asyncio.sleep(1)
        logger.info("Feishu bot stopped")

    try:
        sdk_loop.run_until_complete(_run())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Feishu bot error: {e}", exc_info=True)
        raise


def main():
    """主入口"""
    print("""
╔═══════════════════════════════════════════════════╗
║                                                   ║
║           LearnMate 飞书机器人                    ║
║                                                   ║
║           智能学习助手 - 苏格拉底式引导             ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
    """)

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 加载配置
    config = load_feishu_config()

    if not config.get("enabled"):
        print("错误: 飞书功能未启用")
        print("")
        print("请按以下步骤启用:")
        print("1. 在 .env 文件中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        print("2. 或在 config/config.yaml 中配置 feishu.enabled: true")
        sys.exit(1)

    apps = config.get("apps", [])
    if not apps:
        print("错误: 未配置飞书应用")
        sys.exit(1)

    app_config = apps[0]
    app_id = app_config.get("app_id")
    app_secret = app_config.get("app_secret")

    if not app_id or not app_secret:
        print("错误: 飞书应用配置不完整")
        print("请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        sys.exit(1)

    # 替换环境变量占位符
    if app_id.startswith("${") and app_id.endswith("}"):
        env_var = app_id[2:-1]
        app_id = os.environ.get(env_var, "")

    if app_secret.startswith("${") and app_secret.endswith("}"):
        env_var = app_secret[2:-1]
        app_secret = os.environ.get(env_var, "")

    if not app_id or not app_secret:
        print("错误: 飞书应用 ID 或 Secret 为空")
        print("请确保环境变量已设置")
        sys.exit(1)

    print(f"应用 ID: {app_id[:8]}...")
    print("正在连接飞书...")
    print("")

    # 运行机器人
    try:
        run_feishu_bot(app_id, app_secret)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
