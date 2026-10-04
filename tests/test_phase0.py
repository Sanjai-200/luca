"""Luca OOP Phase 0 test suite.

Covers: config, orchestrator state, memory manager, permissions, tools.
Run with:  python -m pytest tests/test_phase0.py -v
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.bootstrap import LucaConfig, load_config
from core.interfaces import AppState, RiskLevel, PermissionDecision
from application.orchestrator import Orchestrator
from application.memory_manager import MemoryManager
from infrastructure.sqlite_memory import SQLiteMemoryStore
from tools.registry import ToolRegistry
from security.permissions import PermissionManager, SafetyConfig, classify_risk, validate_tool_call


# ═══════════════════════════════════════════════════════════════════════
#  CONFIG TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_defaults(self):
        s = LucaConfig()
        assert s.assistant_name == "Luca"
        assert s.user_title == "Boss"
        assert s.debug is False

    def test_paths_resolve(self):
        s = LucaConfig()
        assert s.project_root != ""
        assert s.data_dir != ""
        assert s.user_data_dir != ""
        assert s.sqlite_path.endswith("luca_memory.db")

    def test_env_overrides(self):
        os.environ["LUCA_DEBUG"] = "true"
        os.environ["OLLAMA_MODEL"] = "test-model"
        try:
            s = load_config()
            assert s.debug is True
            assert s.ai_model == "test-model"
        finally:
            del os.environ["LUCA_DEBUG"]
            del os.environ["OLLAMA_MODEL"]


# ═══════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR STATE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestState:
    def test_initial_state(self):
        # Build empty dependencies
        memory = MemoryManager(SQLiteMemoryStore(":memory:"))
        tools = ToolRegistry()
        orchestrator = Orchestrator(ai_provider=None, memory=memory, tool_registry=tools)
        assert orchestrator.state is AppState.INITIALIZING

    def test_transition_on_start(self):
        memory = MemoryManager(SQLiteMemoryStore(":memory:"))
        tools = ToolRegistry()
        orchestrator = Orchestrator(ai_provider=None, memory=memory, tool_registry=tools)
        orchestrator.start()
        assert orchestrator.state is AppState.STANDBY


# ═══════════════════════════════════════════════════════════════════════
#  MEMORY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestMemory:
    @pytest.fixture
    def memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            store = SQLiteMemoryStore(str(db_path))
            mgr = MemoryManager(store)
            mgr.initialize()
            yield mgr
            mgr.close()

    def test_save_and_get(self, memory):
        item_id = memory.remember("test content")
        assert item_id is not None
        
        item = memory.get(item_id)
        assert item is not None
        assert item.content == "test content"

    def test_search(self, memory):
        memory.remember("python developer", key="skill")
        memory.remember("rust developer", key="skill")
        
        results = memory.recall("python")
        assert len(results) == 1
        assert "python" in results[0].content.lower()

    def test_delete(self, memory):
        item_id = memory.remember("delete me")
        assert memory.get(item_id) is not None
        
        memory.forget(item_id)
        assert memory.get(item_id) is None


# ═══════════════════════════════════════════════════════════════════════
#  SAFETY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSafety:
    def test_classification(self):
        assert classify_risk("run_shell") is RiskLevel.HIGH
        assert classify_risk("open_app") is RiskLevel.LOW
        assert classify_risk("type_keys") is RiskLevel.MEDIUM

    def test_validation_safe(self):
        res = validate_tool_call("run_shell", {"command": "echo hello"})
        assert res.valid is True

    def test_validation_dangerous(self):
        res = validate_tool_call("run_shell", {"command": "rm -rf /"})
        assert res.valid is False
        assert "Dangerous pattern" in res.reason

    def test_permission_defaults(self):
        pm = PermissionManager(SafetyConfig())
        
        # low risk -> allowed
        res = pm.check("open_app")
        assert res.decision is PermissionDecision.ALLOW
        
        # medium risk -> ask
        res = pm.check("type_keys")
        assert res.decision is PermissionDecision.ASK
        
        # high risk -> ask
        res = pm.check("run_shell")
        assert res.decision is PermissionDecision.ASK


class TestCloseAppTool:
    def test_close_app_spec(self):
        from tools.system_tools import CloseAppTool
        tool = CloseAppTool()
        assert tool.name == "close_app"
        assert tool.risk_level.value == "low"
        assert "target" in tool.spec.parameters

    def test_close_app_not_running(self):
        from tools.system_tools import CloseAppTool
        tool = CloseAppTool()
        res = tool.execute(target="nonexistent_process_12345")
        assert res.success is True
        assert "not running" in res.output


class TestPressKeyTool:
    def test_press_key_spec(self):
        from tools.system_tools import PressKeyTool
        tool = PressKeyTool()
        assert tool.name == "press_key"
        assert tool.risk_level.value == "medium"
        assert "key" in tool.spec.parameters

    def test_press_key_validation(self):
        from tools.system_tools import PressKeyTool
        tool = PressKeyTool()
        assert tool.validate(key="enter") is True
        assert tool.validate(key="") is False


class TestSearchWebTool:
    def test_search_web_spec(self):
        from tools.system_tools import SearchWebTool
        tool = SearchWebTool()
        assert tool.name == "search_web"
        assert tool.risk_level.value == "low"
        assert "query" in tool.spec.parameters

    def test_search_web_validation(self):
        from tools.system_tools import SearchWebTool
        tool = SearchWebTool()
        assert tool.validate(query="foods") is True
        assert tool.validate(query="") is False
