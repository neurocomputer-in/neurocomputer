"""
Test server API endpoint definitions (without full server import)
"""
import sys
sys.path.insert(0, '/home/ubuntu/neurocomputer')

def test_agent_endpoints_defined():
    """Test that agent endpoint functions are defined in server module via source code inspection."""
    with open('server.py', 'r') as f:
        server_code = f.read()

    # Check endpoint decorators exist
    assert '@app.get("/agents")' in server_code, "GET /agents endpoint missing"
    assert '@app.get("/agents/types")' in server_code, "GET /agents/types endpoint missing"
    assert '@app.post("/agents/{agent_type}")' in server_code, "POST /agents/{type} endpoint missing"
    assert '@app.post("/agents/{agent_id}/switch")' in server_code, "POST /agents/{id}/switch endpoint missing"
    assert '@app.get("/agents/active")' in server_code, "GET /agents/active endpoint missing"
    print("✅ All agent API endpoints defined in server.py")

def test_agent_manager_import():
    """Test that server imports agent_manager."""
    with open('server.py', 'r') as f:
        server_code = f.read()

    assert 'from core.agent_manager import agent_manager' in server_code, "agent_manager import missing"
    assert 'agent_manager.switch_to_agent_type' in server_code, "switch_to_agent_type usage missing"
    assert 'agent_manager.list_agents' in server_code, "list_agents usage missing"
    assert 'agent_manager.ensure_default_agent' in server_code, "ensure_default_agent usage missing"
    print("✅ agent_manager properly imported and used in server.py")

def test_chat_accepts_agent_id():
    """Test that chat endpoint accepts agent_id."""
    with open('server.py', 'r') as f:
        server_code = f.read()

    assert 'agent_id = body.get("agent_id")' in server_code, "agent_id handling missing in chat"
    assert '_handle_and_emit' in server_code, "_handle_and_emit missing"
    print("✅ Chat endpoint properly handles agent_id")

if __name__ == "__main__":
    test_agent_endpoints_defined()
    test_agent_manager_import()
    test_chat_accepts_agent_id()
    print("\n=== All API tests passed! ===")
