
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
import code_compiler

def test_compiler():
    code = "print('Hello World')"
    print(f"Testing code: {code}")
    out, err = code_compiler.execute_python_code(code, timeout=5)
    print(f"STDOUT: {out}")
    print(f"STDERR: {err}")
    if "Hello World" in out:
        print("RESULT: SUCCESS")
    else:
        print("RESULT: FAILED")

if __name__ == "__main__":
    test_compiler()
