"""Enhanced Python code compiler and executor with validation and safety features."""

import ast
import subprocess
import sys
import tempfile
import os
import re
from typing import Optional, Tuple
from pathlib import Path


class CodeCompilationError(Exception):
    """Exception raised during code compilation."""
    pass


class CodeSyntaxValidator:
    """Validates Python code syntax before execution."""
    
    @staticmethod
    def validate_syntax(code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Python code syntax.
        Returns (is_valid, error_message)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            error_msg = f"Syntax Error at line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\n  {e.text.strip()}"
                error_msg += f"\n  {' ' * (e.offset - 1)}^"
            return False, error_msg
        except Exception as e:
            return False, f"Parse Error: {str(e)}"
    
    @staticmethod
    def check_code_complexity(code: str) -> Tuple[bool, Optional[str]]:
        """
        Check if code is too complex or suspiciously large.
        Returns (is_safe, warning_message)
        """
        lines = code.split('\n')
        if len(lines) > 10000:
            return False, "Code exceeds maximum line limit (10000 lines)"
        
        if len(code) > 1000000:
            return False, "Code exceeds maximum size limit (1MB)"
        
        return True, None


class PythonCodeCompiler:
    """Compiles and executes Python code safely."""
    
    UNSAFE_KEYWORDS = {
        'exec', 'eval', '__import__', '__builtins__',
        'compile', 'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr', 'hasattr',
        'open', 'input', 'raw_input', 'file',
    }
    
    DEFAULT_TIMEOUT = 10  # seconds
    MAX_OUTPUT_SIZE = 100000  # characters
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, enable_security_check: bool = True):
        """
        Initialize the compiler.
        
        Args:
            timeout: Maximum execution time in seconds
            enable_security_check: Whether to check for unsafe operations
        """
        self.timeout = timeout
        self.enable_security_check = enable_security_check
    
    def _check_security(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Check for potentially unsafe code patterns.
        Returns (is_safe, warning_message)
        """
        if not self.enable_security_check:
            return True, None
        
        # Check for unsafe keywords
        for keyword in self.UNSAFE_KEYWORDS:
            # Use word boundaries to avoid false positives (e.g., 'open' in 'reopen')
            if re.search(rf'\b{keyword}\b', code):
                # Some keywords might be in comments/strings, check more carefully
                try:
                    tree = ast.parse(code)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Name) and node.id == keyword:
                            return False, f"Unsafe operation detected: '{keyword}' is not allowed"
                except:
                    pass
        
        return True, None
    
    def compile(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Compile Python code to check for syntax errors.
        Returns (is_valid, error_message)
        """
        # Check syntax
        is_valid, error = CodeSyntaxValidator.validate_syntax(code)
        if not is_valid:
            return False, error
        
        # Check complexity
        is_safe, warning = CodeSyntaxValidator.check_code_complexity(code)
        if not is_safe:
            return False, warning
        
        # Check security if enabled
        if self.enable_security_check:
            is_safe, warning = self._check_security(code)
            if not is_safe:
                return False, warning
        
        return True, None
    
    def execute(self, code: str, timeout: Optional[int] = None) -> Tuple[str, str]:
        """
        Execute Python code using Docker for sandboxing.
        
        Args:
            code: Python code to execute
            timeout: Override default timeout
            
        Returns:
            Tuple of (stdout, stderr)
        """
        # Validate code first
        is_valid, error = self.compile(code)
        if not is_valid:
            return "", error
        
        exec_timeout = timeout or self.timeout
        
        try:
            # Check if Docker is available
            use_docker = os.getenv("USE_DOCKER_SANDBOX", "true").lower() == "true"
            
            if use_docker:
                try:
                    # Execute using Docker
                    # --rm: Remove container after execution
                    # --network none: Disable networking for security
                    # --memory 128m: Limit memory usage
                    # --cpus 0.5: Limit CPU usage
                    # --read-only: Make root filesystem read-only (if possible, but might break some things)
                    
                    # We pass the code via stdin to avoid file mounting complexities
                    result = subprocess.run(
                        [
                            "docker", "run", "--rm", "-i",
                            "--network", "none",
                            "--memory", "128m",
                            "--cpus", "0.5",
                            "aha-python-executor",
                            "python", "-c", code
                        ],
                        capture_output=True,
                        text=True,
                        timeout=exec_timeout,
                        encoding='utf-8'
                    )
                    
                    output = result.stdout[:self.MAX_OUTPUT_SIZE]
                    error = result.stderr[:self.MAX_OUTPUT_SIZE]
                    
                    if len(result.stdout) > self.MAX_OUTPUT_SIZE:
                        output += f"\n... [output truncated]"
                    if len(result.stderr) > self.MAX_OUTPUT_SIZE:
                        error += f"\n... [error truncated]"
                    
                    return output, error
                except subprocess.CalledProcessError as e:
                    return e.stdout, e.stderr
                except FileNotFoundError:
                    # Docker not installed, fallback to local (log warning in real app)
                    pass
            
            # Fallback to local execution (original logic)
            # Create temporary file with explicit utf-8 encoding
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name
            
            try:
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"

                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=exec_timeout,
                    cwd=os.path.dirname(temp_file),
                    encoding='utf-8',
                    env=env
                )
                
                output = result.stdout[:self.MAX_OUTPUT_SIZE]
                error = result.stderr[:self.MAX_OUTPUT_SIZE]
                
                return output, error
                
            finally:
                try: os.unlink(temp_file)
                except: pass
        
        except subprocess.TimeoutExpired:
            return "", f"Execution timeout: Code took longer than {exec_timeout} seconds"
        except Exception as e:
            return "", f"Execution error: {str(e)}"


def execute_python_code(code: str, timeout: int = 10, enable_security_check: bool = True) -> Tuple[str, str]:
    """
    Execute Python code safely.
    
    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds
        enable_security_check: Whether to check for unsafe operations
        
    Returns:
        Tuple of (output, error)
    """
    compiler = PythonCodeCompiler(timeout=timeout, enable_security_check=enable_security_check)
    return compiler.execute(code)
