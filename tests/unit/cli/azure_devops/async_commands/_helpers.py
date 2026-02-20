"""
Shared test helper functions for async_commands tests.
These complement the fixtures in conftest.py.
"""


def get_script_from_call(mock_popen):
    """Extract the Python script from the Popen call args."""
    call_args = mock_popen.call_args[0][0]
    return call_args[2] if len(call_args) > 2 else ""


def assert_function_in_script(script: str, module_path: str, function_name: str):
    """Assert that the generated script calls the correct module and function."""
    assert f"module_path = '{module_path}'" in script, f"Expected module_path='{module_path}' in script"
    assert f"function_name = '{function_name}'" in script, f"Expected function_name='{function_name}' in script"
