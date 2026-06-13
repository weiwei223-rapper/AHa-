from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


LEETCODE_DATASET_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "LeetCodeDataset-v0.3.1-train.jsonl.gz"
)
CURATED_TEMPLATES_PATH = Path(__file__).resolve().parent / "data" / "question_templates.jsonl"
TOP_K = 4
STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "that", "this", "your", "have",
    "will", "about", "they", "them", "then", "here", "there", "would", "could",
    "should", "been", "being", "when", "where", "which", "while", "just", "than",
    "also", "only", "some", "more", "most", "very", "much", "now", "need", "want",
    "like", "video", "python",
}


@dataclass
class QuestionTemplate:
    template_id: str
    source: str
    title: str
    difficulty: str
    tags: list[str]
    pattern: str
    starter_code: str
    answer_shape: str
    test_case_examples: list[str]
    description: str


def _tokenize(text: str) -> set[str]:
    # 支援英文字母與中文字符
    terms = re.findall(r"[A-Za-z0-9_']{2,}|[\u4e00-\u9fa5]", text.lower())
    return {term for term in terms if term not in STOPWORDS}


def _template_from_curated_item(item: dict) -> QuestionTemplate:
    return QuestionTemplate(
        template_id=str(item.get("template_id", "")).strip(),
        source=str(item.get("source", "curated")).strip() or "curated",
        title=str(item.get("title", "Untitled template")).strip() or "Untitled template",
        difficulty=str(item.get("difficulty", "unknown")).strip() or "unknown",
        tags=[str(tag) for tag in item.get("tags", []) if str(tag).strip()],
        pattern=str(item.get("pattern", "")).strip(),
        starter_code=str(item.get("starter_code", "")).rstrip(),
        answer_shape=str(item.get("answer_shape", "")).strip(),
        test_case_examples=[str(case).strip() for case in item.get("test_case_examples", []) if str(case).strip()],
        description=str(item.get("description", "")).strip(),
    )


def _load_curated_templates() -> list[QuestionTemplate]:
    if not CURATED_TEMPLATES_PATH.exists():
        return []

    templates: list[QuestionTemplate] = []
    with CURATED_TEMPLATES_PATH.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                template = _template_from_curated_item(json.loads(stripped))
            except json.JSONDecodeError as exc:
                print(f"Skipping malformed template line {line_number}: {exc}")
                continue
            if template.template_id and template.starter_code:
                templates.append(template)
    return templates


def _load_leetcode_templates() -> list[QuestionTemplate]:
    if not LEETCODE_DATASET_PATH.exists():
        return []

    templates: list[QuestionTemplate] = []
    with gzip.open(LEETCODE_DATASET_PATH, "rt", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            input_output = item.get("input_output") or []
            example_tests = []
            for sample in input_output[:2]:
                raw_input = str(sample.get("input", "")).strip()
                raw_output = str(sample.get("output", "")).strip()
                if raw_input and raw_output:
                    example_tests.append(f"# input: {raw_input} -> output: {raw_output}")

            templates.append(
                QuestionTemplate(
                    template_id=f"leetcode_{item['task_id']}",
                    source="LeetCodeDataset",
                    title=str(item["task_id"]),
                    difficulty=str(item.get("difficulty", "unknown")),
                    tags=[str(tag) for tag in item.get("tags", [])],
                    pattern="Function-oriented coding task derived from a LeetCode problem skeleton.",
                    starter_code=str(item.get("starter_code", "")).rstrip(),
                    answer_shape=f"fill part of solution for entry point {item.get('entry_point', 'solve')}",
                    test_case_examples=example_tests,
                    description=str(item.get("problem_description", ""))[:500],
                )
            )
    return templates


@lru_cache(maxsize=1)
def load_templates() -> list[QuestionTemplate]:
    return [*_load_curated_templates(), *_load_leetcode_templates()]


def retrieve_templates(title: str, topics: list[str], transcript_excerpt: str, top_k: int = TOP_K) -> list[QuestionTemplate]:
    templates = load_templates()
    if not templates:
        return []

    query_terms = _tokenize(" ".join([title, *topics, transcript_excerpt]))
    ranked: list[tuple[int, QuestionTemplate]] = []
    for template in templates:
        template_terms = _tokenize(
            " ".join(
                [
                    template.title,
                    template.description,
                    template.pattern,
                    template.answer_shape,
                    " ".join(template.tags),
                    " ".join(template.test_case_examples),
                ]
            )
        )
        score = len(query_terms & template_terms) + 1
        ranked.append((score, template))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [template for score, template in ranked[:top_k] if score > 0] or [template for _, template in ranked[:top_k]]


def format_templates_for_prompt(templates: list[QuestionTemplate]) -> str:
    if not templates:
        return "No reference templates found."

    blocks: list[str] = []
    for index, template in enumerate(templates, start=1):
        blocks.append(
            "\n".join(
                [
                    f"Template {index}",
                    f"Source: {template.source}",
                    f"Title: {template.title}",
                    f"Difficulty: {template.difficulty}",
                    f"Tags: {', '.join(template.tags)}",
                    f"Pattern: {template.pattern}",
                    f"Starter Code: {template.starter_code}",
                    f"Answer Shape: {template.answer_shape}",
                    f"Example Tests: {' | '.join(template.test_case_examples)}",
                    f"Description: {template.description}",
                ]
            )
        )
    return "\n\n".join(blocks)
