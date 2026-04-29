# Python 編譯器 - 快速參考指南

## 🚀 快速開始

### 安裝
```bash
# 無需額外安裝，使用現有依賴即可
cd backend
python3 -c "from code_compiler import execute_python_code; print('✓ Ready')"
```

### 基本使用
```python
from code_compiler import execute_python_code

# 執行代碼
output, error = execute_python_code('print("Hello")')
print(output)  # "Hello\n"
print(error)   # ""
```

---

## 📋 API 端點

### POST /api/execute-code

**請求:**
```json
{
  "code": "print(2 + 2)"
}
```

**響應:**
```json
{
  "output": "4\n",
  "error": ""
}
```

---

## ✅ 支持的功能

```python
# ✓ 基本操作
print("Hello")
result = 2 + 2

# ✓ 數據結構
lists = [1, 2, 3]
dicts = {"key": "value"}
tuples = (1, 2, 3)

# ✓ 控制流
if x > 0:
    print("positive")
for i in range(10):
    print(i)

# ✓ 函數
def add(a, b):
    return a + b

# ✓ 類
class MyClass:
    def __init__(self):
        pass

# ✓ 列表推導
squares = [x**2 for x in range(10)]

# ✓ 異常處理
try:
    x = 1/0
except ZeroDivisionError:
    print("Error caught")
```

---

## ❌ 被禁用的功能

```python
# ✗ 動態執行
exec("code")        # ❌ 禁用
eval("expression")  # ❌ 禁用
compile(...)        # ❌ 禁用

# ✗ 導入控制
__import__("os")    # ❌ 禁用

# ✗ 文件/系統
open("file")        # ❌ 禁用
os.system("cmd")    # ❌ 禁用

# ✗ 動態屬性
getattr(obj, "x")   # ❌ 禁用
setattr(obj, "x")   # ❌ 禁用
delattr(obj, "x")   # ❌ 禁用
```

---

## 🔧 配置選項

### PythonCodeCompiler 類

```python
from code_compiler import PythonCodeCompiler

# 自定義超時 (秒)
compiler = PythonCodeCompiler(timeout=30)

# 禁用安全檢查 (不推薦)
compiler = PythonCodeCompiler(enable_security_check=False)

# 編譯檢查
is_valid, error = compiler.compile(code)

# 執行代碼
output, error = compiler.execute(code, timeout=15)
```

---

## 📊 限制和限制

| 項目 | 限制 | 說明 |
|-----|------|------|
| 代碼大小 | 1 MB | 防止超大文件 |
| 代碼行數 | 10,000 行 | 防止無限代碼 |
| 執行超時 | 10 秒 (可配置) | 防止無限循環 |
| 輸出大小 | 100 KB | 防止內存溢出 |
| 安全檢查 | 9 項 | 阻止危險操作 |

---

## 🐛 常見錯誤

### Syntax Error
```python
# ❌ 問題
code = 'print("incomplete'

# ✓ 修正
code = 'print("complete")'
```

### Unsafe operation
```python
# ❌ 問題
code = 'exec("print(1)")'

# ✓ 修正
code = 'print(1)'
```

### Timeout
```python
# ❌ 問題
code = """
import time
time.sleep(15)  # 超過 10 秒限制
"""

# ✓ 修正
code = """
import time
time.sleep(5)  # 在限制內
"""
```

### Output truncation
```python
# ❌ 問題
code = 'print("x" * 200000)'  # 超過 100KB

# ✓ 修正 (分次輸出)
code = """
for i in range(10):
    print("x" * 1000)
"""
```

---

## 📈 性能提示

### 快速執行
```python
# ✓ 快 (~50ms)
print(sum(range(100)))
```

### 中等執行
```python
# ≈ (~200ms)
def fibonacci(n):
    return fibonacci(n-1) + fibonacci(n-2) if n > 1 else n
```

### 優化建議
```python
# ✗ 慢 - 重複計算
result = [fibonacci(i) for i in range(50)]

# ✓ 快 - 使用緩存
def fib_memo(n, cache={}):
    if n in cache: return cache[n]
    cache[n] = fib_memo(n-1) + fib_memo(n-2) if n > 1 else n
    return cache[n]
```

---

## 🔒 安全最佳實踐

### 禁止的操作列表

| 函數 | 原因 | 替代方案 |
|-----|------|--------|
| `open()` | 文件訪問 | 使用字符串變數 |
| `exec()` | 代碼注入 | 使用受控函數 |
| `eval()` | 表達式注入 | 使用 ast.literal_eval() |
| `__import__()` | 模塊注入 | 使用預加載的模塊 |
| `getattr()` | 動態訪問 | 使用字典或類屬性 |

---

## 🧪 測試你的代碼

### 運行測試套件
```bash
cd backend
python -m pytest test_compiler.py -v
```

### 運行演示
```bash
cd backend
python3 demo_compiler.py
```

---

## 📚 詳細文檔

| 文檔 | 內容 |
|-----|------|
| `COMPILER_DOCUMENTATION.md` | 完整 API 文檔 |
| `IMPROVEMENTS_SUMMARY.md` | 改進詳情和對比 |
| `COMPLETION_REPORT.md` | 完成報告 |
| `code_compiler.py` | 源代碼 (含註釋) |

---

## 💡 實用示例

### 計算平方和
```python
code = """
numbers = [1, 2, 3, 4, 5]
result = sum(x**2 for x in numbers)
print(f"Sum of squares: {result}")
"""
# 輸出: "Sum of squares: 55\n"
```

### 質數查找
```python
code = """
def is_prime(n):
    return all(n % i != 0 for i in range(2, int(n**0.5) + 1)) if n > 1 else False

primes = [n for n in range(2, 30) if is_prime(n)]
print(primes)
"""
# 輸出: "[2, 3, 5, 7, 11, 13, 17, 19, 23, 29]\n"
```

### 數據統計
```python
code = """
data = [10, 20, 30, 40, 50]
avg = sum(data) / len(data)
print(f"Average: {avg}")
"""
# 輸出: "Average: 30.0\n"
```

---

## 🆘 故障排除

### 問題: "Syntax Error"
**解決:** 檢查引號、括號是否匹配

### 問題: "Unsafe operation"
**解決:** 避免使用 exec, eval, open 等

### 問題: "Execution timeout"
**解決:** 優化代碼或增加超時時間

### 問題: "Output truncated"
**解決:** 分多次輸出或減少輸出量

---

## 📞 支持

- 📖 查看文檔: `COMPILER_DOCUMENTATION.md`
- 🧪 運行演示: `python3 demo_compiler.py`
- ✅ 運行測試: `python -m pytest test_compiler.py -v`

---

**版本:** 2.0  
**最後更新:** 2026-04-29  
**狀態:** ✅ 就緒使用
