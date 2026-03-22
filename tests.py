"""
LearnMate 单元测试

运行方式:
    python tests.py              # 运行所有测试
    python tests.py TestLogger   # 运行特定测试类
    python tests.py -v           # 详细输出
"""

import sys
import os
import unittest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# 确保项目根目录在 path 中
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Test Runner
# ============================================================================

def run_tests(verbose=False):
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = loader.discover(PROJECT_ROOT, pattern='tests.py')

    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


# ============================================================================
# Logger Tests
# ============================================================================

class TestLogger(unittest.TestCase):
    """日志系统测试"""

    def setUp(self):
        """测试前设置"""
        # 创建临时日志目录
        self.temp_dir = tempfile.mkdtemp()
        self.original_log_dir = None

        # 临时修改日志路径
        from utils import logger
        global LOG_DIR, LOG_FILE
        self.original_log_dir = logger.LOG_DIR
        self.original_log_file = logger.LOG_FILE
        logger.LOG_DIR = Path(self.temp_dir)
        logger.LOG_FILE = Path(self.temp_dir) / "test.log"
        logger.LOG_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """测试后清理"""
        from utils import logger
        # 恢复原始路径
        logger.LOG_DIR = self.original_log_dir
        logger.LOG_FILE = self.original_log_file
        # 清理临时目录
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_logger(self):
        """测试获取 logger"""
        from utils import get_logger

        logger1 = get_logger(__name__)
        logger2 = get_logger(__name__)

        # 同一名称应返回同一实例
        self.assertIs(logger1, logger2)
        self.assertEqual(logger1.name, __name__)

    def test_log_levels(self):
        """测试不同日志级别"""
        from utils import get_logger

        logger = get_logger("test_levels")

        # 这些操作不应该抛出异常
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")

    def test_logger_mixin(self):
        """测试 LoggerMixin"""
        from utils import LoggerMixin

        class MyClass(LoggerMixin):
            pass

        obj = MyClass()
        self.assertTrue(hasattr(obj, 'logger'))
        self.assertIsNotNone(obj.logger)

    def test_log_file_created(self):
        """测试日志文件创建"""
        from utils import get_logger

        logger = get_logger("test_file")
        test_message = "test log message"
        logger.info(test_message)

        log_file = Path(self.temp_dir) / "test.log"
        self.assertTrue(log_file.exists())

        with open(log_file, 'r') as f:
            content = f.read()
            self.assertIn(test_message, content)

    def test_set_log_level(self):
        """测试设置日志级别"""
        from utils.logger import set_log_level, _get_log_level

        levels = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }

        for name, expected in levels.items():
            self.assertEqual(_get_log_level(name), expected)

    def test_get_log_file_path(self):
        """测试获取日志文件路径"""
        from utils.logger import get_log_file_path

        path = get_log_file_path()
        self.assertIsInstance(path, Path)


# ============================================================================
# Memory Tests
# ============================================================================

