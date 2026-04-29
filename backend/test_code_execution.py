"""Tests for the improved code execution endpoint."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from main import app
    return TestClient(app)


def test_execute_code_simple_print(client):
    """Test executing simple Python print statement."""
    response = client.post("/api/execute-code", json={"code": 'print("Hello")'})
    assert response.status_code == 200
    data = response.json()
    assert data["output"] == "Hello\n"
    assert data["error"] == ""


def test_execute_code_calculation(client):
    """Test executing mathematical calculation."""
    response = client.post("/api/execute-code", json={"code": "print(2 + 2 * 3)"})
    assert response.status_code == 200
    data = response.json()
    assert data["output"] == "8\n"
    assert data["error"] == ""


def test_execute_code_syntax_error(client):
    """Test handling of syntax errors."""
    response = client.post("/api/execute-code", json={"code": 'print("incomplete'})
    assert response.status_code == 200
    data = response.json()
    assert data["output"] == ""
    assert "Syntax Error" in data["error"]


def test_execute_code_runtime_error(client):
    """Test handling of runtime errors."""
    response = client.post("/api/execute-code", json={"code": "print(1 / 0)"})
    assert response.status_code == 200
    data = response.json()
    assert data["output"] == ""
    assert "ZeroDivisionError" in data["error"]


def test_execute_code_empty_code(client):
    """Test handling of empty code."""
    response = client.post("/api/execute-code", json={"code": ""})
    assert response.status_code == 200
    data = response.json()
    assert "empty" in data["error"].lower()


def test_execute_code_loop(client):
    """Test executing code with loops."""
    code = """
result = []
for i in range(5):
    result.append(i * 2)
print(result)
"""
    response = client.post("/api/execute-code", json={"code": code})
    assert response.status_code == 200
    data = response.json()
    assert "[0, 2, 4, 6, 8]" in data["output"]
    assert data["error"] == ""


def test_execute_code_unsafe_exec(client):
    """Test detection of unsafe exec operation."""
    response = client.post("/api/execute-code", json={"code": 'exec("print(1)")'})
    assert response.status_code == 200
    data = response.json()
    assert data["output"] == ""
    assert "Unsafe operation" in data["error"]


def test_execute_code_unsafe_eval(client):
    """Test detection of unsafe eval operation."""
    response = client.post("/api/execute-code", json={"code": 'eval("1 + 2")'})
    assert response.status_code == 200
    data = response.json()
    assert data["output"] == ""
    assert "Unsafe operation" in data["error"]


def test_execute_code_list_operations(client):
    """Test list operations."""
    code = """
numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers]
print(sum(squared))
"""
    response = client.post("/api/execute-code", json={"code": code})
    assert response.status_code == 200
    data = response.json()
    assert "55" in data["output"]
    assert data["error"] == ""


def test_execute_code_string_operations(client):
    """Test string operations."""
    code = """
text = "hello world"
print(text.upper())
print(len(text))
"""
    response = client.post("/api/execute-code", json={"code": code})
    assert response.status_code == 200
    data = response.json()
    assert "HELLO WORLD" in data["output"]
    assert "11" in data["output"]
    assert data["error"] == ""


def test_execute_code_function_definition(client):
    """Test defining and calling functions."""
    code = """
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
"""
    response = client.post("/api/execute-code", json={"code": code})
    assert response.status_code == 200
    data = response.json()
    assert "Hello, World!" in data["output"]
    assert data["error"] == ""
