#!/usr/bin/env python3
"""
Demonstration of improved Python code compiler features.
Run this script to see all the improvements in action.
"""

import json
from code_compiler import execute_python_code, PythonCodeCompiler


def demo_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def show_result(code: str, output: str, error: str):
    """Display code, output, and error in a formatted way."""
    print(f"\nCode:\n{code}")
    print(f"\nOutput:\n{output if output else '(empty)'}")
    print(f"\nError:\n{error if error else '(none)'}")


def main():
    """Run all demonstrations."""
    
    # Demo 1: Basic Compilation
    demo_header("1. BASIC PYTHON EXECUTION")
    output, error = execute_python_code('print("Hello, World!")')
    show_result('print("Hello, World!")', output, error)
    
    # Demo 2: Mathematical Operations
    demo_header("2. MATHEMATICAL OPERATIONS")
    code = """
# Calculate sum of squares
numbers = [1, 2, 3, 4, 5]
result = sum(x**2 for x in numbers)
print(f"Sum of squares: {result}")
"""
    output, error = execute_python_code(code)
    show_result(code, output, error)
    
    # Demo 3: Syntax Error Detection
    demo_header("3. SYNTAX ERROR DETECTION")
    code = 'print("unterminated string'
    output, error = execute_python_code(code)
    show_result(code, output, error)
    
    # Demo 4: Runtime Error Handling
    demo_header("4. RUNTIME ERROR HANDLING")
    code = """
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Caught: Division by zero")
"""
    output, error = execute_python_code(code)
    show_result(code, output, error)
    
    # Demo 5: Function Definition
    demo_header("5. FUNCTION DEFINITION AND USAGE")
    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(f"5! = {factorial(5)}")
print(f"10! = {factorial(10)}")
"""
    output, error = execute_python_code(code)
    show_result(code, output, error)
    
    # Demo 6: List Comprehension
    demo_header("6. LIST COMPREHENSION AND DATA STRUCTURES")
    code = """
# Generate and process data
data = [i**2 for i in range(1, 6)]
print(f"Squares: {data}")

# Dictionary operations
fruits = {'apple': 5, 'banana': 3, 'orange': 7}
print(f"Total fruits: {sum(fruits.values())}")
print(f"Sorted by count: {sorted(fruits.items(), key=lambda x: x[1], reverse=True)}")
"""
    output, error = execute_python_code(code)
    show_result(code, output, error)
    
    # Demo 7: Complex Logic
    demo_header("7. COMPLEX LOGIC WITH LOOPS")
    code = """
# Prime number finder
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

primes = [n for n in range(2, 30) if is_prime(n)]
print(f"Primes less than 30: {primes}")
print(f"Count: {len(primes)}")
"""
    output, error = execute_python_code(code)
    show_result(code, output, error)
    
    # Demo 8: Security - Blocking unsafe operations
    demo_header("8. SECURITY FEATURE: BLOCKING UNSAFE OPERATIONS")
    demo_unsafe_operations()
    
    # Demo 9: Performance - Output truncation
    demo_header("9. OUTPUT TRUNCATION FOR LARGE OUTPUTS")
    code = 'print("x" * 120000)'
    output, error = execute_python_code(code)
    print(f"\nCode: print('x' * 120000)")
    print(f"\nOutput length: {len(output)} characters")
    print(f"Output preview: {output[:100]}...")
    if "truncated" in output.lower():
        print("✓ Large output properly truncated")
    
    # Demo 10: Custom timeout
    demo_header("10. TIMEOUT HANDLING")
    compiler = PythonCodeCompiler(timeout=2)
    code = """
import time
print("Starting long operation...")
time.sleep(5)
print("This won't print")
"""
    output, error = compiler.execute(code)
    show_result(code, output, error)
    
    # Summary
    demo_header("SUMMARY OF IMPROVEMENTS")
    summary = """
✓ Syntax validation before execution
✓ Detailed error messages with line numbers
✓ Safe execution with security checks
✓ Timeout protection (default 10 seconds)
✓ Output size limits (100KB max)
✓ Unsafe operation detection
✓ Runtime error capture
✓ Support for complex Python features
  - Functions, classes, loops
  - List/dict comprehensions
  - Exception handling
  - Standard library (limited)
"""
    print(summary)


def demo_unsafe_operations():
    """Demonstrate security features."""
    unsafe_operations = [
        ('exec("print(1)")', 'exec()'),
        ('eval("1+1")', 'eval()'),
        ('__import__("os")', '__import__()'),
        ('compile("1+1", "<string>", "eval")', 'compile()'),
        ('open("/etc/passwd")', 'open()'),
    ]
    
    for code, name in unsafe_operations:
        output, error = execute_python_code(code)
        status = "✓ BLOCKED" if "Unsafe" in error else "⚠ Executed"
        print(f"\n{status}: {name}")
        if error:
            print(f"  Error: {error.split(chr(10))[0]}")


if __name__ == "__main__":
    main()
    print("\n" + "=" * 70)
    print("  Demonstration Complete!")
    print("=" * 70 + "\n")
