"""
Test agent configurations
"""
import sys
sys.path.insert(0, '/home/ubuntu/neurocomputer')

from core.agent_configs import AGENT_CONFIGS

def test_agent_configs_exist():
    """Test that expected agent types exist."""
    assert "neuro" in AGENT_CONFIGS, "neuro agent type missing"
    assert "upwork" in AGENT_CONFIGS, "upwork agent type missing"
    print("✅ Agent configs exist: neuro, upwork")

def test_neuro_config():
    """Test neuro agent config."""
    neuro = AGENT_CONFIGS["neuro"]
    assert neuro.name == "Neuro"
    assert neuro.planner_neuro == "planner"
    assert neuro.replier_neuro == "reply"
    print("✅ Neuro config correct")

def test_upwork_config():
    """Test upwork agent config."""
    upwork = AGENT_CONFIGS["upwork"]
    assert upwork.name == "Upwork"
    print("✅ Upwork config correct")

if __name__ == "__main__":
    test_agent_configs_exist()
    test_neuro_config()
    test_upwork_config()
    print("\n=== All config tests passed! ===")