class TestShortTermMemory(unittest.TestCase):
    """短期记忆测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        self.temp_file.close()
        self.temp_path = self.temp_file.name

        # 清理导入的模块缓存
        if 'memory.context' in sys.modules:
            del sys.modules['memory.context']

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_path):
            os.unlink(self.temp_path)
        # 重置全局状态
        import memory.context as ctx_module
        ctx_module._loggers = {}

    def test_create_session(self):
        """测试创建会话"""
        from memory.context import ShortTermMemory

        stm = ShortTermMemory(storage_path=self.temp_path)
        session = stm.create_session(mode='learn')

        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.mode, 'learn')
        self.assertEqual(len(session.messages), 0)

    def test_add_messages(self):
        """测试添加消息"""
        from memory.context import ShortTermMemory

        stm = ShortTermMemory(storage_path=self.temp_path)
        stm.create_session()

        stm.add_user_message("你好")
        stm.add_assistant_message("你好！")

        session = stm.get_current_session()
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.messages[0].role, 'user')
        self.assertEqual(session.messages[1].role, 'assistant')

    def test_session_persistence(self):
        """测试会话持久化"""
        from memory.context import ShortTermMemory

        # 创建并保存会话
        stm1 = ShortTermMemory(storage_path=self.temp_path)
        stm1.create_session()
        stm1.add_user_message("测试消息")
        stm1.save_session()

        # 重新加载
        stm2 = ShortTermMemory(storage_path=self.temp_path)
        sessions = stm2.list_sessions()

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]['message_count'], 1)

    def test_session_to_dict_from_dict(self):
        """测试会话序列化/反序列化"""
        from memory.context import SessionContext, Message

        session = SessionContext(session_id="test-123", mode="learn")
        session.add_message("user", "hello")
        session.add_message("assistant", "hi")

        # 序列化
        data = session.to_dict()
        self.assertEqual(data['session_id'], "test-123")
        self.assertEqual(len(data['messages']), 2)

        # 反序列化
        restored = SessionContext.from_dict(data)
        self.assertEqual(restored.session_id, "test-123")
        self.assertEqual(len(restored.messages), 2)

    def test_get_conversation_history(self):
        """测试获取对话历史"""
        from memory.context import ShortTermMemory

        stm = ShortTermMemory(storage_path=self.temp_path)
        stm.create_session()
        stm.add_user_message("你好")
        stm.add_assistant_message("你好！")
        stm.add_user_message("今天天气")

        history = stm.get_conversation_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]['role'], 'user')


class TestLongTermMemory(unittest.TestCase):
    """长期记忆测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        self.temp_file.close()
        # 初始化为有效的 JSON
        with open(self.temp_file.name, 'w') as f:
            json.dump({
                "learned_terms": [],
                "user_preferences": {},
                "disambiguations": {},
                "learning_history": [],
                "last_updated": datetime.now().isoformat()
            }, f)
        self.temp_path = self.temp_file.name

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_path):
            os.unlink(self.temp_path)

    def test_add_learned_term(self):
        """测试添加已学名词"""
        from memory.long_term import LongTermMemory

        ltm = LongTermMemory(data_path=self.temp_path)
        ltm.add_learned_term("区块链")

        self.assertTrue(ltm.is_learned("区块链"))
        self.assertFalse(ltm.is_learned("不存在"))

    def test_learned_terms_list(self):
        """测试已学名词列表"""
        from memory.long_term import LongTermMemory

        ltm = LongTermMemory(data_path=self.temp_path)
        ltm.add_learned_term("区块链")
        ltm.add_learned_term("人工智能")

        terms = ltm.get_learned_terms()
        self.assertEqual(len(terms), 2)
        self.assertIn("区块链", terms)

    def test_user_preferences(self):
        """测试用户偏好"""
        from memory.long_term import LongTermMemory

        ltm = LongTermMemory(data_path=self.temp_path)
        ltm.set_preference("theme", "dark")
        ltm.set_preference("language", "zh")

        self.assertEqual(ltm.get_preference("theme"), "dark")
        self.assertEqual(ltm.get_preference("language"), "zh")
        self.assertIsNone(ltm.get_preference("not_exist"))

    def test_learning_history(self):
        """测试学习历史"""
        from memory.long_term import LongTermMemory

        ltm = LongTermMemory(data_path=self.temp_path)
        ltm.add_history("区块链", "learn", {"score": 90})
        ltm.add_history("人工智能", "review", {"score": 85})

        history = ltm.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['term'], "区块链")

    def test_stats(self):
        """测试统计信息"""
        from memory.long_term import LongTermMemory

        ltm = LongTermMemory(data_path=self.temp_path)
        ltm.add_learned_term("区块链")
        ltm.add_history("区块链", "learn")

        stats = ltm.get_stats()
        self.assertEqual(stats['total_terms'], 1)
        self.assertEqual(stats['total_history'], 1)


# ============================================================================
# Config Tests
# ============================================================================

