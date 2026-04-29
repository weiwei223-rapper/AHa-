"""Unit tests for the code compiler module."""

import pytest
from code_compiler import PythonCodeCompiler, CodeSyntaxValidator, execute_python_code


class TestCodeSyntaxValidator:
    """Tests for CodeSyntaxValidator class."""
    
    def test_validate_syntax_valid_code(self):
        """Test validation of syntactically correct code."""
        is_valid, error = CodeSyntaxValidator.validate_syntax('print("hello")')
        assert is_valid is True
        assert error is None
    
    def test_validate_syntax_invalid_code(self):
        """Test validation of syntactically incorrect code."""
        is_valid, error = CodeSyntaxValidator.validate_syntax('print("incomplete')
        assert is_valid is False
        assert "Syntax Error" in error
    
    def test_check_code_complexity_small_code(self):
        """Test complexity check for small code."""
        code = "print('hello')"
        is_safe, warning = CodeSyntaxValidator.check_code_complexity(code)
        assert is_safe is True
        assert warning is None
    
    def test_check_code_complexity_too_many_lines(self):
        """Test complexity check for code with too many lines."""
        code = "\n".join(["print(i)"] * 10001)
        is_safe, warning = CodeSyntaxValidator.check_code_complexity(code)
        assert is_safe is False
        assert "exceeds maximum line limit" in warning
    
    def test_check_code_complexity_too_large(self):
        """Test complexity check for code that's too large."""
        code = "a" * 1000001
        is_safe, warning = CodeSyntaxValidator.check_code_complexity(code)
        assert is_safe is False
        assert "exceeds maximum size limit" in warning


class TestPythonCodeCompiler:
    """Tests for PythonCodeCompiler class."""
    
    def test_compile_valid_code(self):
        """Test compiling valid code."""
        compiler = PythonCodeCompiler()
        is_valid, error = compiler.compile('print("hello")')
        assert is_valid is True
        assert error is None
    
    def test_compile_invalid_syntax(self):
        """Test compiling code with syntax errors."""
        compiler = PythonCodeCompiler()
        is_valid, error = compiler.compile('print("incomplete')
        assert is_valid is False
        assert "Syntax Error" in error
    
    def test_compile_unsafe_exec(self):
        """Test detection of unsafe exec."""
        compiler = PythonCodeCompiler(enable_security_check=True)
        is_valid, error = compiler.compile('exec("print(1)")')
        assert is_valid is False
        assert "Unsafe" in error
    
    def test_compile_unsafe_eval(self):
        """Test detection of unsafe eval."""
        compiler = PythonCodeCompiler(enable_security_check=True)
        is_valid, error = compiler.compile('eval("1 + 1")')
        assert is_valid is False
        assert "Unsafe" in error
    
    def test_compile_without_security_check(self):
        """Test compiling unsafe code with security check disabled."""
        compiler = PythonCodeCompiler(enable_security_check=False)
        is_valid, error = compiler.compile('exec("print(1)")')
        assert is_valid is True
        assert error is None
    
    def test_execute_simple_code(self):
        """Test executing simple Python code."""
        compiler = PythonCodeCompiler()
        output, error = compiler.execute('print("hello")')
        assert output == "hello\n"
        assert error == ""
    
    def test_execute_calculation(self):
        """Test executing mathematical calculation."""
        compiler = PythonCodeCompiler()
        output, error = compiler.execute('print(2 + 2)')
        assert output == "4\n"
        assert error == ""
    
    def test_execute_with_runtime_error(self):
        """Test executing code that causes runtime error."""
        compiler = PythonCodeCompiler()
        output, error = compiler.execute('print(1 / 0)')
        assert output == ""
        assert "ZeroDivisionError" in error
    
    def test_execute_with_syntax_error(self):
        """Test executing code with syntax error."""
        compiler = PythonCodeCompiler()
        output, error = compiler.execute('print("incomplete')
        assert output == ""
        assert "Syntax Error" in error
    
    def test_execute_loop(self):
        """Test executing code with loops."""
        compiler = PythonCodeCompiler()
        code = """
result = []
for i in range(5):
    result.append(i * 2)
print(result)
"""
        output, error = compiler.execute(code)
        assert "[0, 2, 4, 6, 8]" in output
        assert error == ""
    
    def test_execute_function_definition(self):
        """Test executing code with function definition."""
        compiler = PythonCodeCompiler()
        code = """
def add(a, b):
    return a + b

print(add(3, 4))
"""
        output, error = compiler.execute(code)
        assert "7" in output
        assert error == ""
    
    def test_execute_timeout(self):
        """Test execution timeout."""
        compiler = PythonCodeCompiler(timeout=1)
        code = """
import time
time.sleep(5)
print("should not reach here")
"""
        output, error = compiler.execute(code)
        assert output == ""
        assert "timeout" in error.lower()
    
    def test_execute_max_output_size(self):
        """Test truncation of large output."""
        compiler = PythonCodeCompiler()
        code = 'print("a" * 200000)'
        output, error = compiler.execute(code)
        assert len(output) <= compiler.MAX_OUTPUT_SIZE + 100  # Small buffer for truncation message
        assert "truncated" in output or len(output) == compiler.MAX_OUTPUT_SIZE


class TestModuleLevelFunction:
    """Tests for module-level execute_python_code function."""
    
    def test_execute_python_code_simple(self):
        """Test module-level execute_python_code function."""
        output, error = execute_python_code('print("hello world")')
        assert output == "hello world\n"
        assert error == ""
    
    def test_execute_python_code_with_calculation(self):
        """Test execution with mathematical operations."""
        output, error = execute_python_code('print(10 * 5)')
        assert "50" in output
        assert error == ""
    
    def test_execute_python_code_unsafe_with_check(self):
        """Test unsafe code detection."""
        output, error = execute_python_code('exec("print(1)")', enable_security_check=True)
        assert output == ""
        assert "Unsafe" in error
    
    def test_execute_python_code_unsafe_without_check(self):
        """Test unsafe code without security check (runs successfully when disabled)."""
        output, error = execute_python_code('exec("print(1)")', enable_security_check=False)
        # When security check is disabled, exec should run successfully
        assert "1" in output
        assert error == ""
