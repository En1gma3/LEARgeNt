"""
日志模块

提供集中式日志功能，支持：
- 日志级别控制
- 文件输出 (data/logs/learnmate.log)
- 控制台输出
- 模块级别 logger 获取

使用方式:
    from utils import get_logger
    logger = get_logger(__name__)
    logger.info("消息")
    logger.debug("调试信息")
    logger.warning("警告")
    logger.error("错误")
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler


# 全局日志级别配置
LOG_LEVEL = os.getenv("LEARNMATE_LOG_LEVEL", "INFO").upper()

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志目录
LOG_DIR = Path("./data/logs")
LOG_FILE = LOG_DIR / "learnmate.log"

# 确保日志目录存在
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _get_log_level(level_str: str) -> int:
    """将字符串转换为日志级别"""
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return levels.get(level_str, logging.INFO)


def _create_logger(name: str) -> logging.Logger:
    """创建并配置 logger"""
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(_get_log_level(LOG_LEVEL))

    # 文件 Handler - 使用 RotatingFileHandler 限制文件大小
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    file_handler.setFormatter(file_formatter)

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_get_log_level(LOG_LEVEL))
    console_formatter = logging.Formatter("%(levelname)-8s | %(message)s")
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 缓存已创建的 logger
_loggers = {}


def get_logger(name: str) -> logging.Logger:
    """
    获取模块 logger

    Args:
        name: 模块名称，通常使用 __name__

    Returns:
        logging.Logger: 配置好的 logger 实例

    Example:
        logger = get_logger(__name__)
        logger.info("这是一条信息日志")
        logger.debug("调试信息: x = {}", x)  # 支持格式化
    """
    if name not in _loggers:
        _loggers[name] = _create_logger(name)
    return _loggers[name]


class LoggerMixin:
    """
    日志混入类

    为类提供 self.logger 属性

    Example:
        class MyClass(LoggerMixin):
            def __init__(self):
                self.logger = get_logger(__name__)

            def do_something(self):
                self.logger.info("做某事")
    """

    @property
    def logger(self) -> logging.Logger:
        """获取 logger"""
        name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        if name not in _loggers:
            _loggers[name] = _create_logger(name)
        return _loggers[name]


def log_module_usage(module_name: str, function_name: str, **kwargs):
    """
    记录模块函数调用（用于追踪）

    Args:
        module_name: 模块名
        function_name: 函数名
        **kwargs: 其他参数
    """
    logger = get_logger(module_name)
    if kwargs:
        logger.debug(f"{function_name} called with: {kwargs}")
    else:
        logger.debug(f"{function_name} called")


def set_log_level(level: str):
    """
    设置全局日志级别

    Args:
        level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    global LOG_LEVEL
    LOG_LEVEL = level.upper()
    root_logger = logging.getLogger()
    root_logger.setLevel(_get_log_level(level))


def get_log_file_path() -> Path:
    """获取日志文件路径"""
    return LOG_FILE


def cleanup_old_logs(days: int = 7):
    """
    清理旧日志文件

    Args:
        days: 保留最近几天的日志
    """
    if not LOG_DIR.exists():
        return

    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
    for log_file in LOG_DIR.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff:
            log_file.unlink()
