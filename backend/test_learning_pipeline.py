from learning_pipeline import _normalize_question


def test_normalize_coding_implementation_keeps_editable_skeleton():
    item = {
        "question": "找因數\n\n請完成函數\n\n提示：使用 for 迴圈",
        "correct_answer": "def find_factor(n):\n    return [i for i in range(1, n + 1) if n % i == 0]",
        "question_type": "coding-implementation",
        "starter_code": "def find_factor(n):\n    # TODO\n    # 回傳 n 的因數\n    pass",
        "test_cases": [
            "assert find_factor(12) == [1, 2, 3, 4, 6, 12]",
            "print(find_factor(12))",
        ],
    }

    question = _normalize_question(item)

    assert question.question_type == "coding-implementation"
    assert question.starter_code == item["starter_code"]
    assert "___" not in question.starter_code
    assert question.test_cases == ["assert find_factor(12) == [1, 2, 3, 4, 6, 12]"]
