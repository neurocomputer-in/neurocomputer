"""
Test Upwork neuros (syntax check only).
"""
import sys
import os
sys.path.insert(0, '/home/ubuntu/neurocomputer')

def test_upwork_neuros_exist():
    """Verify all upwork neuros exist."""
    base = "/home/ubuntu/neurocomputer/neuros"
    neuros = ["upwork_save_frame", "upwork_finalize", "upwork_analyze", "upwork_proposal", "upwork_list"]

    for neuro in neuros:
        neuro_dir = os.path.join(base, neuro)
        assert os.path.isdir(neuro_dir), f"Missing neuro: {neuro}"

        conf_file = os.path.join(neuro_dir, "conf.json")
        code_file = os.path.join(neuro_dir, "code.py")

        assert os.path.exists(conf_file), f"Missing conf.json: {neuro}"
        assert os.path.exists(code_file), f"Missing code.py: {neuro}"
        print(f"✅ {neuro}: conf.json and code.py exist")

def test_upwork_neuros_syntax():
    """Verify upwork neuros compile."""
    import py_compile

    base = "/home/ubuntu/neurocomputer/neuros"
    neuros = ["upwork_save_frame", "upwork_finalize", "upwork_analyze", "upwork_proposal", "upwork_list"]

    for neuro in neuros:
        code_file = os.path.join(base, neuro, "code.py")
        try:
            py_compile.compile(code_file, doraise=True)
            print(f"✅ {neuro}: syntax OK")
        except py_compile.PyCompileError as e:
            print(f"❌ {neuro}: syntax error - {e}")
            return False
    return True

def test_upwork_api_endpoints():
    """Verify upwork API endpoints in server.py."""
    with open('/home/ubuntu/neurocomputer/server.py', 'r') as f:
        code = f.read()

    endpoints = [
        '/upwork/capture',
        '/upwork/finalize',
        '/upwork/jobs',
        '/upwork/job/'
    ]

    for endpoint in endpoints:
        assert endpoint in code, f"Missing endpoint: {endpoint}"
        print(f"✅ Endpoint: {endpoint}")

if __name__ == "__main__":
    print("=== Testing Upwork Neuros ===")
    test_upwork_neuros_exist()
    test_upwork_neuros_syntax()
    test_upwork_api_endpoints()
    print("\n=== All Upwork tests passed! ===")