class TestConfig(unittest.TestCase):
    """配置模块测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.yaml"

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_config_from_yaml(self):
        """测试从 YAML 加载配置"""
        from agent.config import load_config, get_config_path

        # 创建临时配置
        import yaml
        config_data = {
            'llm': {
                'provider': 'minimax',
                'model': 'MiniMax-M2.5',
                'api_key': 'test-key',
                'temperature': 0.5
            }
        }
        with open(self.config_path, 'w') as f:
            yaml.dump(config_data, f)

        # 临时修改路径
        original_get_path = get_config_path
        from agent import config
        config.get_config_path = lambda: self.config_path

        loaded = load_config()

        # 恢复
        config.get_config_path = original_get_path

        self.assertEqual(loaded['llm']['provider'], 'minimax')
        self.assertEqual(loaded['llm']['model'], 'MiniMax-M2.5')

    def test_env_override(self):
        """测试环境变量覆盖"""
        from agent.config import apply_env_overrides

        config = {'llm': {}}

        # 模拟环境变量
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'openai',
            'LLM_MODEL': 'gpt-4'
        }):
            result = apply_env_overrides(config)

        self.assertEqual(result['llm']['provider'], 'openai')
        self.assertEqual(result['llm']['model'], 'gpt-4')

    def test_default_config(self):
        """测试默认配置"""
        from agent.config import get_default_config

        config = get_default_config()
        self.assertIn('llm', config)
        self.assertIn('provider', config['llm'])
        self.assertIn('model', config['llm'])


# ============================================================================
# LLM Client Tests
# ============================================================================

class TestLLMClient(unittest.TestCase):
    """LLM 客户端测试"""

    def test_create_llm_client_mock(self):
        """测试创建 Mock 客户端"""
        from agent.llm_client import create_llm_client, MockLLMClient

        client = create_llm_client(provider='mock')
        self.assertIsInstance(client, MockLLMClient)

    def test_create_llm_client_minimax(self):
        """测试创建 MiniMax 客户端"""
        from agent.llm_client import create_llm_client, MiniMaxClient

        client = create_llm_client(
            provider='minimax',
            api_key='test-key',
            base_url='https://api.test.com',
            model='test-model'
        )
        self.assertIsInstance(client, MiniMaxClient)
        self.assertEqual(client.api_key, 'test-key')
        self.assertEqual(client.base_url, 'https://api.test.com')
        self.assertEqual(client.model, 'test-model')

    def test_mock_client_response(self):
        """测试 Mock 客户端响应"""
        from agent.llm_client import MockLLMClient

        client = MockLLMClient()
        messages = [{'role': 'user', 'content': '你好'}]
        response = client.chat(messages)

        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

    def test_get_llm_client(self):
        """测试获取全局 LLM 客户端"""
        from agent.llm_client import get_llm_client, reset_llm_client

        # 重置以确保干净状态
        reset_llm_client()

        client1 = get_llm_client()
        client2 = get_llm_client()

        # 应该返回同一实例
        self.assertIs(client1, client2)


# ============================================================================
# Intent Recognition Tests
# ============================================================================

class TestIntentRecognition(unittest.TestCase):
    """意图识别测试"""

    def setUp(self):
        """测试前设置"""
        from agent.intent import IntentRecognizer
        self.recognizer = IntentRecognizer()

    def test_learn_intent(self):
        """测试学习意图"""
        from agent.intent import Intent

        intent, entity, params = self.recognizer.recognize("/learn 区块链")
        self.assertEqual(intent, Intent.LEARN)
        self.assertEqual(params['content'], '区块链')

        intent, entity, params = self.recognizer.recognize("学习 机器学习")
        self.assertEqual(intent, Intent.LEARN)

    def test_session_intent(self):
        """测试会话意图"""
        from agent.intent import Intent

        intent, entity, params = self.recognizer.recognize("/sessions")
        self.assertEqual(intent, Intent.SESSIONS)

        intent, entity, params = self.recognizer.recognize("/sessions view abc123")
        self.assertEqual(intent, Intent.SESSIONS)
        self.assertEqual(params['action'], 'view')

    def test_tag_intent(self):
        """测试标签意图"""
        from agent.intent import Intent

        intent, entity, params = self.recognizer.recognize("/tag list")
        self.assertEqual(intent, Intent.TAG)
        self.assertEqual(entity, 'list')

        intent, entity, params = self.recognizer.recognize("/tag add 区块链 技术")
        self.assertEqual(intent, Intent.TAG)
        self.assertEqual(params['term'], '区块链')
        self.assertEqual(params['tag'], '技术')

    def test_view_intent(self):
        """测试查看意图"""
        from agent.intent import Intent

        intent, entity, params = self.recognizer.recognize("/view 区块链")
        self.assertEqual(intent, Intent.VIEW)
        self.assertEqual(params['term'], '区块链')

    def test_quit_intent(self):
        """测试退出意图"""
        from agent.intent import Intent

        for cmd in ["/exit", "/quit", "exit", "quit"]:
            intent, entity, params = self.recognizer.recognize(cmd)
            self.assertEqual(intent, Intent.QUIT, f"Failed for {cmd}")

    def test_help_intent(self):
        """测试帮助意图"""
        from agent.intent import Intent

        intent, entity, params = self.recognizer.recognize("/help")
        self.assertEqual(intent, Intent.HELP)

        intent, entity, params = self.recognizer.recognize("/help learn")
        self.assertEqual(intent, Intent.HELP)
        self.assertEqual(params['topic'], 'learn')


# ============================================================================
# Dialogue Manager Tests
# ============================================================================

class TestDialogueManager(unittest.TestCase):
    """对话管理器测试"""

    def setUp(self):
        """测试前设置"""
        # 临时文件用于测试
        self.temp_session_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        self.temp_session_file.write('{"sessions": [], "last_updated": ""}')
        self.temp_session_file.close()

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_session_file.name):
            os.unlink(self.temp_session_file.name)

    def test_dialogue_manager_init(self):
        """测试对话管理器初始化"""
        from agent.dialogue import DialogueManager

        dm = DialogueManager()
        self.assertIsNotNone(dm.short_memory)
        self.assertIsNotNone(dm.long_memory)
        self.assertIsNotNone(dm.knowledge_db)

    def test_start_session(self):
        """测试开始会话"""
        from agent.dialogue import DialogueManager

        dm = DialogueManager()
        result = dm.start_session()

        self.assertIsNotNone(result)
        # 可能有复习提醒，或者欢迎消息
        self.assertTrue(
            '欢迎' in result or '复习' in result,
            f"Unexpected result: {result}"
        )

    def test_handle_sessions_command(self):
        """测试 /sessions 命令"""
        from agent.dialogue import DialogueManager

        dm = DialogueManager()
        response = dm.handle_input("/sessions")

        self.assertIsInstance(response, str)
        # 应该包含 "会话历史" 或 "暂无"
        self.assertTrue(
            "会话历史" in response or "暂无" in response,
            f"Unexpected response: {response}"
        )

    def test_handle_learn_command(self):
        """测试 /learn 命令"""
        from agent.dialogue import DialogueManager

        dm = DialogueManager()
        # 使用一个确定没学过的概念
        response = dm.handle_input("/learn __test_concept__")

        self.assertIsInstance(response, str)

    def test_handle_unknown(self):
        """测试未知输入"""
        from agent.dialogue import DialogueManager

        dm = DialogueManager()
        response = dm.handle_input("这是一个随机的未知输入")

        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)


# ============================================================================
# Knowledge DB Tests
# ============================================================================

class TestKnowledgeDB(unittest.TestCase):
    """知识库测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_db = tempfile.NamedTemporaryFile(
            suffix='.db', delete=False
        )
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_knowledge_db_init(self):
        """测试知识库初始化"""
        from knowledge import KnowledgeDB

        db = KnowledgeDB(db_path=self.db_path)
        self.assertTrue(os.path.exists(self.db_path))

    def test_add_term(self):
        """测试添加名词"""
        from knowledge import KnowledgeDB, Term

        db = KnowledgeDB(db_path=self.db_path)
        term = Term(
            id="",
            name="测试术语",
            definition="这是一个测试定义",
            source="test"
        )

        term_id = db.add_term(term)
        self.assertIsNotNone(term_id)

        # 验证添加成功
        retrieved = db.get_term(term_id)
        self.assertEqual(retrieved.name, "测试术语")

    def test_get_term_by_name(self):
        """测试按名称获取名词"""
        from knowledge import KnowledgeDB, Term

        db = KnowledgeDB(db_path=self.db_path)
        term = Term(id="", name="区块链", definition="分布式账本")
        db.add_term(term)

        retrieved = db.get_term_by_name("区块链")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "区块链")

    def test_search_terms(self):
        """测试搜索名词"""
        from knowledge import KnowledgeDB, Term

        db = KnowledgeDB(db_path=self.db_path)
        db.add_term(Term(id="", name="区块链", definition="分布式账本技术"))
        db.add_term(Term(id="", name="人工智能", definition="AI技术"))

        results = db.search_terms("区块链", limit=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].name, "区块链")

    def test_add_tag(self):
        """测试添加标签"""
        from knowledge import KnowledgeDB, Tag

        db = KnowledgeDB(db_path=self.db_path)
        tag = Tag(id="", name="技术", color="#ff0000")

        tag_id = db.add_tag(tag)
        self.assertIsNotNone(tag_id)

        retrieved = db.get_tag_by_name("技术")
        self.assertEqual(retrieved.name, "技术")


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_session_flow(self):
        """测试完整会话流程"""
        from memory.context import ShortTermMemory
        from agent.dialogue import DialogueManager

        temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        temp_file.close()

        try:
            # 创建会话
            stm = ShortTermMemory(storage_path=temp_file.name)
            session = stm.create_session()

            # 添加消息
            stm.add_user_message("你好")
            stm.add_assistant_message("你好！")
            stm.add_user_message("我想学习机器学习")

            # 保存
            stm.save_session()

            # 重新加载
            stm2 = ShortTermMemory(storage_path=temp_file.name)
            sessions = stm2.list_sessions()

            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]['message_count'], 3)

        finally:
            os.unlink(temp_file.name)

    def test_config_to_llm_client_flow(self):
        """测试配置到 LLM 客户端流程"""
        from agent.config import get_default_config
        from agent.llm_client import create_llm_client

        config = get_default_config()
        client = create_llm_client(
            provider=config['llm']['provider'],
            api_key=config['llm'].get('api_key'),
            model=config['llm'].get('model')
        )

        self.assertIsNotNone(client)


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    # 解析命令行参数
    verbose = '-v' in sys.argv or '--verbose' in sys.argv

    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        # 运行特定测试类
        test_name = sys.argv[1]
        suite = unittest.TestSuite()
        try:
            suite.addTests(unittest.TestLoader().loadTestsFromName(test_name))
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            sys.exit(0 if result.wasSuccessful() else 1)
        except AttributeError:
            print(f"Test '{test_name}' not found")
            sys.exit(1)

    sys.exit(run_tests(verbose=verbose))
