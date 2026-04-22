"""
Test agent manager (without Brain initialization)
"""
import sys
sys.path.insert(0, '/home/ubuntu/neurocomputer')

# Test just the AgentConfig and agent manager logic
from core.agent import AgentConfig

def test_agent_config_dataclass():
    """Test AgentConfig creation."""
    config = AgentConfig(
        name="Test Agent",
        description="Test description",
        router_neuro="test_router",
        planner_neuro="test_planner"
    )
    assert config.name == "Test Agent"
    assert config.router_neuro == "test_router"
    print("✅ AgentConfig dataclass works")

def test_agent_manager_singleton():
    """Test AgentManager is a singleton."""
    from core.agent_manager import AgentManager

    mgr1 = AgentManager()
    mgr2 = AgentManager()
    assert mgr1 is mgr2, "AgentManager should be singleton"
    print("✅ AgentManager is singleton")

def test_agent_manager_state():
    """Test AgentManager internal state."""
    from core.agent_manager import AgentManager

    mgr = AgentManager()
    # Initial state should be empty
    assert len(mgr.agents) == 0, "Should start with no agents"
    assert mgr.active_agent_id is None, "No active agent initially"
    print("✅ AgentManager initial state correct")

def test_agent_manager_list_types():
    """Test listing agent types."""
    from core.agent_manager import AgentManager

    mgr = AgentManager()
    types = mgr.list_agent_types()
    assert len(types) >= 2, "Should have at least neuro and upwork"
    type_names = [t["type"] for t in types]
    assert "neuro" in type_names, "Should have neuro"
    assert "upwork" in type_names, "Should have upwork"
    print(f"✅ Agent types: {type_names}")

if __name__ == "__main__":
    test_agent_config_dataclass()
    test_agent_manager_singleton()
    test_agent_manager_state()
    test_agent_manager_list_types()
    print("\n=== All agent manager tests passed! ===")
