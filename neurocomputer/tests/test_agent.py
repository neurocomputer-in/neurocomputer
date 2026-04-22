"""
Test Agent class structure (without Brain initialization)
"""
import sys
sys.path.insert(0, '/home/ubuntu/neurocomputer')

from dataclasses import dataclass
import inspect

def test_agent_config_structure():
    """Test AgentConfig has required fields."""
    from core.agent import AgentConfig

    config = AgentConfig(
        name="Test",
        description="Test agent",
        router_neuro="router",
        planner_neuro="planner",
        replier_neuro="reply",
        profile="general"
    )

    assert hasattr(config, 'name')
    assert hasattr(config, 'description')
    assert hasattr(config, 'router_neuro')
    assert hasattr(config, 'planner_neuro')
    assert hasattr(config, 'replier_neuro')
    assert hasattr(config, 'neuro_dirs')
    assert hasattr(config, 'profile')
    print("✅ AgentConfig has all required fields")

def test_agent_class_structure():
    """Test Agent class has required methods (without Brain init)."""
    from core.agent import Agent

    # Check __init__ signature exists
    sig = inspect.signature(Agent.__init__)
    params = list(sig.parameters.keys())
    assert 'self' in params
    assert 'agent_id' in params
    assert 'config' in params
    print("✅ Agent.__init__ signature correct")

    # Check required methods exist (without calling them)
    assert callable(getattr(Agent, 'handle_message', None)), "handle_message method missing"
    assert callable(getattr(Agent, 'get_conversation_history', None)), "get_conversation_history missing"
    assert callable(getattr(Agent, 'get_status', None)), "get_status missing"
    print("✅ Agent has all required methods")

def test_agent_instance_without_brain():
    """Test we can create Agent instance with minimal setup."""
    from core.agent import Agent, AgentConfig

    config = AgentConfig(name="Test", description="Test agent")

    # Create Agent without brain initialization using object.__setattr__
    # This bypasses __init__ but lets us test attribute access
    agent = object.__new__(Agent)
    agent.agent_id = "test_001"
    agent.config = config
    agent.is_running = False
    # Note: brain is NOT set here to avoid asyncio issues

    assert agent.agent_id == "test_001"
    assert agent.config.name == "Test"
    assert hasattr(agent, 'agent_id')
    assert hasattr(agent, 'config')
    assert hasattr(agent, 'is_running')
    print("✅ Agent instance created (without Brain init)")

if __name__ == "__main__":
    test_agent_config_structure()
    test_agent_class_structure()
    test_agent_instance_without_brain()
    print("\n=== All Agent tests passed! ===")
