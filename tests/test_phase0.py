"""Luca Phase 0 test suite.

Covers: config, state, memory, safety, tools, controller lifecycle.
Run with:  python -m pytest tests/ -v
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from config import (Identity, IdentityConfig, LLMConfig, SafetyConfig,
                     Settings, load_settings)
from state import AppState, StateManager
from memory import (MemoryCategory, MemoryItem, MemoryManager,
                     SQLiteMemoryStore)
from safety import (PermissionDecision, PermissionManager, RiskLevel,
                     classify_risk, validate_tool_call)
from tools import Tool, ToolRegistry, ToolResult


# ═══════════════════════════════════════════════════════════════════════
#  CONFIG TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_defaults(self):
        s = Settings()
        assert s.identity.assistant_name == "Luca"
        assert s.identity.user_title == "Boss"
        assert s.debug is False

    def test_paths_resolve(self):
        s = Settings()
        assert s.project_root != ""
        assert s.data_dir != ""
        assert s.user_data_dir != ""
        assert s.memory.sqlite_path.endswith("luca_memory.db")

    def test_env_overrides(self):
        os.environ["LUCA_DEBUG"] = "true"
        os.environ["OLLAMA_MODEL"] = "test-model"
        try:
            s = load_settings(apply_env=True)
            assert s.debug is True
            assert s.llm.model == "test-model"
        finally:
            del os.environ["LUCA_DEBUG"]
            del os.environ["OLLAMA_MODEL"]

    def test_identity_from_config(self):
        cfg = IdentityConfig(assistant_name="Aria", user_title="Chief")
        ident = Identity(cfg)
        assert ident.assistant_name == "Aria"
        assert "Chief" in ident.greeting()
        assert "Aria" in ident.greeting()

    def test_load_settings_no_crash(self):
        s = load_settings(apply_env=False)
        assert isinstance(s, Settings)


# ═══════════════════════════════════════════════════════════════════════
#  STATE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestState:
    def test_initial_state(self):
        sm = StateManager()
        assert sm.state is AppState.INITIALIZING

    def test_transition(self):
        sm = StateManager()
        sm.transition(AppState.STANDBY)
        assert sm.state is AppState.STANDBY

    def test_no_op_same_state(self):
        sm = StateManager()
        sm.transition(AppState.INITIALIZING)  # same as initial
        assert sm.state is AppState.INITIALIZING

    def test_listener_called(self):
        transitions = []
        sm = StateManager()
        sm.add_listener(lambda old, new: transitions.append((old, new)))
        sm.transition(AppState.STANDBY)
        sm.transition(AppState.THINKING)
        assert len(transitions) == 2
        assert transitions[0] == (AppState.INITIALIZING, AppState.STANDBY)
        assert transitions[1] == (AppState.STANDBY, AppState.THINKING)

    def test_remove_listener(self):
        calls = []
        fn = lambda old, new: calls.append(1)
        sm = StateManager()
        sm.add_listener(fn)
        sm.transition(AppState.STANDBY)
        sm.remove_listener(fn)
        sm.transition(AppState.THINKING)
        assert len(calls) == 1  # only the first transition

    def test_listener_exception_doesnt_crash(self):
        def bad_listener(old, new):
            raise ValueError("oops")
        sm = StateManager()
        sm.add_listener(bad_listener)
        sm.transition(AppState.STANDBY)  # should NOT raise
        assert sm.state is AppState.STANDBY


# ═══════════════════════════════════════════════════════════════════════
#  MEMORY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestMemory:
    def _make_manager(self, tmp_path: Path) -> MemoryManager:
        store = SQLiteMemoryStore(str(tmp_path / "test.db"))
        mgr = MemoryManager(store)
        mgr.initialize()
        return mgr

    def test_init_creates_db(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert Path(tmp_path / "test.db").exists()
        mgr.close()

    def test_remember_and_recall(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        item_id = mgr.remember("I like coffee", key="preference")
        assert isinstance(item_id, str) and len(item_id) > 0
        results = mgr.recall("coffee")
        assert len(results) >= 1
        assert any("coffee" in r.content for r in results)
        mgr.close()

    def test_forget(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        item_id = mgr.remember("delete me")
        assert mgr.forget(item_id) is True
        assert mgr.get(item_id) is None
        mgr.close()

    def test_get(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        item_id = mgr.remember("test item", category=MemoryCategory.PROJECT, importance=0.9)
        item = mgr.get(item_id)
        assert item is not None
        assert item.content == "test item"
        assert item.category is MemoryCategory.PROJECT
        assert item.importance == 0.9
        mgr.close()

    def test_search_by_category(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.remember("python project", category=MemoryCategory.PROJECT)
        mgr.remember("prefer dark mode", category=MemoryCategory.PREFERENCE)
        results = mgr.recall("project", category=MemoryCategory.PROJECT)
        assert all(r.category is MemoryCategory.PROJECT for r in results)
        mgr.close()

    def test_forget_nonexistent(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.forget("nonexistent-id") is False
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════
#  SAFETY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSafety:
    def test_risk_classification(self):
        assert classify_risk("open_application") is RiskLevel.LOW
        assert classify_risk("create_file") is RiskLevel.MEDIUM
        assert classify_risk("delete_file") is RiskLevel.HIGH
        assert classify_risk("unknown_op") is RiskLevel.MEDIUM  # default

    def test_validator_blocks_dangerous(self):
        r = validate_tool_call("shell", {"command": "rm -rf /"})
        assert r.valid is False

        r = validate_tool_call("shell", {"command": "format C:"})
        assert r.valid is False

    def test_validator_allows_safe(self):
        r = validate_tool_call("files", {"path": "/some/file.txt"})
        assert r.valid is True

    def test_validator_rejects_empty_name(self):
        r = validate_tool_call("", {})
        assert r.valid is False

    def test_permission_low_auto_approve(self):
        pm = PermissionManager(SafetyConfig(auto_approve_low_risk=True))
        r = pm.check("open_application")
        assert r.decision is PermissionDecision.ALLOW

    def test_permission_medium_asks(self):
        pm = PermissionManager(SafetyConfig(auto_approve_medium_risk=False))
        r = pm.check("create_file")
        assert r.decision is PermissionDecision.ASK

    def test_permission_high_blocked(self):
        pm = PermissionManager(SafetyConfig(block_high_risk=True))
        r = pm.check("delete_file")
        assert r.decision is PermissionDecision.DENY

    def test_permission_high_asks_when_not_blocked(self):
        pm = PermissionManager(SafetyConfig(block_high_risk=False))
        r = pm.check("delete_file")
        assert r.decision is PermissionDecision.ASK


# ═══════════════════════════════════════════════════════════════════════
#  TOOLS TESTS
# ═══════════════════════════════════════════════════════════════════════

class _DummyTool(Tool):
    @property
    def name(self):
        return "dummy"
    @property
    def description(self):
        return "A test tool"
    def execute(self, **kwargs):
        return ToolResult(success=True, output="ok")


class TestTools:
    def test_register_and_get(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        assert reg.get("dummy") is not None
        assert reg.get("nonexistent") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        assert "dummy" in reg.tool_names

    def test_execute(self):
        t = _DummyTool()
        result = t.execute()
        assert result.success is True
        assert result.output == "ok"


# ═══════════════════════════════════════════════════════════════════════
#  CONTROLLER TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestController:
    def _make_ctrl(self, tmp_path: Path):
        s = load_settings(apply_env=False)
        s.user_data_dir = str(tmp_path / "user_data")
        s.data_dir = str(tmp_path / "data")
        s.logs_dir = str(tmp_path / "logs")
        s.models_dir = str(tmp_path / "models")
        s.memory.sqlite_path = str(tmp_path / "test.db")
        from controller import Controller
        return Controller(s)

    def test_startup_and_shutdown(self, tmp_path):
        ctrl = self._make_ctrl(tmp_path)
        ctrl.start()
        assert ctrl.state.state is AppState.STANDBY
        ctrl.shutdown()
        assert ctrl.state.state is AppState.SHUTTING_DOWN

    def test_chat_without_llm(self, tmp_path):
        ctrl = self._make_ctrl(tmp_path)
        ctrl.start()
        response = ctrl.chat("hello")
        # Without Ollama running, should return a friendly fallback
        assert "LLM" in response or "Ollama" in response or ctrl.identity.assistant_name in response
        ctrl.shutdown()

    def test_chat_empty_input(self, tmp_path):
        ctrl = self._make_ctrl(tmp_path)
        ctrl.start()
        assert ctrl.chat("") == ""
        ctrl.shutdown()

    def test_identity_accessible(self, tmp_path):
        ctrl = self._make_ctrl(tmp_path)
        assert ctrl.identity.assistant_name == "Luca"
        assert ctrl.identity.user_title == "Boss"

    def test_directories_created(self, tmp_path):
        ctrl = self._make_ctrl(tmp_path)
        ctrl.start()
        assert Path(ctrl.settings.user_data_dir).exists()
        assert Path(ctrl.settings.logs_dir).exists()
        ctrl.shutdown()
