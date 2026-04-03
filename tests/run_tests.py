#!/usr/bin/env python3
"""
Run all tests for the multi-agent system.
Usage: python3 tests/run_tests.py
"""
import subprocess
import sys

def run_test(name, command):
    print(f"\n{'='*50}")
    print(f"Running: {name}")
    print('='*50)
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        print(f"❌ FAILED: {name}")
        return False
    print(f"✅ PASSED: {name}")
    return True

def main():
    tests = [
        ("Agent Configs", "python3 tests/test_agent_configs.py"),
        ("Agent Manager", "python3 tests/test_agent_manager.py"),
        ("Agent Class", "python3 tests/test_agent.py"),
        ("Server API", "python3 tests/test_api.py"),
        ("Upwork Neuros", "python3 tests/test_upwork.py"),
    ]

    results = []
    for name, cmd in tests:
        results.append(run_test(name, cmd))

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    passed = sum(results)
    total = len(results)
    print(f"{passed}/{total} test suites passed")

    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
